import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pymol_chat.api_client import OpenAIHTTPClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class APIClientTests(unittest.TestCase):
    @patch("pymol_chat.api_client.urllib.request.urlopen")
    def test_response_is_exposed_with_sdk_like_attributes(self, urlopen):
        urlopen.return_value = FakeResponse({
            "id": "resp-1",
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "Done."}],
            }],
        })
        result = OpenAIHTTPClient("test-key").responses.create(model="test", input="hello")
        self.assertEqual(result.id, "resp-1")
        self.assertEqual(result.output_text, "Done.")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(json.loads(request.data), {"model": "test", "input": "hello"})

    @patch("pymol_chat.api_client.urllib.request.urlopen")
    def test_transcription_uses_multipart_audio(self, urlopen):
        urlopen.return_value = FakeResponse({"text": "show the ligand"})
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "request.wav"
            audio.write_bytes(b"RIFFtest-audio")
            text = OpenAIHTTPClient("test-key").transcribe(audio, "transcribe-model")
        self.assertEqual(text, "show the ligand")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/audio/transcriptions")
        self.assertIn(b"transcribe-model", request.data)
        self.assertIn(b"RIFFtest-audio", request.data)
