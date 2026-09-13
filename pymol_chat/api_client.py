"""Tiny dependency-free client for the OpenAI endpoints used by this plugin."""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path


API_ROOT = "https://api.openai.com/v1"


class APIError(RuntimeError):
    pass


class AttrDict(dict):
    """Dictionary with SDK-like attribute access for the agent loop."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _objects(value):
    if isinstance(value, dict):
        return AttrDict({key: _objects(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_objects(item) for item in value]
    return value


def _error_message(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", "replace"))
        return payload.get("error", {}).get("message") or str(exc)
    except Exception:
        return str(exc)


class OpenAIHTTPClient:
    def __init__(self, api_key: str, timeout: int = 120):
        self.api_key = api_key
        self.timeout = timeout
        # Preserve the small interface used by the official SDK so tests and
        # the agent loop remain simple (`client.responses.create(...)`).
        self.responses = self

    def _request(self, path: str, body: bytes, content_type: str):
        request = urllib.request.Request(
            API_ROOT + path,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": content_type,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "pymol-chat/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise APIError(_error_message(exc)) from exc
        except urllib.error.URLError as exc:
            raise APIError(f"Connection error: {exc.reason}") from exc

    def create(self, **kwargs):
        payload = self._request(
            "/responses",
            json.dumps(kwargs, separators=(",", ":")).encode("utf-8"),
            "application/json",
        )
        output_text = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text.append(content.get("text", ""))
        payload["output_text"] = "\n".join(output_text)
        return _objects(payload)

    def transcribe(self, path: Path, model: str) -> str:
        boundary = "----PyMOLChat" + uuid.uuid4().hex
        filename = path.name
        mime = mimetypes.guess_type(filename)[0] or "audio/wav"
        chunks = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{model}\r\n".encode(),
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n"
            ).encode(),
            path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode(),
        ]
        payload = self._request(
            "/audio/transcriptions",
            b"".join(chunks),
            f"multipart/form-data; boundary={boundary}",
        )
        return str(payload.get("text", "")).strip()
