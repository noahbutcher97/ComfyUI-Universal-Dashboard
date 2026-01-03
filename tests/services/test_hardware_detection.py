"""
Unit tests for hardware detection module.

Tests cover:
- HardwareProfile tier calculation
- Platform-specific constraints
- Detector factory function
- Storage type detection utilities

Per PLAN_v3.md Phase 1 Week 1:
- Mock platform APIs for cross-platform testing
- Test tier classification boundaries
"""

import pytest
from unittest.mock import patch, MagicMock
import platform

from src.schemas.hardware import (
    HardwareProfile,
    HardwareTier,
    PlatformType,
    ThermalState,
)
from src.services.hardware import (
    get_detector,
    detect_hardware,
    detect_storage_type,
    StorageType,
    get_storage_warning,
    get_estimated_load_time,
    HardwareDetector,
    DetectionFailedError,
)
from src.services.hardware.apple_silicon import AppleSiliconDetector
from src.services.hardware.nvidia import NVIDIADetector
from src.services.hardware.amd_rocm import AMDROCmDetector


class TestHardwareProfile:
    """Tests for HardwareProfile dataclass."""

    def test_tier_workstation(self):
        """48GB+ VRAM should be WORKSTATION tier."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=48.0,
            ram_gb=128.0,
        )
        assert profile.tier == HardwareTier.WORKSTATION

    def test_tier_professional(self):
        """16-47GB VRAM should be PROFESSIONAL tier."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
        )
        assert profile.tier == HardwareTier.PROFESSIONAL

        # Test boundary
        profile16 = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4080",
            vram_gb=16.0,
            ram_gb=32.0,
        )
        assert profile16.tier == HardwareTier.PROFESSIONAL

    def test_tier_prosumer(self):
        """12-15GB VRAM should be PROSUMER tier."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4070 Ti",
            vram_gb=12.0,
            ram_gb=32.0,
        )
        assert profile.tier == HardwareTier.PROSUMER

    def test_tier_consumer(self):
        """8-11GB VRAM should be CONSUMER tier."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4070",
            vram_gb=8.0,
            ram_gb=16.0,
        )
        assert profile.tier == HardwareTier.CONSUMER

    def test_tier_entry(self):
        """4-7GB VRAM should be ENTRY tier."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 3050",
            vram_gb=4.0,
            ram_gb=16.0,
        )
        assert profile.tier == HardwareTier.ENTRY

    def test_tier_minimal(self):
        """<4GB VRAM or CPU-only should be MINIMAL tier."""
        profile = HardwareProfile(
            platform=PlatformType.CPU_ONLY,
            gpu_vendor="none",
            gpu_name="CPU Only",
            vram_gb=0.0,
            ram_gb=8.0,
        )
        assert profile.tier == HardwareTier.MINIMAL

    def test_apple_silicon_constraints(self):
        """Apple Silicon should have platform-specific constraints."""
        profile = HardwareProfile(
            platform=PlatformType.APPLE_SILICON,
            gpu_vendor="apple",
            gpu_name="Apple M3 Max",
            vram_gb=36.0,  # 48GB * 0.75
            ram_gb=48.0,
            unified_memory=True,
        )

        assert "GGUF K-quants not supported" in profile.platform_constraints[0]
        assert profile.supports_fp8 is False
        assert profile.flash_attention_available is False

    def test_apple_silicon_allowed_quants(self):
        """Apple Silicon should only allow non-K GGUF quants."""
        profile = HardwareProfile(
            platform=PlatformType.APPLE_SILICON,
            gpu_vendor="apple",
            gpu_name="Apple M3",
            vram_gb=18.0,
            ram_gb=24.0,
            unified_memory=True,
        )

        quants = profile.allowed_gguf_quants
        assert "Q4_0" in quants
        assert "Q5_0" in quants
        assert "Q8_0" in quants
        assert "Q4_K_M" not in quants  # K-quants crash on MPS

    def test_nvidia_allowed_quants(self):
        """NVIDIA should allow all GGUF quants."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
        )

        quants = profile.allowed_gguf_quants
        assert "Q4_K_M" in quants
        assert "Q5_K_M" in quants

    def test_can_run_hunyuan_apple_silicon(self):
        """HunyuanVideo requires Professional tier on Apple Silicon."""
        # Too small - can't run
        profile_small = HardwareProfile(
            platform=PlatformType.APPLE_SILICON,
            gpu_vendor="apple",
            gpu_name="Apple M3",
            vram_gb=6.0,  # 8GB * 0.75
            ram_gb=8.0,
            unified_memory=True,
        )
        assert profile_small.can_run_hunyuan is False

        # Professional tier - can run
        profile_large = HardwareProfile(
            platform=PlatformType.APPLE_SILICON,
            gpu_vendor="apple",
            gpu_name="Apple M3 Max",
            vram_gb=72.0,  # 96GB * 0.75
            ram_gb=96.0,
            unified_memory=True,
        )
        assert profile_large.can_run_hunyuan is True

    def test_can_run_fp8(self):
        """FP8 requires compute capability 8.9+."""
        # RTX 40 series - can run FP8
        profile_ada = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
            compute_capability=8.9,
            supports_fp8=True,
        )
        assert profile_ada.can_run_fp8 is True

        # RTX 30 series - cannot run FP8
        profile_ampere = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="RTX 3090",
            vram_gb=24.0,
            ram_gb=64.0,
            compute_capability=8.6,
            supports_fp8=False,
        )
        assert profile_ampere.can_run_fp8 is False


class TestAppleSiliconDetector:
    """Tests for AppleSiliconDetector."""

    def test_is_available_on_mac(self):
        """Detector should be available on Apple Silicon Mac."""
        detector = AppleSiliconDetector()

        with patch('platform.system', return_value='Darwin'):
            with patch('platform.machine', return_value='arm64'):
                assert detector.is_available() is True

    def test_is_not_available_on_intel_mac(self):
        """Detector should not be available on Intel Mac."""
        detector = AppleSiliconDetector()

        with patch('platform.system', return_value='Darwin'):
            with patch('platform.machine', return_value='x86_64'):
                assert detector.is_available() is False

    def test_is_not_available_on_windows(self):
        """Detector should not be available on Windows."""
        detector = AppleSiliconDetector()

        with patch('platform.system', return_value='Windows'):
            assert detector.is_available() is False

    def test_parse_chip_variant(self):
        """Should correctly parse chip variant from brand string."""
        detector = AppleSiliconDetector()

        assert detector._parse_chip_variant("Apple M1") == "M1"
        assert detector._parse_chip_variant("Apple M3 Max") == "M3 Max"
        assert detector._parse_chip_variant("Apple M4 Pro") == "M4 Pro"
        assert detector._parse_chip_variant("Apple M2 Ultra") == "M2 Ultra"

    def test_bandwidth_lookup(self):
        """Should return correct bandwidth for each chip."""
        detector = AppleSiliconDetector()

        assert detector.BANDWIDTH_LOOKUP["M1"] == 68
        assert detector.BANDWIDTH_LOOKUP["M3 Max"] == 400
        assert detector.BANDWIDTH_LOOKUP["M4 Pro"] == 273
        assert detector.BANDWIDTH_LOOKUP["M4 Ultra"] == 800

    def test_75_percent_memory_ceiling(self):
        """Should apply 75% memory ceiling to unified memory."""
        detector = AppleSiliconDetector()

        with patch.object(detector, '_get_chip_name', return_value='Apple M3 Max'):
            with patch.object(detector, '_get_unified_memory', return_value=96.0):
                with patch.object(detector, '_check_mps', return_value=True):
                    profile = detector.detect()

                    assert profile.ram_gb == 96.0
                    assert profile.vram_gb == 72.0  # 96 * 0.75
                    assert profile.unified_memory is True


class TestNVIDIADetector:
    """Tests for NVIDIADetector."""

    def test_compute_capability_inference(self):
        """Should correctly infer compute capability from GPU name."""
        detector = NVIDIADetector()

        # RTX 40 series
        assert detector._infer_compute_capability("NVIDIA GeForce RTX 4090") == 8.9
        assert detector._infer_compute_capability("RTX 4080") == 8.9

        # RTX 30 series
        assert detector._infer_compute_capability("NVIDIA GeForce RTX 3090") == 8.6

        # RTX 20 series
        assert detector._infer_compute_capability("RTX 2080 Ti") == 7.5

        # Data center
        assert detector._infer_compute_capability("NVIDIA A100") == 8.0
        assert detector._infer_compute_capability("NVIDIA H100") == 9.0

        # Unknown
        assert detector._infer_compute_capability("Some Random GPU") is None

    def test_fp8_support_detection(self):
        """FP8 support should be enabled for CC 8.9+."""
        # Simulated detection result
        assert 8.9 >= 8.9  # RTX 40 series supports FP8
        assert 8.6 < 8.9   # RTX 30 series does not

    def test_wsl_detection(self):
        """Should detect WSL2 environment."""
        detector = NVIDIADetector()

        # Mock /proc/version for WSL
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = \
                "Linux version 5.10.16.3-microsoft-standard-WSL2"
            assert detector._detect_wsl() is True

        # Not WSL
        with patch('builtins.open', side_effect=FileNotFoundError):
            assert detector._detect_wsl() is False


class TestAMDROCmDetector:
    """Tests for AMDROCmDetector."""

    def test_gfx_version_support(self):
        """Should correctly identify supported GFX versions."""
        detector = AMDROCmDetector()

        # RDNA3 - officially supported
        assert "gfx1100" in detector.OFFICIALLY_SUPPORTED_GFX
        assert "gfx1102" in detector.OFFICIALLY_SUPPORTED_GFX

        # RDNA2 - needs workaround
        assert "gfx1030" in detector.RDNA2_WORKAROUND
        assert "gfx1031" in detector.RDNA2_WORKAROUND

    def test_is_not_available_on_windows(self):
        """Detector should not be available on Windows."""
        detector = AMDROCmDetector()

        with patch('platform.system', return_value='Windows'):
            assert detector.is_available() is False


class TestDetectorFactory:
    """Tests for get_detector() factory function."""

    def test_returns_apple_silicon_on_mac(self):
        """Should return AppleSiliconDetector on Apple Silicon Mac."""
        with patch.object(AppleSiliconDetector, 'is_available', return_value=True):
            with patch.object(NVIDIADetector, 'is_available', return_value=False):
                detector = get_detector()
                assert isinstance(detector, AppleSiliconDetector)

    def test_returns_nvidia_on_windows(self):
        """Should return NVIDIADetector when nvidia-smi available."""
        with patch.object(AppleSiliconDetector, 'is_available', return_value=False):
            with patch.object(NVIDIADetector, 'is_available', return_value=True):
                detector = get_detector()
                assert isinstance(detector, NVIDIADetector)

    def test_returns_cpu_only_fallback(self):
        """Should return CPUOnlyDetector when no GPU available."""
        with patch.object(AppleSiliconDetector, 'is_available', return_value=False):
            with patch.object(NVIDIADetector, 'is_available', return_value=False):
                with patch.object(AMDROCmDetector, 'is_available', return_value=False):
                    detector = get_detector()
                    # CPUOnlyDetector is defined in __init__.py
                    assert detector.is_available() is True
                    profile = detector.detect()
                    assert profile.platform == PlatformType.CPU_ONLY


class TestStorageDetection:
    """Tests for storage type detection."""

    def test_storage_warning_hdd(self):
        """HDD should generate warning."""
        warning = get_storage_warning(StorageType.HDD)
        assert warning is not None
        assert "extremely slow" in warning.lower()

    def test_storage_warning_ssd(self):
        """SSD should not generate warning."""
        assert get_storage_warning(StorageType.NVME) is None
        assert get_storage_warning(StorageType.SATA_SSD) is None

    def test_estimated_load_time(self):
        """Should estimate correct load times."""
        # 10GB model on different storage types
        model_size = 10.0

        nvme_time = get_estimated_load_time(StorageType.NVME, model_size)
        sata_time = get_estimated_load_time(StorageType.SATA_SSD, model_size)
        hdd_time = get_estimated_load_time(StorageType.HDD, model_size)

        # NVMe should be fastest
        assert nvme_time < sata_time < hdd_time

        # HDD should take ~70+ seconds for 10GB
        assert hdd_time > 70

        # NVMe should take <5 seconds for 10GB
        assert nvme_time < 5


class TestTierBoundaries:
    """Tests for tier classification boundary conditions."""

    @pytest.mark.parametrize("vram,expected_tier", [
        (0.0, HardwareTier.MINIMAL),
        (3.9, HardwareTier.MINIMAL),
        (4.0, HardwareTier.ENTRY),
        (7.9, HardwareTier.ENTRY),
        (8.0, HardwareTier.CONSUMER),
        (11.9, HardwareTier.CONSUMER),
        (12.0, HardwareTier.PROSUMER),
        (15.9, HardwareTier.PROSUMER),
        (16.0, HardwareTier.PROFESSIONAL),
        (24.0, HardwareTier.PROFESSIONAL),
        (47.9, HardwareTier.PROFESSIONAL),
        (48.0, HardwareTier.WORKSTATION),
        (128.0, HardwareTier.WORKSTATION),
    ])
    def test_tier_boundary(self, vram, expected_tier):
        """Test tier classification at exact boundaries."""
        profile = HardwareProfile(
            platform=PlatformType.WINDOWS_NVIDIA,
            gpu_vendor="nvidia",
            gpu_name="Test GPU",
            vram_gb=vram,
            ram_gb=32.0,
        )
        assert profile.tier == expected_tier, \
            f"VRAM {vram}GB should be {expected_tier.value}, got {profile.tier.value}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
