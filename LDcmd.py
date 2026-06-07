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
    Qt, QSize, QTimer, pyqtSignal, QProcess, QProcessEnvironment, QObject, QEvent
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
        from winpty import PTY as _WinPTY
        WinPTY = _WinPTY
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
        input_bg="#11111b", selection="#585b7066", accent="#89b4fa",
        glow=False, glow_color=None, radius=10,
    ),
    "light": dict(
        name="Light", bg="#eff1f5", fg="#4c4f69", prompt="#1e66f5",
        error="#d20f39", success="#40a02b", warning="#df8e1d",
        info="#179299", title_bg="#e6e9ef", border="#ccd0da",
        input_bg="#e6e9ef", selection="#bcc0cc88", accent="#1e66f5",
        glow=False, glow_color=None, radius=10,
    ),
    "glassmorphism": dict(
        name="Glassmorphism", bg="#1a1a2e", fg="#e0e0ff", prompt="#00d4ff",
        error="#ff6b6b", success="#4ecdc4", warning="#ffe66d",
        info="#a8e6cf", title_bg="#16213e", border="#0f3460",
        input_bg="#16213e88", selection="#0f346066", accent="#00d4ff",
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
    """Clean terminal output: convert key escape sequences, strip the rest."""
    if not text:
        return ""

    text = re.sub(r'\x1b\[(?:0?|1)G', '\r', text)
    text = re.sub(r'\x1b\[\d+;1H', '\r', text)
    text = re.sub(r'\x1b\[H', '\r', text)
    text = re.sub(r'\x1b\[\d?D', '\b', text)
    text = re.sub(r'\x1b\[\d*J', '', text)
    text = re.sub(r'\x1b\[\d*K', '', text)
    text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
    text = re.sub(r'\x1b\][^\x1b]*\x1b\\', '', text)
    text = re.sub(r'\x1b\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]', '', text)
    text = re.sub(r'\x1b[\x40-\x5f]', '', text)
    text = text.replace('\x1b', '')
    text = re.sub(r'[\x80-\x9f]', '', text)

    cleaned = []
    for ch in text:
        c = ord(ch)
        if c in (0, 7, 27, 127):
            continue
        elif c == 8:
            cleaned.append('\b')
        elif c == 9:
            cleaned.append('  ')
        elif c == 10:
            cleaned.append('\n')
        elif c == 13:
            cleaned.append('\r')
        elif c < 32 or c == 0xFFFD:
            continue
        else:
            cleaned.append(ch)
    return ''.join(cleaned)


def find_cmd():
    sr = os.environ.get('SystemRoot', '')
    if sr:
        p = os.path.join(sr, 'System32', 'cmd.exe')
        if os.path.isfile(p):
            return p
    for base in [r'C:\Windows', r'D:\Windows']:
        p = os.path.join(base, 'System32', 'cmd.exe')
        if os.path.isfile(p):
            return p
    for d in os.environ.get('PATH', '').split(';'):
        p = os.path.join(d.strip(), 'cmd.exe')
        if os.path.isfile(p):
            return p
    return 'cmd.exe'


# ──────────────────────── TITLE BAR ─────────────────────────────

class TitleBar(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self._drag = None
        self.setFixedHeight(40)
        self._build()

    def _build(self):
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
        self._cmd_hist = []
        self._cmd_hist_idx = -1
        self._cmd_saved = ""

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
        QTimer.singleShot(100, lambda: self.cmd_input.setFocus())

    # ── Backend ──

    def _start_backend(self):
        if HAS_WINPTY:
            try:
                import winpty
                wdir = os.path.dirname(winpty.__file__)
                os.environ['PATH'] = os.environ.get('PATH', '') + ';' + wdir
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
                self._reader = threading.Thread(target=self._pty_read_loop, daemon=True)
                self._reader.start()
                self._print_welcome("PTY")
                return
            except Exception as e:
                self._pty = None
                self.mode = "subprocess"
                self._print_welcome("Subprocess", str(e))
                return
        self._print_welcome("Subprocess", "pywinpty not installed")

    def _print_welcome(self, mode_name, err=None):
        self.print_output(f"\n  Welcome to LDcmd  [{mode_name} mode]\n", "success")
        if err:
            self.print_output(f"  Note: {err}\n", "warning")
        self.print_output(f"  System : {platform.system()} {platform.release()} ({platform.machine()})\n", "info")
        self.print_output(f"  Python : {platform.python_version()}\n", "info")
        self.print_output(f"  CWD    : {self.cwd}\n\n", "info")
        self.print_output('  Type "ldcmd help" to view built-in choices\n\n', "warning")
        self._update_status()

    # ── PTY reader ──

    def _pty_read_loop(self):
        time.sleep(0.2)
        while self._alive and self._pty:
            try:
                if WINPTY_V2:
                    data = self._pty.read(4096)
                    if not data:
                        break
                else:
                    data = self._pty.read()
                    if not data:
                        try:
                            if not self._pty.is_alive:
                                break
                        except Exception:
                            break
                if data and self._alive:
                    self.new_output.emit(data)
            except Exception:
                if self._alive:
                    try:
                        if WINPTY_V2:
                            if not self._pty.isalive():
                                break
                        elif not self._pty.is_alive:
                            break
                    except Exception:
                        break
        if self._alive:
            self.new_output.emit("\n  [Process ended. Type 'ldcmd restart' to reopen.]\n")

    def _pty_write(self, data):
        if not self._pty:
            return
        try:
            if WINPTY_V2:
                self._pty.write(data)
            else:
                self._pty.write(data)
        except Exception:
            pass

    # ── Subprocess mode ──

    def _sub_run(self, cmd):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._killed = True
            self.process.kill()
            self.process.waitForFinished(500)
        self._killed = False
        self._program_running = True
        self._update_status()
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setWorkingDirectory(self.cwd)
        self.process.setProcessEnvironment(env)
        self.process.start("cmd.exe", ["/C", cmd])

    def _sub_read(self):
        data = self.process.readAllStandardOutput().data()
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("mbcs", errors="replace")
        self.print_output(clean_terminal_text(text), "fg")

    def _sub_finished(self, exit_code, exit_status):
        if self._killed:
            self._killed = False
            return
        self._finalize_line("fg")
        self._program_running = False
        self._stop_stage = 0
        self._update_status()

    def _sub_error(self, error):
        if self._killed:
            return
        msgs = {
            QProcess.ProcessError.FailedToStart: "Command not found",
            QProcess.ProcessError.Crashed: "Crashed",
            QProcess.ProcessError.Timedout: "Timed out",
        }
        self.print_output(f"\n  ✗ {msgs.get(error, 'Error')}\n", "error")
        self._program_running = False
        self._stop_stage = 0
        self._update_status()

    def _kill_subprocess(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._killed = True
            self.process.kill()
            self.process.waitForFinished(1000)
        self._finalize_line("fg")
        self.print_output("\n  ⛔ Stopped.\n", "warning")
        self._program_running = False
        self._stop_stage = 0
        self._update_status()

    # ── UI ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.inner = QFrame()
        self.inner.setObjectName("inner")
        col = QVBoxLayout(self.inner)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.tbar = TitleBar(self)

        self.sep1 = QFrame()
        self.sep1.setFixedHeight(1)
        self.sep1.setObjectName("sep")

        # Upper terminal history log
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 11))
        self.output.setFrameStyle(QFrame.Shape.NoFrame)
        self.output.setAcceptRichText(False)
        self.output.setObjectName("output")
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.output.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.output.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.sep_input = QFrame()
        self.sep_input.setFixedHeight(1)
        self.sep_input.setObjectName("sep")

        # ── SEPARATE COMMAND WRITING CONTAINER AT THE BOTTOM ──
        self.input_container = QWidget()
        self.input_container.setObjectName("input_container")
        self.input_container.setFixedHeight(42)
        ic_lay = QHBoxLayout(self.input_container)
        ic_lay.setContentsMargins(14, 0, 14, 0)
        ic_lay.setSpacing(4)

        self.prompt_lbl = QLabel(">")
        self.prompt_lbl.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.prompt_lbl.setObjectName("prompt_lbl")

        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(QFont("Consolas", 11))
        self.cmd_input.setFrame(False)
        self.cmd_input.setObjectName("cmd_input")
        self.cmd_input.installEventFilter(self) # For handling up/down/tab navigation hooks

        ic_lay.addWidget(self.prompt_lbl)
        ic_lay.addWidget(self.cmd_input, 1)

        self.sep2 = QFrame()
        self.sep2.setFixedHeight(1)
        self.sep2.setObjectName("sep")

        # Status Bar
        self.status_bar = QFrame()
        self.status_bar.setObjectName("status_bar")
        self.status_bar.setFixedHeight(32)
        sb_lay = QHBoxLayout(self.status_bar)
        sb_lay.setContentsMargins(14, 0, 14, 0)
        sb_lay.setSpacing(12)

        self.mode_lbl = QLabel("● Subprocess")
        self.mode_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.mode_lbl.setObjectName("mode_lbl")

        self.cwd_lbl = QLabel(self._short_cwd())
        self.cwd_lbl.setFont(QFont("Consolas", 9))
        self.cwd_lbl.setObjectName("cwd_lbl")

        self.run_lbl = QLabel("")
        self.run_lbl.setFont(QFont("Consolas", 9))
        self.run_lbl.setObjectName("run_lbl")

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedSize(80, 22)
        self.stop_btn.setVisible(False)
        self.stop_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_btn.clicked.connect(self._stop_clicked)

        sb_lay.addWidget(self.mode_lbl)
        sb_lay.addWidget(self.cwd_lbl)
        sb_lay.addStretch()
        sb_lay.addWidget(self.run_lbl)
        sb_lay.addWidget(self.stop_btn)

        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)

        col.addWidget(self.tbar)
        col.addWidget(self.sep1)
        col.addWidget(self.output, 1)
        col.addWidget(self.sep_input)
        col.addWidget(self.input_container)
        col.addWidget(self.sep2)
        col.addWidget(self.status_bar)
        main_lay.addWidget(self.inner)

    # ── Helpers ──

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

    def _update_status(self):
        self.mode_lbl.setText(f"● {self.mode.capitalize()}")
        self.cwd_lbl.setText(self._short_cwd())
        if self._program_running:
            if self._stop_stage == 2:
                self.run_lbl.setText("⚠ Stuck?")
                self.stop_btn.setText("☠ Force Kill")
            else:
                self.run_lbl.setText("⏳ Running...")
                self.stop_btn.setText("■ Stop")
            self.stop_btn.setVisible(True)
        else:
            self.run_lbl.setText("")
            self.stop_btn.setVisible(False)
            self._stop_stage = 0

    # ── Command Submission & Navigation Events ──

    def eventFilter(self, obj, event):
        """Intercepts special key entries inside the dedicated command input line box."""
        if obj == self.cmd_input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()

            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._submit_command()
                return True

            elif key == Qt.Key.Key_Escape:
                if self.mode == "pty" and self._pty:
                    self._pty_write('\x03')
                elif self.mode == "subprocess" and self._program_running:
                    self._kill_subprocess()
                return True

            elif key == Qt.Key.Key_L and mods & Qt.KeyboardModifier.ControlModifier:
                self.output.clear()
                self._line_buf = ""
                return True

            elif key == Qt.Key.Key_Up:
                if self._cmd_hist and self._cmd_hist_idx > 0:
                    if self._cmd_hist_idx == len(self._cmd_hist):
                        self._cmd_saved = self.cmd_input.text()
                    self._cmd_hist_idx -= 1
                    self.cmd_input.setText(self._cmd_hist[self._cmd_hist_idx])
                return True

            elif key == Qt.Key.Key_Down:
                if self._cmd_hist_idx < len(self._cmd_hist) - 1:
                    self._cmd_hist_idx += 1
                    self.cmd_input.setText(self._cmd_hist[self._cmd_hist_idx])
                elif self._cmd_hist_idx == len(self._cmd_hist) - 1:
                    self._cmd_hist_idx = len(self._cmd_hist)
                    self.cmd_input.setText(self._cmd_saved)
                return True

            elif key == Qt.Key.Key_Tab:
                self._tab_complete()
                return True

        return super().eventFilter(obj, event)

    def _submit_command(self):
        raw = self.cmd_input.text()
        cmd = raw.strip()
        
        # Log command echo visually into output log
        if cmd:
            self.print_output(f"\n> {raw}\n", "prompt")
            if not self._cmd_hist or self._cmd_hist[-1] != cmd:
                self._cmd_hist.append(cmd)
        else:
            self.print_output("\n>\n", "prompt")

        self.cmd_input.clear()
        self._cmd_hist_idx = len(self._cmd_hist)
        self._cmd_saved = ""

        if not cmd:
            return

        low = cmd.lower()
        parts = cmd.split()

        # Route custom commands instantly
        if low.startswith("ldcmd"):
            self._exec_ldcmd_suite(parts)
            return

        if low == "pwd":
            self.print_output(self.cwd + "\n", "fg")
            return

        if low.startswith("cd ") or low == "cd":
            self._cmd_cd(cmd)
            return

        # Backend Dispatching
        if self.mode == "pty" and self._pty:
            self._pty_write(cmd + '\r')
        else:
            self._sub_run(cmd)

    def _tab_complete(self):
        txt = self.cmd_input.text()
        if not txt:
            return
        parts = txt.rsplit(maxsplit=1)
        if txt.endswith(" "):
            partial, prefix = "", txt
        elif len(parts) > 1:
            partial, prefix = parts[-1], parts[0] + " "
        else:
            partial, prefix = txt, ""
        try:
            entries = os.listdir(self.cwd)
            matches = [en for en in entries if en.lower().startswith(partial.lower())]
            if len(matches) == 1:
                m = matches[0]
                if " " in m: m = f'"{m}"'
                if os.path.isdir(os.path.join(self.cwd, matches[0])):
                    m += os.sep
                self.cmd_input.setText(prefix + m)
            elif matches:
                self.print_output("\n" + "  ".join(matches) + "\n", "info")
        except Exception:
            pass

    # ── Built-in Execution Core Suite ──

    def _exec_ldcmd_suite(self, parts):
        if len(parts) == 1:
            self.print_output(f"  LDcmd v1.0  |  Active Engine: {self.mode}\n", "accent")
            self.print_output("  Type 'ldcmd help' to see options.\n", "info")
            return
            
        sub = parts[1].lower()
        
        if sub in ("list", "ls", "themes", "theme"):
            if len(parts) >= 3 and parts[2].lower() in THEMES:
                name = parts[2].lower()
                self.theme_name = name
                self.apply_theme(name)
                self.print_output(f"  ✓ Theme changed to {THEMES[name]['name']}\n", "success")
                return
            self.print_output("\n  Available Themes\n", "success")
            self.print_output("  ─────────────────────────────────────\n", "info")
            for n, t in THEMES.items():
                cur = "  ◄ current" if n == self.theme_name else ""
                c = "prompt" if n == self.theme_name else "fg"
                self.print_output(f"  ● {t['name']:16s}{cur}\n", c)
            self.print_output("\n  Usage: ldcmd <theme_name>\n", "warning")
            return
            
        if sub in THEMES:
            self.theme_name = sub
            self.apply_theme(sub)
            self.print_output(f"  ✓ Theme changed to {THEMES[sub]['name']}\n", "success")
            return
            
        if sub in ("cls", "clear"):
            self.output.clear()
            self._line_buf = ""
            return
            
        if sub == "help":
            self._cmd_help()
            return
            
        if sub == "restart":
            self._restart_pty()
            return
            
        self.print_output(f"  ✗ Unknown choice '{parts[1]}'. Use 'ldcmd help' for help board.\n", "error")

    def _cmd_cd(self, raw):
        parts = raw.split(maxsplit=1)
        if len(parts) == 1:
            self.print_output(self.cwd + "\n", "fg")
            return
        target = parts[1].strip().strip('"').strip("'")
        if target == "~":
            nd = os.path.expanduser("~")
        elif os.path.isabs(target):
            nd = os.path.normpath(target)
        else:
            nd = os.path.normpath(os.path.join(self.cwd, target))
        try:
            r = os.path.realpath(nd)
            if os.path.isdir(r):
                self.cwd = r
                self._update_status()
                # If running on winpty instance, match back-end environment working directory path explicitly
                if self.mode == "pty" and self._pty:
                    self._pty_write(f'cd /d "{r}"\r')
            else:
                self.print_output("  Path not found.\n", "error")
        except Exception:
            self.print_output("  Path not found.\n", "error")

    # ── Line Buffer Layout Drivers ──

    def print_output(self, text, color="fg"):
        if not text:
            return
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if ch == '\r':
                if i + 1 < n and text[i + 1] == '\n':
                    self._finalize_line(color)
                    i += 2
                    continue
                self._line_buf = ""
                i += 1
                continue
            if ch == '\n':
                self._finalize_line(color)
                i += 1
                continue
            if ch == '\b':
                if self._line_buf:
                    self._line_buf = self._line_buf[:-1]
                i += 1
                continue
            j = i
            while j < n and text[j] not in ('\r', '\n', '\b'):
                j += 1
            self._line_buf += text[i:j]
            i = j
        self._render_current_line(color)

    def _finalize_line(self, color):
        self._render_current_line(color)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText('\n')
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()
        self._line_buf = ""

    def _render_current_line(self, color):
        t = THEMES[self.theme_name]
        c = QColor(t.get(color, t["fg"]))
        bold = self.theme_name == "cyberpunk" and color in ("prompt", "info", "success")

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
            fmt.setForeground(c)
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            cursor.setCharFormat(fmt)
            cursor.insertText(self._line_buf)

        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    # ── Emergency Interrupters ──

    def _stop_clicked(self):
        if self.mode == "pty" and self._pty:
            if self._stop_stage < 2:
                for _ in range(5):
                    self._pty_write('\x03')
                self._stop_stage = 1
                self._update_status()
                QTimer.singleShot(2000, self._check_still_running)
            else:
                self._force_kill_pty()
        elif self.mode == "subprocess":
            self._kill_subprocess()

    def _check_still_running(self):
        if self._program_running:
            self._stop_stage = 2
            self._update_status()

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
        self._line_buf = ""
        self.print_output("\n  ☠ Force-killed. Type 'ldcmd restart' to rebuild back-end stream.\n", "error")

    def _on_output(self, data):
        clean = clean_terminal_text(data)
        if not clean:
            return
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

    # ── Help System ──

    def _cmd_help(self):
        self.print_output("\n  ╔═══════════════════════════════════════════╗\n", "accent")
        self.print_output("  ║          LDcmd  —  Help Board             ║\n", "accent")
        self.print_output("  ╠═══════════════════════════════════════════╣\n", "accent")
        self.print_output("  ║  ldcmd list          List theme libraries ║\n", "info")
        self.print_output("  ║  ldcmd <theme_name>  Change theme colors  ║\n", "info")
        self.print_output("  ║  ldcmd clear         Flush log visibility ║\n", "info")
        self.print_output("  ║  ldcmd restart       Rebuild PTY shell    ║\n", "info")
        self.print_output("  ║  ldcmd help          Open this directory  ║\n", "info")
        self.print_output("  ╠═══════════════════════════════════════════╣\n", "accent")
        self.print_output("  ║  cd <path>           Change Directory     ║\n", "fg")
        self.print_output("  ║  pwd                 Print layout location║\n", "fg")
        self.print_output(f"  ║  Active Mode: {self.mode:<28s}║\n", "accent")
        self.print_output("  ╠═══════════════════════════════════════════╣\n", "accent")
        self.print_output("  ║  Esc          Interrupt execution        ║\n", "fg")
        self.print_output("  ║  Ctrl+L       Flush terminal history window║\n", "fg")
        self.print_output("  ║  Up/Down      Navigate command history box║\n", "fg")
        self.print_output("  ║  Tab          Auto-complete names         ║\n", "fg")
        self.print_output("  ╚═══════════════════════════════════════════╝\n\n", "accent")

    def _restart_pty(self):
        if not HAS_WINPTY:
            self.print_output("  pywinpty not installed.\n\n", "error")
            return
        cmd = find_cmd()
        try:
            if WINPTY_V2:
                self._pty = PtyProcess.spawn(cmd, cwd=self.cwd, env=os.environ)
            else:
                self._pty = WinPTY(120, 30)
                self._pty.spawn(cmd)
            self.mode = "pty"
            self._program_running = False
            self._stop_stage = 0
            self._update_status()
            self._reader = threading.Thread(target=self._pty_read_loop, daemon=True)
            self._reader.start()
            self.print_output("  ✓ Terminal restarted [PTY mode]\n\n", "success")
        except Exception as e:
            self.print_output(f"  ✗ Restart failed: {e}\n\n", "error")

    # ── Theme Application Engine ──

    def apply_theme(self, name):
        t = THEMES[name]
        R = t["radius"]
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
        
        for s in (self.sep1, self.sep_input, self.sep2):
            s.setStyleSheet(f"background-color:{t['border']};")
            
        self.output.setStyleSheet(f"""
            QTextEdit#output{{background-color:{t['bg']};color:{t['fg']};border:none;padding:12px 14px;selection-background-color:{t['accent']};selection-color:{t['bg']};}}
            QScrollBar:vertical{{background:{t['bg']};width:10px;margin:0;border-radius:5px;}}
            QScrollBar::handle:vertical{{background:{t['border']};min-height:30px;border-radius:5px;}}
            QScrollBar::handle:vertical:hover{{background:{t['accent']}88;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}
        """)

        # Separate bottom command input styling
        self.input_container.setStyleSheet(f"QWidget#input_container{{background-color:{t['input_bg']};}}")
        self.prompt_lbl.setStyleSheet(f"color:{t['prompt']};padding-bottom:1px;")
        self.cmd_input.setStyleSheet(f"QLineEdit#cmd_input{{background:transparent;color:{t['fg']};border:none;}}")

        self.status_bar.setStyleSheet(f"QFrame#status_bar{{background-color:{t['title_bg']};border-bottom-left-radius:{R}px;border-bottom-right-radius:{R}px;}}")
        self.mode_lbl.setStyleSheet(f"color:{t['accent']};")
        self.cwd_lbl.setStyleSheet(f"color:{t['fg']}88;")
        self.run_lbl.setStyleSheet(f"color:{t['warning']};")
        self.stop_btn.setStyleSheet(f"QPushButton#stop_btn{{background-color:{t['error']};color:white;border:none;border-radius:4px;padding:2px 6px;font-weight:bold;}}QPushButton#stop_btn:hover{{background-color:{t['error']}CC;}}")
        self.tbar.badge.setText(f"● {t['name']}")

    # ── Window Resizing ──

    def toggle_max(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.grip.move(self.width() - 18, self.height() - 18)

    def focusInEvent(self, e):
        self.cmd_input.setFocus()
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
    window = CmdWrapper()
    scr = app.primaryScreen()
    if scr:
        g = scr.geometry()
        window.move((g.width() - window.width()) // 2, (g.height() - window.height()) // 2)
    window.show()
    window.cmd_input.setFocus()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()