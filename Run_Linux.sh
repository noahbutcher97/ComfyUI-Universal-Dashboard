#!/bin/bash
cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please install via: brew install python@3.10"
    else
        echo "Please install via your package manager (apt/dnf/pacman)."
    fi
    exit 1
fi

# Delegate to Universal Launcher
python3 launch.py
