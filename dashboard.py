import os
import sys
import shutil
import subprocess
import platform
import psutil
import json
import threading
import time
import customtkinter as ctk
from tkinter import filedialog
import shutil

# --- Config & Constants ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".comfy_dashboard")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"

DEFAULT_CONFIG = {
    "install_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
    "auto_launch": False
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
INSTALL_DIR = CONFIG["install_path"]

# --- Helper Logic ---
class Logic:
    @staticmethod
    def get_venv_python():
        if platform.system() == "Windows":
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "python")

    @staticmethod
    def get_venv_pip():
        if platform.system() == "Windows":
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "pip.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "pip")

    @staticmethod
    def is_installed():
        return os.path.exists(os.path.join(INSTALL_DIR, "main.py"))

    @staticmethod
    def open_folder(path):
        if not os.path.exists(path): return
        if platform.system() == "Windows": os.startfile(path)
        elif platform.system() == "Darwin": subprocess.run(["open", path])
        else: subprocess.run(["xdg-open", path])

# --- Main App ---
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ComfyUI Universal Dashboard")
        self.geometry("1000x700")

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        self.logo = ctk.CTkLabel(self.sidebar, text="ComfyUI\nDashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_overview = ctk.CTkButton(self.sidebar, text="Overview", command=lambda: self.show_frame("overview"))
        self.btn_overview.grid(row=1, column=0, padx=20, pady=10)

        self.btn_install = ctk.CTkButton(self.sidebar, text="Install / Update", command=lambda: self.show_frame("install"))
        self.btn_install.grid(row=2, column=0, padx=20, pady=10)

        self.btn_models = ctk.CTkButton(self.sidebar, text="Model Browser", command=lambda: self.show_frame("models"))
        self.btn_models.grid(row=3, column=0, padx=20, pady=10)
        
        self.btn_settings = ctk.CTkButton(self.sidebar, text="Settings", command=lambda: self.show_frame("settings"))
        self.btn_settings.grid(row=4, column=0, padx=20, pady=10)

        self.btn_exit = ctk.CTkButton(self.sidebar, text="Exit", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.destroy)
        self.btn_exit.grid(row=6, column=0, padx=20, pady=20)

        # Content Area
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Init Frames
        self.frames = {}
        self.setup_overview_frame()
        self.setup_install_frame()
        self.setup_models_frame()
        self.setup_settings_frame()

        self.show_frame("overview")
        
        # Start Metrics Thread
        self.update_metrics()

    def show_frame(self, name):
        # Hide all
        for frame in self.frames.values():
            frame.pack_forget()
        # Show selected
        self.frames[name].pack(fill="both", expand=True)

    # --- Overview Tab ---
    def setup_overview_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["overview"] = frame

        # Status Banner
        self.status_label = ctk.CTkLabel(frame, text="Checking status...", font=ctk.CTkFont(size=16))
        self.status_label.pack(pady=10, anchor="w")

        # Metrics
        self.metrics_frame = ctk.CTkFrame(frame)
        self.metrics_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.metrics_frame, text="System Metrics").pack(pady=5)
        
        self.cpu_bar = ctk.CTkProgressBar(self.metrics_frame)
        self.cpu_bar.pack(fill="x", padx=10, pady=5)
        self.cpu_label = ctk.CTkLabel(self.metrics_frame, text="CPU: 0%")
        self.cpu_label.pack(anchor="e", padx=10)

        self.ram_bar = ctk.CTkProgressBar(self.metrics_frame)
        self.ram_bar.set(0)
        self.ram_bar.pack(fill="x", padx=10, pady=5)
        self.ram_label = ctk.CTkLabel(self.metrics_frame, text="RAM: 0%")
        self.ram_label.pack(anchor="e", padx=10)

        # Launch Button
        self.btn_launch = ctk.CTkButton(frame, text="🚀 Launch ComfyUI", height=50, font=ctk.CTkFont(size=18), command=self.launch_comfyui)
        self.btn_launch.pack(pady=30, fill="x")

        self.btn_smoke = ctk.CTkButton(frame, text="🧪 Run Smoke Test", fg_color="gray", command=self.run_smoke_test)
        self.btn_smoke.pack(pady=5, fill="x")

    def update_metrics(self):
        try:
            cpu = psutil.cpu_percent() / 100
            ram = psutil.virtual_memory().percent / 100
            self.cpu_bar.set(cpu)
            self.cpu_label.configure(text=f"CPU: {int(cpu*100)}%")
            self.ram_bar.set(ram)
            self.ram_label.configure(text=f"RAM: {int(ram*100)}%")
            
            # Status Check
            if Logic.is_installed():
                self.status_label.configure(text=f"✅ ComfyUI Installed at: {INSTALL_DIR}", text_color="green")
                self.btn_launch.configure(state="normal")
            else:
                self.status_label.configure(text=f"❌ ComfyUI Not Found at: {INSTALL_DIR}", text_color="red")
                self.btn_launch.configure(state="disabled")
                
        except: pass
        self.after(2000, self.update_metrics)

    # --- Install Tab ---
    def setup_install_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["install"] = frame

        controls = ctk.CTkFrame(frame)
        controls.pack(fill="x", pady=10)

        ctk.CTkButton(controls, text="Install (Clean)", command=self.do_install).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(controls, text="Update (Git Pull)", command=self.do_update).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(controls, text="Install Node.js", fg_color="orange", command=self.do_install_node).pack(side="left", padx=5, expand=True, fill="x")

        # Console Log
        self.console_log = ctk.CTkTextbox(frame, font=("Consolas", 12))
        self.console_log.pack(fill="both", expand=True, pady=10)
        self.log("Ready for tasks.")

    def log(self, message):
        self.console_log.insert("end", str(message) + "\n")
        self.console_log.see("end")

    def run_thread(self, target):
        threading.Thread(target=target, daemon=True).start()

    # --- Model Browser Tab ---
    def setup_models_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["models"] = frame

        ctk.CTkLabel(frame, text="Installed Models (Checkpoints)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        self.model_list = ctk.CTkTextbox(frame, state="disabled")
        self.model_list.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkButton(frame, text="Refresh List", command=self.refresh_models).pack(pady=5)
        ctk.CTkButton(frame, text="Open Models Folder", command=lambda: Logic.open_folder(os.path.join(INSTALL_DIR, "models"))).pack(pady=5)

    def refresh_models(self):
        self.model_list.configure(state="normal")
        self.model_list.delete("0.0", "end")
        
        ckpt_path = os.path.join(INSTALL_DIR, "models", "checkpoints")
        if not os.path.exists(ckpt_path):
            self.model_list.insert("end", "Models folder not found.\n")
        else:
            files = os.listdir(ckpt_path)
            if not files: self.model_list.insert("end", "No checkpoints found.\n")
            for f in files:
                if f.endswith((".safetensors", ".ckpt")):
                    size_mb = os.path.getsize(os.path.join(ckpt_path, f)) / (1024 * 1024)
                    self.model_list.insert("end", f"• {f}  ({int(size_mb)} MB)\n")
        
        self.model_list.configure(state="disabled")

    # --- Settings Tab ---
    def setup_settings_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["settings"] = frame
        
        ctk.CTkLabel(frame, text="Installation Path").pack(anchor="w")
        
        self.path_entry = ctk.CTkEntry(frame)
        self.path_entry.insert(0, INSTALL_DIR)
        self.path_entry.pack(fill="x", pady=5)
        
        ctk.CTkButton(frame, text="Browse...", command=self.browse_path).pack(anchor="e", pady=5)
        ctk.CTkButton(frame, text="Save Config", command=self.save_settings, fg_color="green").pack(pady=20)

    def browse_path(self):
        path = filedialog.askdirectory(initialdir=INSTALL_DIR)
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def save_settings(self):
        global INSTALL_DIR
        new_path = self.path_entry.get()
        CONFIG["install_path"] = new_path
        save_config(CONFIG)
        INSTALL_DIR = new_path
        self.log(f"Path updated to: {INSTALL_DIR}")

    # --- Actions ---
    def launch_comfyui(self):
        if not Logic.is_installed(): return
        args = ["--auto-launch"]
        if platform.system() == "Darwin": args.append("--force-fp16")
        
        subprocess.Popen([Logic.get_venv_python(), "main.py"] + args, cwd=INSTALL_DIR)
        self.log("ComfyUI Launched!")

    def run_smoke_test(self):
        self.log("Starting Smoke Test...")
        def _test():
            try:
                proc = subprocess.Popen([Logic.get_venv_python(), "main.py", "--port", "8199", "--cpu"], cwd=INSTALL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import urllib.request
                success = False
                for _ in range(15):
                    time.sleep(1)
                    try:
                        if urllib.request.urlopen("http://127.0.0.1:8199").getcode() == 200: success = True; break
                    except: pass
                proc.terminate()
                self.log("Smoke Test Passed: ✅" if success else "Smoke Test Failed: ❌")
            except Exception as e: self.log(f"Test Error: {e}")
        self.run_thread(_test)

    def do_install(self):
        def _install():
            self.log("Cloning Repo...")
            if not os.path.exists(INSTALL_DIR):
                subprocess.call(["git", "clone", REPO_URL, INSTALL_DIR])
            
            self.log("Creating Venv...")
            subprocess.call([sys.executable, "-m", "venv", "venv"], cwd=INSTALL_DIR)
            
            self.log("Installing Deps (this may take time)...")
            pip = Logic.get_venv_pip()
            subprocess.call([pip, "install", "--upgrade", "pip"], cwd=INSTALL_DIR)
            subprocess.call([pip, "install", "torch", "torchvision", "torchaudio"], cwd=INSTALL_DIR)
            subprocess.call([pip, "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
            
            self.log("Done!")
        self.run_thread(_install)

    def do_update(self):
        def _update():
            self.log("Git Pulling...")
            subprocess.call(["git", "pull"], cwd=INSTALL_DIR)
            self.log("Updating Requirements...")
            subprocess.call([Logic.get_venv_pip(), "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
            self.log("Updated.")
        self.run_thread(_update)

    def do_install_node(self):
        def _node():
            self.log("Installing Node.js...")
            if platform.system() == "Darwin": subprocess.call(["brew", "install", "node"])
            elif platform.system() == "Windows": subprocess.call(["winget", "install", "-e", "--id", "OpenJS.NodeJS"])
            self.log("Node Install command finished. Restart app to verify.")
        self.run_thread(_node)

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()
