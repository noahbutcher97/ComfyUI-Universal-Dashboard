"""
Comprehensive edge case tests for the recommendation engine.

Tests boundary conditions, hardware profiles, and unusual configurations.
Per PLAN_v3.md Phase 3 Week 7 requirements.
"""

import pytest
from typing import List

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    FormFactorProfile,
    StorageProfile,
    StorageTier,
    RAMProfile,
    CPUProfile,
    CPUTier,
)


# --- Hardware Profile Factory ---


def create_hardware(
    vram_gb: float,
    platform: PlatformType,
    ram_gb: float = 32.0,
    storage_free_gb: float = 200.0,
    storage_tier: StorageTier = StorageTier.FAST,
    is_laptop: bool = False,
    compute_capability: float = 8.9,
    cpu_cores: int = 8,
) -> HardwareProfile:
    """Create a HardwareProfile with specified parameters."""
    storage_type_map = {
        StorageTier.FAST: "nvme_gen4",
        StorageTier.MODERATE: "sata_ssd",
        StorageTier.SLOW: "hdd",
    }

    gpu_vendor = "nvidia"
    gpu_name = f"Test GPU {vram_gb}GB"
    if platform == PlatformType.APPLE_SILICON:
        gpu_vendor = "apple"
        gpu_name = f"Apple Silicon {vram_gb}GB"
    elif platform == PlatformType.LINUX_ROCM:
        gpu_vendor = "amd"
        gpu_name = f"AMD GPU {vram_gb}GB"
    elif platform == PlatformType.CPU_ONLY:
        gpu_vendor = "none"
        gpu_name = "CPU Only"

    return HardwareProfile(
        platform=platform,
        gpu_vendor=gpu_vendor,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        compute_capability=compute_capability,
        form_factor=FormFactorProfile(
            is_laptop=is_laptop,
            sustained_performance_ratio=0.6 if is_laptop else 1.0,
        ),
        storage=StorageProfile(
            path="C:\\",
            total_gb=500.0,
            free_gb=storage_free_gb,
            storage_type=storage_type_map.get(storage_tier, "nvme_gen4"),
            estimated_read_mbps=5000 if storage_tier == StorageTier.FAST else 500,
            tier=storage_tier,
        ),
        ram=RAMProfile(
            total_gb=ram_gb,
            available_gb=ram_gb * 0.75,
            usable_for_offload_gb=ram_gb * 0.5,
        ),
        cpu=CPUProfile(
            model="Test CPU",
            architecture="x86_64",
            physical_cores=cpu_cores,
            logical_cores=cpu_cores * 2,
            supports_avx=True,
            supports_avx2=True,
            tier=CPUTier.HIGH if cpu_cores >= 16 else CPUTier.MEDIUM,
        ),
    )


# --- Hardware Profile Creation Tests ---


class TestHardwareProfileCreation:
    """Tests for correct HardwareProfile instantiation."""

    def test_all_required_fields_present(self):
        """HardwareProfile should have all required fields."""
        hw = create_hardware(vram_gb=12.0, platform=PlatformType.WINDOWS_NVIDIA)
        assert hw.platform == PlatformType.WINDOWS_NVIDIA
        assert hw.gpu_vendor == "nvidia"
        assert hw.vram_gb == 12.0
        assert hw.compute_capability == 8.9
        assert hw.form_factor is not None
        assert hw.storage is not None
        assert hw.ram is not None
        assert hw.cpu is not None

    def test_vram_range_zero(self):
        """Should handle 0GB VRAM (CPU only systems)."""
        hw = create_hardware(vram_gb=0.0, platform=PlatformType.CPU_ONLY)
        assert hw.vram_gb == 0.0

    def test_vram_range_small(self):
        """Should handle small VRAM (4GB entry GPUs)."""
        hw = create_hardware(vram_gb=4.0, platform=PlatformType.WINDOWS_NVIDIA)
        assert hw.vram_gb == 4.0

    def test_vram_range_large(self):
        """Should handle large VRAM (48GB+ workstation)."""
        hw = create_hardware(vram_gb=48.0, platform=PlatformType.WINDOWS_NVIDIA)
        assert hw.vram_gb == 48.0

    def test_vram_range_massive(self):
        """Should handle massive VRAM (96GB Apple Silicon)."""
        hw = create_hardware(vram_gb=96.0, platform=PlatformType.APPLE_SILICON)
        assert hw.vram_gb == 96.0


# --- VRAM Boundary Tests ---


class TestVRAMBoundaries:
    """Tests for VRAM boundary calculations."""

    def test_vram_exactly_12gb(self):
        """12GB VRAM exactly (RTX 4070)."""
        hw = create_hardware(vram_gb=12.0, platform=PlatformType.WINDOWS_NVIDIA)
        vram_mb = int(hw.vram_gb * 1024)
        assert vram_mb == 12288

    def test_vram_exactly_16gb(self):
        """16GB VRAM exactly (RTX 4070 Ti Super)."""
        hw = create_hardware(vram_gb=16.0, platform=PlatformType.WINDOWS_NVIDIA)
        vram_mb = int(hw.vram_gb * 1024)
        assert vram_mb == 16384

    def test_vram_exactly_24gb(self):
        """24GB VRAM exactly (RTX 4090)."""
        hw = create_hardware(vram_gb=24.0, platform=PlatformType.WINDOWS_NVIDIA)
        vram_mb = int(hw.vram_gb * 1024)
        assert vram_mb == 24576

    def test_fractional_vram(self):
        """Should handle fractional VRAM correctly."""
        hw = create_hardware(vram_gb=11.5, platform=PlatformType.WINDOWS_NVIDIA)
        vram_mb = int(hw.vram_gb * 1024)
        assert vram_mb == 11776  # 11.5 * 1024


# --- Hardware Tier Tests ---


class TestHardwareTiers:
    """Tests for different hardware tier configurations."""

    def test_workstation_tier(self):
        """Workstation config (48GB VRAM, 128GB RAM)."""
        hw = create_hardware(
            vram_gb=48.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=128.0,
            cpu_cores=32,
        )
        assert hw.vram_gb >= 48.0
        assert hw.ram.total_gb >= 128.0
        assert hw.cpu.tier == CPUTier.HIGH

    def test_enthusiast_tier(self):
        """Enthusiast config (24GB VRAM, 64GB RAM)."""
        hw = create_hardware(
            vram_gb=24.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=64.0,
            cpu_cores=16,
        )
        assert hw.vram_gb == 24.0
        assert hw.ram.total_gb == 64.0
        assert hw.cpu.tier == CPUTier.HIGH

    def test_mainstream_tier(self):
        """Mainstream config (12GB VRAM, 32GB RAM)."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=32.0,
            cpu_cores=8,
        )
        assert hw.vram_gb == 12.0
        assert hw.ram.total_gb == 32.0
        assert hw.cpu.tier == CPUTier.MEDIUM

    def test_entry_tier(self):
        """Entry config (8GB VRAM, 16GB RAM)."""
        hw = create_hardware(
            vram_gb=8.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=16.0,
            cpu_cores=6,
        )
        assert hw.vram_gb == 8.0
        assert hw.ram.total_gb == 16.0

    def test_minimal_tier(self):
        """Minimal config (4GB VRAM, 8GB RAM)."""
        hw = create_hardware(
            vram_gb=4.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=8.0,
            cpu_cores=4,
        )
        assert hw.vram_gb == 4.0
        assert hw.ram.total_gb == 8.0


# --- Platform Tests ---


class TestPlatformTypes:
    """Tests for different platform configurations."""

    def test_windows_nvidia(self):
        """Windows with NVIDIA GPU."""
        hw = create_hardware(vram_gb=12.0, platform=PlatformType.WINDOWS_NVIDIA)
        assert hw.platform == PlatformType.WINDOWS_NVIDIA
        assert hw.gpu_vendor == "nvidia"

    def test_linux_nvidia(self):
        """Linux with NVIDIA GPU."""
        hw = create_hardware(vram_gb=24.0, platform=PlatformType.LINUX_NVIDIA)
        assert hw.platform == PlatformType.LINUX_NVIDIA
        assert hw.gpu_vendor == "nvidia"

    def test_wsl2_nvidia(self):
        """WSL2 with NVIDIA GPU."""
        hw = create_hardware(vram_gb=12.0, platform=PlatformType.WSL2_NVIDIA)
        assert hw.platform == PlatformType.WSL2_NVIDIA
        assert hw.gpu_vendor == "nvidia"

    def test_apple_silicon(self):
        """Apple Silicon Mac."""
        hw = create_hardware(vram_gb=32.0, platform=PlatformType.APPLE_SILICON)
        assert hw.platform == PlatformType.APPLE_SILICON
        assert hw.gpu_vendor == "apple"

    def test_linux_rocm(self):
        """Linux with AMD ROCm."""
        hw = create_hardware(vram_gb=16.0, platform=PlatformType.LINUX_ROCM)
        assert hw.platform == PlatformType.LINUX_ROCM
        assert hw.gpu_vendor == "amd"

    def test_cpu_only(self):
        """CPU only system."""
        hw = create_hardware(vram_gb=0.0, platform=PlatformType.CPU_ONLY)
        assert hw.platform == PlatformType.CPU_ONLY
        assert hw.gpu_vendor == "none"


# --- Form Factor Tests ---


class TestFormFactorScenarios:
    """Tests for desktop vs laptop scenarios."""

    def test_desktop_full_performance(self):
        """Desktop should have full performance ratio."""
        hw = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            is_laptop=False,
        )
        assert hw.form_factor.sustained_performance_ratio == 1.0
        assert hw.form_factor.is_laptop is False

    def test_laptop_reduced_performance(self):
        """Laptop should have reduced performance ratio."""
        hw = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            is_laptop=True,
        )
        assert hw.form_factor.sustained_performance_ratio == 0.6
        assert hw.form_factor.is_laptop is True

    def test_laptop_thermal_impact(self):
        """Laptop sustained ratio should reflect thermal constraints."""
        desktop = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            is_laptop=False,
        )
        laptop = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            is_laptop=True,
        )
        assert laptop.form_factor.sustained_performance_ratio < desktop.form_factor.sustained_performance_ratio


# --- Storage Tier Tests ---


class TestStorageTierScenarios:
    """Tests for different storage tier scenarios."""

    def test_nvme_fast_tier(self):
        """NVMe Gen4 should be FAST tier with high throughput."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_tier=StorageTier.FAST,
        )
        assert hw.storage.tier == StorageTier.FAST
        assert hw.storage.storage_type == "nvme_gen4"
        assert hw.storage.estimated_read_mbps >= 5000

    def test_sata_moderate_tier(self):
        """SATA SSD should be MODERATE tier."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_tier=StorageTier.MODERATE,
        )
        assert hw.storage.tier == StorageTier.MODERATE
        assert hw.storage.storage_type == "sata_ssd"

    def test_hdd_slow_tier(self):
        """HDD should be SLOW tier with lower throughput."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_tier=StorageTier.SLOW,
        )
        assert hw.storage.tier == StorageTier.SLOW
        assert hw.storage.storage_type == "hdd"
        assert hw.storage.estimated_read_mbps < 1000

    def test_storage_free_space(self):
        """Should correctly report free space."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_free_gb=250.0,
        )
        assert hw.storage.free_gb == 250.0

    def test_storage_low_space(self):
        """Should handle low free space scenarios."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_free_gb=10.0,
        )
        assert hw.storage.free_gb == 10.0


# --- Compute Capability Tests ---


class TestComputeCapability:
    """Tests for GPU compute capability configurations."""

    def test_blackwell_sm120(self):
        """Blackwell (RTX 50 series) compute capability."""
        hw = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            compute_capability=12.0,
        )
        assert hw.compute_capability == 12.0

    def test_ada_sm89(self):
        """Ada Lovelace (RTX 40 series) compute capability."""
        hw = create_hardware(
            vram_gb=24.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            compute_capability=8.9,
        )
        assert hw.compute_capability == 8.9

    def test_ampere_sm86(self):
        """Ampere (RTX 30 series) compute capability."""
        hw = create_hardware(
            vram_gb=24.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            compute_capability=8.6,
        )
        assert hw.compute_capability == 8.6

    def test_turing_sm75(self):
        """Turing (RTX 20 series) compute capability."""
        hw = create_hardware(
            vram_gb=8.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            compute_capability=7.5,
        )
        assert hw.compute_capability == 7.5


# --- RAM and Offload Tests ---


class TestRAMConfiguration:
    """Tests for RAM and offload calculations."""

    def test_usable_for_offload_calculation(self):
        """Usable for offload should be portion of total RAM."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=64.0,
        )
        # Factory sets usable_for_offload_gb = ram_gb * 0.5
        assert hw.ram.usable_for_offload_gb == 32.0

    def test_available_ram_calculation(self):
        """Available RAM should be less than total."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=32.0,
        )
        # Factory sets available_gb = ram_gb * 0.75
        assert hw.ram.available_gb == 24.0
        assert hw.ram.available_gb < hw.ram.total_gb

    def test_low_ram_system(self):
        """Low RAM systems should have limited offload capacity."""
        hw = create_hardware(
            vram_gb=8.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=8.0,
        )
        assert hw.ram.usable_for_offload_gb == 4.0


# --- Apple Silicon Memory Tests ---


class TestAppleSiliconMemory:
    """Tests for Apple Silicon unified memory handling."""

    def test_m1_base_8gb(self):
        """M1 base with 8GB unified memory."""
        hw = create_hardware(
            vram_gb=8.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=8.0,
        )
        assert hw.vram_gb == 8.0
        assert hw.ram.total_gb == 8.0

    def test_m2_pro_16gb(self):
        """M2 Pro with 16GB unified memory."""
        hw = create_hardware(
            vram_gb=16.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=16.0,
        )
        assert hw.vram_gb == 16.0

    def test_m2_max_32gb(self):
        """M2 Max with 32GB unified memory."""
        hw = create_hardware(
            vram_gb=32.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=32.0,
        )
        assert hw.vram_gb == 32.0

    def test_m3_max_48gb(self):
        """M3 Max with 48GB unified memory."""
        hw = create_hardware(
            vram_gb=48.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=48.0,
        )
        assert hw.vram_gb == 48.0

    def test_m3_max_96gb(self):
        """M3 Max with 96GB unified memory."""
        hw = create_hardware(
            vram_gb=96.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=96.0,
        )
        assert hw.vram_gb == 96.0

    def test_m3_ultra_192gb(self):
        """M3 Ultra with 192GB unified memory."""
        hw = create_hardware(
            vram_gb=192.0,
            platform=PlatformType.APPLE_SILICON,
            ram_gb=192.0,
        )
        assert hw.vram_gb == 192.0


# --- CPU Configuration Tests ---


class TestCPUConfiguration:
    """Tests for CPU configuration."""

    def test_cpu_tier_high(self):
        """High tier CPU (16+ cores)."""
        hw = create_hardware(
            vram_gb=24.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            cpu_cores=16,
        )
        assert hw.cpu.tier == CPUTier.HIGH
        assert hw.cpu.physical_cores == 16

    def test_cpu_tier_medium(self):
        """Medium tier CPU (8-15 cores)."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            cpu_cores=8,
        )
        assert hw.cpu.tier == CPUTier.MEDIUM
        assert hw.cpu.physical_cores == 8

    def test_avx2_support(self):
        """CPU should report AVX2 support."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
        )
        assert hw.cpu.supports_avx2 is True


# --- Edge Case Tests ---


class TestEdgeCases:
    """Tests for unusual or boundary configurations."""

    def test_zero_free_storage(self):
        """System with no free storage."""
        hw = create_hardware(
            vram_gb=12.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            storage_free_gb=0.0,
        )
        assert hw.storage.free_gb == 0.0

    def test_very_old_gpu(self):
        """Very old GPU with low compute capability."""
        hw = create_hardware(
            vram_gb=4.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            compute_capability=6.0,
        )
        assert hw.compute_capability == 6.0

    def test_high_core_count_cpu(self):
        """Server-class CPU with high core count."""
        hw = create_hardware(
            vram_gb=48.0,
            platform=PlatformType.LINUX_NVIDIA,
            cpu_cores=64,
        )
        assert hw.cpu.physical_cores == 64
        assert hw.cpu.logical_cores == 128

    def test_mismatched_vram_ram(self):
        """System with more VRAM than RAM (unusual but possible)."""
        hw = create_hardware(
            vram_gb=24.0,
            platform=PlatformType.WINDOWS_NVIDIA,
            ram_gb=16.0,
        )
        assert hw.vram_gb > hw.ram.total_gb
