"""Tests runnable inside PyMOL's Python environment."""

import unittest
from pathlib import Path
from unittest.mock import patch

from pymol_chat.executor import PyMOLExecutor


class ExecutorTests(unittest.TestCase):
    def test_direct_cmd_execution(self):
        calls = []
        with patch("pymol_chat.executor.cmd.color", lambda color, selection: calls.append((color, selection))):
            result = PyMOLExecutor().execute("cmd.color('yellow', 'organic')")
        self.assertTrue(result.ok)
        self.assertEqual(calls, [("yellow", "organic")])

    def test_result_and_error_are_returned(self):
        executor = PyMOLExecutor()
        good = executor.execute("print(cmd.count_atoms('all'))")
        bad = executor.execute("cmd.this_command_does_not_exist()")
        self.assertTrue(good.ok and good.output)
        self.assertFalse(bad.ok)
        self.assertIn("AttributeError", bad.error)

    def test_os_access_is_rejected(self):
        result = PyMOLExecutor().execute("import os\nos.system('echo no')")
        self.assertFalse(result.ok)
        self.assertIn("Import not allowed", result.error)

    def test_pymol_command_language_escape_is_rejected(self):
        result = PyMOLExecutor().execute("cmd.do('system whoami')")
        self.assertFalse(result.ok)
        self.assertIn("cmd.do", result.error)

    def test_whitelisted_pymol_import_is_allowed(self):
        result = PyMOLExecutor().execute("from pymol import cmd\nprint(cmd.count_atoms('all'))")
        self.assertTrue(result.ok)

    def test_pymol_module_import_is_rejected(self):
        result = PyMOLExecutor().execute("import pymol")
        self.assertFalse(result.ok)

    def test_imported_cmd_alias_still_has_boundaries(self):
        result = PyMOLExecutor().execute("from pymol import cmd as c\nc.do('system whoami')")
        self.assertFalse(result.ok)
        self.assertIn("cmd.do", result.error)

    def test_fetch_is_allowed_but_forced_into_app_directory(self):
        calls = []

        def fake_fetch(*args, **kwargs):
            calls.append((args, kwargs))
            return "2hhb"

        with (
            patch("pymol_chat.executor.cmd.fetch", fake_fetch),
            patch("pymol_chat.executor.ensure_app_dirs"),
            patch("pymol_chat.executor.DOWNLOAD_DIR", Path("/private/app/downloads")),
        ):
            result = PyMOLExecutor().execute("print(cmd.fetch('2HHB'))")
        self.assertTrue(result.ok)
        self.assertEqual(calls[0][0], ("2HHB",))
        self.assertEqual(calls[0][1]["path"], "/private/app/downloads")
        self.assertEqual(calls[0][1]["async_"], 0)
