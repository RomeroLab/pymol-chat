"""Small, dependency-free configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path


APP_DIR = Path(os.environ.get("PYMOL_CHAT_WORKDIR", Path.home() / ".pymol-chat")).expanduser()
CAPTURE_DIR = APP_DIR / "captures"
DOWNLOAD_DIR = APP_DIR / "downloads"
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"


def ensure_app_dirs() -> None:
    APP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    CAPTURE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def load_local_env() -> None:
    """Load a nearby .env without requiring python-dotenv.

    Existing environment variables always win. Only simple KEY=VALUE lines are
    accepted; this intentionally does not evaluate shell syntax.
    """
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            if key.replace("_", "").isalnum():
                os.environ.setdefault(key, value)
        return


def api_key() -> str:
    load_local_env()
    environment_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if environment_key:
        return environment_key
    if os.name == "posix":
        from .keychain import read_api_key

        return read_api_key()
    return ""


def model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip()


def transcription_model() -> str:
    return os.environ.get("OPENAI_TRANSCRIBE_MODEL", DEFAULT_TRANSCRIBE_MODEL).strip()
