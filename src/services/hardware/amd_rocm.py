"""
AMD ROCm hardware detector per SPEC_v3 Section 4.4.

Handles detection for Linux with AMD GPUs using ROCm.
~20% of target user base.

Key constraints:
- Marked as experimental
- RDNA2 requires HSA_OVERRIDE_GFX_VERSION workaround
- Some CUDA-specific ComfyUI nodes unavailable
- Limited Flash Attention support

NEW in Phase 1 - does not replace existing code.
See: docs/MIGRATION_PROTOCOL.md Section 3
"""

import platform
import subprocess
import shutil
import re
from typing import Optional

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
)
from src.services.hardware.base import HardwareDetector, DetectionFailedError, NoROCmError
from src.utils.logger import log


class AMDROCmDetector(HardwareDetector):
    """
    Detection strategy for Linux with AMD GPUs.

    Uses rocminfo and amd-smi for detection.
    Marks RDNA2 GPUs as requiring workaround.
    """

    # Officially supported GFX versions (RDNA3)
    # Per SPEC_v3 Section 4.4
    OFFICIALLY_SUPPORTED_GFX = {
        "gfx1100": "RX 7900 XTX/XT",
        "gfx1101": "RX 7900 GRE",
        "gfx1102": "RX 7800 XT/7700 XT",
    }

    # RDNA2 GPUs requiring workaround
    RDNA2_WORKAROUND = {
        "gfx1030": ("RX 6900 XT/6800", "HSA_OVERRIDE_GFX_VERSION=10.3.0"),
        "gfx1031": ("RX 6700 XT", "HSA_OVERRIDE_GFX_VERSION=10.3.0"),
        "gfx1032": ("RX 6600 XT", "HSA_OVERRIDE_GFX_VERSION=10.3.0"),
    }

    def is_available(self) -> bool:
        """Check if AMD ROCm detection is possible."""
        # Only available on Linux
        if platform.system() != "Linux":
            return False

        # Check for rocminfo or amd-smi
        return shutil.which("rocminfo") is not None or shutil.which("amd-smi") is not None

    def detect(self) -> HardwareProfile:
        """
        Detect AMD ROCm hardware.

        Returns:
            HardwareProfile with ROCm-specific info and experimental flag

        Raises:
            NoROCmError: If ROCm tools are not available
            DetectionFailedError: If detection fails
        """
        if not self.is_available():
            raise NoROCmError()

        # Get GPU info via rocminfo
        gpu_name, gfx_version = self._get_gpu_info()

        # Get VRAM via amd-smi or rocm-smi
        vram_gb = self._get_vram()

        # Get ROCm version
        rocm_version = self._get_rocm_version()

        # Check if officially supported
        officially_supported = gfx_version in self.OFFICIALLY_SUPPORTED_GFX
        hsa_override = None

        if not officially_supported and gfx_version in self.RDNA2_WORKAROUND:
            _, hsa_override = self.RDNA2_WORKAROUND[gfx_version]

        # Get system RAM
        ram_gb = self._get_system_ram()

        # Build warnings list
        warnings = ["ROCm support is experimental"]
        if not officially_supported:
            if hsa_override:
                warnings.append(f"RDNA2 GPU - set {hsa_override} before running")
            else:
                warnings.append(f"GPU architecture {gfx_version} may have compatibility issues")

        return HardwareProfile(
            platform=PlatformType.LINUX_ROCM,
            gpu_vendor="amd",
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            unified_memory=False,
            # AMD doesn't support these in the same way
            compute_capability=None,
            supports_fp8=False,  # Not available on current AMD GPUs
            supports_bf16=True,  # RDNA3 supports BF16
            supports_tf32=False,
            flash_attention_available=False,  # Limited FA support on ROCm
            # ROCm-specific
            rocm_version=rocm_version,
            gfx_version=gfx_version,
            officially_supported=officially_supported,
            hsa_override_required=hsa_override,
            warnings=warnings,
        )

    def _get_gpu_info(self) -> tuple[str, str]:
        """
        Get GPU name and GFX version via rocminfo.

        Returns:
            (gpu_name, gfx_version) tuple
        """
        try:
            output = subprocess.check_output(
                ["rocminfo"],
                stderr=subprocess.DEVNULL
            ).decode()

            # Parse GPU name
            name_match = re.search(r"Marketing Name:\s+(.+)", output)
            gpu_name = name_match.group(1).strip() if name_match else "AMD GPU"

            # Parse GFX version
            gfx_match = re.search(r"Name:\s+(gfx\d+)", output)
            gfx_version = gfx_match.group(1) if gfx_match else "unknown"

            return gpu_name, gfx_version
        except Exception as e:
            log.warning(f"rocminfo parsing failed: {e}")
            return "AMD GPU", "unknown"

    def _get_vram(self) -> float:
        """Get VRAM via amd-smi or rocm-smi."""
        # Try amd-smi first (newer tool)
        if shutil.which("amd-smi"):
            try:
                output = subprocess.check_output(
                    ["amd-smi", "static", "--vram"],
                    stderr=subprocess.DEVNULL
                ).decode()
                # Parse VRAM from output (format varies)
                match = re.search(r"(\d+)\s*(?:MB|GB)", output, re.IGNORECASE)
                if match:
                    value = int(match.group(1))
                    if "GB" in output.upper():
                        return float(value)
                    return value / 1024  # Convert MB to GB
            except Exception as e:
                log.warning(f"amd-smi failed: {e}")

        # Fallback to rocm-smi
        if shutil.which("rocm-smi"):
            try:
                output = subprocess.check_output(
                    ["rocm-smi", "--showmeminfo", "vram"],
                    stderr=subprocess.DEVNULL
                ).decode()
                # Parse total VRAM
                match = re.search(r"Total Memory \(B\):\s+(\d+)", output)
                if match:
                    return int(match.group(1)) / (1024 ** 3)
            except Exception as e:
                log.warning(f"rocm-smi failed: {e}")

        raise DetectionFailedError(
            component="VRAM",
            message="Could not detect AMD GPU VRAM",
            details="Neither amd-smi nor rocm-smi provided VRAM information."
        )

    def _get_rocm_version(self) -> Optional[str]:
        """Get installed ROCm version."""
        try:
            # Check /opt/rocm/.info/version
            with open("/opt/rocm/.info/version", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            pass

        # Try rocminfo output
        try:
            output = subprocess.check_output(
                ["rocminfo"],
                stderr=subprocess.DEVNULL
            ).decode()
            match = re.search(r"ROCm Runtime Version:\s+(.+)", output)
            if match:
                return match.group(1).strip()
        except Exception:
            pass

        return None

    def _get_system_ram(self) -> float:
        """Get system RAM in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            # Fallback to /proc/meminfo
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return kb / (1024 ** 2)
            except Exception:
                pass
            return 0.0

    def get_thermal_state(self) -> Optional[str]:
        """
        Get GPU thermal state via amd-smi or rocm-smi.

        Note: Thermal monitoring is lower priority - returns None for now.
        """
        # TODO: Implement if needed
        return None
