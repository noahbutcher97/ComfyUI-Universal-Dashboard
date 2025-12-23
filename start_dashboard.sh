#!/bin/bash

# ==============================================================================
# ComfyUI Universal Dashboard - Mac/Linux Launcher
# ==============================================================================

echo "Initializing Dashboard..."

OS_TYPE="$(uname)"

# --- Dependency Checks ---

if [ "$OS_TYPE" == "Darwin" ]; then
    # macOS: Use Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        ARCH_NAME="$(uname -m)"
        if [[ "$ARCH_NAME" == "arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
    
    if ! command -v python3 &> /dev/null; then
        brew install python@3.10
    fi
    brew install python-tk@3.10 2>/dev/null

elif [ "$OS_TYPE" == "Linux" ]; then
    if ! command -v python3 &> /dev/null; then
        echo "Python3 not found. Please install python3-venv and python3-pip."
        exit 1
    fi
    python3 -c "import tkinter" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Missing 'tkinter'. Installing..."
        if command -v apt &> /dev/null; then sudo apt update && sudo apt install -y python3-tk
        elif command -v pacman &> /dev/null; then sudo pacman -S --noconfirm tk
        elif command -v dnf &> /dev/null; then sudo dnf install -y python3-tkinter
        fi
    fi
fi

# --- Environment Setup ---

DASHBOARD_DIR="$HOME/.comfy_dashboard_tools"
mkdir -p "$DASHBOARD_DIR"

if [ ! -d "$DASHBOARD_DIR/venv" ]; then
    echo "Setting up Dashboard tools..."
    python3 -m venv "$DASHBOARD_DIR/venv"
fi

source "$DASHBOARD_DIR/venv/bin/activate"

# --- Install & Run ---
pip install customtkinter psutil >/dev/null 2>&1

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
python3 "$SCRIPT_DIR/dashboard.py"

# --- Error Catch ---
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================"
    echo "ERROR: Dashboard crashed with exit code $EXIT_CODE"
    echo "========================================================"
    read -p "Press Enter to exit..."
fi
