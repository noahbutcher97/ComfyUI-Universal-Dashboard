# AI Universal Suite (formerly ComfyUI Dashboard)

## Project Overview

**AI Universal Suite** is a cross-platform (Windows, macOS, Linux) desktop application designed to manage and streamline the installation and usage of various AI development tools, with a primary focus on **ComfyUI** and AI CLI agents (Gemini, Claude, DeepSeek, etc.).

It features a modern GUI built with **CustomTkinter** that provides:
*   **System Status**: Auto-detection of GPU and VRAM.
*   **Dev Tools**: Management of Node.js and AI CLI installations.
*   **ComfyUI Studio**: A "Smart Wizard" for installing and configuring ComfyUI with optimized settings and model recipes based on hardware capabilities.
*   **Settings & Keys**: A secure vault for managing API keys.

## Architecture & Tech Stack

*   **Language**: Python 3.10+
*   **GUI Framework**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern wrapper around Tkinter)
*   **OS Support**: Windows, macOS, Linux
*   **Configuration**: JSON-based config stored in `~/.ai_universal_suite/config.json`

### Key Components

*   **`src/dashboard.py`**: The single-file source containing the entire application logic.
    *   **`App` Class**: Main GUI application class inheriting from `ctk.CTk`.
    *   **`DevService` Class**: Static methods for managing Node.js/NPM and CLI tool installations.
    *   **`ComfyService` Class**: Static methods for hardware detection and generating ComfyUI installation manifests.
    *   **`main_wrapper`**: Entry point with error handling.

## Installation & Usage

### 🚀 Standard Launchers

The project includes platform-specific scripts to automate the setup (creating virtual environment, installing dependencies, launching the app).

*   **Windows**: Double-click `Run_Windows.bat`
*   **macOS**: Double-click `Run_Mac.command`
*   **Linux**: Run `Run_Linux.sh`

### 🛠️ Manual Development Setup

1.  **Prerequisites**: Ensure Python 3.10+ is installed.
2.  **Virtual Environment**:
    The project typically uses a local virtual environment located at `.dashboard_env/venv`.
    ```bash
    python -m venv .dashboard_env/venv
    # Activate:
    # Windows: .dashboard_env\venv\Scripts\activate
    # Unix: source .dashboard_env/venv/bin/activate
    ```
3.  **Dependencies**:
    Install required packages (primarily `customtkinter`, `requests`, `psutil`, `keyring`).
    ```bash
    pip install customtkinter requests psutil keyring
    ```
4.  **Run**:
    ```bash
    python src/main.py
    ```

## Development Conventions

*   **Modular Architecture**: Logic is split into `src/ui`, `src/services`, and `src/config`.
*   **Entry Point**: `src/main.py` handles initialization and error trapping.
*   **Services**: Core logic resides in `src/services/` (ComfyUI management, System checks, CLI tools).
*   **Security**: API Keys are stored in the OS Keyring via `src/config/manager.py`.
*   **Error Handling**: The application uses a "Crash Catcher" wrapper (`main_wrapper`) to catch top-level exceptions and display them or keep the window open for debugging.
*   **External Tools**: The app relies on external binaries (`git`, `node`, `npm`, `nvidia-smi`) which it attempts to detect or install.
