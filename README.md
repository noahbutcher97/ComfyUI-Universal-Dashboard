# ComfyUI Universal Dashboard

A cross-platform (Windows, macOS, Linux) installer and management dashboard for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## Features

- **🖥️ Universal Dashboard:** A beautiful terminal-based UI that works on all operating systems.
- **🚀 One-Click Install:** Automatically sets up Python, Virtual Environment, and Git.
- **🧠 Smart Detection:** 
    - **Windows:** Detects NVIDIA GPUs and installs CUDA-enabled PyTorch.
    - **macOS:** Installs Metal (MPS) optimized PyTorch for Apple Silicon.
- **⚡ Management:** Install Manager, Download Models, and Update with one click.
- **🧪 Smoke Test:** Verifies the server actually starts and responds before you try to use it.

## Quick Start

### Windows
Double-click **`launch.cmd`**.

### macOS / Linux
Open your terminal and run:
```bash
bash launch.cmd
```

## Dashboard Preview

The dashboard provides real-time system metrics (CPU/RAM/Disk) and allows you to manage your ComfyUI installation.

1.  **Install/Update:** Clones the repo and sets up the venv.
2.  **Smoke Test:** Starts a background instance to verify health.
3.  **Launch:** Starts ComfyUI with the best flags for your OS.

## Requirements

- **Internet Connection**
- **Windows:** Python 3.10+ (Check "Add to PATH" during install)
- **macOS:** Homebrew (The script will attempt to install it if missing)
- **Linux:** `python3-venv`, `python3-pip`, `git`
