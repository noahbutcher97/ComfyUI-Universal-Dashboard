import shutil
import subprocess
import platform
import sys
from functools import lru_cache
from src.utils.logger import log

class SystemService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpu_info():
        """
        Detects GPU Name and VRAM. Cached result.
        Returns: (gpu_name, vram_gb)
        """
        gpu_name = "CPU (Slow)"
        vram_gb = 0
        try:
            if shutil.which("nvidia-smi"):
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                ).decode()
                name, mem = output.strip().split(',')
                gpu_name = name
                vram_gb = int(float(mem) / 1024)
            elif platform.system() == "Darwin" and platform.machine() == "arm64":
                gpu_name = "Apple Silicon (MPS)"
                # Rough estimate or assume high unified memory for M-series
                vram_gb = 16 
        except Exception as e:
            log.warning(f"GPU Detection failed: {e}")
        
        return gpu_name, vram_gb

    @staticmethod
    @lru_cache(maxsize=32)
    def check_dependency(name, check_cmd_tuple):
        """
        Checks if a tool is installed. Cached result.
        name: Display name
        check_cmd_tuple: Command tuple to run (tuple is hashable, list is not)
        """
        try:
            subprocess.check_call(
                check_cmd_tuple, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                shell=(platform.system()=="Windows")
            )
            return True
        except:
            return False

    @staticmethod
    def verify_environment():
        """
        Returns a dict of status checks.
        """
        return {
            "git": SystemService.check_dependency("Git", ("git", "--version")),
            "node": SystemService.check_dependency("Node", ("node", "--version")),
            "npm": SystemService.check_dependency("NPM", ("npm", "--version")),
            "python": True # Assumed since we are running
        }

    @staticmethod
    def get_python_exec():
        return sys.executable
