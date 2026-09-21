import unittest
from unittest.mock import patch, MagicMock

from pymol.Qt import QtWidgets
from pymol_chat.speech import spoken_text, speech_payload, SpeechRequest, SpeechPlayer
from pymol_chat.ui import PyMOLChatDock


class SpeechTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_skips_code_and_formatting(self):
        self.assertEqual(spoken_text("I've highlighted **heme**.\n```python\ncmd.show('sticks')\n```"),
                         "I've highlighted heme.")

    def test_marin_stream_request_and_cancellation(self):
        import json
        job = SpeechRequest(3, "I've colored the chains.", "test-key")
        chunks = []
        def received(generation, data):
            chunks.append((generation, data))
            job.cancelled.set()
        job.signals.chunk.connect(received)
        response = MagicMock()
        response.read1.side_effect = [b"\x00\x01", b"more", b""]
        with patch("pymol_chat.speech.urllib.request.urlopen") as request:
            request.return_value.__enter__.return_value = response
            job.run()
            payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["voice"], "marin")
        self.assertEqual(payload["model"], "gpt-4o-mini-tts")
        self.assertEqual(payload["response_format"], "pcm")
        self.assertEqual(chunks, [(3, b"\x00\x01")])
        self.assertEqual(job.key, "")

    def test_cancelled_audio_cannot_restart_playback(self):
        player = SpeechPlayer()
        old_generation = player.generation
        player.stop()
        player._chunk(old_generation, b"old audio")
        player._done(old_generation)
        self.assertFalse(player.pending)
        self.assertIsNone(player.audio)

    def test_playback_starts_before_network_finishes_and_drains(self):
        player = SpeechPlayer()
        output = MagicMock()
        sink = MagicMock()
        sink.write.side_effect = lambda data: len(data)
        output.start.return_value = sink
        output.bytesFree.return_value = 20000
        output.state.return_value = player.audio_module.QAudio.ActiveState
        player.audio = output
        generation = player.generation
        player._chunk(generation, b"\0" * 14398)
        output.start.assert_not_called()
        player._chunk(generation, b"\0" * 2)
        self.assertFalse(player.finished)
        output.start.assert_called_once()
        sink.write.assert_called_once()
        player._done(generation)
        output.stop.assert_not_called()
        output.state.return_value = player.audio_module.QAudio.IdleState
        player._pump()
        output.stop.assert_called_once()

    def test_short_finished_reply_does_not_wait_for_full_buffer(self):
        player = SpeechPlayer()
        output = MagicMock()
        sink = MagicMock()
        sink.write.side_effect = lambda data: len(data)
        output.start.return_value = sink
        output.bytesFree.return_value = 20000
        output.state.return_value = player.audio_module.QAudio.ActiveState
        player.audio = output
        generation = player.generation
        player._chunk(generation, b"\0" * 4000)
        output.start.assert_not_called()
        player._done(generation)
        output.start.assert_called_once()
        sink.write.assert_called_once_with(b"\0" * 4000)
        player.stop()

    def test_reply_and_microphone_playback(self):
        dock = PyMOLChatDock()
        try:
            dock.show()
            dock.speech_action.setChecked(True)
            with patch.object(dock.speech, "speak") as speak:
                dock._answer_received("I've colored the chains.")
                speak.assert_called_once_with("I've colored the chains.")
                dock.speech_action.setChecked(False)
                dock._answer_received("I've hidden the water.")
                self.assertEqual(speak.call_count, 1)
            with patch.object(dock, "_ensure_api_key", return_value=True), \
                    patch.object(dock.speech, "stop") as stop, \
                    patch.object(dock.voice, "toggle") as toggle:
                dock.toggle_recording()
                stop.assert_called_once()
                toggle.assert_called_once()
        finally:
            dock.speech_action.setChecked(True)
            dock.close()
