import os
import sys
import time
import shutil
import subprocess
import platform
import psutil
import webbrowser
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt, Confirm

# --- Global Context ---
CONSOLE = Console()
OS_SYSTEM = platform.system() # 'Windows', 'Darwin', 'Linux'
IS_WINDOWS = OS_SYSTEM == "Windows"
IS_MAC = OS_SYSTEM == "Darwin"

# --- Paths ---
# Windows: C:\Users\Name\ComfyUI, Unix: ~/ComfyUI
INSTALL_DIR = os.path.join(os.path.expanduser("~"), "ComfyUI")
REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"

# --- Platform Handler ---
class PlatformHandler:
    @staticmethod
    def get_venv_python():
        if IS_WINDOWS:
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "python")

    @staticmethod
    def get_venv_pip():
        if IS_WINDOWS:
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "pip.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "pip")

    @staticmethod
    def open_folder(path):
        if IS_WINDOWS:
            os.startfile(path)
        elif IS_MAC:
            subprocess.run(["open", path])
        else: # Linux
            subprocess.run(["xdg-open", path])

    @staticmethod
    def has_nvidia_gpu():
        if shutil.which("nvidia-smi"):
            return True
        return False

# --- Core Logic ---

def get_system_metrics():
    try:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage(os.path.expanduser("~")).percent
        return cpu, memory, disk
    except:
        return 0, 0, 0

def is_installed():
    return os.path.exists(os.path.join(INSTALL_DIR, "main.py"))

def check_health():
    health = {
        "OS": f"{OS_SYSTEM} {platform.release()}",
        "Python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "Git": "Installed" if shutil.which("git") else "[bold red]Missing[/]",
        "ComfyUI": "Installed" if is_installed() else "[yellow]Not Found[/]",
        "Venv": "OK" if os.path.exists(os.path.dirname(PlatformHandler.get_venv_python())) else "Missing"
    }
    return health

def run_cmd(cmd_list, cwd=None, description=None):
    """Runs a command safely, hiding output unless error"""
    try:
        # On Windows, shell=True is often needed for some cmds, but list args are safer
        # We use list args and shell=False generally, unless it's a raw string
        subprocess.check_call(cmd_list, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

# --- Installation Logic ---

def install_torch(progress_task, progress_obj):
    pip_cmd = PlatformHandler.get_venv_pip()
    
    # 1. Determine correct torch command
    cmd = [pip_cmd, "install", "torch", "torchvision", "torchaudio"]
    
    if IS_WINDOWS or OS_SYSTEM == "Linux":
        if PlatformHandler.has_nvidia_gpu():
            # CUDA 12.1 is standard for modern ComfyUI
            progress_obj.update(progress_task, description="[cyan]Detected NVIDIA GPU. Installing CUDA Torch...[/]")
            cmd.extend(["--index-url", "https://download.pytorch.org/whl/cu121"])
        else:
            progress_obj.update(progress_task, description="[yellow]No NVIDIA GPU detected. Installing CPU Torch...[/]")
            # Standard install usually defaults to CPU or basic CUDA, but explicit CPU is safer if no GPU
            # But let's stick to standard to allow possible AMD support if configured later
            pass 
    elif IS_MAC:
        progress_obj.update(progress_task, description="[cyan]macOS Detected. Installing MPS-ready Torch...[/]")
        # Standard pip install is fine for Mac ARM64 now
    
    run_cmd(cmd, cwd=INSTALL_DIR)

def install_comfyui():
    CONSOLE.clear()
    CONSOLE.print(Panel("[bold green]Installing ComfyUI...[/]", title="Installer"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        
        # Step 1: Clone
        task1 = progress.add_task("[cyan]Cloning Repository...", total=100)
        if not os.path.exists(INSTALL_DIR):
            run_cmd(["git", "clone", REPO_URL, INSTALL_DIR])
        else:
            run_cmd(["git", "pull"], cwd=INSTALL_DIR)
        progress.update(task1, completed=100)
        
        # Step 2: Venv
        task2 = progress.add_task("[cyan]Creating Virtual Environment...", total=100)
        if not os.path.exists(os.path.join(INSTALL_DIR, "venv")):
            run_cmd([sys.executable, "-m", "venv", "venv"], cwd=INSTALL_DIR)
        progress.update(task2, completed=100)
        
        # Step 3: Requirements
        task3 = progress.add_task("[cyan]Installing Core Dependencies...", total=100)
        pip_cmd = PlatformHandler.get_venv_pip()
        
        run_cmd([pip_cmd, "install", "--upgrade", "pip"], cwd=INSTALL_DIR)
        install_torch(task3, progress) # Handle GPU logic
        
        progress.update(task3, description="[cyan]Installing requirements.txt...", advance=50)
        run_cmd([pip_cmd, "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
        progress.update(task3, completed=100)
        
        # Step 4: Manager
        task4 = progress.add_task("[cyan]Installing ComfyUI Manager...", total=100)
        custom_nodes = os.path.join(INSTALL_DIR, "custom_nodes")
        os.makedirs(custom_nodes, exist_ok=True)
        if not os.path.exists(os.path.join(custom_nodes, "ComfyUI-Manager")):
            run_cmd(["git", "clone", MANAGER_URL], cwd=custom_nodes)
        progress.update(task4, completed=100)

    CONSOLE.print("[bold green]Installation Complete![/]")
    time.sleep(2)

def smoke_test():
    CONSOLE.clear()
    CONSOLE.print(Panel("[bold cyan]Running Smoke Test...[/]", title="Diagnostics"))
    
    if not is_installed():
        CONSOLE.print("[bold red]ComfyUI is not installed.[/]")
        time.sleep(2)
        return

    python_exec = PlatformHandler.get_venv_python()
    CONSOLE.print("[dim]Attempting to start server on port 8199 (test mode)...[/]")
    
    # We use a non-standard port to avoid conflicts
    cmd = [python_exec, "main.py", "--port", "8199", "--cpu"] # Force CPU for quick test stability
    
    try:
        proc = subprocess.Popen(
            cmd, 
            cwd=INSTALL_DIR, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        import urllib.request
        success = False
        for i in range(20):
            time.sleep(1)
            try:
                code = urllib.request.urlopen("http://127.0.0.1:8199").getcode()
                if code == 200:
                    success = True
                    break
            except:
                pass
        
        proc.terminate()
        
        if success:
            CONSOLE.print(Panel("[bold green]PASS: Server responded successfully![/)", border_style="green"))
        else:
            CONSOLE.print(Panel("[bold red]FAIL: Server did not respond.[/]", border_style="red"))
            
    except Exception as e:
        CONSOLE.print(f"[bold red]Error: {e}[/]")
    
    CONSOLE.input("\nPress Enter to return...")

def launch_app():
    if not is_installed():
        CONSOLE.print("[red]Not installed![/]")
        time.sleep(1)
        return
        
    python_exec = PlatformHandler.get_venv_python()
    CONSOLE.print("[green]Launching ComfyUI...[/]")
    
    # Arguments
    args = ["--auto-launch"]
    if IS_MAC:
        args.append("--force-fp16") # Optimization for Mac
    
    cmd = [python_exec, "main.py"] + args
    
    # Launch and let go
    subprocess.Popen(cmd, cwd=INSTALL_DIR)
    CONSOLE.print("[dim]ComfyUI is running in the background.[/]")
    time.sleep(2)

# --- UI Layout ---

def get_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(Layout(name="left"), Layout(name="right"))
    return layout

def main():
    layout = get_layout()
    
    while True:
        # Header
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(
            "[b magenta]ComfyUI Universal Dashboard[/b magenta]", 
            f"[dim]{OS_SYSTEM} | {platform.machine()}[/dim]"
        )
        layout["header"].update(Panel(grid, style="white on blue"))
        
        # Stats
        cpu, ram, disk = get_system_metrics()
        t_stats = Table(title="Metrics", expand=True, border_style="dim")
        t_stats.add_column("Metric"); t_stats.add_column("Value", justify="right")
        t_stats.add_row("CPU", f"{cpu}%")
        t_stats.add_row("RAM", f"{ram}%")
        t_stats.add_row("Disk", f"{disk}%")
        layout["left"].update(Panel(t_stats, title="System", border_style="blue"))
        
        # Health
        health = check_health()
        t_health = Table(title="Status", expand=True, border_style="dim")
        t_health.add_column("Component"); t_health.add_column("State")
        for k,v in health.items():
            t_health.add_row(k, v)
        layout["right"].update(Panel(t_health, title="Health", border_style="green"))
        
        # Menu
        t_menu = Table(show_header=False, expand=True, box=None)
        t_menu.add_row("[1] Install / Update", "[3] Smoke Test", "[5] Launch ComfyUI")
        t_menu.add_row("[2] Download Models", "[4] Open Folder", "[Q] Quit")
        layout["footer"].update(Panel(t_menu, title="Actions", border_style="white"))
        
        CONSOLE.clear()
        CONSOLE.print(layout)
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "q", "Q"], default="q")
        
        if choice in ["q", "Q"]:
            break
        elif choice == "1":
            install_comfyui()
        elif choice == "3":
            smoke_test()
        elif choice == "5":
            launch_app()
        elif choice == "4":
            PlatformHandler.open_folder(INSTALL_DIR if os.path.exists(INSTALL_DIR) else os.path.expanduser("~"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
