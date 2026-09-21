"""Minimal Qt dock UI hosted by the standard PyMOL application."""

from __future__ import annotations

import html
import os
from pathlib import Path

from pymol import cmd
from pymol.Qt import QtCore, QtGui, QtWidgets

from .agent import PyMOLAgent
from .audio import VoiceRecorder, transcribe
from .config import api_key
from .keychain import delete_api_key, read_api_key, save_api_key
from .speech import SpeechPlayer


class TaskSignals(QtCore.QObject):
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)


class Task(QtCore.QRunnable):
    def __init__(self, function, *args):
        super().__init__()
        self.function, self.args = function, args
        self.signals = TaskSignals()

    def run(self):
        try:
            self.signals.done.emit(self.function(*self.args))
        except Exception as exc:
            messages = [str(exc) or type(exc).__name__]
            cause = exc.__cause__
            while cause is not None and len(messages) < 3:
                detail = str(cause) or type(cause).__name__
                if detail not in messages:
                    messages.append(detail)
                cause = cause.__cause__
            self.signals.failed.emit(" — ".join(messages))


class DropPanel(QtWidgets.QWidget):
    files_dropped = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if any(Path(path).suffix.lower() in {".pdb", ".cif", ".mmcif", ".pse"} for path in paths):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.files_dropped.emit([url.toLocalFile() for url in event.mimeData().urls()])
        event.acceptProposedAction()


class APIKeyDialog(QtWidgets.QDialog):
    """API key status and replacement dialog backed by macOS Keychain."""

    def __init__(self, parent=None, has_key=False, source=""):
        super().__init__(parent)
        self.setWindowTitle("OpenAI API Key")
        self.setModal(True)
        self.setMinimumWidth(440)
        layout = QtWidgets.QVBoxLayout(self)

        status_row = QtWidgets.QHBoxLayout()
        status_dot = QtWidgets.QLabel("●")
        status_dot.setObjectName("api_key_status_dot")
        status_dot.setStyleSheet(f"color:{'#49D86D' if has_key else '#777777'}")
        status_text = QtWidgets.QLabel(
            f"API key active — {source}" if has_key else "No API key configured"
        )
        status_row.addWidget(status_dot)
        status_row.addWidget(status_text)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        explanation = QtWidgets.QLabel(
            "For security, an active key is never displayed. Paste a new key below "
            "only when you want to add or replace it. Keys entered here are saved "
            "in the macOS login Keychain and are not included in PyMOL session files."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        link = QtWidgets.QLabel(
            '<a style="color:#9B81FD" href="https://platform.openai.com/api-keys">'
            "Create or manage an API key</a>"
        )
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.key_input.setPlaceholderText(
            "Paste a replacement key…" if has_key else "Paste your API key…"
        )
        layout.addWidget(self.key_input)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color:#FF6B68")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Save).clicked.connect(self._save)
        buttons.rejected.connect(self.reject)
        if read_api_key():
            clear_button = buttons.addButton("Remove Key", QtWidgets.QDialogButtonBox.DestructiveRole)
            clear_button.clicked.connect(self._clear)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background-color:#343434; color:#E8E8E8; }
            QLabel { color:#E8E8E8; }
            QLineEdit { min-height:28px; padding:0 8px; background-color:#222222;
                color:#E8E8E8; border:1px solid #494949; border-radius:3px; }
            QPushButton { min-height:24px; padding:1px 10px; background-color:#3E3E3E;
                color:#E8E8E8; border:1px solid #555555; border-radius:3px; }
            QPushButton:hover { background-color:#494949; border-color:#60B0DC; }
        """)

    def _save(self):
        key = self.key_input.text().strip()
        if len(key) < 20:
            self.error_label.setText("That does not look like a complete API key.")
            return
        try:
            save_api_key(key)
        except Exception as exc:
            self.error_label.setText(str(exc))
            return
        os.environ["OPENAI_API_KEY"] = key
        self.accept()

    def _clear(self):
        delete_api_key()
        os.environ.pop("OPENAI_API_KEY", None)
        self.done(2)


class PyMOLChatDock(QtWidgets.QDockWidget):
    debug_message = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Chat with PyMOL", parent)
        self.setObjectName("PyMOLChatDock")
        self.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setMinimumHeight(210)
        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self.agent = None
        self.busy = False
        self.speech = SpeechPlayer(self)
        self.speech.error.connect(self.show_error)
        self.settings = QtCore.QSettings("RomeroLab", "PyMOLChat")

        root = DropPanel(self)
        root.setObjectName("pymol_chat_panel")
        root.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        root.setAutoFillBackground(True)
        self.panel_root = root
        root.files_dropped.connect(self.load_files)
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self.history = QtWidgets.QTextBrowser()
        self.history.setObjectName("chat_history")
        self.history.setOpenExternalLinks(True)
        self.history.setPlaceholderText("Ask PyMOL to change or inspect the current scene.")
        layout.addWidget(self.history, 1)

        self.debug_view = QtWidgets.QPlainTextEdit()
        self.debug_view.setObjectName("chat_debug")
        self.debug_view.setReadOnly(True)
        self.debug_view.setMaximumBlockCount(500)
        self.debug_view.setVisible(False)
        self.debug_view.setMaximumHeight(130)
        layout.addWidget(self.debug_view)
        self.debug_message.connect(self.debug_view.appendPlainText)

        input_row = QtWidgets.QHBoxLayout()
        self.mic_button = QtWidgets.QPushButton("●")
        self.mic_button.setObjectName("chat_mic_button")
        self.mic_button.setToolTip("Start voice input")
        self.mic_button.setFixedSize(34, 30)
        self.input = QtWidgets.QLineEdit()
        self.input.setObjectName("chat_input")
        self.input.setPlaceholderText("Ask PyMOL…")
        self.input.returnPressed.connect(self.send)

        self.key_status = QtWidgets.QLabel("●")
        self.key_status.setObjectName("chat_key_status")
        self.key_status.setAlignment(QtCore.Qt.AlignCenter)
        self.key_status.setFixedWidth(12)

        self.menu_button = QtWidgets.QToolButton()
        self.menu_button.setObjectName("chat_menu_button")
        self.menu_button.setText("⋯")
        self.menu_button.setToolTip("Options")
        self.menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.menu_button.setFixedSize(30, 30)
        self.options_menu = QtWidgets.QMenu(self.menu_button)
        self.key_action = self.options_menu.addAction("API Key Settings…")
        self.key_action.triggered.connect(self.show_key_dialog)
        self.options_menu.addSeparator()
        self.speech_action = self.options_menu.addAction("Spoken Replies")
        self.speech_action.setCheckable(True)
        self.speech_action.setToolTip("Marin — AI-generated voice from OpenAI; API usage charges apply")
        self.options_menu.setToolTipsVisible(True)
        self.speech_action.setChecked(self.settings.value("spoken_replies", True, type=bool))
        self.speech_action.setEnabled(self.speech.available)
        self.speech_action.toggled.connect(self._speech_toggled)
        self.options_menu.addSeparator()
        self.debug_action = self.options_menu.addAction("Show Command Log")
        self.debug_action.setCheckable(True)
        self.debug_action.toggled.connect(self.debug_view.setVisible)
        self.menu_button.setMenu(self.options_menu)

        input_row.addWidget(self.mic_button)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.key_status)
        input_row.addWidget(self.menu_button)
        layout.addLayout(input_row)
        self.setWidget(root)

        self.voice = VoiceRecorder(self)
        self.voice.state_changed.connect(self._recording_changed)
        self.voice.finished.connect(self._recording_finished)
        self.voice.error.connect(self.show_error)
        self.mic_button.clicked.connect(self.toggle_recording)
        self._update_key_status()
        self._apply_style()
        # PyMOL finishes applying its application palette during startup.
        # Reassert the dock's local theme after that pass as well.
        QtCore.QTimer.singleShot(0, self._apply_style)
        QtCore.QTimer.singleShot(750, self._apply_style)
        QtCore.QTimer.singleShot(1000, self._offer_key_setup)

    def _apply_style(self):
        window = QtGui.QColor("#343434")
        base = QtGui.QColor("#222222")
        field = QtGui.QColor("#3E3E3E")
        text = QtGui.QColor("#E8E8E8")
        muted = QtGui.QColor("#A8A8A8")

        panel_palette = self.panel_root.palette()
        panel_palette.setColor(QtGui.QPalette.Window, window)
        panel_palette.setColor(QtGui.QPalette.WindowText, text)
        self.panel_root.setPalette(panel_palette)

        for widget, background in (
            (self.history, base),
            (self.debug_view, base),
            (self.input, field),
        ):
            palette = widget.palette()
            palette.setColor(QtGui.QPalette.Base, background)
            palette.setColor(QtGui.QPalette.Text, text)
            palette.setColor(QtGui.QPalette.Window, background)
            if hasattr(QtGui.QPalette, "PlaceholderText"):
                palette.setColor(QtGui.QPalette.PlaceholderText, muted)
            widget.setPalette(palette)
            widget.setAutoFillBackground(True)

        self.setStyleSheet("""
            QDockWidget { color: #E8E8E8; background-color: #343434; border: 1px solid #494949; }
            QDockWidget::title { background-color: #343434; color: #E8E8E8; padding: 5px; }
            QWidget#pymol_chat_panel { background-color: #343434; color: #E8E8E8; }
            QTextBrowser#chat_history, QPlainTextEdit#chat_debug {
                background-color: #222222; color: #E8E8E8; border: 1px solid #494949;
                border-radius: 3px; selection-background-color: #6655A8;
            }
            QLineEdit#chat_input {
                min-height: 28px; padding: 0px 8px; background-color: #3E3E3E;
                color: #E8E8E8; border: 1px solid #494949; border-radius: 3px;
                selection-background-color: #6655A8;
            }
            QLineEdit#chat_input:focus { border-color: #9B81FD; }
            QLineEdit#chat_input:disabled { color: #888888; background-color: #2B2B2B; }
            QPushButton#chat_mic_button {
                background-color: #3E3E3E; color: #CECECE; border: 1px solid #494949;
                border-radius: 3px; font-size: 15px; padding: 0px;
            }
            QPushButton#chat_mic_button:hover { background-color: #494949; border-color: #60B0DC; }
            QPushButton#chat_mic_button[recording="true"] {
                color: white; background-color: #C74440; border-color: #FF7770;
            }
            QLabel#chat_key_status { color: #49D86D; font-size: 14px; }
            QLabel#chat_key_status[active="false"] { color: #777777; }
            QToolButton#chat_menu_button {
                background-color: transparent; color: #CECECE; border: 0px;
                border-radius: 3px; font-size: 18px; padding: 0px;
            }
            QToolButton#chat_menu_button:hover { background-color: #494949; }
            QToolButton#chat_menu_button::menu-indicator { image: none; width: 0px; }
            QMenu { background-color: #343434; color: #E8E8E8;
                border: 1px solid #555555; padding: 4px; }
            QMenu::item { padding: 5px 24px 5px 8px; }
            QMenu::item:selected { background-color: #525252; }
            QScrollBar:vertical { background-color: #222222; width: 8px; }
            QScrollBar::handle:vertical { background-color: #555555; min-height: 18px; border-radius: 3px; }
        """)

    def _ensure_agent(self):
        if self.agent is None:
            # Agent work runs off the GUI thread; emitting a Qt signal safely
            # queues debug updates back onto the GUI thread.
            self.agent = PyMOLAgent(debug=self.debug_message.emit)
        return self.agent

    def _offer_key_setup(self):
        if not api_key():
            self.show_key_dialog()

    def _update_key_status(self):
        active = bool(api_key())
        self.key_status.setProperty("active", active)
        self.key_status.setToolTip(
            "OpenAI API key active" if active else "No OpenAI API key configured"
        )
        self.key_status.style().unpolish(self.key_status)
        self.key_status.style().polish(self.key_status)

    def show_key_dialog(self):
        active_key = api_key()
        stored_key = read_api_key()
        source = "macOS Keychain" if stored_key and stored_key == active_key else "environment configuration"
        dialog = APIKeyDialog(self, has_key=bool(active_key), source=source)
        result = dialog.exec_()
        if result == QtWidgets.QDialog.Accepted:
            self.agent = None
            self._update_key_status()
            self._append_message("PyMOL", "API key saved securely in macOS Keychain.")
            return True
        if result == 2:
            self.agent = None
            self._update_key_status()
            message = "Keychain key removed."
            if api_key():
                message += " A key from the environment configuration remains active."
            self._append_message("PyMOL", message)
        return False

    def _ensure_api_key(self):
        return bool(api_key()) or self.show_key_dialog()

    def send(self):
        text = self.input.text().strip()
        if not text or self.busy:
            return
        if not self._ensure_api_key():
            return
        self.speech.stop()
        self.input.clear()
        self._append_message("You", text)
        self._set_busy(True)
        try:
            agent = self._ensure_agent()
        except Exception as exc:
            self.show_error(str(exc))
            self._set_busy(False)
            return
        task = Task(agent.ask, text)
        task.signals.done.connect(self._answer_received)
        task.signals.failed.connect(self._task_failed)
        self.thread_pool.start(task)

    def _answer_received(self, answer):
        self._append_message("PyMOL", str(answer))
        self._set_busy(False)
        if self.speech_action.isChecked() and self.isVisible() and not self.voice.is_recording:
            self.speech.speak(str(answer))

    def _speech_toggled(self, enabled):
        self.settings.setValue("spoken_replies", enabled)
        if not enabled:
            self.speech.stop()

    def hideEvent(self, event):
        self.speech.stop()
        super().hideEvent(event)

    def _task_failed(self, message):
        self.show_error(message)
        self._set_busy(False)

    def _append_message(self, who: str, text: str):
        safe = html.escape(text).replace("\n", "<br>")
        colors = {"You": "#9B81FD", "PyMOL": "#49D86D", "Error": "#FF6B68"}
        color = colors.get(who, "#E8E8E8")
        self.history.append(
            f'<div style="margin: 3px 2px 7px 2px;">'
            f'<b style="color: {color};">{html.escape(who)}</b><br>{safe}</div>'
        )

    def _set_busy(self, busy: bool):
        self.busy = busy
        self.input.setEnabled(not busy)
        self.mic_button.setEnabled(not busy)
        self.input.setPlaceholderText("Working…" if busy else "Ask PyMOL…")
        if not busy:
            self.input.setFocus()

    def show_error(self, message: str):
        self._append_message("Error", message)

    def load_files(self, paths):
        allowed = {".pdb", ".cif", ".mmcif", ".pse"}
        loaded = []
        for raw_path in paths:
            path = Path(raw_path).expanduser().resolve()
            if path.is_file() and path.suffix.lower() in allowed:
                cmd.load(str(path))
                loaded.append(path.name)
        if loaded:
            if any(Path(path).suffix.lower() != ".pse" for path in paths):
                cmd.orient("all")
            self._append_message("PyMOL", "Loaded " + ", ".join(loaded))

    def toggle_recording(self):
        if not self._ensure_api_key():
            return
        try:
            self.speech.stop()
            self.voice.toggle()
        except Exception as exc:
            self.show_error(str(exc))

    def _recording_finished(self, path):
        if path is None:
            return
        self._set_busy(True)
        self._start_transcription(path)

    def _start_transcription(self, path):
        task = Task(transcribe, path)
        task.signals.done.connect(self._transcribed)
        task.signals.failed.connect(self._task_failed)
        self.thread_pool.start(task)

    def _recording_changed(self, recording: bool):
        self.mic_button.setProperty("recording", recording)
        self.mic_button.setText("■" if recording else "●")
        self.mic_button.setToolTip("Listening — click to stop" if recording else "Start voice input")
        self.input.setEnabled(not recording and not self.busy)
        self.input.setPlaceholderText("Listening…" if recording else ("Working…" if self.busy else "Ask PyMOL…"))
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)

    def _transcribed(self, text):
        self._set_busy(False)
        self.input.setText(str(text))
        self.send()
