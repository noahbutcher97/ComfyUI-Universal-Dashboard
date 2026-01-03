"""
NVIDIA GPU hardware detector per SPEC_v3 Section 4.3.

Handles detection for Windows/Linux with NVIDIA GPUs.
40% Windows + portion of 20% Linux = ~50% of target user base.

Key features:
- CUDA compute capability detection for FP8/BF16/Flash Attention support
- Multi-GPU detection with NVLink topology
- WSL2 detection
- Thermal state monitoring

NEW in Phase 1 - does not replace existing code.
See: docs/MIGRATION_PROTOCOL.md Section 3
"""

import platform
import subprocess
import shutil
from typing import Optional, Tuple

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    ThermalState,
)
from src.services.hardware.base import HardwareDetector, DetectionFailedError, NoCUDAError
from src.utils.logger import log


class NVIDIADetector(HardwareDetector):
    """
    Detection strategy for Windows/Linux with NVIDIA GPUs.

    Uses PyTorch CUDA APIs for primary detection with nvidia-smi fallback.
    Detects compute capability for precision support (FP8, BF16, etc.).
    """

    def is_available(self) -> bool:
        """Check if NVIDIA GPU detection is possible."""
        # Check for nvidia-smi first (fast check)
        if shutil.which("nvidia-smi"):
            return True

        # Check for CUDA via PyTorch
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def detect(self) -> HardwareProfile:
        """
        Detect NVIDIA GPU hardware.

        Returns:
            HardwareProfile with compute capability and precision support

        Raises:
            NoCUDAError: If CUDA is not available
            DetectionFailedError: If detection fails
        """
        try:
            import torch
        except ImportError:
            raise DetectionFailedError(
                component="PyTorch",
                message="PyTorch not installed",
                details="Install PyTorch with CUDA support for full detection."
            )

        if not torch.cuda.is_available():
            # Try nvidia-smi as fallback for basic info
            if shutil.which("nvidia-smi"):
                return self._detect_via_nvidia_smi()
            raise NoCUDAError()

        # GPU identification via PyTorch
        gpu_name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = vram_bytes / (1024 ** 3)

        # Compute capability determines available optimizations
        major, minor = torch.cuda.get_device_capability(0)
        compute_capability = float(f"{major}.{minor}")

        # Multi-GPU detection
        gpu_count = torch.cuda.device_count()

        # NVLink detection (if multi-GPU)
        nvlink_available = self._check_nvlink() if gpu_count > 1 else False

        # WSL2 detection
        is_wsl = self._detect_wsl()

        # System RAM
        ram_gb = self._get_system_ram()

        # Determine platform type
        if is_wsl:
            plat = PlatformType.WSL2_NVIDIA
        elif platform.system() == "Windows":
            plat = PlatformType.WINDOWS_NVIDIA
        else:
            plat = PlatformType.LINUX_NVIDIA

        return HardwareProfile(
            platform=plat,
            gpu_vendor="nvidia",
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            unified_memory=False,
            # Compute capability-based features
            compute_capability=compute_capability,
            supports_fp8=compute_capability >= 8.9,      # Ada Lovelace+
            supports_bf16=compute_capability >= 8.0,     # Ampere+
            supports_tf32=compute_capability >= 8.0,     # Ampere+
            flash_attention_available=compute_capability >= 8.0,
            # Multi-GPU
            gpu_count=gpu_count,
            nvlink_available=nvlink_available,
        )

    def _detect_via_nvidia_smi(self) -> HardwareProfile:
        """
        Fallback detection via nvidia-smi when PyTorch CUDA unavailable.

        Provides basic GPU info without compute capability details.
        """
        try:
            creation_flags = 0
            if platform.system() == "Windows":
                creation_flags = subprocess.CREATE_NO_WINDOW

            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                creationflags=creation_flags,
                stderr=subprocess.DEVNULL
            ).decode()

            name, mem = output.strip().split(',')
            vram_gb = float(mem.strip()) / 1024

            # Infer compute capability from GPU name (approximate)
            cc = self._infer_compute_capability(name)

            return HardwareProfile(
                platform=PlatformType.WINDOWS_NVIDIA if platform.system() == "Windows" else PlatformType.LINUX_NVIDIA,
                gpu_vendor="nvidia",
                gpu_name=name.strip(),
                vram_gb=vram_gb,
                ram_gb=self._get_system_ram(),
                unified_memory=False,
                compute_capability=cc,
                supports_fp8=cc is not None and cc >= 8.9,
                supports_bf16=cc is not None and cc >= 8.0,
                supports_tf32=cc is not None and cc >= 8.0,
                flash_attention_available=cc is not None and cc >= 8.0,
                warnings=["Compute capability inferred from GPU name (PyTorch CUDA unavailable)"],
            )
        except Exception as e:
            raise DetectionFailedError(
                component="NVIDIA GPU",
                message=f"nvidia-smi detection failed: {e}",
                details="Ensure NVIDIA drivers are installed and nvidia-smi is accessible."
            )

    def _infer_compute_capability(self, gpu_name: str) -> Optional[float]:
        """
        Infer compute capability from GPU name.

        This is a fallback when PyTorch CUDA is unavailable.
        Per SPEC_v3 Section 4.3 compute capability matrix.
        """
        name = gpu_name.upper()

        # RTX 50 series (Blackwell) - CC 12.0
        if any(x in name for x in ["5090", "5080", "5070"]):
            return 12.0

        # RTX 40 series (Ada Lovelace) - CC 8.9
        if any(x in name for x in ["4090", "4080", "4070", "4060"]):
            return 8.9

        # RTX 30 series (Ampere) - CC 8.6
        if any(x in name for x in ["3090", "3080", "3070", "3060"]):
            return 8.6

        # RTX 20 series (Turing) - CC 7.5
        if any(x in name for x in ["2080", "2070", "2060"]):
            return 7.5

        # Data center GPUs
        if "H100" in name:
            return 9.0
        if "A100" in name:
            return 8.0
        if "V100" in name:
            return 7.0

        return None

    def _detect_wsl(self) -> bool:
        """Detect if running in WSL2."""
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except FileNotFoundError:
            return False

    def _check_nvlink(self) -> bool:
        """Check if NVLink is available between GPUs."""
        try:
            creation_flags = 0
            if platform.system() == "Windows":
                creation_flags = subprocess.CREATE_NO_WINDOW

            output = subprocess.check_output(
                ["nvidia-smi", "nvlink", "--status"],
                creationflags=creation_flags,
                stderr=subprocess.DEVNULL
            ).decode()

            return "NVLink" in output and "inactive" not in output.lower()
        except Exception:
            return False

    def _get_system_ram(self) -> float:
        """Get system RAM in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            log.warning("psutil not available, cannot get system RAM")
            return 0.0

    def get_thermal_state(self) -> Optional[str]:
        """
        Get GPU thermal state via nvidia-smi.

        Per SPEC_v3 Section 4.6.1:
        - NORMAL: <82C
        - WARNING: 82-84C (approaching throttle)
        - CRITICAL: 85C+ (active throttling)
        """
        try:
            creation_flags = 0
            if platform.system() == "Windows":
                creation_flags = subprocess.CREATE_NO_WINDOW

            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                creationflags=creation_flags,
                stderr=subprocess.DEVNULL
            ).decode()

            temp = int(output.strip().split('\n')[0])

            if temp >= 85:
                return ThermalState.CRITICAL.value
            elif temp >= 82:
                return ThermalState.WARNING.value
            else:
                return ThermalState.NORMAL.value
        except Exception as e:
            log.debug(f"Thermal state detection failed: {e}")
            return None
