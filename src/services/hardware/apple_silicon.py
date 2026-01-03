"""
Apple Silicon hardware detector per SPEC_v3 Section 4.2.

Handles detection for macOS with Apple Silicon (M1/M2/M3/M4).
40% of target user base.

Key constraints:
- 75% memory ceiling for effective VRAM
- No FP8 support
- K-quants crash on MPS (filter to Q4_0, Q5_0, Q8_0)
- No Flash Attention
- HunyuanVideo impractical (<Professional tier)

NEW in Phase 1 - does not replace existing code.
See: docs/MIGRATION_PROTOCOL.md Section 3
"""

import platform
import subprocess
import re
from typing import Optional

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    ThermalState,
)
from src.services.hardware.base import HardwareDetector, DetectionFailedError
from src.utils.logger import log


class AppleSiliconDetector(HardwareDetector):
    """
    Detection strategy for Apple Silicon Macs.

    Uses sysctl for primary detection with system_profiler as fallback.
    Applies 75% memory ceiling for effective VRAM calculation.
    """

    # Memory bandwidth lookup table (GB/s) per chip variant
    # Per SPEC_v3 Section 4.2
    BANDWIDTH_LOOKUP = {
        "M1": 68,
        "M1 Pro": 200,
        "M1 Max": 400,
        "M1 Ultra": 800,
        "M2": 100,
        "M2 Pro": 200,
        "M2 Max": 400,
        "M2 Ultra": 800,
        "M3": 100,
        "M3 Pro": 150,
        "M3 Max": 400,
        "M3 Ultra": 800,  # Added - same as M2 Ultra architecture
        "M4": 120,
        "M4 Pro": 273,
        "M4 Max": 546,
        "M4 Ultra": 800,  # Added - estimated based on architecture
    }

    def is_available(self) -> bool:
        """Check if running on Apple Silicon Mac."""
        return (
            platform.system() == "Darwin" and
            platform.machine() == "arm64"
        )

    def detect(self) -> HardwareProfile:
        """
        Detect Apple Silicon hardware.

        Returns:
            HardwareProfile with 75% memory ceiling applied

        Raises:
            DetectionFailedError: If RAM detection fails with no valid fallback
        """
        # Get chip name
        chip_string = self._get_chip_name()
        chip_variant = self._parse_chip_variant(chip_string)

        # Get unified memory - CRITICAL: No fallback to 16GB
        unified_memory_gb = self._get_unified_memory()

        # Apply 75% memory ceiling (macOS reserves ~25%)
        effective_vram_gb = unified_memory_gb * 0.75

        # Check MPS availability
        mps_available = self._check_mps()

        # Look up memory bandwidth
        bandwidth = self.BANDWIDTH_LOOKUP.get(chip_variant, 68)

        return HardwareProfile(
            platform=PlatformType.APPLE_SILICON,
            gpu_vendor="apple",
            gpu_name=chip_string,
            vram_gb=effective_vram_gb,
            ram_gb=unified_memory_gb,
            unified_memory=True,
            # Apple Silicon does not support these
            compute_capability=None,
            supports_fp8=False,
            supports_bf16=False,  # Not hardware-accelerated
            supports_tf32=False,
            flash_attention_available=False,
            # Apple-specific
            mps_available=mps_available,
            memory_bandwidth_gbps=bandwidth,
            chip_variant=chip_variant,
        )

    def _get_chip_name(self) -> str:
        """Get Apple Silicon chip name via sysctl."""
        try:
            result = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL
            )
            return result.decode().strip()
        except Exception as e:
            log.warning(f"Failed to get chip name via sysctl: {e}")
            # Fallback to generic name - this is safe since it doesn't affect recommendations
            return "Apple Silicon"

    def _get_unified_memory(self) -> float:
        """
        Get unified memory size.

        CRITICAL: Per SPEC_v3, we must NOT fallback to 16GB on error.
        Wrong RAM = wrong recommendations for 8GB and 128GB machines.

        Raises:
            DetectionFailedError: If both sysctl and system_profiler fail
        """
        # Primary: sysctl
        try:
            result = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL
            )
            ram_bytes = int(result.decode().strip())
            return ram_bytes / (1024 ** 3)
        except Exception as e:
            log.warning(f"sysctl hw.memsize failed: {e}, trying system_profiler")

        # Fallback: system_profiler (slower but more reliable)
        try:
            result = subprocess.check_output(
                ["system_profiler", "SPHardwareDataType"],
                stderr=subprocess.DEVNULL
            )
            output = result.decode()
            # Parse "Memory: 16 GB" or "Memory: 128 GB"
            match = re.search(r"Memory:\s*(\d+)\s*GB", output)
            if match:
                return float(match.group(1))
        except Exception as e:
            log.error(f"system_profiler also failed: {e}")

        # CRITICAL: Do NOT fallback to 16GB
        # Per SPEC_v3 Section 4.2: "Must fail explicitly or use alternative detection"
        raise DetectionFailedError(
            component="RAM",
            message="Could not detect unified memory size",
            details=(
                "Both sysctl and system_profiler failed. "
                "Please report this issue with your Mac model."
            )
        )

    def _parse_chip_variant(self, chip_string: str) -> str:
        """
        Parse chip variant from brand string.

        Examples:
            "Apple M3 Max" -> "M3 Max"
            "Apple M1" -> "M1"
        """
        # Remove "Apple " prefix if present
        chip = chip_string.replace("Apple ", "")

        # Match M1/M2/M3/M4 with optional Pro/Max/Ultra suffix
        match = re.match(r"(M[1-4](?:\s+(?:Pro|Max|Ultra))?)", chip)
        if match:
            return match.group(1)

        # Unknown variant - return as-is for logging
        return chip

    def _check_mps(self) -> bool:
        """Check if MPS (Metal Performance Shaders) is available."""
        try:
            import torch
            return torch.backends.mps.is_available()
        except ImportError:
            log.warning("PyTorch not available, cannot check MPS")
            return False
        except Exception as e:
            log.warning(f"MPS check failed: {e}")
            return False

    def get_thermal_state(self) -> Optional[str]:
        """
        Get thermal state via IOKit (macOS).

        Note: Requires additional implementation for full thermal monitoring.
        Returns None for now as thermal detection is lower priority.
        """
        # TODO: Implement via IOKit if needed
        return None
