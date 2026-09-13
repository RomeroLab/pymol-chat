import unittest

from pymol.Qt import QtWidgets

import pymol_chat
from pymol_chat.ui import PyMOLChatDock


class PluginWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_resolves_real_qt_window_without_using_pmgapp(self):
        window = QtWidgets.QMainWindow()
        window.pymolwidget = object()
        window.show()
        self.application.processEvents()
        try:
            self.assertIs(pymol_chat._qt_main_window(), window)
        finally:
            window.close()

    def test_chat_dock_constructs(self):
        window = QtWidgets.QMainWindow()
        dock = PyMOLChatDock(window)
        try:
            self.assertEqual(dock.input.placeholderText(), "Ask PyMOL…")
            self.assertFalse(dock.debug_view.isVisible())
            self.assertEqual(
                [action.text() for action in dock.options_menu.actions() if not action.isSeparator()],
                ["API Key Settings…", "Show Command Log"],
            )
            self.assertTrue(dock.debug_action.isCheckable())
        finally:
            dock.close()
            window.close()
