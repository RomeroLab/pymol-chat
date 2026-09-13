"""Constrained Python execution with direct access to the live pymol.cmd API."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import math
import statistics
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymol import cmd

from .config import CAPTURE_DIR, DOWNLOAD_DIR, ensure_app_dirs


class UnsafeCodeError(ValueError):
    pass


class ExecutionTimedOut(TimeoutError):
    pass


class SafetyVisitor(ast.NodeVisitor):
    """Block OS access while leaving the PyMOL API broadly available."""

    ALLOWED_IMPORTS = {"pymol", "math", "statistics", "collections", "itertools"}
    BLOCKED_CALLS = {"open", "eval", "exec", "compile", "input", "__import__"}
    # These pymol.cmd entry points can escape into files, the network, or the
    # PyMOL command language (which itself exposes OS commands). File loading is
    # instead handled by the user-facing, extension-checked file picker.
    BLOCKED_CMD_METHODS = {
        "cd", "do", "load", "log", "mpng", "png", "pwd", "run",
        "save", "system",
    }

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root == "pymol" or root not in self.ALLOWED_IMPORTS:
                raise UnsafeCodeError(f"Import not allowed: {alias.name}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module or node.module.split(".", 1)[0] not in self.ALLOWED_IMPORTS:
            raise UnsafeCodeError(f"Import not allowed: {node.module}")
        if node.module == "pymol" and any(alias.name not in {"cmd", "stored"} for alias in node.names):
            raise UnsafeCodeError("Only cmd and stored may be imported from pymol")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            raise UnsafeCodeError("Dunder attribute access is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__") or node.id in self.BLOCKED_CALLS:
            raise UnsafeCodeError(f"Call not allowed: {node.id}")

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "cmd"
            and function.attr in self.BLOCKED_CMD_METHODS
        ):
            raise UnsafeCodeError(f"PyMOL method not available to the model: cmd.{function.attr}")
        self.generic_visit(node)


class ImportNormalizer(ast.NodeTransformer):
    """Make `from pymol import cmd` refer to the constrained live proxy."""

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module != "pymol":
            return node
        replacement = []
        stored_aliases = [alias for alias in node.names if alias.name == "stored"]
        if stored_aliases:
            replacement.append(ast.ImportFrom(module="pymol", names=stored_aliases, level=0))
        for alias in node.names:
            if alias.name == "cmd" and alias.asname and alias.asname != "cmd":
                replacement.append(
                    ast.Assign(targets=[ast.Name(id=alias.asname, ctx=ast.Store())], value=ast.Name(id="cmd", ctx=ast.Load()))
                )
        return replacement or ast.Pass()


class CmdProxy:
    """Expose the real API while denying its filesystem/network escape hatches."""

    def __getattr__(self, name: str):
        if name.startswith("_") or name in SafetyVisitor.BLOCKED_CMD_METHODS:
            raise UnsafeCodeError(f"PyMOL method not available to the model: cmd.{name}")
        if name == "fetch":
            return self._safe_fetch
        return getattr(cmd, name)

    @staticmethod
    def _safe_fetch(*args, **kwargs):
        """Fetch public structure IDs into the private application directory."""
        if len(args) > 9:
            raise UnsafeCodeError("cmd.fetch path/file arguments are managed by the application")
        ensure_app_dirs()
        positional = list(args)
        if len(positional) == 9:
            positional[8] = 0
            kwargs.pop("async_", None)
            kwargs.pop("async", None)
        else:
            kwargs.pop("async", None)
            kwargs["async_"] = 0
        kwargs.pop("file", None)
        kwargs["path"] = str(DOWNLOAD_DIR)
        return cmd.fetch(*positional, **kwargs)


@dataclass
class ExecutionResult:
    ok: bool
    output: str
    error: str = ""

    def as_json(self) -> str:
        return json.dumps({"ok": self.ok, "output": self.output, "error": self.error})


class PyMOLExecutor:
    def __init__(self) -> None:
        self.locals: dict[str, Any] = {}
        self.safe_cmd = CmdProxy()

    def execute(self, code: str) -> ExecutionResult:
        if len(code) > 20_000:
            return ExecutionResult(False, "", "Code exceeds the 20,000 character limit")
        stream = io.StringIO()
        try:
            tree = ast.parse(code, mode="exec")
            SafetyVisitor().visit(tree)
            tree = ast.fix_missing_locations(ImportNormalizer().visit(tree))
            compiled = compile(tree, "<pymol-agent>", "exec")
            safe_builtins = {
                "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
                "enumerate": enumerate, "float": float, "int": int, "len": len,
                "list": list, "max": max, "min": min, "next": next, "print": print,
                "range": range, "repr": repr, "reversed": reversed, "round": round,
                "set": set, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
                "zip": zip, "Exception": Exception, "ValueError": ValueError,
                "RuntimeError": RuntimeError, "__import__": __import__,
            }
            namespace = {
                "__builtins__": safe_builtins,
                "cmd": self.safe_cmd,
                "math": math,
                "statistics": statistics,
                **self.locals,
            }
            deadline = time.monotonic() + 20.0

            def timeout_trace(_frame, _event, _arg):
                if time.monotonic() > deadline:
                    raise ExecutionTimedOut("Python execution exceeded 20 seconds")
                return timeout_trace

            previous_trace = sys.gettrace()
            try:
                sys.settrace(timeout_trace)
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    exec(compiled, namespace, namespace)
            finally:
                sys.settrace(previous_trace)
            self.locals = {
                key: value for key, value in namespace.items()
                if not key.startswith("__") and key not in {"cmd", "math", "statistics"}
            }
            output = stream.getvalue().strip()
            return ExecutionResult(True, output or "Executed successfully.")
        except Exception as exc:
            message = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            captured = stream.getvalue().strip()
            return ExecutionResult(False, captured, message)

    def scene_summary(self) -> dict[str, Any]:
        objects = cmd.get_names("objects")
        selections = cmd.get_names("selections")
        object_details = []
        for name in objects[:50]:
            try:
                chains = cmd.get_chains(name)
                atoms = cmd.count_atoms(name)
                object_details.append({"name": name, "chains": chains, "atoms": atoms})
            except Exception as exc:
                object_details.append({"name": name, "error": str(exc)})
        return {
            "objects": object_details,
            "selections": selections[:50],
            "enabled": cmd.get_names("all", enabled_only=1),
        }

    def capture_viewport(self) -> tuple[Path, str]:
        ensure_app_dirs()
        path = CAPTURE_DIR / "viewport.png"
        cmd.png(str(path), width=1200, height=900, dpi=150, ray=0, quiet=1)
        if not path.is_file():
            raise RuntimeError("PyMOL did not create the viewport capture")
        import base64
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return path, f"data:image/png;base64,{encoded}"
