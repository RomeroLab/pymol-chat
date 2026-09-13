"""Store an API key in the macOS login Keychain."""

from __future__ import annotations

import getpass
import subprocess


SERVICE = "org.openai.pymol-chat"
ACCOUNT = getpass.getuser()
SECURITY = "/usr/bin/security"


def read_api_key() -> str:
    try:
        result = subprocess.run(
            [SECURITY, "find-generic-password", "-a", ACCOUNT, "-s", SERVICE, "-w"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def save_api_key(value: str) -> None:
    key = value.strip()
    if not key:
        raise ValueError("Enter an API key before saving.")
    try:
        result = subprocess.run(
            [
                SECURITY,
                "add-generic-password",
                "-U",
                "-a",
                ACCOUNT,
                "-s",
                SERVICE,
                "-w",
                key,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Could not save the API key in macOS Keychain.") from exc
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not save the API key in macOS Keychain.")


def delete_api_key() -> None:
    subprocess.run(
        [SECURITY, "delete-generic-password", "-a", ACCOUNT, "-s", SERVICE],
        check=False,
        capture_output=True,
        timeout=5,
    )
