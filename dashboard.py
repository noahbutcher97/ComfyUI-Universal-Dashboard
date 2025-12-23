import os
import sys
import shutil
import subprocess
import platform
import psutil
import json
import threading
import time
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

# --- Config & Constants ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ai_universal_suite")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "comfy_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
    "api_keys": {},
    "cli_scope": "user" # or 'system'
}

def load_config():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE): save_config(DEFAULT_CONFIG); return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

CONFIG = load_config()

# --- Logic: Dev Tools Service ---
class DevService:
    @staticmethod
    def is_node_installed():
        return shutil.which("node") is not None

    @staticmethod
    def is_npm_installed():
        return shutil.which("npm") is not None

    @staticmethod
    def install_node_cmd():
        sys_plat = platform.system()
        if sys_plat == "Darwin": return ["brew", "install", "node"]
        if sys_plat == "Windows": return ["winget", "install", "-e", "--id", "OpenJS.NodeJS"]
        return ["echo", "Please install Node.js manually on Linux"]

    @staticmethod
    def install_cli(cli_name, scope="user"):
        # Map friendly names to install commands
        # Scope: 'user' means no sudo/admin if possible, 'system' might need it.
        # For NPM, 'user' usually implies local, but CLI tools are usually global (-g).
        # We will assume -g for CLIs but warn user.
        
        cmds = {
            "Claude CLI": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
            "Gemini CLI": ["npm", "install", "-g", "gemini-chat-cli"], # Example package
            "Vercel (AI SDK)": ["npm", "install", "-g", "vercel"],
            "OpenAI CLI": ["pip", "install", "openai"],
            "Heroku CLI": ["npm", "install", "-g", "heroku"]
        }
        return cmds.get(cli_name, ["echo", "Unknown Tool"])

# --- Logic: Comfy Service ---
class ComfyService:
    MODEL_TYPES = {
        "Checkpoints": "checkpoints",
        "LoRAs": "loras",
        "VAE": "vae",
        "ControlNet": "controlnet"
    }
    
    @staticmethod
    def get_root_path(): return CONFIG["comfy_path"]

    @staticmethod
    def is_installed(): return os.path.exists(os.path.join(CONFIG["comfy_path"], "main.py"))

    @staticmethod
    def get_venv_python():
        path = CONFIG["comfy_path"]
        if platform.system() == "Windows": return os.path.join(path, "venv", "Scripts", "python.exe")
        return os.path.join(path, "venv", "bin", "python")

    @staticmethod
    def get_venv_pip():
        path = CONFIG["comfy_path"]
        if platform.system() == "Windows": return os.path.join(path, "venv", "Scripts", "pip.exe")
        return os.path.join(path, "venv", "bin", "pip")

    @staticmethod
    def detect_hardware():
        # Simple VRAM estimator (Platform specific)
        vram_gb = "Unknown"
        gpu_name = "Unknown"
        try:
            if shutil.which("nvidia-smi"):
                # Run nvidia-smi to get memory
                output = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]).decode()
                vram_gb = int(float(output.strip()) / 1024)
                gpu_name = "NVIDIA GPU"
            elif platform.system() == "Darwin" and platform.machine() == "arm64":
                gpu_name = "Apple Silicon"
                # Harder to get unified memory easily without apple-specific tools
                vram_gb = "Unified"
        except: pass
        return gpu_name, vram_gb

# --- UI Application ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Universal Suite")
        self.geometry("1200x800")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="AI Universal\nSuite", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 20))
        
        self.sidebar_btn(1, "Dashboard", "overview")
        self.sidebar_btn(2, "Dev Tools (CLI)", "devtools")
        self.sidebar_btn(3, "ComfyUI Studio", "comfyui")
        self.sidebar_btn(4, "Model Manager", "models")
        self.sidebar_btn(5, "Settings", "settings")
        
        ctk.CTkButton(self.sidebar, text="Exit", fg_color="transparent", border_width=1, command=self.destroy).pack(side="bottom", pady=20, padx=20, fill="x")

        # --- Content Area ---
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frames = {}
        self.init_frames()
        self.show_frame("overview")

    def sidebar_btn(self, idx, text, frame_name):
        btn = ctk.CTkButton(self.sidebar, text=text, height=40, anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.show_frame(frame_name))
        btn.pack(fill="x", padx=10, pady=5)

    def init_frames(self):
        self.frames["overview"] = self.create_overview()
        self.frames["devtools"] = self.create_devtools()
        self.frames["comfyui"] = self.create_comfyui()
        self.frames["models"] = self.create_models()
        self.frames["settings"] = self.create_settings()

    def show_frame(self, name):
        for f in self.frames.values(): f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    # --- Frames ---

    def create_overview(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        
        ctk.CTkLabel(frame, text="System Status", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Hardware Info
        gpu, vram = ComfyService.detect_hardware()
        info_frame = ctk.CTkFrame(frame)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, text=f"OS: {platform.system()} {platform.release()}").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(info_frame, text=f"GPU: {gpu} ({vram} GB)").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(info_frame, text=f"Node.js: {'Installed' if DevService.is_node_installed() else 'Missing'}").pack(side="left", padx=20, pady=15)

        # Quick Actions
        ctk.CTkLabel(frame, text="Quick Launch", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(20, 10))
        launch_frame = ctk.CTkFrame(frame)
        launch_frame.pack(fill="x")
        
        ctk.CTkButton(launch_frame, text="Start ComfyUI", height=50, font=("Arial", 16), command=self.launch_comfy).pack(padx=20, pady=20, fill="x")

        return frame

    def create_devtools(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="Developer Tools & CLIs", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)

        # Node Section
        node_frame = ctk.CTkFrame(frame)
        node_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(node_frame, text="Core Dependencies", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        if not DevService.is_node_installed():
            ctk.CTkLabel(node_frame, text="Node.js is missing.", text_color="orange").pack(side="left", padx=10)
            ctk.CTkButton(node_frame, text="Install Node.js (LTS)", command=self.install_node).pack(side="right", padx=10, pady=10)
        else:
            ctk.CTkLabel(node_frame, text="✅ Node.js is installed.", text_color="green").pack(side="left", padx=10, pady=10)

        # CLI Section
        cli_frame = ctk.CTkFrame(frame)
        cli_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(cli_frame, text="AI Command Line Tools", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Checkboxes
        self.cli_vars = {}
        tools = ["Claude CLI", "Gemini CLI", "OpenAI CLI", "Vercel (AI SDK)", "Heroku CLI"]
        
        check_frame = ctk.CTkScrollableFrame(cli_frame, height=200)
        check_frame.pack(fill="x", padx=10, pady=5)
        
        for t in tools:
            var = ctk.BooleanVar()
            ctk.CTkCheckBox(check_frame, text=t, variable=var).pack(anchor="w", pady=5)
            self.cli_vars[t] = var

        # Config
        opt_frame = ctk.CTkFrame(cli_frame, fg_color="transparent")
        opt_frame.pack(fill="x", padx=10)
        self.scope_var = ctk.StringVar(value="user")
        ctk.CTkRadioButton(opt_frame, text="User Scope", variable=self.scope_var, value="user").pack(side="left", padx=10)
        ctk.CTkRadioButton(opt_frame, text="System Scope (-g)", variable=self.scope_var, value="system").pack(side="left", padx=10)
        
        ctk.CTkButton(cli_frame, text="Install Selected Tools", fg_color="green", command=self.install_selected_tools).pack(pady=20)
        
        return frame

    def create_comfyui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="ComfyUI Studio", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Wizard Button
        ctk.CTkButton(frame, text="✨ Run Setup Wizard", height=60, font=("Arial", 18), fg_color="#6A0dad", command=self.open_wizard_popup).pack(fill="x", pady=20)
        
        # Manual Controls
        man_frame = ctk.CTkFrame(frame)
        man_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(man_frame, text="Manual Management").pack(pady=10)
        ctk.CTkButton(man_frame, text="Update (Git Pull)", command=self.update_comfy).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(man_frame, text="Repair Dependencies", command=self.repair_comfy).pack(fill="x", padx=20, pady=5)
        
        return frame

    def create_models(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="Model Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        ctk.CTkLabel(frame, text="Use the tabs below to organize your files.").pack(anchor="w")
        
        # Placeholder for the treeview logic from previous iteration
        # (Simplified for this restructure demo)
        ctk.CTkButton(frame, text="Open Models Folder", command=lambda: Logic.open_folder(os.path.join(CONFIG["comfy_path"], "models"))).pack(pady=20)
        
        return frame

    def create_settings(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="Configuration", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Path
        ctk.CTkLabel(frame, text="ComfyUI Path:").pack(anchor="w", padx=10)
        self.path_entry = ctk.CTkEntry(frame)
        self.path_entry.insert(0, CONFIG["comfy_path"])
        self.path_entry.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(frame, text="Save", command=self.save_settings).pack(anchor="e", padx=10)
        
        # API Keys
        ctk.CTkLabel(frame, text="API Keys (Stored locally in config.json)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(30, 10))
        
        self.keys_frame = ctk.CTkScrollableFrame(frame, height=200)
        self.keys_frame.pack(fill="x", padx=10)
        
        self.api_entries = {}
        for provider in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY"]:
            row = ctk.CTkFrame(self.keys_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=provider, width=150, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(row, show="*")
            if provider in CONFIG.get("api_keys", {}):
                ent.insert(0, CONFIG["api_keys"Показать больше]")
            ent.pack(side="left", fill="x", expand=True)
            self.api_entries[provider] = ent

        ctk.CTkButton(frame, text="Save Keys", fg_color="green", command=self.save_keys).pack(pady=20)

        return frame

    # --- Actions ---

    def launch_comfy(self):
        path = CONFIG["comfy_path"]
        if not os.path.exists(os.path.join(path, "main.py")):
            messagebox.showerror("Error", "ComfyUI not found at path.")
            return
        
        py = ComfyService.get_venv_python()
        subprocess.Popen([py, "main.py", "--auto-launch"], cwd=path)

    def install_node(self):
        cmd = DevService.install_node_cmd()
        subprocess.Popen(cmd)
        messagebox.showinfo("Installer", "Node.js installer launched.")

    def install_selected_tools(self):
        to_install = [name for name, var in self.cli_vars.items() if var.get()]
        if not to_install: return
        
        # In a real app, we'd spawn a thread and show a console
        print(f"Installing: {to_install}")
        messagebox.showinfo("Dev Tools", f"Installing {len(to_install)} tools... Check console for progress.")

    def open_wizard_popup(self):
        # The Questionnaire
        win = ctk.CTkToplevel(self)
        win.title("ComfyUI Setup Wizard")
        win.geometry("500x600")
        
        ctk.CTkLabel(win, text="ComfyUI Setup Wizard", font=("Arial", 20, "bold")).pack(pady=20)
        
        # Style
        ctk.CTkLabel(win, text="1. What is your primary art style?").pack(anchor="w", padx=20)
        style_var = ctk.StringVar(value="General")
        ctk.CTkSegmentedButton(win, values=["Photorealistic", "Anime", "General"], variable=style_var).pack(fill="x", padx=20, pady=5)
        
        # Media
        ctk.CTkLabel(win, text="2. What media do you generate?").pack(anchor="w", padx=20, pady=(20, 0))
        media_var = ctk.StringVar(value="Images")
        ctk.CTkCheckBox(win, text="Video (AnimateDiff)").pack(anchor="w", padx=20, pady=5)
        ctk.CTkCheckBox(win, text="Image Editing (Inpainting)").pack(anchor="w", padx=20, pady=5)
        
        # Hardware
        gpu, vram = ComfyService.detect_hardware()
        ctk.CTkLabel(win, text=f"Detected: {gpu} ({vram}GB)", text_color="yellow").pack(pady=20)
        
        ctk.CTkButton(win, text="Generate Recipe & Install", fg_color="green", height=50, command=lambda: win.destroy()).pack(side="bottom", fill="x", padx=20, pady=20)

    def save_settings(self):
        CONFIG["comfy_path"] = self.path_entry.get()
        save_config(CONFIG)
        messagebox.showinfo("Saved", "Path saved.")

    def save_keys(self):
        if "api_keys" not in CONFIG: CONFIG["api_keys"] = {}
        for k, ent in self.api_entries.items():
            CONFIG["api_keys"][k] = ent.get()
        save_config(CONFIG)
        messagebox.showinfo("Saved", "API Keys stored.")

    def update_comfy(self):
        pass # Placeholder for git pull logic
    
    def repair_comfy(self):
        pass # Placeholder for pip install logic

if __name__ == "__main__":
    app = App()
    app.mainloop()
