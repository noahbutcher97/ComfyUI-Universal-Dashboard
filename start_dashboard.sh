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
        echo "Installing Homebrew (Required for macOS dependencies)..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        ARCH_NAME="$(uname -m)"
        if [[ "$ARCH_NAME" == "arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "Installing Python 3.10..."
        brew install python@3.10
    fi

elif [ "$OS_TYPE" == "Linux" ]; then
    # Linux: Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "Python3 not found. Please install python3-venv and python3-pip using your package manager."
        echo "Example: sudo apt install python3 python3-venv python3-pip git"
        exit 1
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
pip install rich psutil >/dev/null 2>&1

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
python3 "$SCRIPT_DIR/dashboard.py"
