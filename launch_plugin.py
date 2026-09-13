"""Development launcher loaded by PyMOL with `pymol -r launch_plugin.py`."""

from pymol.Qt import QtCore

import pymol_chat

pymol_chat.__init_plugin__()
QtCore.QTimer.singleShot(800, pymol_chat.show)
