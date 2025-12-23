#!/bin/bash

# ==============================================================================
# ComfyUI GUI Installer for macOS
# ==============================================================================

# --- Configuration & Defaults ---
COMFY_REPO_URL="https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_REPO_URL="https://github.com/ltdrdata/ComfyUI-Manager.git"
IMPACT_PACK_REPO_URL="https://github.com/ltdrdata/ComfyUI-Impact-Pack.git"
PYTHON_VERSION="python@3.10"

# --- Helper: Run AppleScript ---
# Executes a snippet of AppleScript and returns the result
osascript_cmd() {
    osascript -e "$1" 2>/dev/null
}

# --- Helper: GUI Dialogs ---
show_alert() {
    osascript_cmd "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon note with title \"ComfyUI Installer\""
}

ask_confirmation() {
    RESULT=$(osascript_cmd "display dialog \"$1\" buttons {\"Cancel\", \"$2\"} default button \"$2\" with icon caution with title \"ComfyUI Installer\"")
    if [[ "$RESULT" != *"button returned:$2"* ]]; then
        echo "User Cancelled."
        exit 0
    fi
}

# --- 1. Welcome Screen ---
clear
echo "=========================================="
echo "   ComfyUI macOS Installer - GUI Mode"
echo "=========================================="

ask_confirmation "Welcome to the ComfyUI Installer for Mac.\n\nThis will guide you through setting up Python, ComfyUI, and necessary dependencies.\n\nClick 'Start' to begin." "Start"

# --- 2. Configuration Options ---
# Returns a comma-separated list of selected items
OPTIONS_SELECTED=$(osascript_cmd 'set myOptions to {"Install ComfyUI Manager", "Create Desktop Shortcut", "Auto-Launch after Install", "Install Impact Pack (Optional)"}
set selectedOptions to choose from list myOptions with title "Configuration" with prompt "Select features to install (Cmd+Click to select multiple):" default items {"Install ComfyUI Manager", "Create Desktop Shortcut", "Auto-Launch after Install"} with multiple selections allowed
if selectedOptions is false then return "CANCEL"
return selectedOptions')

if [[ "$OPTIONS_SELECTED" == "CANCEL" ]]; then
    echo "User cancelled configuration."
    exit 0
fi

# Parse Options
DO_INSTALL_MANAGER=false
DO_CREATE_SHORTCUT=false
DO_AUTO_LAUNCH=false
DO_INSTALL_IMPACT=false

[[ "$OPTIONS_SELECTED" == *"Install ComfyUI Manager"* ]] && DO_INSTALL_MANAGER=true
[[ "$OPTIONS_SELECTED" == *"Create Desktop Shortcut"* ]] && DO_CREATE_SHORTCUT=true
[[ "$OPTIONS_SELECTED" == *"Auto-Launch after Install"* ]] && DO_AUTO_LAUNCH=true
[[ "$OPTIONS_SELECTED" == *"Install Impact Pack"* ]] && DO_INSTALL_IMPACT=true

# --- 3. Install Location ---
PARENT_DIR=$(osascript_cmd 'POSIX path of (choose folder with prompt "Select the folder where you want to install ComfyUI:")')

if [ -z "$PARENT_DIR" ]; then
    echo "No folder selected. Exiting."
    exit 0
fi

PARENT_DIR="${PARENT_DIR%/}" # Strip trailing slash
INSTALL_DIR="$PARENT_DIR/ComfyUI"

echo "Target Directory: $INSTALL_DIR"

# --- 4. Main Installation Logic ---

# (We keep the terminal output visible here so the user sees progress)

echo "----------------------------------------------------------------"
echo "Starting Installation..."
echo "----------------------------------------------------------------"

# A. Homebrew
if ! command -v brew &> /dev/null; then
    echo "🍺 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add to path
    ARCH_NAME="$(uname -m)"
    if [[ "$ARCH_NAME" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

# B. Dependencies
echo "📦 Installing System Dependencies (Git, Python 3.10)..."
brew install git $PYTHON_VERSION

# C. Clone
if [ -d "$INSTALL_DIR" ]; then
    echo "🔄 Updating existing ComfyUI..."
    cd "$INSTALL_DIR" && git pull
else
    echo "⬇️  Cloning ComfyUI..."
    git clone "$COMFY_REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# D. Virtual Env
echo "🐍 Setting up Python Environment..."
PYTHON_EXEC="$(brew --prefix $PYTHON_VERSION)/bin/python3"
[[ ! -f "$PYTHON_EXEC" ]] && PYTHON_EXEC="python3"

"$PYTHON_EXEC" -m venv venv
source venv/bin/activate
pip install --upgrade pip

# E. Requirements
echo "🔥 Installing PyTorch & Requirements..."
pip install torch torchvision torchaudio
pip install -r requirements.txt

# F. Custom Nodes
mkdir -p custom_nodes
cd custom_nodes

if [ "$DO_INSTALL_MANAGER" = true ]; then
    echo "🔧 Installing ComfyUI Manager..."
    if [ ! -d "ComfyUI-Manager" ]; then
        git clone "$MANAGER_REPO_URL"
    else
        cd ComfyUI-Manager && git pull && cd ..
    fi
fi

if [ "$DO_INSTALL_IMPACT" = true ]; then
    echo "💥 Installing Impact Pack..."
    if [ ! -d "ComfyUI-Impact-Pack" ]; then
        git clone "$IMPACT_PACK_REPO_URL"
        # Impact pack has its own requirements
        echo "   Installing Impact Pack requirements..."
        cd ComfyUI-Impact-Pack
        pip install -r requirements.txt
        # Run install.py if it exists
        if [ -f "install.py" ]; then python install.py; fi
        cd ..
    else
        cd ComfyUI-Impact-Pack && git pull && cd ..
    fi
fi
cd ..

# G. Shortcut
if [ "$DO_CREATE_SHORTCUT" = true ]; then
    echo "📝 Creating Desktop Shortcut..."
    LAUNCHER="$HOME/Desktop/Run_ComfyUI.command"
    cat <<EOF > "$LAUNCHER"
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
echo "Launching ComfyUI..."
python main.py --force-fp16 --auto-launch
EOF
    chmod +x "$LAUNCHER"
fi

# --- 5. Completion ---

echo "----------------------------------------------------------------"
echo "✅ Installation Complete!"
echo "----------------------------------------------------------------"

FINAL_MSG="Installation successful!\n\nLocation: $INSTALL_DIR"

if [ "$DO_AUTO_LAUNCH" = true ]; then
    FINAL_MSG="$FINAL_MSG\n\nLaunching ComfyUI now..."
    show_alert "$FINAL_MSG"
    open "$HOME/Desktop/Run_ComfyUI.command"
else
    show_alert "$FINAL_MSG"
fi
