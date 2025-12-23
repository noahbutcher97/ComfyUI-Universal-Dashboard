#!/bin/bash

# ==============================================================================
# ComfyUI Automated Installer for macOS
# Robust, Resilient, Apple Silicon Optimized
# With Interactive Folder Selection
# ==============================================================================

# --- Configuration ---
COMFY_REPO_URL="https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_REPO_URL="https://github.com/ltdrdata/ComfyUI-Manager.git"
PYTHON_VERSION="python@3.10"

# --- Logging & Error Handling ---
log() { echo -e "\033[1;32m[INFO]\033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; exit 1; }
check_error() { if [ $? -ne 0 ]; then error "$1"; fi; }

# --- 1. OS & Arch Detection ---
log "Checking Environment..."
[[ "$(uname)" != "Darwin" ]] && error "macOS only."
ARCH_NAME="$(uname -m)"
log "Architecture: $ARCH_NAME"

# --- 2. Interactive Install Location Selection ---
log "Launching Finder to select installation folder..."
echo "Please look at the popup window to select a folder."

# Uses AppleScript to pop up a native folder selection dialog
PARENT_DIR=$(osascript -e 'POSIX path of (choose folder with prompt "Select the folder where you want to install ComfyUI (a new ComfyUI folder will be created inside):")' 2>/dev/null)

if [ -z "$PARENT_DIR" ]; then
    warn "User cancelled or no folder selected. Defaulting to Home directory ($HOME)."
    PARENT_DIR="$HOME"
fi

# Remove trailing slash if present to avoid //
PARENT_DIR="${PARENT_DIR%/}"
INSTALL_DIR="$PARENT_DIR/ComfyUI"

log "✅ ComfyUI will be installed to: $INSTALL_DIR"

# --- 3. Homebrew Check/Install ---
if ! command -v brew &> /dev/null; then
    log "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    [[ "$ARCH_NAME" == "arm64" ]] && eval "$(/opt/homebrew/bin/brew shellenv)" || eval "$(/usr/local/bin/brew shellenv)"
fi

# --- 4. Install Dependencies ---
log "Installing Python 3.10 and Git..."
brew install git $PYTHON_VERSION
check_error "Dependency install failed."

# --- 5. Clone / Update Repository ---
if [ -d "$INSTALL_DIR" ]; then
    log "Updating existing installation at $INSTALL_DIR..."
    cd "$INSTALL_DIR" && git pull
else
    log "Cloning ComfyUI to $INSTALL_DIR..."
    git clone "$COMFY_REPO_URL" "$INSTALL_DIR"
    check_error "Clone failed."
    cd "$INSTALL_DIR"
fi

# --- 6. Virtual Environment ---
log "Setting up Virtual Environment..."
PYTHON_EXEC="$(brew --prefix $PYTHON_VERSION)/bin/python3"
[[ ! -f "$PYTHON_EXEC" ]] && PYTHON_EXEC="python3"

"$PYTHON_EXEC" -m venv venv
source venv/bin/activate
pip install --upgrade pip

# --- 7. Install PyTorch & Requirements ---
log "Installing PyTorch (MPS/Metal optimized)..."
pip install torch torchvision torchaudio
pip install -r requirements.txt
check_error "Python requirements failed."

# --- 8. Install ComfyUI Manager ---
log "Installing Manager..."
mkdir -p custom_nodes
cd custom_nodes
if [ ! -d "ComfyUI-Manager" ]; then
    git clone "$MANAGER_REPO_URL"
else
    cd ComfyUI-Manager && git pull && cd ..
fi
cd ..

# --- 9. Create Desktop Launcher ---
LAUNCHER="$HOME/Desktop/Run_ComfyUI.command"
cat <<EOF > "$LAUNCHER"
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
echo "Launching ComfyUI..."
python main.py --force-fp16 --auto-launch
EOF
chmod +x "$LAUNCHER"

echo ""
echo "============================================================"
echo "✅ SETUP COMPLETE"
echo "============================================================"
echo "ComfyUI Installed at: $INSTALL_DIR"
echo "Launch it using the 'Run_ComfyUI.command' shortcut on your Desktop."
echo "============================================================"
