#!/bin/bash
cd "$(dirname "$0")"

# Function to install Python
install_python() {
    echo "[INIT] Python 3 missing. Attempting installation..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &> /dev/null; then
            echo "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.10 git
    elif command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-tk git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-tk git
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python python-tk git
    else
        echo "[ERROR] Could not detect package manager. Please install Python 3.10+ manually."
        exit 1
    fi
}

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    install_python
fi

# 2. Check Git
if ! command -v git &> /dev/null; then
    echo "[INIT] Git missing. Installing..."
    install_python # Re-runs install block which includes git
fi

# 3. Launch
python3 launch.py