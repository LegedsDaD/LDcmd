<div align="center">

# 🚀 LDcmd (LegendDaD's Command prompt )

### A Modern, Theme-Aware Windows Command Prompt Wrapper

Transform the classic Windows CMD into a beautiful, interactive terminal with customizable themes, PTY support, command history, tab completion, and a polished developer experience.

<br>

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/github/license/YOUR_USERNAME/LDcmd?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/YOUR_USERNAME/LDcmd?style=for-the-badge)
![Issues](https://img.shields.io/github/issues/YOUR_USERNAME/LDcmd?style=for-the-badge)

</div>

---

## ✨ Overview

**LDcmd** is a modern desktop wrapper around the Windows Command Prompt built with **PyQt6**.

Instead of using the plain black CMD window, LDcmd provides a beautiful interface featuring multiple themes, interactive command execution, PTY support, command history, tab completion, custom built-in commands, and a polished developer-focused experience.

---

## 📸 Features

### 🎨 Beautiful Themes

Switch themes instantly with:

```bash
ldcmd theme <theme-name>
```

Available themes:

| Theme | Description |
|---------|-------------|
| 🌙 Dark | Clean modern dark theme |
| ☀️ Light | Bright and professional |
| 🔮 Glassmorphism | Frosted-glass futuristic look |
| 💻 DevCore | GitHub-inspired developer theme |
| 🌈 Cyberpunk | Neon futuristic terminal |

---
## 🖼️ Theme Showcase

### 🌙 Dark
Modern and clean daily-driver theme :

<img width="600" height="300" alt="ldcmd_dark" src="https://github.com/user-attachments/assets/b9b2e4bd-a816-41b9-861c-af80276c4f8c" />


### ☀️ Light
Professional light-mode experience:

<img width="600" height="300" alt="ldcmd_light" src="https://github.com/user-attachments/assets/044909d7-7262-475d-8e69-d5c61d6ef829" />


### 🔮 Glassmorphism
Blur-inspired futuristic interface :

<img width="600" height="300" alt="ldcmd_glassmorphism" src="https://github.com/user-attachments/assets/329143dd-ed3c-4d7a-bb33-7bfeb6c1c99d" />


### 💻 DevCore
GitHub-inspired developer workspace :

<img width="600" height="300" alt="ldcmd_devcore" src="https://github.com/user-attachments/assets/62967a32-3e10-4b2a-8081-28b23b65b0a8" />


### 🌈 Cyberpunk
Neon aesthetics with glowing accents :

<img width="600" height="300" alt="ldcmd_cyberpunk" src="https://github.com/user-attachments/assets/baaf8412-c8a3-47b9-91c2-c5d0419b9043" />


### ⚡ Interactive Terminal

- Real-time command execution
- Interactive PTY support
- Supports CLI applications
- Supports keyboard-driven programs
- Instant key forwarding

---

### ⌨️ Smart Input

- Command history navigation
- Tab completion
- Multi-directory support
- Built-in directory navigation
- Quick terminal restart

---

### 🛑 Process Control

- Stop running processes
- Ctrl+C emulation
- Force kill support
- Process state indicators

---

### 📋 Better Output

- ANSI cleanup
- Clean rendering
- Select and copy text
- Auto-scroll
- Rich terminal display

---

### 🖥️ Modern Window

- Custom title bar
- Frameless design
- Window dragging
- Resize support
- Minimize / Maximize controls

---

## 🎯 Built-in Commands

### General

```bash
ldcmd
ldcmd info
ldcmd version
ldcmd help
```

### Themes

```bash
ldcmd theme
ldcmd theme dark
ldcmd theme light
ldcmd theme glassmorphism
ldcmd theme devcore
ldcmd theme cyberpunk
```

### Navigation

```bash
ldcmd pwd
ldcmd cd <path>
```

### Terminal

```bash
ldcmd cls
ldcmd clear
ldcmd restart
```

---

## 🚀 Installation

### Download **.exe**(Recommended option)

Go to [Releases](https://github.com/LegedsDaD/LDcmd/releases/tag/Standalone_LDcmd) and [Download](https://github.com/LegedsDaD/LDcmd/releases/tag/Standalone_LDcmd/LDcmd.exe) the executable LDcmd.exe from their .

### Clone Repository

```bash
git clone https://github.com/LegedsDaD/LDcmd.git
cd LDcmd
```

### Install Dependencies

```bash
pip install PyQt6 pywinpty
```

### Run

```bash
python ldcmd.py
```

---

### 📦 Building an Executable

Using PyInstaller:

```bash
pip install pyinstaller
```

```bash
pyinstaller --onefile --windowed ldcmd.py
```

Output:

```text
dist/
└── LDcmd.exe
```

Users **do not need Python installed** when using the generated executable.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|-----------|---------|
| Enter | Execute command |
| Tab | Auto-complete |
| ↑ | Previous command |
| ↓ | Next command |
| Ctrl + L | Clear screen |
| Ctrl + C | Interrupt process |
| Esc | Stop running process |
| Ctrl + A | Select all output |

---

## 🏗️ Architecture

```text
┌─────────────────────────┐
│        LDcmd UI         │
├─────────────────────────┤
│        PyQt6 GUI        │
├─────────────────────────┤
│   PTY / Subprocess API  │
├─────────────────────────┤
│     Windows CMD.exe     │
└─────────────────────────┘
```

---

## 🔧 Technologies

- Python
- PyQt6
- pywinpty
- Windows Command Prompt
- QProcess
- Native Windows APIs

---

## 🌟 Why LDcmd?

✅ Beautiful modern interface

✅ Interactive PTY support

✅ Multiple built-in themes

✅ Smart command handling

✅ Fully standalone executable

✅ Lightweight and fast

✅ Familiar CMD workflow

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

### ⭐ If you like LDcmd, consider starring the repository!

Built with ❤️ using Python & PyQt6 by @LegedsDaD

</div>
