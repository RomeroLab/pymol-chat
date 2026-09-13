"""One-click macOS voice capture and OpenAI transcription."""

from __future__ import annotations

from pathlib import Path

from pymol.Qt import QtCore

from .api_client import OpenAIHTTPClient
from .config import APP_DIR, api_key, ensure_app_dirs, transcription_model


HELPER_EXECUTABLE = (
    Path(__file__).resolve().parents[1]
    / "voice_helper"
    / "PyMOLChatVoice.app"
    / "Contents"
    / "MacOS"
    / "PyMOLChatVoice"
)


class VoiceRecorder(QtCore.QObject):
    """Manage the privacy-declared native recorder helper."""

    state_changed = QtCore.pyqtSignal(bool)
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        ensure_app_dirs()
        self.path = APP_DIR / "voice-request.wav"
        self.process = QtCore.QProcess(self)
        self.process.finished.connect(self._process_finished)
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def toggle(self) -> None:
        if self.is_recording:
            self.process.write(b"stop\n")
        else:
            self.start()

    def start(self) -> None:
        if not HELPER_EXECUTABLE.is_file():
            raise RuntimeError(
                "The voice helper is not built. Quit PyMOL and run ./run.sh again."
            )
        if self.path.exists():
            self.path.unlink()
        self.process.setProgram(str(HELPER_EXECUTABLE))
        self.process.setArguments([str(self.path)])
        self.process.start()
        if not self.process.waitForStarted(3000):
            raise RuntimeError(self.process.errorString() or "Could not start voice recording")
        self._recording = True
        self.state_changed.emit(True)

    def _process_finished(self, exit_code, _exit_status) -> None:
        was_recording = self._recording
        self._recording = False
        if was_recording:
            self.state_changed.emit(False)

        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", "replace").strip()
        if exit_code == 0 and self.path.is_file() and self.path.stat().st_size > 44:
            self.finished.emit(self.path)
            return
        self.finished.emit(None)
        if stderr:
            self.error.emit(stderr)
        elif was_recording:
            self.error.emit("Voice recording ended before audio was captured.")


def transcribe(path: Path) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("An OpenAI API key is required. Open ⋯ → API Key Settings… to add one.")
    return OpenAIHTTPClient(key).transcribe(path, transcription_model())
