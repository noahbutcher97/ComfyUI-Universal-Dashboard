"""
CPU detection module per HARDWARE_DETECTION.md Section 3.

Provides platform-agnostic CPU detection for:
- Model name and architecture
- Physical and logical core counts
- AVX/AVX2/AVX512 instruction support (x86 only)
- CPU tier classification for offload viability

Phase 1 Week 2a implementation.
"""

import platform
import subprocess
from typing import Tuple

from src.schemas.hardware import CPUProfile, CPUTier
from src.services.hardware.base import DetectionFailedError
from src.utils.logger import log


def detect_cpu() -> CPUProfile:
    """
    Detect CPU specifications across platforms.

    Returns:
        CPUProfile with model, cores, AVX support, and tier

    Raises:
        DetectionFailedError: If CPU detection fails completely

    Example:
        cpu = detect_cpu()
        if cpu.can_offload:
            print(f"{cpu.model} supports layer offload")
    """
    try:
        model = get_cpu_model_name()
        architecture = platform.machine()  # x86_64, arm64, etc.
        physical_cores, logical_cores = get_core_counts()
        avx, avx2, avx512 = detect_avx_support(architecture)

        return CPUProfile(
            model=model,
            architecture=architecture,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            supports_avx=avx,
            supports_avx2=avx2,
            supports_avx512=avx512,
        )
    except Exception as e:
        log.error(f"CPU detection failed: {e}")
        raise DetectionFailedError(
            component="CPU",
            message="Could not detect CPU specifications",
            details=str(e)
        )


def get_cpu_model_name() -> str:
    """
    Get CPU model name using platform-specific methods.

    Returns:
        Human-readable CPU model name

    Detection methods:
    - Windows: Registry HKEY_LOCAL_MACHINE\\HARDWARE\\...\\CentralProcessor\\0
    - macOS: sysctl -n machdep.cpu.brand_string
    - Linux: /proc/cpuinfo model name field
    """
    system = platform.system()

    if system == "Windows":
        return _get_cpu_model_windows()
    elif system == "Darwin":
        return _get_cpu_model_macos()
    elif system == "Linux":
        return _get_cpu_model_linux()
    else:
        return f"Unknown CPU ({platform.processor() or 'unknown'})"


def _get_cpu_model_windows() -> str:
    """Get CPU model name on Windows via registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        model, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return model.strip()
    except Exception as e:
        log.debug(f"Windows registry CPU detection failed: {e}")
        # Fallback to platform.processor()
        return platform.processor() or "Unknown Windows CPU"


def _get_cpu_model_macos() -> str:
    """Get CPU model name on macOS via sysctl."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # For Apple Silicon, try different approach
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Apple Silicon chips report via system_profiler
        if platform.machine() == "arm64":
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if "Chip:" in line:
                        return line.split(":")[-1].strip()

        return f"Apple {platform.machine()}"
    except Exception as e:
        log.debug(f"macOS CPU detection failed: {e}")
        return f"Unknown macOS CPU ({platform.machine()})"


def _get_cpu_model_linux() -> str:
    """Get CPU model name on Linux via /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":")[1].strip()
                # ARM processors may use different field
                if line.startswith("Model"):
                    return line.split(":")[1].strip()
        return "Unknown Linux CPU"
    except Exception as e:
        log.debug(f"Linux /proc/cpuinfo CPU detection failed: {e}")
        return platform.processor() or "Unknown Linux CPU"


def get_core_counts() -> Tuple[int, int]:
    """
    Get physical and logical CPU core counts.

    Returns:
        Tuple of (physical_cores, logical_cores)

    Uses psutil for accurate cross-platform detection.
    Falls back to os.cpu_count() if psutil unavailable.
    """
    try:
        import psutil
        physical = psutil.cpu_count(logical=False) or 1
        logical = psutil.cpu_count(logical=True) or physical
        return (physical, logical)
    except ImportError:
        log.warning("psutil not available, using os.cpu_count()")
        import os
        logical = os.cpu_count() or 1
        # Assume hyperthreading: physical = logical / 2
        physical = max(1, logical // 2)
        return (physical, logical)


def detect_avx_support(architecture: str) -> Tuple[bool, bool, bool]:
    """
    Detect AVX, AVX2, and AVX-512 support.

    Args:
        architecture: CPU architecture (x86_64, arm64, etc.)

    Returns:
        Tuple of (avx, avx2, avx512) booleans

    Note:
        - AVX instructions only apply to x86/x86_64
        - ARM64 uses NEON which is always available
        - Returns (False, False, False) for non-x86 or detection failure
    """
    # AVX only applies to x86/x86_64
    if architecture not in ("x86_64", "AMD64", "x86", "i386", "i686"):
        log.debug(f"AVX detection skipped for {architecture} architecture")
        return (False, False, False)

    # Try cpuinfo library first (most reliable)
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        flags = info.get("flags", [])

        avx = "avx" in flags
        avx2 = "avx2" in flags
        avx512 = any(f.startswith("avx512") for f in flags)

        log.debug(f"AVX support detected via cpuinfo: AVX={avx}, AVX2={avx2}, AVX512={avx512}")
        return (avx, avx2, avx512)
    except ImportError:
        log.debug("cpuinfo library not available, trying fallback detection")
    except Exception as e:
        log.debug(f"cpuinfo detection failed: {e}")

    # Fallback: Try platform-specific detection
    system = platform.system()

    if system == "Linux":
        return _detect_avx_linux()
    elif system == "Windows":
        return _detect_avx_windows()

    # Default: Assume no AVX (safe fallback)
    log.warning("Could not detect AVX support, assuming unavailable")
    return (False, False, False)


def _detect_avx_linux() -> Tuple[bool, bool, bool]:
    """Detect AVX support on Linux via /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            content = f.read().lower()

        flags_section = ""
        for line in content.split('\n'):
            if line.startswith("flags"):
                flags_section = line
                break

        avx = " avx " in f" {flags_section} "
        avx2 = " avx2 " in f" {flags_section} "
        avx512 = "avx512" in flags_section

        return (avx, avx2, avx512)
    except Exception as e:
        log.debug(f"Linux AVX detection failed: {e}")
        return (False, False, False)


def _detect_avx_windows() -> Tuple[bool, bool, bool]:
    """
    Detect AVX support on Windows.

    Note: Windows detection without cpuinfo is limited.
    We assume modern x86_64 CPUs (post-2011) have at least AVX.
    """
    # Most x86_64 CPUs from 2013+ have AVX2
    # This is a conservative fallback
    log.debug("Windows AVX detection: assuming AVX/AVX2 available on modern x86_64")
    return (True, True, False)


def calculate_cpu_tier(physical_cores: int) -> CPUTier:
    """
    Calculate CPU tier from physical core count.

    Per HARDWARE_DETECTION.md Section 3.3:
    - HIGH: 16+ cores
    - MEDIUM: 8-15 cores
    - LOW: 4-7 cores
    - MINIMAL: <4 cores

    Args:
        physical_cores: Number of physical CPU cores

    Returns:
        CPUTier enum value
    """
    if physical_cores >= 16:
        return CPUTier.HIGH
    elif physical_cores >= 8:
        return CPUTier.MEDIUM
    elif physical_cores >= 4:
        return CPUTier.LOW
    else:
        return CPUTier.MINIMAL
