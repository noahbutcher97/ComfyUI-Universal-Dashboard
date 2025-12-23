#!/bin/bash

# ==============================================================================
# ComfyUI Universal Dashboard - Boot Script
# ==============================================================================

# Resolve Root Dir (One level up from bin)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$SCRIPT_DIR/.."

echo "Initializing Dashboard..."

OS_TYPE="$(uname)"

if [ "$OS_TYPE" == "Darwin" ]; then
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [[ "$(uname -m)" == "arm64" ]]; then eval "$(/opt/homebrew/bin/brew shellenv)"; else eval "$(/usr/local/bin/brew shellenv)"; fi
    fi
    if ! command -v python3 &> /dev/null; then brew install python@3.10; fi
    brew install python-tk@3.10 2>/dev/null

elif [ "$OS_TYPE" == "Linux" ]; then
    if ! command -v python3 &> /dev/null; then echo "Python3 not found."; exit 1; fi
    python3 -c "import tkinter" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Missing 'tkinter'. Installing..."
        if command -v apt &> /dev/null; then sudo apt update && sudo apt install -y python3-tk
        elif command -v pacman &> /dev/null; then sudo pacman -S --noconfirm tk
        elif command -v dnf &> /dev/null; then sudo dnf install -y python3-tkinter
        fi
    fi
fi

# Environment
DASH_ENV="$ROOT_DIR/.dashboard_env"
mkdir -p "$DASH_ENV"

if [ ! -d "$DASH_ENV/venv" ]; then
    echo "Setting up venv..."
    python3 -m venv "$DASH_ENV/venv"
fi

source "$DASH_ENV/venv/bin/activate"
pip install customtkinter psutil requests >/dev/null 2>&1

# Launch
python3 "$ROOT_DIR/src/dashboard.py"

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Crashed with exit code $EXIT_CODE"
    read -p "Press Enter..."
fi
