"""
NVIDIA GPU hardware detector per SPEC_v3 Section 4.3.

Handles detection for Windows/Linux with NVIDIA GPUs.
40% Windows + portion of 20% Linux = ~50% of target user base.

Key features:
- CUDA compute capability detection for FP8/BF16/Flash Attention support
- Multi-GPU detection with NVLink topology
- WSL2 detection
- Thermal state monitoring
- Phase 1 Week 2a: CPU, RAM, Storage, Form Factor detection

NEW in Phase 1 - does not replace existing code.
See: docs/spec/MIGRATION_PROTOCOL.md Section 3
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
from src.services.hardware.cpu import detect_cpu
from src.services.hardware.ram import detect_ram
from src.services.hardware.storage import detect_storage
from src.services.hardware.form_factor import detect_form_factor
from src.utils.logger import log
from src.utils.subprocess_utils import run_command


class NVIDIADetector(HardwareDetector):
    """
    Detection strategy for Windows/Linux with NVIDIA GPUs.

    Uses PyTorch CUDA APIs for primary detection with nvidia-smi fallback.
    Detects compute capability for precision support (FP8, BF16, etc.).
    """

    # GPU memory bandwidth lookup table (GB/s)
    # Based on memory type and bus width per GPU series
    # Source: NVIDIA specifications
    GPU_BANDWIDTH_GBPS = {
        # Blackwell (RTX 50 series) - GDDR7
        "5090": 1792,  # 512-bit GDDR7
        "5080": 960,   # 256-bit GDDR7
        "5070 ti": 896,
        "5070": 672,
        # Ada Lovelace (RTX 40 series) - GDDR6X
        "4090": 1008,  # 384-bit GDDR6X
        "4080 super": 736,
        "4080": 736,   # 256-bit GDDR6X
        "4070 ti super": 672,
        "4070 ti": 504,
        "4070 super": 504,
        "4070": 504,   # 192-bit GDDR6X
        "4060 ti": 288,
        "4060": 272,   # 128-bit GDDR6
        # Ampere (RTX 30 series) - GDDR6X/GDDR6
        "3090 ti": 1008,
        "3090": 936,   # 384-bit GDDR6X
        "3080 ti": 912,
        "3080": 760,   # 320-bit GDDR6X
        "3070 ti": 608,
        "3070": 448,   # 256-bit GDDR6
        "3060 ti": 448,
        "3060": 360,   # 192-bit GDDR6
        # Turing (RTX 20 series) - GDDR6
        "2080 ti": 616,
        "2080 super": 496,
        "2080": 448,
        "2070 super": 448,
        "2070": 448,
        "2060 super": 448,
        "2060": 336,
        # Data center
        "h100": 3350,  # HBM3
        "a100": 2039,  # HBM2e
        "v100": 900,   # HBM2
    }

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

    def _lookup_gpu_bandwidth(self, gpu_name: str) -> Optional[float]:
        """
        Look up GPU memory bandwidth from specifications.

        Args:
            gpu_name: GPU name string (e.g., "NVIDIA GeForce RTX 4090")

        Returns:
            Memory bandwidth in GB/s, or None if not found
        """
        import re

        # Normalize GPU name
        name_lower = gpu_name.lower()
        name_lower = name_lower.replace("nvidia", "")
        name_lower = name_lower.replace("geforce", "")
        name_lower = name_lower.replace("rtx", "")
        name_lower = name_lower.replace("gtx", "")
        name_lower = name_lower.strip()

        # Try exact match with suffixes first
        for key, bandwidth in self.GPU_BANDWIDTH_GBPS.items():
            if key in name_lower:
                return float(bandwidth)

        # Try to extract model number
        model_pattern = r'(\d{4})\s*(ti|super)?'
        match = re.search(model_pattern, name_lower)

        if match:
            model_key = match.group(1)
            suffix = match.group(2) or ""
            if suffix:
                full_key = f"{model_key} {suffix}"
                if full_key in self.GPU_BANDWIDTH_GBPS:
                    return float(self.GPU_BANDWIDTH_GBPS[full_key])

            if model_key in self.GPU_BANDWIDTH_GBPS:
                return float(self.GPU_BANDWIDTH_GBPS[model_key])

        log.debug(f"No bandwidth data found for GPU: {gpu_name}")
        return None

    def detect(self) -> HardwareProfile:
        """
        Detect NVIDIA GPU hardware.

        Returns:
            HardwareProfile with compute capability and precision support

        Raises:
            NoCUDAError: If CUDA is not available
            DetectionFailedError: If detection fails
        """
        # Try PyTorch CUDA first for best detection (compute capability, etc.)
        torch_available = False
        try:
            import torch
            torch_available = torch.cuda.is_available()
        except ImportError:
            # PyTorch not installed - will use nvidia-smi fallback
            log.info("PyTorch not installed, using nvidia-smi for GPU detection")

        if not torch_available:
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

        # Determine platform type
        if is_wsl:
            plat = PlatformType.WSL2_NVIDIA
        elif platform.system() == "Windows":
            plat = PlatformType.WINDOWS_NVIDIA
        else:
            plat = PlatformType.LINUX_NVIDIA

        # Phase 1 Week 2a: Extended detection
        # CPU detection
        try:
            cpu_profile = detect_cpu()
        except DetectionFailedError as e:
            log.warning(f"CPU detection failed: {e.message}")
            cpu_profile = None

        # RAM detection
        try:
            ram_profile = detect_ram()
        except DetectionFailedError as e:
            log.warning(f"RAM detection failed: {e.message}")
            ram_profile = None

        # Storage detection (uses current working directory)
        try:
            storage_profile = detect_storage()
        except Exception as e:
            log.warning(f"Storage detection failed: {e}")
            storage_profile = None

        # Form factor detection (NVIDIA-specific)
        try:
            form_factor_profile = detect_form_factor(gpu_name)
        except Exception as e:
            log.warning(f"Form factor detection failed: {e}")
            form_factor_profile = None

        # GPU memory bandwidth lookup
        gpu_bandwidth = self._lookup_gpu_bandwidth(gpu_name)

        return HardwareProfile(
            platform=plat,
            gpu_vendor="nvidia",
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            unified_memory=False,
            # Nested profiles (Phase 1 Week 2a)
            cpu=cpu_profile,
            ram=ram_profile,
            storage=storage_profile,
            form_factor=form_factor_profile,
            # Compute capability-based features
            compute_capability=compute_capability,
            supports_fp8=compute_capability >= 8.9,      # Ada Lovelace+
            supports_bf16=compute_capability >= 8.0,     # Ampere+
            supports_tf32=compute_capability >= 8.0,     # Ampere+
            flash_attention_available=compute_capability >= 8.0,
            # Memory bandwidth for offload calculations
            gpu_bandwidth_gbps=gpu_bandwidth,
            # Multi-GPU
            gpu_count=gpu_count,
            nvlink_available=nvlink_available,
        )

    def _detect_via_nvidia_smi(self) -> HardwareProfile:
        """
        Fallback detection via nvidia-smi when PyTorch CUDA unavailable.

        Provides basic GPU info without compute capability details.
        Uses shared utilities per ARCHITECTURE_PRINCIPLES.md.
        """
        try:
            # Use shared utility for consistent error handling
            output = run_command(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                timeout=10
            )

            if not output:
                raise DetectionFailedError(
                    component="NVIDIA GPU",
                    message="nvidia-smi returned no output",
                    details="Ensure NVIDIA drivers are installed."
                )

            name, mem = output.strip().split(',')
            vram_gb = float(mem.strip()) / 1024

            # Infer compute capability from GPU name (approximate)
            cc = self._infer_compute_capability(name)
            gpu_name_clean = name.strip()

            # GPU memory bandwidth lookup
            gpu_bandwidth = self._lookup_gpu_bandwidth(gpu_name_clean)

            return HardwareProfile(
                platform=PlatformType.WINDOWS_NVIDIA if platform.system() == "Windows" else PlatformType.LINUX_NVIDIA,
                gpu_vendor="nvidia",
                gpu_name=gpu_name_clean,
                vram_gb=vram_gb,
                unified_memory=False,
                compute_capability=cc,
                supports_fp8=cc is not None and cc >= 8.9,
                supports_bf16=cc is not None and cc >= 8.0,
                supports_tf32=cc is not None and cc >= 8.0,
                flash_attention_available=cc is not None and cc >= 8.0,
                gpu_bandwidth_gbps=gpu_bandwidth,
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
        # Use shared utility for consistent error handling
        output = run_command(["nvidia-smi", "nvlink", "--status"], timeout=5)
        if not output:
            return False
        return "NVLink" in output and "inactive" not in output.lower()

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
        # Use shared utility for consistent error handling
        output = run_command(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            timeout=5
        )

        if not output:
            log.debug("Thermal state detection returned no output")
            return None

        try:
            temp = int(output.strip().split('\n')[0])

            if temp >= 85:
                return ThermalState.CRITICAL.value
            elif temp >= 82:
                return ThermalState.WARNING.value
            else:
                return ThermalState.NORMAL.value
        except (ValueError, IndexError) as e:
            log.debug(f"Thermal state parsing failed: {e}")
            return None
