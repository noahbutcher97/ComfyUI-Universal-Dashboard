# ComfyUI Universal Dashboard

A cross-platform (Windows, macOS, Linux) installer and management dashboard for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## 🚀 Quick Start

Download this repository, unzip it, and double-click the file for your system:

| Operating System | File to Double-Click |
| :--- | :--- |
| **Windows** | **`Run_Windows.bat`** |
| **macOS** | **`Run_Mac.command`** |
| **Linux** | **`Run_Linux.sh`** |

*(Note for Mac Users: If it says "Unidentified Developer", right-click the file -> Open -> Open).*

## Features

- **🖥️ Universal Dashboard:** A beautiful terminal-based UI that works on all operating systems.
- **🚀 One-Click Install:** Automatically sets up Python, Virtual Environment, and Git.
- **🧠 Smart Detection:** 
    - **Windows:** Detects NVIDIA GPUs and installs CUDA-enabled PyTorch.
    - **macOS:** Installs Metal (MPS) optimized PyTorch for Apple Silicon.
- **⚡ Management:** Install Manager, Download Models, and Update with one click.
- **🧪 Smoke Test:** Verifies the server actually starts and responds before you try to use it.

## Requirements

- **Internet Connection**
- **Windows:** Python 3.10+ (Check "Add to PATH" during install)
- **macOS:** Homebrew (The script will attempt to install it if missing)
- **Linux:** `python3-venv`, `python3-pip`, `git`
