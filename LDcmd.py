#!/usr/bin/env python3
"""
LDcmd — Colorful CMD Wrapper with PyQt6
Install: pip install PyQt6 pywinpty
"""

import sys
import os
import platform
import re
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QPushButton, QFrame, QSizeGrip,
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QProcess, QProcessEnvironment,
    QObject, QEvent,
)
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

# ── Try pywinpty ──
HAS_WINPTY = False
WINPTY_V2 = False
PtyProcess = None
WinPTY = None

try:
    from winpty import PtyProcess
    HAS_WINPTY = True
    WINPTY_V2 = True
except ImportError:
    try:
        from winpty import PTY as _W
        WinPTY = _W
        HAS_WINPTY = True
        WINPTY_V2 = False
    except ImportError:
        pass

# ──────────────────────────── THEMES ────────────────────────────

THEMES = {
    "dark": dict(
        name="Dark", bg="#1e1e2e", fg="#cdd6f4", prompt="#89b4fa",
        error="#f38ba8", success="#a6e3a1", warning="#f9e2af",
        info="#89dceb", title_bg="#181825", border="#313244",
        input_bg="#1e1e2e", selection="#585b7066", accent="#89b4fa",
        glow=False, glow_color=None, radius=10,
    ),
    "light": dict(
        name="Light", bg="#eff1f5", fg="#4c4f69", prompt="#1e66f5",
        error="#d20f39", success="#40a02b", warning="#df8e1d",
        info="#179299", title_bg="#e6e9ef", border="#ccd0da",
        input_bg="#eff1f5", selection="#bcc0cc88", accent="#1e66f5",
        glow=False, glow_color=None, radius=10,
    ),
    "glassmorphism": dict(
        name="Glassmorphism", bg="#1a1a2e", fg="#e0e0ff", prompt="#00d4ff",
        error="#ff6b6b", success="#4ecdc4", warning="#ffe66d",
        info="#a8e6cf", title_bg="#16213e", border="#0f3460",
        input_bg="#1a1a2e", selection="#0f346066", accent="#00d4ff",
        glow=True, glow_color="#00d4ff", radius=14,
    ),
    "devcore": dict(
        name="DevCore", bg="#0d1117", fg="#c9d1d9", prompt="#58a6ff",
        error="#f85149", success="#3fb950", warning="#d29922",
        info="#79c0ff", title_bg="#010409", border="#21262d",
        input_bg="#161b22", selection="#1f6feb44", accent="#58a6ff",
        glow=False, glow_color=None, radius=8,
    ),
    "cyberpunk": dict(
        name="Cyberpunk", bg="#0a0a0f", fg="#e0e0ff", prompt="#00ffff",
        error="#ff0040", success="#39ff14", warning="#ffff00",
        info="#ff00ff", title_bg="#0f0015", border="#ff00ff",
        input_bg="#0f0a1a", selection="#ff00ff33", accent="#ff00ff",
        glow=True, glow_color="#ff00ff", radius=4,
    ),
}

# ──────────────────────── HELPERS ───────────────────────────────

def clean_terminal_text(text):
    if not text:
        return ""
    text = re.sub(r'\x1b\[(?:0?|1)G', '\r', text)
    text = re.sub(r'\x1b\[\d+;1H', '\r', text)
    text = re.sub(r'\x1b\[H', '\r', text)
    text = re.sub(r'\x1b\[\d?D', '\b', text)
    text = re.sub(r'\x1b\[\d*[JK]', '', text)
    text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
    text = re.sub(r'\x1b\][^\x1b]*\x1b\\', '', text)
    text = re.sub(r'\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]', '', text)
    text = re.sub(r'\x1b[\x40-\x5f]', '', text)
    text = text.replace('\x1b', '')
    text = re.sub(r'[\x80-\x9f]', '', text)
    out = []
    for ch in text:
        c = ord(ch)
        if c in (0, 7, 27, 127): continue
        elif c == 8:  out.append('\b')
        elif c == 9:  out.append('  ')
        elif c == 10: out.append('\n')
        elif c == 13: out.append('\r')
        elif c < 32 or c == 0xFFFD: continue
        else: out.append(ch)
    return ''.join(out)


def find_cmd():
    sr = os.environ.get('SystemRoot', '')
    if sr:
        p = os.path.join(sr, 'System32', 'cmd.exe')
        if os.path.isfile(p): return p
    for b in [r'C:\Windows', r'D:\Windows']:
        p = os.path.join(b, 'System32', 'cmd.exe')
        if os.path.isfile(p): return p
    for d in os.environ.get('PATH', '').split(';'):
        p = os.path.join(d.strip(), 'cmd.exe')
        if os.path.isfile(p): return p
    return 'cmd.exe'


# ──────────────────── OUTPUT EVENT FILTER ───────────────────────

class OutputFilter(QObject):
    def __init__(self, w):
        super().__init__(w)
        self.w = w

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.KeyPress:
            key = ev.key()
            mods = ev.modifiers()
            if key == Qt.Key.Key_C and mods & Qt.KeyboardModifier.ControlModifier:
                cur = self.w.output.textCursor()
                if cur.hasSelection():
                    QApplication.clipboard().setText(
                        cur.selectedText().replace('\u2029', '\n'))
                    return True
            if key == Qt.Key.Key_A and mods & Qt.KeyboardModifier.ControlModifier:
                self.w.output.selectAll()
                return True
            self.w.input.setFocus()
            QApplication.sendEvent(self.w.input, ev)
            return True
        return False


# ──────────────────────── TITLE BAR ─────────────────────────────

class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self._drag = None
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 2, 0)
        lay.setSpacing(6)
        self.icon = QLabel("⟩")
        self.icon.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        self.icon.setFixedWidth(22)
        self.title = QLabel("LDcmd")
        self.title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.badge = QLabel("")
        self.badge.setFont(QFont("Segoe UI", 9))
        lay.addWidget(self.icon)
        lay.addWidget(self.title)
        lay.addStretch()
        lay.addWidget(self.badge)
        lay.addStretch()
        self.b_min = QPushButton("─")
        self.b_max = QPushButton("□")
        self.b_cls = QPushButton("✕")
        for b in (self.b_min, self.b_max, self.b_cls):
            b.setFixedSize(46, 40)
            b.setFont(QFont("Segoe UI", 10))
            b.setFlat(True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.b_min)
        lay.addWidget(self.b_max)
        lay.addWidget(self.b_cls)
        self.b_min.clicked.connect(self.win.showMinimized)
        self.b_max.clicked.connect(self.win.toggle_max)
        self.b_cls.clicked.connect(self.win.close)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.MouseButton.LeftButton:
            if self.win.isMaximized():
                self.win.showNormal()
                self._drag = None
                return
            self.win.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.win.toggle_max()


# ──────────────────── CMD INPUT ─────────────────────────────────

class CmdInput(QLineEdit):
    def __init__(self, wrapper):
        super().__init__(wrapper)
        self.w = wrapper
        self._history = []
        self._hist_idx = -1
        self._saved = ""

    def push_history(self, cmd):
        if cmd and (not self._history or self._history[-1] != cmd):
            self._history.append(cmd)
        self._hist_idx = len(self._history)
        self._saved = ""

    def keyPressEvent(self, e):
        key = e.key()
        mods = e.modifiers()
        w = self.w

        if key == Qt.Key.Key_Escape:
            if w._program_running:
                if w.mode == "pty" and w._pty:
                    w._pty_write('\x03')
                elif w.mode == "subprocess":
                    w._kill_subprocess()
            self.setText("")
            return

        if key == Qt.Key.Key_L and mods & Qt.KeyboardModifier.ControlModifier:
            w.output.clear()
            w._line_buf = ""
            return

        # ── Running: send every key instantly ──
        if w._program_running and w.mode == "pty" and w._pty:
            self._send_key_to_pty(e)
            return

        if w._program_running and w.mode == "subprocess":
            self._send_key_to_subprocess(e)
            return

        # ── Idle: normal editing ──
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            w._submit_input()
            return

        if key == Qt.Key.Key_Up:
            if self._history and self._hist_idx > 0:
                if self._hist_idx == len(self._history):
                    self._saved = self.text()
                self._hist_idx -= 1
                self.setText(self._history[self._hist_idx])
            return

        if key == Qt.Key.Key_Down:
            if self._hist_idx < len(self._history) - 1:
                self._hist_idx += 1
                self.setText(self._history[self._hist_idx])
            elif self._hist_idx == len(self._history) - 1:
                self._hist_idx = len(self._history)
                self.setText(self._saved)
            return

        if key == Qt.Key.Key_Tab:
            w._tab_complete()
            return

        super().keyPressEvent(e)

    def _send_key_to_pty(self, e):
        key = e.key()
        text = e.text()
        mods = e.modifiers()
        pw = self.w._pty_write

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter): pw('\r')
        elif key == Qt.Key.Key_Backspace: pw('\x08')
        elif key == Qt.Key.Key_Tab: pw('\t')
        elif key == Qt.Key.Key_Up:    pw('\x1b[A')
        elif key == Qt.Key.Key_Down:  pw('\x1b[B')
        elif key == Qt.Key.Key_Right: pw('\x1b[C')
        elif key == Qt.Key.Key_Left:  pw('\x1b[D')
        elif key == Qt.Key.Key_Home:  pw('\x1b[H')
        elif key == Qt.Key.Key_End:   pw('\x1b[F')
        elif key == Qt.Key.Key_Delete: pw('\x1b[3~')
        elif key == Qt.Key.Key_PageUp: pw('\x1b[5~')
        elif key == Qt.Key.Key_PageDown: pw('\x1b[6~')
        elif key == Qt.Key.Key_Insert: pw('\x1b[2~')
        elif key == Qt.Key.Key_F1:  pw('\x1bOP')
        elif key == Qt.Key.Key_F2:  pw('\x1bOQ')
        elif key == Qt.Key.Key_F3:  pw('\x1bOR')
        elif key == Qt.Key.Key_F4:  pw('\x1bOS')
        elif key == Qt.Key.Key_F5:  pw('\x1b[15~')
        elif key == Qt.Key.Key_F6:  pw('\x1b[17~')
        elif key == Qt.Key.Key_F7:  pw('\x1b[18~')
        elif key == Qt.Key.Key_F8:  pw('\x1b[19~')
        elif key == Qt.Key.Key_F9:  pw('\x1b[20~')
        elif key == Qt.Key.Key_F10: pw('\x1b[21~')
        elif key == Qt.Key.Key_F11: pw('\x1b[23~')
        elif key == Qt.Key.Key_F12: pw('\x1b[24~')
        elif mods & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_C:   pw('\x03')
            elif key == Qt.Key.Key_V:
                cb = QApplication.clipboard().text()
                if cb: pw(cb)
            elif key == Qt.Key.Key_Z: pw('\x1a')
            elif key == Qt.Key.Key_D: pw('\x04')
            elif key == Qt.Key.Key_A: pw('\x01')
            elif key == Qt.Key.Key_E: pw('\x05')
            elif text:
                code = ord(text.upper()) - 64
                if 1 <= code <= 26: pw(chr(code))
        elif mods & Qt.KeyboardModifier.AltModifier:
            if text: pw('\x1b' + text)
        elif text:
            pw(text)
        self.setText("")

    def _send_key_to_subprocess(self, e):
        key = e.key()
        text = e.text()
        mods = e.modifiers()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.w.process.write(b'\r\n')
        elif key == Qt.Key.Key_Backspace:
            self.w.process.write(b'\x08')
        elif text:
            if mods & Qt.KeyboardModifier.ControlModifier:
                code = ord(text.upper()) - 64
                if 1 <= code <= 26:
                    self.w.process.write(bytes([code]))
            else:
                self.w.process.write(text.encode('utf-8', errors='replace'))
        self.setText("")


# ──────────────────── MAIN WINDOW ───────────────────────────────

class CmdWrapper(QMainWindow):
    new_output = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.theme_name = "dark"
        self.cwd = os.getcwd()
        self._program_running = False
        self._prompt_re = re.compile(r'[A-Za-z]:[\\/][^\r\n>]*>', re.MULTILINE)
        self._alive = True
        self.mode = "subprocess"
        self._pty = None
        self._killed = False
        self._stop_stage = 0
        self._line_buf = ""

        self.setWindowTitle("LDcmd")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(QSize(680, 420))
        self.resize(940, 620)

        self.new_output.connect(self._on_output)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._sub_read)
        self.process.finished.connect(self._sub_finished)
        self.process.errorOccurred.connect(self._sub_error)

        self._build_ui()
        self.apply_theme(self.theme_name)
        self._start_backend()
        QTimer.singleShot(100, lambda: self.input.setFocus())

    # ── Backend ──

    def _start_backend(self):
        if HAS_WINPTY:
            try:
                import winpty
                os.environ['PATH'] = os.environ.get('PATH', '') + ';' + os.path.dirname(winpty.__file__)
            except Exception:
                pass
            cmd = find_cmd()
            try:
                if WINPTY_V2:
                    self._pty = PtyProcess.spawn(cmd, cwd=self.cwd, env=os.environ)
                else:
                    self._pty = WinPTY(120, 30)
                    self._pty.spawn(cmd)
                self.mode = "pty"
                threading.Thread(target=self._pty_read_loop, daemon=True).start()
                self._print_welcome("PTY")
                return
            except Exception as e:
                self._pty = None
                self.mode = "subprocess"
                self._print_welcome("Subprocess", str(e))
                return
        self._print_welcome("Subprocess", "pip install pywinpty")

    def _print_welcome(self, mode_name, err=None):
        self.print_output(f"\n  Welcome to LDcmd  [{mode_name} mode]\n", "success")
        if err:
            self.print_output(f"  Note: {err}\n", "warning")
        self.print_output(f"  System : {platform.system()} {platform.release()} ({platform.machine()})\n", "info")
        self.print_output(f"  Python : {platform.python_version()}\n", "info")
        self.print_output(f"  CWD    : {self.cwd}\n\n", "info")
        self.print_output('  "ldcmd help" → all commands\n\n', "warning")
        self._update_status()
        self._update_input_state()

    # ── PTY ──

    def _pty_read_loop(self):
        time.sleep(0.2)
        while self._alive and self._pty:
            try:
                if WINPTY_V2:
                    data = self._pty.read(4096)
                    if not data: break
                else:
                    data = self._pty.read()
                    if not data:
                        try:
                            if not self._pty.is_alive: break
                        except Exception: break
                if data and self._alive:
                    self.new_output.emit(data)
            except Exception:
                if self._alive:
                    try:
                        if WINPTY_V2:
                            if not self._pty.isalive(): break
                        elif not self._pty.is_alive: break
                    except Exception: break
        if self._alive:
            self.new_output.emit("\n  [Process ended. Type 'restart' to reopen.]\n")

    def _pty_write(self, data):
        if not self._pty: return
        try:
            if WINPTY_V2: self._pty.write(data)
            else: self._pty.write(data)
        except Exception: pass

    # ── Subprocess ──

    def _sub_run(self, cmd):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._killed = True
            self.process.kill()
            self.process.waitForFinished(500)
        self._killed = False
        self._program_running = True
        self._update_status()
        self._update_input_state()
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setWorkingDirectory(self.cwd)
        self.process.setProcessEnvironment(env)
        self.process.start("cmd.exe", ["/C", cmd])

    def _sub_read(self):
        data = self.process.readAllStandardOutput().data()
        try: text = data.decode("utf-8", errors="replace")
        except: text = data.decode("mbcs", errors="replace")
        self.print_output(clean_terminal_text(text), "fg")

    def _sub_finished(self, ec, es):
        if self._killed:
            self._killed = False
            return
        self._finalize_line(QColor(THEMES[self.theme_name]["fg"]))
        self._program_running = False
        self._stop_stage = 0
        self._update_status()
        self._update_input_state()

    def _sub_error(self, err):
        if self._killed: return
        msgs = {QProcess.ProcessError.FailedToStart: "Command not found",
                QProcess.ProcessError.Crashed: "Crashed",
                QProcess.ProcessError.Timedout: "Timed out"}
        self.print_output(f"\n  ✗ {msgs.get(err, 'Error')}\n", "error")
        self._program_running = False
        self._stop_stage = 0
        self._update_status()
        self._update_input_state()

    def _kill_subprocess(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._killed = True
            self.process.kill()
            self.process.waitForFinished(1000)
        self._finalize_line(QColor(THEMES[self.theme_name]["fg"]))
        self.print_output("\n  ⛔ Stopped.\n", "warning")
        self._program_running = False
        self._stop_stage = 0
        self._update_status()
        self._update_input_state()

    # ── UI ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.inner = QFrame()
        self.inner.setObjectName("inner")
        col = QVBoxLayout(self.inner)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.tbar = TitleBar(self)
        self.sep1 = QFrame(); self.sep1.setFixedHeight(1); self.sep1.setObjectName("sep")

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 11))
        self.output.setFrameStyle(QFrame.Shape.NoFrame)
        self.output.setAcceptRichText(False)
        self.output.setObjectName("output")
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.output.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.output.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.output.installEventFilter(OutputFilter(self))

        self.sep2 = QFrame(); self.sep2.setFixedHeight(1); self.sep2.setObjectName("sep")

        self.inp_widget = QWidget()
        self.inp_widget.setObjectName("inp_widget")
        inp_lay = QHBoxLayout(self.inp_widget)
        inp_lay.setContentsMargins(14, 6, 14, 8)
        inp_lay.setSpacing(8)

        self.prompt_lbl = QLabel(self._prompt_str())
        self.prompt_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.prompt_lbl.setObjectName("prompt_lbl")

        self.input = CmdInput(self)
        self.input.setFont(QFont("Consolas", 11))
        self.input.setObjectName("cmd_input")
        self.input.setPlaceholderText("type a command...")

        self.stop_btn_input = QPushButton("■ Stop")
        self.stop_btn_input.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.stop_btn_input.setObjectName("stop_btn_input")
        self.stop_btn_input.setFixedSize(90, 28)
        self.stop_btn_input.setVisible(False)
        self.stop_btn_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_btn_input.clicked.connect(self._stop_clicked)

        inp_lay.addWidget(self.prompt_lbl)
        inp_lay.addWidget(self.input, 1)
        inp_lay.addWidget(self.stop_btn_input)

        self.status_bar = QFrame()
        self.status_bar.setObjectName("status_bar")
        self.status_bar.setFixedHeight(32)
        sb = QHBoxLayout(self.status_bar)
        sb.setContentsMargins(14, 0, 14, 0)
        sb.setSpacing(12)

        self.mode_lbl = QLabel("● Subprocess")
        self.mode_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.mode_lbl.setObjectName("mode_lbl")
        self.cwd_lbl = QLabel(self._short_cwd())
        self.cwd_lbl.setFont(QFont("Consolas", 9))
        self.cwd_lbl.setObjectName("cwd_lbl")
        self.run_lbl = QLabel("")
        self.run_lbl.setFont(QFont("Consolas", 9))
        self.run_lbl.setObjectName("run_lbl")

        sb.addWidget(self.mode_lbl)
        sb.addWidget(self.cwd_lbl)
        sb.addStretch()
        sb.addWidget(self.run_lbl)

        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)

        col.addWidget(self.tbar)
        col.addWidget(self.sep1)
        col.addWidget(self.output, 1)
        col.addWidget(self.sep2)
        col.addWidget(self.inp_widget)
        col.addWidget(self.status_bar)
        root.addWidget(self.inner)

    # ── Prompt helpers ──

    def _prompt_str(self):
        p = self.cwd
        h = os.path.expanduser("~")
        if p.lower().startswith(h.lower()):
            p = "~" + p[len(h):]
        if len(p) > 45:
            s = p.split(os.sep)
            if len(s) > 3:
                p = s[0] + os.sep + "…" + os.sep + os.sep.join(s[-2:])
        return f"{p}>"

    def _short_cwd(self):
        p = self.cwd
        h = os.path.expanduser("~")
        if p.lower().startswith(h.lower()):
            p = "~" + p[len(h):]
        if len(p) > 40:
            s = p.split(os.sep)
            if len(s) > 3:
                p = s[0] + os.sep + "…" + os.sep + os.sep.join(s[-2:])
        return p

    def _update_input_state(self):
        if self._program_running:
            self.prompt_lbl.setText("🎮")
            self.input.setPlaceholderText("press any key to send to program...")
            self.stop_btn_input.setVisible(True)
            if self._stop_stage == 2:
                self.stop_btn_input.setText("☠ Force Kill")
            else:
                self.stop_btn_input.setText("■ Stop")
        else:
            self.prompt_lbl.setText(self._prompt_str())
            self.input.setPlaceholderText("type a command...")
            self.stop_btn_input.setVisible(False)

    def _update_status(self):
        self.mode_lbl.setText(f"● {self.mode.capitalize()}")
        self.cwd_lbl.setText(self._short_cwd())
        if self._program_running:
            if self._stop_stage == 2:
                self.run_lbl.setText("⚠ Stuck? → click Force Kill")
            else:
                self.run_lbl.setText("⏳ Running — press keys to interact")
        else:
            self.run_lbl.setText("")
            self._stop_stage = 0

    # ── Line buffer output ──

    def print_output(self, text, color="fg"):
        if not text: return
        t = THEMES[self.theme_name]
        c = QColor(t.get(color, t["fg"]))
        bold = self.theme_name == "cyberpunk" and color in ("prompt", "info", "success")

        i = 0; n = len(text)
        while i < n:
            ch = text[i]
            if ch == '\r':
                if i + 1 < n and text[i + 1] == '\n':
                    self._finalize_line(c, bold); i += 2; continue
                self._line_buf = ""; i += 1; continue
            if ch == '\n':
                self._finalize_line(c, bold); i += 1; continue
            if ch == '\b':
                if self._line_buf: self._line_buf = self._line_buf[:-1]
                i += 1; continue
            j = i
            while j < n and text[j] not in ('\r', '\n', '\b'): j += 1
            self._line_buf += text[i:j]
            i = j
        self._render_current_line(c, bold)

    def _finalize_line(self, color, bold=False):
        self._render_current_line(color, bold)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText('\n')
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()
        self._line_buf = ""

    def _render_current_line(self, color, bold=False):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        end_pos = cursor.position()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        start_pos = cursor.position()
        if end_pos > start_pos:
            cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        if self._line_buf:
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            if bold: fmt.setFontWeight(QFont.Weight.Bold)
            cursor.setCharFormat(fmt)
            cursor.insertText(self._line_buf)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    # ── Submit input ──

    def _submit_input(self):
        text = self.input.text()
        self.input.clear()
        cmd = text.strip()

        # ── Intercept ldcmd commands in ALL modes ──
        if cmd and cmd.split()[0].lower() == "ldcmd":
            self.input.push_history(text)
            self.print_output(self._prompt_str() + " " + text + "\n", "prompt")
            self._exec_ldcmd(cmd)
            return

        # ── PTY mode ──
        if self.mode == "pty" and self._pty:
            self._pty_write(text + '\r')
            if not self._program_running and cmd:
                self._program_running = True
                self._stop_stage = 0
                self._update_status()
                self._update_input_state()
            self.input.push_history(text)

        # ── Subprocess mode ──
        elif self.mode == "subprocess":
            self.input.push_history(text)
            self.print_output(self._prompt_str() + " " + text + "\n", "prompt")
            if cmd:
                self._sub_run(cmd)

    # ── ldcmd command dispatcher ──

    def _exec_ldcmd(self, raw):
        parts = raw.split()
        low_parts = [p.lower() for p in parts]

        # ldcmd           → info
        # ldcmd info      → info
        if len(parts) == 1 or (len(parts) == 2 and low_parts[1] == "info"):
            self.print_output(f"\n  LDcmd v1.0  |  Mode: {self.mode}\n", "accent")
            self.print_output(f"  CWD  : {self.cwd}\n", "info")
            self.print_output(f"  PTY  : {'available' if HAS_WINPTY else 'not installed'}\n\n", "info")
            return

        # ldcmd help      → help
        if low_parts[1] == "help":
            self._cmd_help(); return

        # ldcmd theme     → list themes
        # ldcmd theme list→ list themes
        # ldcmd theme <n> → switch theme
        if low_parts[1] == "theme":
            self._cmd_theme(parts[2:]); return

        # ldcmd cls / clear
        if low_parts[1] in ("cls", "clear"):
            self.output.clear(); self._line_buf = ""; return

        # ldcmd pwd
        if low_parts[1] == "pwd":
            self.print_output(self.cwd + "\n", "fg"); return

        # ldcmd cd <path>
        if low_parts[1] == "cd":
            self._cmd_cd(" ".join(parts[2:])); return

        # ldcmd restart
        if low_parts[1] == "restart":
            self._restart_pty(); return

        # ldcmd version
        if low_parts[1] == "version":
            self.print_output("  LDcmd v1.0\n\n", "accent"); return

        # Unknown subcommand
        self.print_output(f"  ✗ Unknown: ldcmd {parts[1]}\n", "error")
        self.print_output('  Type "ldcmd help" for commands\n\n', "warning")

    # ── Tab completion ──

    def _tab_complete(self):
        text = self.input.text()
        if not text: return

        # If starts with "ldcmd ", complete ldcmd subcommands
        low = text.lower()
        if low.startswith("ldcmd ") or low == "ldcmd":
            subcmds = ["help", "theme", "cls", "clear", "pwd", "cd", "restart", "info", "version"]
            if low == "ldcmd" or low == "ldcmd ":
                partial = text[6:].strip().lower()
                matches = [s for s in subcmds if s.startswith(partial)]
                if len(matches) == 1:
                    self.setText("ldcmd " + matches[0] + " ")
                elif matches:
                    self._finalize_line(QColor(THEMES[self.theme_name]["info"]))
                    self.print_output("  ".join(matches) + "\n", "info")
            elif low.startswith("ldcmd theme"):
                theme_partial = text[12:].strip().lower()
                names = list(THEMES.keys())
                matches = [n for n in names if n.startswith(theme_partial)]
                if len(matches) == 1:
                    self.setText("ldcmd theme " + matches[0])
                elif matches:
                    self._finalize_line(QColor(THEMES[self.theme_name]["info"]))
                    self.print_output("  ".join(matches) + "\n", "info")
            return

        # Normal file completion
        parts = text.rsplit(maxsplit=1)
        if text.endswith(" "):
            partial, prefix = "", text
        elif len(parts) > 1:
            partial, prefix = parts[-1], parts[0] + " "
        else:
            partial, prefix = text, ""
        try:
            entries = os.listdir(self.cwd)
            matches = [e for e in entries if e.lower().startswith(partial.lower())]
            if len(matches) == 1:
                m = matches[0]
                if " " in m: m = f'"{m}"'
                if os.path.isdir(os.path.join(self.cwd, matches[0])): m += os.sep
                self.input.setText(prefix + m)
            elif matches:
                self._finalize_line(QColor(THEMES[self.theme_name]["info"]))
                self.print_output("  ".join(matches) + "\n", "info")
        except Exception: pass

    # ── Subcmd implementations ──

    def _cmd_cd(self, path_arg):
        if not path_arg:
            self.print_output(self.cwd + "\n", "fg"); return
        target = path_arg.strip().strip('"').strip("'")
        if target == "~": nd = os.path.expanduser("~")
        elif os.path.isabs(target): nd = os.path.normpath(target)
        else: nd = os.path.normpath(os.path.join(self.cwd, target))
        try:
            r = os.path.realpath(nd)
            if os.path.isdir(r):
                self.cwd = r
                self._update_status()
                self._update_input_state()
            else:
                self.print_output("  Path not found.\n", "error")
        except Exception:
            self.print_output("  Path not found.\n", "error")

    # ── Stop ──

    def _stop_clicked(self):
        if self.mode == "pty" and self._pty:
            if self._stop_stage < 2:
                for _ in range(5):
                    self._pty_write('\x03')
                self._stop_stage = 1
                self._update_status()
                self._update_input_state()
                QTimer.singleShot(2000, self._check_still_running)
            else:
                self._force_kill_pty()
        elif self.mode == "subprocess":
            self._kill_subprocess()

    def _check_still_running(self):
        if self._program_running:
            self._stop_stage = 2
            self._update_status()
            self._update_input_state()

    def _force_kill_pty(self):
        try:
            if WINPTY_V2: self._pty.terminate()
            else: self._pty.close()
        except Exception: pass
        self._pty = None
        self._program_running = False
        self._stop_stage = 0
        self.mode = "none"
        self._update_status()
        self._update_input_state()
        self._line_buf = ""
        self.print_output("\n  ☠ Force-killed. Type 'ldcmd restart' to reopen.\n", "error")

    # ── PTY output handler ──

    def _on_output(self, data):
        clean = clean_terminal_text(data)
        if not clean: return
        self.print_output(clean, "fg")
        flat = clean.replace('\r', '').replace('\b', '')
        if self._prompt_re.search(flat):
            m = self._prompt_re.search(flat)
            if m:
                path = m.group(0)[:-1]
                if len(path) >= 3 and path[1] == ':':
                    self.cwd = path
                    self._update_status()
            if self._program_running:
                self._program_running = False
                self._stop_stage = 0
                self._update_status()
                self._update_input_state()

    # ── Built-in commands ──

    def _cmd_theme(self, parts):
        if not parts or (len(parts) == 1 and parts[0].lower() in ("list", "ls")):
            self.print_output("\n  Available Themes\n", "success")
            self.print_output("  ─────────────────────────────────────\n", "info")
            for n, t in THEMES.items():
                cur = "  ◄ current" if n == self.theme_name else ""
                c = "prompt" if n == self.theme_name else "fg"
                self.print_output(f"  ● {t['name']:16s}{cur}\n", c)
            self.print_output("\n  Usage: ldcmd theme <name>\n\n", "warning")
            return
        name = parts[0].lower()
        if name in THEMES:
            self.theme_name = name
            self.apply_theme(name)
            self.print_output(f"  ✓ Theme → {THEMES[name]['name']}\n\n", "success")
        else:
            self.print_output(f"  ✗ Unknown '{parts[0]}'\n", "error")
            self.print_output(f"  Available: {', '.join(THEMES.keys())}\n\n", "warning")

    def _cmd_help(self):
        self.print_output("\n  ╔══════════════════════════════════════════╗\n", "accent")
        self.print_output("  ║         LDcmd  —  All Commands           ║\n", "accent")
        self.print_output("  ╠══════════════════════════════════════════╣\n", "accent")
        self.print_output("  ║  ldcmd              About LDcmd          ║\n", "info")
        self.print_output("  ║  ldcmd help         This help            ║\n", "info")
        self.print_output("  ║  ldcmd version      Version info         ║\n", "info")
        self.print_output("  ║  ldcmd theme        List themes          ║\n", "info")
        self.print_output("  ║  ldcmd theme <name> Switch theme         ║\n", "info")
        self.print_output("  ║  ldcmd cd <path>    Change directory     ║\n", "info")
        self.print_output("  ║  ldcmd pwd          Print working dir    ║\n", "info")
        self.print_output("  ║  ldcmd cls          Clear screen         ║\n", "info")
        self.print_output("  ║  ldcmd restart      Restart terminal     ║\n", "info")
        self.print_output("  ╠══════════════════════════════════════════╣\n", "accent")
        self.print_output(f"  ║  Mode: {self.mode:<33s} ║\n", "info")
        self.print_output("  ╠══════════════════════════════════════════╣\n", "accent")
        self.print_output("  ║  When idle:  Type command + Enter        ║\n", "fg")
        self.print_output("  ║  When running: Keys sent instantly       ║\n", "fg")
        self.print_output("  ║    w/a/s/d → game movement               ║\n", "fg")
        self.print_output("  ║    arrows  → navigation                  ║\n", "fg")
        self.print_output("  ║    Enter   → send line                   ║\n", "fg")
        self.print_output("  ║  Esc          Cancel / Ctrl+C            ║\n", "fg")
        self.print_output("  ║  Ctrl+L       Clear screen               ║\n", "fg")
        self.print_output("  ║  Click output → drag → Ctrl+C to copy    ║\n", "fg")
        self.print_output("  ╚══════════════════════════════════════════╝\n\n", "accent")

    def _restart_pty(self):
        if not HAS_WINPTY:
            self.print_output("  pywinpty not installed.\n\n", "error"); return
        cmd = find_cmd()
        try:
            if WINPTY_V2: self._pty = PtyProcess.spawn(cmd, cwd=self.cwd, env=os.environ)
            else:
                self._pty = WinPTY(120, 30)
                self._pty.spawn(cmd)
            self.mode = "pty"
            self._program_running = False
            self._stop_stage = 0
            self._update_status()
            self._update_input_state()
            threading.Thread(target=self._pty_read_loop, daemon=True).start()
            self.print_output("  ✓ Terminal restarted [PTY mode]\n\n", "success")
        except Exception as e:
            self.print_output(f"  ✗ Restart failed: {e}\n\n", "error")

    # ── Theme ──

    def apply_theme(self, name):
        t = THEMES[name]
        R = t["radius"]
        glow = f"border:1px solid {t['glow_color']}44;" if t["glow"] and t["glow_color"] else ""

        self.setStyleSheet(f"QMainWindow{{background-color:{t['bg']};}}")
        self.inner.setStyleSheet(f"QFrame#inner{{background-color:{t['bg']};border:2px solid {t['border']};border-radius:{R}px;}}")
        self.tbar.setStyleSheet(f"QWidget{{background-color:{t['title_bg']};border-top-left-radius:{R}px;border-top-right-radius:{R}px;}}")
        self.tbar.icon.setStyleSheet(f"color:{t['accent']};")
        self.tbar.title.setStyleSheet(f"color:{t['fg']};")
        self.tbar.badge.setStyleSheet(f"color:{t['accent']};")
        bs = f"QPushButton{{color:{t['fg']}99;background:transparent;border:none;font-size:12px;}}QPushButton:hover{{background:{t['border']};color:{t['fg']};}}"
        self.tbar.b_min.setStyleSheet(bs)
        self.tbar.b_max.setStyleSheet(bs)
        self.tbar.b_cls.setStyleSheet(bs + f"QPushButton:hover{{background:#e81123;color:white;border-top-right-radius:{R}px;}}")
        for s in (self.sep1, self.sep2):
            s.setStyleSheet(f"background-color:{t['border']};")

        self.output.setStyleSheet(f"""
            QTextEdit#output{{background-color:{t['bg']};color:{t['fg']};border:none;padding:12px 14px;selection-background-color:{t['accent']};selection-color:{t['bg']};}}
            QScrollBar:vertical{{background:{t['bg']};width:10px;margin:0;border-radius:5px;}}
            QScrollBar::handle:vertical{{background:{t['border']};min-height:30px;border-radius:5px;}}
            QScrollBar::handle:vertical:hover{{background:{t['accent']}88;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}
        """)

        self.inp_widget.setStyleSheet(f"QWidget#inp_widget{{background-color:{t['bg']};}}")
        self.prompt_lbl.setStyleSheet(f"color:{t['prompt']};")
        self.input.setStyleSheet(f"""
            QLineEdit#cmd_input{{
                background-color:{t['input_bg']};color:{t['fg']};border:none;
                border-bottom:1px solid {t['border']};padding:4px 0;{glow}
            }}
            QLineEdit#cmd_input:focus{{border-bottom:1px solid {t['accent']};}}
        """)
        self.stop_btn_input.setStyleSheet(f"""
            QPushButton#stop_btn_input{{
                background-color:{t['error']};color:white;border:none;
                border-radius:4px;padding:2px 8px;font-weight:bold;
            }}
            QPushButton#stop_btn_input:hover{{background-color:{t['error']}CC;}}
        """)

        self.status_bar.setStyleSheet(f"QFrame#status_bar{{background-color:{t['title_bg']};border-bottom-left-radius:{R}px;border-bottom-right-radius:{R}px;}}")
        self.mode_lbl.setStyleSheet(f"color:{t['accent']};")
        self.cwd_lbl.setStyleSheet(f"color:{t['fg']}88;")
        self.run_lbl.setStyleSheet(f"color:{t['warning']};")
        self.tbar.badge.setText(f"● {t['name']}")

    # ── Window ──

    def toggle_max(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - 18, self.height() - 18)

    def focusInEvent(self, e):
        self.input.setFocus()
        super().focusInEvent(e)

    def closeEvent(self, e):
        self._alive = False
        if self._pty:
            try: self._pty_write('exit\r')
            except: pass
            try:
                if WINPTY_V2: self._pty.terminate()
                else: self._pty.close()
            except: pass
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = CmdWrapper()
    s = app.primaryScreen()
    if s:
        g = s.geometry()
        w.move((g.width() - w.width()) // 2, (g.height() - w.height()) // 2)
    w.show()
    w.input.setFocus()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()