"""
Form factor detection module per HARDWARE_DETECTION.md Section 2.

NVIDIA-specific detection of laptop vs desktop GPUs based on power limits.
Calculates sustained performance ratio for thermal-constrained mobile GPUs.

Performance ratio = sqrt(actual_power / reference_tdp)
Example: RTX 4090 Laptop (175W) = sqrt(175/450) ≈ 62% of desktop performance

Phase 1 Week 2a implementation.
"""

import math
import platform
import re
import subprocess
from typing import Optional, Tuple

from src.schemas.hardware import FormFactorProfile
from src.utils.logger import log


# Reference TDP database per HARDWARE_DETECTION.md Section 2.3
# Maps normalized GPU names to desktop reference TDP in watts
GPU_REFERENCE_TDP = {
    # Blackwell (RTX 50 series)
    "5090": 575,
    "5080": 360,
    "5070 ti": 300,
    "5070": 250,

    # Ada Lovelace (RTX 40 series)
    "4090": 450,
    "4080 super": 320,
    "4080": 320,
    "4070 ti super": 285,
    "4070 ti": 285,
    "4070 super": 220,
    "4070": 200,
    "4060 ti": 165,
    "4060": 115,

    # Ampere (RTX 30 series)
    "3090 ti": 450,
    "3090": 350,
    "3080 ti": 350,
    "3080": 320,
    "3070 ti": 290,
    "3070": 220,
    "3060 ti": 200,
    "3060": 170,

    # Turing (RTX 20 series)
    "2080 ti": 250,
    "2080 super": 250,
    "2080": 215,
    "2070 super": 215,
    "2070": 175,
    "2060 super": 175,
    "2060": 160,

    # Data center GPUs
    "h100": 700,
    "a100": 400,
    "a6000": 300,
    "a5000": 230,
    "a4000": 140,
    "v100": 300,
    "t4": 70,
}


def detect_form_factor(gpu_name: str) -> FormFactorProfile:
    """
    Detect GPU form factor (laptop vs desktop) based on power limits.

    Args:
        gpu_name: NVIDIA GPU name (e.g., "NVIDIA GeForce RTX 4090")

    Returns:
        FormFactorProfile with is_laptop, power limits, and performance ratio

    Example:
        form = detect_form_factor("NVIDIA GeForce RTX 4090 Laptop GPU")
        if form.is_laptop and form.sustained_performance_ratio < 0.8:
            print("Significant performance reduction on this laptop")
    """
    # Get actual power limit from nvidia-smi
    power_limit = detect_power_limit()

    if power_limit is None:
        # Fallback: Check if GPU name indicates mobile
        is_mobile = _detect_mobile_from_name(gpu_name)
        return FormFactorProfile(
            is_laptop=is_mobile,
            power_limit_watts=None,
            reference_tdp_watts=None,
            sustained_performance_ratio=0.85 if is_mobile else 1.0,
        )

    # Calculate performance ratio
    is_laptop, ratio, ref_tdp = calculate_sustained_performance_ratio(
        gpu_name, power_limit
    )

    return FormFactorProfile(
        is_laptop=is_laptop,
        power_limit_watts=power_limit,
        reference_tdp_watts=ref_tdp,
        sustained_performance_ratio=ratio,
    )


def detect_power_limit() -> Optional[float]:
    """
    Get GPU power limit via nvidia-smi.

    Returns:
        Power limit in watts, or None if detection fails

    Note:
        Uses power.limit query which shows enforced limit,
        not power.max_limit (hardware maximum).
    """
    try:
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=power.limit",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            # May return multiple values for multi-GPU, take first
            power_str = result.stdout.strip().split('\n')[0]
            return float(power_str)

    except FileNotFoundError:
        log.debug("nvidia-smi not found, cannot detect power limit")
    except subprocess.TimeoutExpired:
        log.debug("nvidia-smi timed out")
    except Exception as e:
        log.debug(f"Power limit detection failed: {e}")

    return None


def _detect_mobile_from_name(gpu_name: str) -> bool:
    """
    Detect if GPU name indicates mobile variant.

    Args:
        gpu_name: GPU name string

    Returns:
        True if name suggests mobile GPU
    """
    name_lower = gpu_name.lower()

    mobile_indicators = [
        "laptop",
        "mobile",
        "max-q",
        "notebook",
        "laptop gpu",
    ]

    return any(ind in name_lower for ind in mobile_indicators)


def lookup_reference_tdp(gpu_name: str) -> Optional[float]:
    """
    Look up desktop reference TDP for a GPU.

    Args:
        gpu_name: GPU name string (e.g., "NVIDIA GeForce RTX 4090")

    Returns:
        Reference TDP in watts, or None if not found
    """
    # Normalize GPU name
    name_lower = gpu_name.lower()

    # Remove common prefixes
    name_lower = name_lower.replace("nvidia", "")
    name_lower = name_lower.replace("geforce", "")
    name_lower = name_lower.replace("rtx", "")
    name_lower = name_lower.replace("gtx", "")
    name_lower = name_lower.replace("laptop gpu", "")
    name_lower = name_lower.replace("laptop", "")
    name_lower = name_lower.replace("mobile", "")
    name_lower = name_lower.replace("max-q", "")
    name_lower = name_lower.strip()

    # Try exact match first
    if name_lower in GPU_REFERENCE_TDP:
        return GPU_REFERENCE_TDP[name_lower]

    # Try to extract model number with regex
    # Matches patterns like "4090", "3080 ti", "4070 super"
    model_pattern = r'(\d{4})\s*(ti|super)?'
    match = re.search(model_pattern, name_lower)

    if match:
        model_key = match.group(1)
        suffix = match.group(2) or ""
        if suffix:
            model_key = f"{model_key} {suffix}"

        if model_key in GPU_REFERENCE_TDP:
            return GPU_REFERENCE_TDP[model_key]

        # Try without suffix
        if match.group(1) in GPU_REFERENCE_TDP:
            return GPU_REFERENCE_TDP[match.group(1)]

    # Check for data center GPUs
    for key in ["h100", "a100", "a6000", "a5000", "a4000", "v100", "t4"]:
        if key in name_lower:
            return GPU_REFERENCE_TDP[key]

    log.debug(f"No reference TDP found for GPU: {gpu_name}")
    return None


def calculate_sustained_performance_ratio(
    gpu_name: str,
    actual_power_limit: float
) -> Tuple[bool, float, Optional[float]]:
    """
    Calculate sustained performance ratio for mobile GPUs.

    Per HARDWARE_DETECTION.md Section 2.2:
    - Performance ratio = sqrt(actual_power / reference_tdp)
    - Desktop GPUs at full power = 1.0
    - Laptops typically 60-85% of desktop

    Args:
        gpu_name: GPU name for TDP lookup
        actual_power_limit: Detected power limit in watts

    Returns:
        Tuple of (is_laptop, performance_ratio, reference_tdp)

    Example:
        RTX 4090 Desktop at 450W → (False, 1.0, 450)
        RTX 4090 Laptop at 175W → (True, 0.623, 450)
    """
    reference_tdp = lookup_reference_tdp(gpu_name)

    if reference_tdp is None:
        # Unknown GPU - can't determine form factor from power
        # Check name for mobile indicators
        is_mobile = _detect_mobile_from_name(gpu_name)
        return (is_mobile, 0.85 if is_mobile else 1.0, None)

    # Calculate power ratio
    power_ratio = actual_power_limit / reference_tdp

    # Desktop threshold: within 5% of reference TDP
    if power_ratio >= 0.95:
        return (False, 1.0, reference_tdp)

    # Mobile GPU - calculate performance ratio using sqrt
    # sqrt approximates the relationship between power and performance
    performance_ratio = math.sqrt(power_ratio)

    # Clamp to reasonable range (50% - 100%)
    performance_ratio = max(0.5, min(1.0, performance_ratio))

    return (True, performance_ratio, reference_tdp)


def get_form_factor_warning(profile: FormFactorProfile) -> Optional[str]:
    """
    Generate user-facing warning for laptop GPUs.

    Args:
        profile: FormFactorProfile to analyze

    Returns:
        Warning string or None if no warning needed
    """
    if not profile.is_laptop:
        return None

    if profile.sustained_performance_ratio >= 0.85:
        return None  # Minor difference, no warning

    pct = int(profile.sustained_performance_ratio * 100)

    if profile.power_limit_watts and profile.reference_tdp_watts:
        return (
            f"Laptop GPU detected with ~{pct}% sustained performance "
            f"({profile.power_limit_watts:.0f}W vs "
            f"{profile.reference_tdp_watts:.0f}W desktop reference). "
            "Generation times may be 25-50% longer than desktop benchmarks."
        )
    else:
        return (
            f"Laptop GPU detected with ~{pct}% sustained performance. "
            "Generation times may be longer than desktop benchmarks."
        )
