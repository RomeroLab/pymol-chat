"""PyMOL Chat plugin entry point."""

from __future__ import annotations

_dock = None


def _qt_main_window():
    """Return PyMOL's real QMainWindow, not its legacy PMGApp wrapper."""
    from pymol.Qt import QtWidgets

    application = QtWidgets.QApplication.instance()
    if application is None:
        raise RuntimeError("PyMOL's Qt application is not running")

    active = application.activeWindow()
    if isinstance(active, QtWidgets.QMainWindow):
        return active

    main_windows = [
        widget for widget in application.topLevelWidgets()
        if isinstance(widget, QtWidgets.QMainWindow)
    ]
    # The PyMOL window owns `pymolwidget`; prefer it over auxiliary windows.
    for window in main_windows:
        if hasattr(window, "pymolwidget"):
            return window
    if main_windows:
        return main_windows[0]
    raise RuntimeError("Could not find PyMOL's Qt main window")


def show():
    """Show (or create) the chat dock in the active PyMOL window."""
    global _dock
    from pymol.Qt import QtCore

    from .ui import PyMOLChatDock

    parent = _qt_main_window()
    if _dock is None:
        _dock = PyMOLChatDock(parent)
        parent.addDockWidget(QtCore.Qt.BottomDockWidgetArea, _dock)
    _dock.show()
    _dock.raise_()
    return _dock


def __init_plugin__(app=None):
    """Called by PyMOL's plugin manager."""
    from pymol.plugins import addmenuitemqt

    addmenuitemqt("Chat with PyMOL", show)
