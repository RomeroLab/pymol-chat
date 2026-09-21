"""Key precedence tests using fake credentials only."""

import os
import unittest
from unittest.mock import patch

from pymol_chat.config import api_key


class ConfigTests(unittest.TestCase):
    def resolve(self, stored, configured):
        with (
            patch("pymol_chat.config.load_local_env"),
            patch("pymol_chat.config.os.name", "posix"),
            patch("pymol_chat.keychain.read_api_key", return_value=stored),
            patch.dict(os.environ, {"OPENAI_API_KEY": configured}),
        ):
            return api_key()

    def test_saved_key_wins_over_stale_configuration_after_restart(self):
        for _ in range(2):
            self.assertEqual(self.resolve("new-saved-test-key", "expired-test-key"), "new-saved-test-key")

    def test_configuration_is_fallback_without_saved_key(self):
        self.assertEqual(self.resolve("", " fallback-test-key "), "fallback-test-key")

    def test_no_key_returns_empty(self):
        self.assertEqual(self.resolve("", ""), "")
