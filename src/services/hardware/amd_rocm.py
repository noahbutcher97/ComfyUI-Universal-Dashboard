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
from src.services.hardware.cpu import detect_cpu
from src.services.hardware.ram import detect_ram
from src.services.hardware.storage import detect_storage
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

    # GPU memory bandwidth lookup table (GB/s)
    # Based on memory type and bus width per GPU series
    GPU_BANDWIDTH_GBPS = {
        # RDNA3 (RX 7000 series) - GDDR6
        "7900 xtx": 960,    # 384-bit GDDR6
        "7900 xt": 800,     # 320-bit GDDR6
        "7900 gre": 576,    # 256-bit GDDR6
        "7800 xt": 576,     # 256-bit GDDR6
        "7700 xt": 432,     # 192-bit GDDR6
        "7600 xt": 288,     # 128-bit GDDR6
        "7600": 288,        # 128-bit GDDR6
        # RDNA2 (RX 6000 series) - GDDR6
        "6950 xt": 576,     # 256-bit GDDR6
        "6900 xt": 512,     # 256-bit GDDR6
        "6800 xt": 512,     # 256-bit GDDR6
        "6800": 512,        # 256-bit GDDR6
        "6700 xt": 384,     # 192-bit GDDR6
        "6600 xt": 256,     # 128-bit GDDR6
        "6600": 224,        # 128-bit GDDR6
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

        # GPU memory bandwidth lookup
        gpu_bandwidth = self._lookup_gpu_bandwidth(gpu_name)

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
            unified_memory=False,
            # Nested profiles (Phase 1 Week 2a)
            cpu=cpu_profile,
            ram=ram_profile,
            storage=storage_profile,
            form_factor=None,  # AMD GPUs don't use power-based form factor detection (yet)
            # AMD doesn't support these in the same way
            compute_capability=None,
            supports_fp8=False,  # Not available on current AMD GPUs
            supports_bf16=True,  # RDNA3 supports BF16
            supports_tf32=False,
            flash_attention_available=False,  # Limited FA support on ROCm
            # GPU memory bandwidth for offload calculations
            gpu_bandwidth_gbps=gpu_bandwidth,
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

    def _lookup_gpu_bandwidth(self, gpu_name: str) -> Optional[float]:
        """
        Look up GPU memory bandwidth from specifications.

        Args:
            gpu_name: GPU name string (e.g., "AMD Radeon RX 7900 XTX")

        Returns:
            Memory bandwidth in GB/s, or None if not found
        """
        # Normalize GPU name
        name_lower = gpu_name.lower()
        name_lower = name_lower.replace("amd", "")
        name_lower = name_lower.replace("radeon", "")
        name_lower = name_lower.replace("rx", "")
        name_lower = name_lower.strip()

        # Try direct match
        for key, bandwidth in self.GPU_BANDWIDTH_GBPS.items():
            if key in name_lower:
                return float(bandwidth)

        # Try extracting model number
        model_pattern = r'(\d{4})\s*(xt|xtx|gre)?'
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

        log.debug(f"No bandwidth data found for AMD GPU: {gpu_name}")
        return None

    def get_thermal_state(self) -> Optional[str]:
        """
        Get GPU thermal state via rocm-smi temperature reading.

        Uses `rocm-smi --showtemp` to get GPU temperature.
        Returns: "nominal", "fair", "serious", "critical", or None if detection fails.

        Thermal thresholds (typical for AMD GPUs):
        - nominal: < 70°C
        - fair: 70-85°C
        - serious: 85-95°C
        - critical: > 95°C

        Per SPEC §4.6.1: Maps to ThermalState enum values.
        """
        try:
            # Try rocm-smi first
            result = subprocess.run(
                ["rocm-smi", "--showtemp"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self._parse_rocm_smi_temp(result.stdout)

            # Fall back to amd-smi (newer ROCm versions)
            result = subprocess.run(
                ["amd-smi", "metric", "-t"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return self._parse_amd_smi_temp(result.stdout)

            log.debug("Both rocm-smi and amd-smi failed for thermal detection")
            return None

        except subprocess.TimeoutExpired:
            log.warning("ROCm thermal check timed out")
            return None
        except FileNotFoundError:
            log.debug("rocm-smi/amd-smi not found")
            return None
        except Exception as e:
            log.warning(f"AMD thermal state detection failed: {e}")
            return None

    def _parse_rocm_smi_temp(self, output: str) -> Optional[str]:
        """Parse temperature from rocm-smi --showtemp output."""
        # Look for temperature values like "Temperature (Sensor edge) (C): 45.0"
        # or "GPU[0] : Temperature (Sensor junction) (C): 52.0"
        temp_match = re.search(r'Temperature.*?:\s*(\d+(?:\.\d+)?)', output)
        if temp_match:
            temp = float(temp_match.group(1))
            return self._temp_to_state(temp)

        return None

    def _parse_amd_smi_temp(self, output: str) -> Optional[str]:
        """Parse temperature from amd-smi metric -t output."""
        # amd-smi outputs temperature with field labels like:
        # "TEMPERATURE: 45.0 C" or "Temperature (C): 52" or "GPU Temperature: 67°C"
        # Use specific patterns to avoid matching unrelated numbers (e.g. "PCIe Gen3")
        patterns = [
            r'[Tt]emperature[^:]*:\s*(\d+(?:\.\d+)?)\s*[°]?C?',  # "Temperature: 45.0 C"
            r'TEMP(?:ERATURE)?[^:]*:\s*(\d+(?:\.\d+)?)',         # "TEMP: 45" or "TEMPERATURE: 45"
            r'(\d+(?:\.\d+)?)\s*°C',                              # "45.0°C" (degree symbol required)
        ]
        for pattern in patterns:
            temp_match = re.search(pattern, output, re.IGNORECASE)
            if temp_match:
                temp = float(temp_match.group(1))
                return self._temp_to_state(temp)

        return None

    def _temp_to_state(self, temp_celsius: float) -> str:
        """Convert temperature to thermal state string."""
        if temp_celsius < 70:
            return "nominal"
        elif temp_celsius < 85:
            return "fair"
        elif temp_celsius < 95:
            return "serious"
        else:
            return "critical"
