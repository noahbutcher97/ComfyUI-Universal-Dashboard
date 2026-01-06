"""
System service for environment detection and dependency checking.

MIGRATION NOTE (Phase 1):
The GPU detection in get_gpu_info() now delegates to the new platform-specific
detectors in src/services/hardware/. The old implementation is preserved below
for reference but no longer executes.

See: docs/MIGRATION_PROTOCOL.md Section 3
"""

import shutil
import subprocess
import platform
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict
from functools import lru_cache
from src.utils.logger import log
from src.schemas.environment import EnvironmentReport

# Feature flag for new hardware detection (Pattern C from migration protocol)
USE_NEW_HARDWARE_DETECTION = True


class SystemService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpu_info() -> Tuple[str, str, float]:
        """
        Detects GPU Name, Vendor, and VRAM. Cached result.
        Returns: (gpu_vendor, gpu_name, vram_gb)

        .. deprecated::
            This method now delegates to src/services/hardware/ detectors.
            For full hardware profile, use:
                from src.services.hardware import detect_hardware
                profile = detect_hardware()

            This function will be simplified in v1.0.
            See: docs/MIGRATION_PROTOCOL.md Section 3
        """
        if USE_NEW_HARDWARE_DETECTION:
            # NEW: Delegate to platform-specific detectors
            # Per SPEC_v3 Section 4 and MIGRATION_PROTOCOL Pattern B
            from src.services.hardware import get_legacy_gpu_info
            return get_legacy_gpu_info()

        # OLD implementation preserved for rollback (Pattern C toggle)
        # This code path is disabled by default
        return _legacy_get_gpu_info()

    @staticmethod
    def get_system_ram_gb() -> Optional[float]:
        """
        Returns total system RAM in GB.

        Returns: RAM in GB, or None if detection fails.

        Per ARCHITECTURE_PRINCIPLES: Explicit failure, no silent fallbacks.
        """
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            log.error("psutil not installed - cannot detect RAM")
            return None
        except Exception as e:
            log.error(f"RAM detection failed: {e}")
            return None

    @staticmethod
    def get_disk_free_gb(path: str = ".") -> Optional[int]:
        """
        Returns free disk space at path in GB.

        Returns: Free space in GB, or None if detection fails.

        Per ARCHITECTURE_PRINCIPLES: Explicit failure, no silent fallbacks.
        """
        try:
            total, used, free = shutil.disk_usage(os.path.abspath(path))
            return int(free / (1024**3))
        except FileNotFoundError:
            log.error(f"Path not found for disk check: {path}")
            return None
        except Exception as e:
            log.error(f"Disk space detection failed: {e}")
            return None

    @staticmethod
    def detect_form_factor() -> str:
        """
        Detect system form factor (desktop, laptop, mini, workstation).

        Per ARCHITECTURE_PRINCIPLES: Uses run_powershell() with -NoProfile.
        """
        if platform.system() == "Windows":
            try:
                from src.utils.subprocess_utils import run_powershell

                cmd = "Get-CimInstance -ClassName Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"
                output = run_powershell(cmd, timeout=10)

                if output:
                    # ChassisTypes: 9, 10, 14 = Laptop/Notebook/Sub-Notebook
                    if any(x in output for x in ["9", "10", "14"]):
                        return "laptop"
            except ImportError:
                log.warning("subprocess_utils not available, using fallback")
                # Fallback to direct call if utilities not available
                try:
                    cmd = "Get-CimInstance -ClassName Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"
                    output = subprocess.check_output(
                        ["powershell", "-NoProfile", "-Command", cmd],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    ).decode().strip()
                    if any(x in output for x in ["9", "10", "14"]):
                        return "laptop"
                except Exception:
                    pass
            except Exception as e:
                log.warning(f"Form factor detection failed: {e}")

        # Default to desktop if detection fails
        return "desktop"

    @staticmethod
    def detect_storage_type(path: str = ".") -> str:
        """
        Detect storage type (NVMe, SATA SSD, HDD).
        """
        # Very platform specific. Returning generic for now to be safe.
        # Can implement the specific `df` or `wmi` logic from specs later
        # once we add `wmi` to requirements.
        return "unknown"

    @staticmethod
    def detect_power_state() -> Tuple[str, bool]:
        """
        Detect current power state and profile.

        Returns: (power_profile, on_battery)
            - power_profile: "high_performance", "balanced", "power_saver", "unknown"
            - on_battery: True if running on battery, False if plugged in

        Per SPEC §4.6: Platform-specific power detection.
        """
        system = platform.system()

        if system == "Windows":
            return SystemService._detect_power_state_windows()
        elif system == "Darwin":
            return SystemService._detect_power_state_macos()
        elif system == "Linux":
            return SystemService._detect_power_state_linux()
        else:
            return "unknown", False

    @staticmethod
    def _detect_power_state_windows() -> Tuple[str, bool]:
        """Windows power state detection via GetSystemPowerStatus."""
        try:
            import ctypes
            from ctypes import wintypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD),
                ]

            status = SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                log.warning("GetSystemPowerStatus failed")
                return "unknown", False

            # ACLineStatus: 0 = offline (battery), 1 = online (plugged in), 255 = unknown
            on_battery = status.ACLineStatus == 0

            # Try to detect power profile via powercfg
            try:
                from src.utils.subprocess_utils import run_powershell
                output = run_powershell("powercfg /getactivescheme", timeout=5)
                if output:
                    output_lower = output.lower()
                    if "high performance" in output_lower:
                        return "high_performance", on_battery
                    elif "power saver" in output_lower:
                        return "power_saver", on_battery
                    elif "balanced" in output_lower:
                        return "balanced", on_battery
            except Exception:
                pass

            return "balanced", on_battery

        except Exception as e:
            log.warning(f"Windows power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def _detect_power_state_macos() -> Tuple[str, bool]:
        """macOS power state detection via pmset."""
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return "unknown", False

            output = result.stdout.lower()

            # Check power source
            on_battery = "battery power" in output or "'battery power'" in output
            on_ac = "ac power" in output or "'ac power'" in output

            if on_ac:
                on_battery = False
            elif not on_battery and not on_ac:
                # Default to plugged in if unclear
                on_battery = False

            # macOS doesn't have explicit power profiles like Windows
            # Detect if Low Power Mode is enabled
            try:
                lpm_result = subprocess.run(
                    ["pmset", "-g"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "lowpowermode" in lpm_result.stdout.lower() and "1" in lpm_result.stdout:
                    return "power_saver", on_battery
            except Exception:
                pass

            return "balanced", on_battery

        except subprocess.TimeoutExpired:
            log.warning("pmset power check timed out")
            return "unknown", False
        except FileNotFoundError:
            return "unknown", False
        except Exception as e:
            log.warning(f"macOS power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def _detect_power_state_linux() -> Tuple[str, bool]:
        """Linux power state detection via /sys/class/power_supply."""
        try:
            import os

            power_supply_path = "/sys/class/power_supply"
            on_battery = True  # Default to battery if no AC found

            if os.path.exists(power_supply_path):
                for supply in os.listdir(power_supply_path):
                    supply_path = os.path.join(power_supply_path, supply)
                    type_path = os.path.join(supply_path, "type")
                    online_path = os.path.join(supply_path, "online")

                    if os.path.exists(type_path):
                        with open(type_path, 'r') as f:
                            supply_type = f.read().strip().lower()

                        # Check if AC adapter is online
                        if supply_type in ("mains", "usb"):
                            if os.path.exists(online_path):
                                with open(online_path, 'r') as f:
                                    online = f.read().strip()
                                    if online == "1":
                                        on_battery = False
                                        break

            # Linux power profiles (if available)
            profile = "balanced"
            try:
                # Check power-profiles-daemon (GNOME)
                result = subprocess.run(
                    ["powerprofilesctl", "get"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    profile_output = result.stdout.strip().lower()
                    if "performance" in profile_output:
                        profile = "high_performance"
                    elif "power-saver" in profile_output:
                        profile = "power_saver"
                    elif "balanced" in profile_output:
                        profile = "balanced"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            return profile, on_battery

        except Exception as e:
            log.warning(f"Linux power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def scan_full_environment() -> EnvironmentReport:
        """
        Comprehensive environment scan.
        """
        gpu_vendor, gpu_name, vram_gb = SystemService.get_gpu_info()
        ram_gb = SystemService.get_system_ram_gb()
        disk_free = SystemService.get_disk_free_gb()

        # Software checks
        git_ok = SystemService.check_dependency("Git", ("git", "--version"))
        node_ok = SystemService.check_dependency("Node", ("node", "--version"))
        npm_ok = SystemService.check_dependency("NPM", ("npm", "--version"))

        return EnvironmentReport(
            os_name=platform.system(),
            os_version=platform.release(),
            arch=platform.machine(),
            gpu_vendor=gpu_vendor,
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            disk_free_gb=disk_free,

            form_factor=SystemService.detect_form_factor(),

            python_version=sys.version.split()[0],
            git_installed=git_ok,
            node_installed=node_ok,
            npm_installed=npm_ok,

            # TODO: Add logic to find existing ComfyUI
            comfyui_path=None
        )

    @staticmethod
    @lru_cache(maxsize=32)
    def check_dependency(name, check_cmd_tuple):
        """
        Checks if a tool is installed.
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
    def verify_environment() -> Dict[str, bool]:
        """Quick check for Overview Frame."""
        return {
            "git": SystemService.check_dependency("Git", ("git", "--version")),
            "node": SystemService.check_dependency("Node", ("node", "--version")),
            "npm": SystemService.check_dependency("NPM", ("npm", "--version"))
        }


# Legacy implementation moved outside class for rollback purposes
def _legacy_get_gpu_info() -> Tuple[str, str, float]:
    """
    Legacy GPU detection implementation.

    DEPRECATED: This function is kept for rollback purposes only.
    Do not use directly - use SystemService.get_gpu_info() instead.

    Known issues (per SPEC_v3 audit):
    - Falls back to 16GB on Apple Silicon detection error (CRITICAL)
    - No 75% memory ceiling for Apple Silicon
    - No CUDA compute capability detection
    - No AMD ROCm support
    """
    gpu_vendor = "none"
    gpu_name = "CPU (Slow)"
    vram_gb = 0.0

    try:
        # 1. NVIDIA Check
        if shutil.which("nvidia-smi"):
            try:
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                ).decode()
                name, mem = output.strip().split(',')
                gpu_vendor = "nvidia"
                gpu_name = name
                vram_gb = float(mem) / 1024
                return gpu_vendor, gpu_name, vram_gb
            except Exception as e:
                log.warning(f"NVIDIA detection failed: {e}")

        # 2. Apple Silicon Check
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            gpu_vendor = "apple"
            gpu_name = "Apple Silicon (MPS)"
            try:
                # Get unified memory size
                result = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
                ram_bytes = int(result.strip())
                # BUG: Should apply 75% ceiling, but keeping for backwards compat
                vram_gb = ram_bytes / (1024**3)

                # Try to get specific chip name
                chip = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
                gpu_name = chip
            except Exception as e:
                log.warning(f"Mac RAM detection failed: {e}")
                # BUG: 16GB fallback causes wrong recommendations
                # This is why we migrated to new detectors
                vram_gb = 16.0
            return gpu_vendor, gpu_name, vram_gb

        # 3. AMD/Intel Check (Basic)
        # This is harder to do cross-platform without 3rd party libs like wmi/pyobjc
        # We'll leave as "none" for now unless specific tools are found

    except Exception as e:
        log.warning(f"GPU Detection failed: {e}")

    return gpu_vendor, gpu_name, vram_gb
