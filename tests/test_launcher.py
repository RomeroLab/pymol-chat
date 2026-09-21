"""Exercise the actual PyMOL run command from an unrelated directory."""

from pathlib import Path
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
assert Path(pymol_chat.__file__).resolve().parent == Path(sys.argv[1]).parent / 'pymol_chat'
"""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-I", "-c", script, str(launcher)],
                                    cwd=directory, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
