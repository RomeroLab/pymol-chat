"""Stream OpenAI's Marin voice without blocking PyMOL."""
import importlib
import json
import re
import threading
import urllib.error
import urllib.request
from pymol.Qt import QtCore
from .config import api_key


def spoken_text(text):
    text = re.sub(r"```.*?```", "", str(text), flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    return " ".join(re.sub(r"[*`#_]", "", text).split())


def speech_payload(text):
    return {
        "model": "gpt-4o-mini-tts", "voice": "marin", "input": text,
        "response_format": "pcm",
        "instructions": "Speak like a friendly colleague explaining what just changed in a molecule. "
        "Use a relaxed, natural conversational tone and a comfortably brisk pace. "
        "Avoid a theatrical or announcer delivery. Read the supplied words faithfully.",
    }


class SpeechSignals(QtCore.QObject):
    chunk = QtCore.pyqtSignal(int, bytes)
    failed = QtCore.pyqtSignal(int, str)
    done = QtCore.pyqtSignal(int)


class SpeechRequest(QtCore.QRunnable):
    def __init__(self, generation, text, key):
        super().__init__()
        self.generation, self.text, self.key = generation, text, key
        self.cancelled = threading.Event()
        self.signals = SpeechSignals()

    def run(self):
        try:
            if self.cancelled.is_set():
                return
            request = urllib.request.Request(
                "https://api.openai.com/v1/audio/speech",
                data=json.dumps(speech_payload(self.text)).encode("utf-8"),
                headers={"Authorization": "Bearer " + self.key,
                         "Content-Type": "application/json", "Accept": "application/octet-stream"},
                method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                while not self.cancelled.is_set():
                    chunk = response.read1(8192)
                    if not chunk:
                        break
                    if not self.cancelled.is_set():
                        self.signals.chunk.emit(self.generation, chunk)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                self._error("OpenAI rejected the API key for speech. Update it in ⋯ → API Key Settings….")
            else:
                self._error("OpenAI speech request failed (HTTP %s)." % exc.code)
        except Exception:
            self._error("Could not stream Marin's voice. Check your connection.")
        finally:
            self.key = ""
            self.signals.done.emit(self.generation)

    def _error(self, message):
        if not self.cancelled.is_set():
            self.signals.failed.emit(self.generation, message)


class SpeechPlayer(QtCore.QObject):
    error = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.audio_module = importlib.import_module(QtCore.__name__.split(".")[0] + ".QtMultimedia")
        except ImportError:
            self.audio_module = None
        self.generation = 0
        self.jobs = {}
        self.audio = self.sink = None
        self.pending = bytearray()
        self.finished = False
        self.received = 0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._pump)
        app = QtCore.QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop)

    @property
    def available(self):
        return self.audio_module is not None

    def stop(self):
        self.generation += 1
        for job in self.jobs.values():
            job.cancelled.set()
        self.timer.stop()
        self.pending.clear()
        if self.audio is not None:
            self.audio.stop()
            self.audio.deleteLater()
        self.audio = self.sink = None

    def speak(self, text):
        self.stop()
        text = spoken_text(text)
        if not text:
            return
        key = api_key()
        if not self.available or not key:
            self.error.emit("Marin needs an API key and Qt audio support. The reply is shown in chat.")
            return
        if len(text) > 4096:
            self.error.emit("This reply is too long to speak. Please read it in chat.")
            return
        audio = self.audio_module
        fmt = audio.QAudioFormat()
        fmt.setSampleRate(24000)
        fmt.setChannelCount(1)
        fmt.setSampleSize(16)
        fmt.setCodec("audio/pcm")
        fmt.setByteOrder(audio.QAudioFormat.LittleEndian)
        fmt.setSampleType(audio.QAudioFormat.SignedInt)
        device = audio.QAudioDeviceInfo.defaultOutputDevice()
        if not device.isFormatSupported(fmt):
            self.error.emit("Your audio output does not support Marin playback. The reply is shown in chat.")
            return
        self.audio = audio.QAudioOutput(device, fmt, self)
        self.audio.setBufferSize(16384)
        self.finished = False
        self.received = 0
        job = SpeechRequest(self.generation, text, key)
        self.jobs[self.generation] = job
        job.signals.chunk.connect(self._chunk)
        job.signals.failed.connect(self._failed)
        job.signals.done.connect(self._done)
        QtCore.QThreadPool.globalInstance().start(job)

    def _chunk(self, generation, data):
        if generation != self.generation:
            return
        self.received += len(data)
        self.pending.extend(data)
        self._pump()

    def _done(self, generation):
        self.jobs.pop(generation, None)
        if generation == self.generation:
            self.finished = True
            if not self.received:
                self._failed(generation, "Marin returned no audio.")
            elif self.received % 2:
                self._failed(generation, "Marin's audio stream was incomplete.")
            else:
                self._pump()

    def _failed(self, generation, message):
        if generation == self.generation:
            self.stop()
            self.error.emit(message + " The reply is still shown in chat.")

    def _pump(self):
        if self.audio is None:
            return
        # Buffer 300 ms of 24 kHz, mono, 16-bit PCM for a steadier start.
        if self.sink is None:
            if len(self.pending) < 14400 and not self.finished:
                return
            self.sink = self.audio.start()
            if self.sink is None:
                self._failed(self.generation, "Could not open the audio output.")
                return
            self.timer.start()
        count = min(len(self.pending), self.audio.bytesFree()) // 2 * 2
        if count:
            written = self.sink.write(bytes(self.pending[:count]))
            if written < 0:
                self._failed(self.generation, "Audio playback failed.")
                return
            del self.pending[:written]
        state = self.audio.state()
        if state == self.audio_module.QAudio.StoppedState:
            self._failed(self.generation, "Audio output stopped unexpectedly.")
        elif self.finished and not self.pending and state == self.audio_module.QAudio.IdleState:
            self.stop()
