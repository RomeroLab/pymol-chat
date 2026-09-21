"""Exercise the actual PyMOL run command from an unrelated directory."""

from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest


class LauncherTests(unittest.TestCase):
    def test_run_main_finds_adjacent_package(self):
        launcher = Path(__file__).resolve().parents[1] / "launch_plugin.py"
        script = """
import sys
from unittest.mock import patch
from pymol import cmd
from pymol.Qt import QtCore
with patch('pymol.plugins.addmenuitemqt'), patch.object(QtCore.QTimer, 'singleShot'):
    cmd.run(sys.argv[1], 'main')
import pymol_chat
from pathlib import Path
assert Path(pymol_chat.__file__).resolve().parent == Path(sys.argv[1]).resolve().parent / 'pymol_chat'
assert sys.dont_write_bytecode
"""
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'resources'
            package.mkdir()
            shutil.copy2(launcher, package / launcher.name)
            shutil.copytree(launcher.parent / 'pymol_chat', package / 'pymol_chat',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            result = subprocess.run([sys.executable, "-I", "-c", script, str(package / launcher.name)],
                                    cwd=directory, capture_output=True, text=True, timeout=30)
            self.assertEqual(list(package.rglob('*.pyc')), [])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_apps_declare_microphone_usage(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ('packaging/launcher/Info.plist',
                         'voice_helper/PyMOLChatVoice.app/Contents/Info.plist'):
            with self.subTest(plist=relative):
                with (root / relative).open('rb') as stream:
                    info = plistlib.load(stream)
                self.assertTrue(info.get('NSMicrophoneUsageDescription', '').strip())

    def test_native_launcher_disables_bytecode(self):
        source = Path(__file__).resolve().parents[1] / 'packaging/launcher/main.m'
        self.assertIn('environment[@"PYTHONDONTWRITEBYTECODE"] = @"1";', source.read_text())
