# LDcmd — Colorful Windows CMD Wrapper

A modern, theme-aware terminal wrapper for Windows Command Prompt built with **Python** and **PyQt6**. 
LDcmd replaces the boring default CMD aesthetic with a sleek, customizable UI featuring 5 beautiful themes, non-blocking command execution, and a fully interactive experience.

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green?logo=qt)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)

---

## Screenshots
Your Command Line before :

<img width="600" height="400" alt="cmd" src="https://github.com/user-attachments/assets/29f7270a-3d4e-4013-be82-b017d5e1c0e1" />

Your Command Line using LDcmd :

<img width="600" height="400" alt="LDcmd" src="https://github.com/user-attachments/assets/37ca2f91-dc82-462b-bbeb-504d7c2bc0d4" />

---

## Themes
Glassmorphism :



## Features

- **5 Built-in Themes** — Dark, Light, Glassmorphism, DevCore, Cyberpunk
- **Non-Blocking UI** — Run commands via `QProcess`; the terminal never freezes
- **Live Status Indicator** — Shows "⏳ Running..." and a Stop button while commands execute
- **Command History** — Navigate with `↑` / `↓` arrow keys
- **Tab Auto-Complete** — Auto-completes files and directories in the current path
- **Custom Window** — Frameless design with a draggable title bar, minimize/maximize/close, and edge resizing
-  *Built-in Commands** — `theme`, `cd`, `set`, `cls`, `pwd`, `help`, `exit`
- **Pass-through** — Any unrecognized command is sent directly to real `cmd.exe`

---

## Installation

### Prerequisites
- **Windows OS** (uses `cmd.exe` under the hood)

### Install Dependencies

```bash
pip install PyQt6
```

## Download

### Running main python script

## Keyboard Shortcuts
| Shortcut	| Action |
| Enter	| Execute the typed command |
| ↑ / ↓	| Navigate command history |
| Tab	| Auto-complete file/folder names |
|Esc	| Stop a running command / Clear input |
| Ctrl + L	| Clear the terminal screen |
| Double-click title bar	| Maximize / Restore window |

---
