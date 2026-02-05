"""
Hardware detection module per SPEC_v3 Section 4.

Provides platform-specific hardware detection with a unified interface.

Usage:
    from src.services.hardware import get_detector, detect_hardware

    # Get appropriate detector for current platform
    detector = get_detector()
    profile = detector.detect()

    # Or use convenience function
    profile = detect_hardware()

NEW in Phase 1 - does not replace existing code.
See: docs/spec/MIGRATION_PROTOCOL.md Section 3
"""

import platform
from typing import Optional

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    HardwareTier,
    CPUProfile,
    CPUTier,
    RAMProfile,
    StorageProfile,
    StorageTier,
    FormFactorProfile,
)
from src.services.hardware.base import (
    HardwareDetector,
    DetectionFailedError,
    NoCUDAError,
    NoROCmError,
)
from src.services.hardware.apple_silicon import AppleSiliconDetector
from src.services.hardware.nvidia import NVIDIADetector
from src.services.hardware.amd_rocm import AMDROCmDetector
from src.services.hardware.cpu import detect_cpu, get_cpu_model_name, detect_avx_support
from src.services.hardware.ram import (
    detect_ram,
    calculate_offload_viability,
    detect_memory_type,
    get_bandwidth_for_type,
)
from src.services.hardware.storage import (
    StorageType,
    detect_storage_type,
    detect_storage,
    get_storage_warning,
    get_estimated_load_time,
)
from src.services.hardware.form_factor import (
    detect_form_factor,
    detect_power_limit,
    calculate_sustained_performance_ratio,
)
from src.utils.logger import log


# Export public interface
__all__ = [
    # Main functions
    "get_detector",
    "detect_hardware",
    # Detection functions
    "detect_cpu",
    "detect_ram",
    "detect_storage",
    "detect_storage_type",
    "detect_form_factor",
    "detect_memory_type",
    "detect_power_limit",
    # Profile types
    "HardwareProfile",
    "CPUProfile",
    "RAMProfile",
    "StorageProfile",
    "FormFactorProfile",
    # Enums
    "HardwareTier",
    "PlatformType",
    "StorageType",
    "CPUTier",
    "StorageTier",
    # Detectors (for advanced use)
    "HardwareDetector",
    "AppleSiliconDetector",
    "NVIDIADetector",
    "AMDROCmDetector",
    # Errors
    "DetectionFailedError",
    "NoCUDAError",
    "NoROCmError",
    # Utility functions
    "get_storage_warning",
    "get_estimated_load_time",
    "get_cpu_model_name",
    "detect_avx_support",
    "calculate_offload_viability",
    "calculate_sustained_performance_ratio",
    "get_bandwidth_for_type",
]


def get_detector() -> HardwareDetector:
    """
    Factory function to get the appropriate hardware detector.

    Detection order (per SPEC_v3):
    1. Apple Silicon (Darwin + arm64)
    2. NVIDIA (nvidia-smi or CUDA available)
    3. AMD ROCm (Linux + rocminfo available)
    4. CPU-only fallback

    Returns:
        Appropriate HardwareDetector for the current platform

    Example:
        detector = get_detector()
        profile = detector.detect()
        print(f"Tier: {profile.tier.value}")
    """
    # 1. Apple Silicon
    apple_detector = AppleSiliconDetector()
    if apple_detector.is_available():
        log.debug("Using AppleSiliconDetector")
        return apple_detector

    # 2. NVIDIA
    nvidia_detector = NVIDIADetector()
    if nvidia_detector.is_available():
        log.debug("Using NVIDIADetector")
        return nvidia_detector

    # 3. AMD ROCm
    rocm_detector = AMDROCmDetector()
    if rocm_detector.is_available():
        log.debug("Using AMDROCmDetector")
        return rocm_detector

    # 4. CPU-only fallback
    log.warning("No GPU detected, using CPUOnlyDetector")
    return CPUOnlyDetector()


def detect_hardware() -> HardwareProfile:
    """
    Convenience function to detect hardware in one call.

    Returns:
        HardwareProfile for the current system

    Raises:
        DetectionFailedError: If detection fails

    Example:
        profile = detect_hardware()
        if profile.can_run_fp8:
            print("FP8 models available")
    """
    detector = get_detector()
    return detector.detect()


class CPUOnlyDetector(HardwareDetector):
    """
    Fallback detector when no GPU is detected.

    Returns minimal profile for CPU-only operation.
    """

    def is_available(self) -> bool:
        """Always available as fallback."""
        return True

    def detect(self) -> HardwareProfile:
        """Return CPU-only profile with nested profiles."""
        # Phase 1 Week 2a: Nested profile detection
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

        # Storage detection
        try:
            storage_profile = detect_storage()
        except Exception as e:
            log.warning(f"Storage detection failed: {e}")
            storage_profile = None

        return HardwareProfile(
            platform=PlatformType.CPU_ONLY,
            gpu_vendor="none",
            gpu_name="CPU Only",
            vram_gb=0.0,  # No GPU VRAM
            unified_memory=False,
            # Nested profiles (Phase 1 Week 2a)
            cpu=cpu_profile,
            ram=ram_profile,
            storage=storage_profile,
            form_factor=None,  # No GPU form factor
            warnings=[
                "No GPU detected - AI workloads will be very slow",
                "Consider using cloud APIs for generation tasks",
            ],
        )


# Utility functions for migration compatibility

def get_legacy_gpu_info() -> tuple:
    """
    Legacy-compatible function returning (gpu_vendor, gpu_name, vram_gb).

    Used by SystemService.get_gpu_info() during migration.
    See: docs/spec/MIGRATION_PROTOCOL.md Pattern B
    """
    try:
        profile = detect_hardware()
        return (profile.gpu_vendor, profile.gpu_name, profile.vram_gb)
    except DetectionFailedError as e:
        log.error(f"Hardware detection failed: {e}")
        # Return safe fallback that won't cause wrong recommendations
        # Note: This is different from the old 16GB fallback - we return 0
        # so the recommendation engine knows detection failed
        return ("none", f"Detection failed: {e.message}", 0.0)
