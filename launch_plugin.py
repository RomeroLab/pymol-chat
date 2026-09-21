"""Development launcher loaded by PyMOL with `pymol -r launch_plugin.py`."""

import sys

# Also protect the signed bundle when this file is loaded with PyMOL's run
# command, bypassing the native launcher's environment configuration.
sys.dont_write_bytecode = True

from pathlib import Path

# PyMOL's `run ..., main` supplies __script__, not the script's __file__.
# Add the adjacent package explicitly when launched outside this directory.
_launcher_path = globals().get("__script__") or __file__
_package_root = str(Path(_launcher_path).resolve().parent)
if _package_root not in sys.path:
    sys.path.insert(0, _package_root)

from pymol.Qt import QtCore

import pymol_chat

pymol_chat.__init_plugin__()
QtCore.QTimer.singleShot(800, pymol_chat.show)
