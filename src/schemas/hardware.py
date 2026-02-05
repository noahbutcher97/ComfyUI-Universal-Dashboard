"""
Hardware detection schemas per SPEC_v3 Section 4.5.

Defines HardwareProfile and related dataclasses for platform-specific
hardware detection and tier classification.

Phase 1 Week 2a: Extended with CPUProfile, StorageProfile, RAMProfile,
FormFactorProfile for comprehensive hardware detection.

See: docs/spec/HARDWARE_DETECTION.md Sections 2-5
See: docs/spec/MIGRATION_PROTOCOL.md Section 3
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.hardware.storage import StorageType


class PlatformType(Enum):
    """Supported platform types."""
    APPLE_SILICON = "apple_silicon"
    WINDOWS_NVIDIA = "windows_nvidia"
    LINUX_NVIDIA = "linux_nvidia"
    WSL2_NVIDIA = "wsl2_nvidia"
    LINUX_ROCM = "linux_rocm"
    CPU_ONLY = "cpu_only"
    UNKNOWN = "unknown"


class HardwareTier(Enum):
    """
    Hardware capability tiers per SPEC_v3 Section 4.5.

    Determines recommended models and capabilities.
    """
    WORKSTATION = "workstation"   # 48GB+ - All FP16, training, multi-model
    PROFESSIONAL = "professional" # 16-24GB - All FP8, HunyuanVideo
    PROSUMER = "prosumer"         # 12GB - Flux FP8, Wan 14B Q5
    CONSUMER = "consumer"         # 8GB - SDXL, Flux Q4-Q5, Wan 5B
    ENTRY = "entry"               # 4-6GB - SD1.5, SDXL Q4
    MINIMAL = "minimal"           # <4GB or CPU only


class ThermalState(Enum):
    """GPU thermal state classification."""
    NORMAL = "normal"
    WARNING = "warning"     # Approaching throttle (82-84C)
    CRITICAL = "critical"   # Active throttling (85C+)
    UNKNOWN = "unknown"


class CPUTier(Enum):
    """
    CPU capability tiers per HARDWARE_DETECTION.md Section 3.3.

    Determines CPU offload viability and GGUF inference performance.
    """
    HIGH = "high"         # 16+ physical cores - excellent offload
    MEDIUM = "medium"     # 8-15 physical cores - good offload
    LOW = "low"           # 4-7 physical cores - limited offload
    MINIMAL = "minimal"   # <4 physical cores - offload not viable


class StorageTier(Enum):
    """
    Storage speed tiers per HARDWARE_DETECTION.md Section 4.3.

    Affects model loading times and workspace viability.
    """
    FAST = "fast"         # NVMe Gen3+ - optimal for AI workloads
    MODERATE = "moderate" # SATA SSD - acceptable performance
    SLOW = "slow"         # HDD - significant performance impact


@dataclass
class CPUProfile:
    """
    CPU detection profile per HARDWARE_DETECTION.md Section 3.

    Captures CPU characteristics relevant to AI workloads:
    - Core count for parallel processing
    - AVX support for GGUF inference optimization
    - Tier classification for offload viability
    """
    model: str                    # "AMD Ryzen 9 7950X", "Apple M3 Max"
    architecture: str             # "x86_64", "arm64"
    physical_cores: int
    logical_cores: int
    supports_avx: bool = False    # x86 only
    supports_avx2: bool = False   # x86 only, required for fast GGUF
    supports_avx512: bool = False # x86 only, optional optimization
    tier: CPUTier = CPUTier.MINIMAL

    def __post_init__(self):
        """Auto-calculate tier from physical cores."""
        if self.tier == CPUTier.MINIMAL:
            self.tier = self._calculate_tier()

    def _calculate_tier(self) -> CPUTier:
        """
        Calculate CPU tier based on physical core count.
        Per HARDWARE_DETECTION.md Section 3.3.
        """
        cores = self.physical_cores
        if cores >= 16:
            return CPUTier.HIGH
        elif cores >= 8:
            return CPUTier.MEDIUM
        elif cores >= 4:
            return CPUTier.LOW
        else:
            return CPUTier.MINIMAL

    @property
    def can_offload(self) -> bool:
        """Check if CPU tier supports viable layer offload."""
        return self.tier in (CPUTier.HIGH, CPUTier.MEDIUM)

    @property
    def gguf_optimized(self) -> bool:
        """Check if CPU has AVX2 for optimized GGUF inference."""
        # ARM64 has NEON which is always available
        if self.architecture == "arm64":
            return True
        return self.supports_avx2


@dataclass
class StorageProfile:
    """
    Storage detection profile per HARDWARE_DETECTION.md Section 4.

    Captures storage characteristics for model management:
    - Capacity for model downloads
    - Speed tier for load time estimates
    - Type for performance expectations
    """
    path: str                     # Path that was analyzed
    total_gb: float               # Total storage capacity
    free_gb: float                # Available free space
    storage_type: str             # StorageType value as string
    estimated_read_mbps: int      # Estimated sequential read speed
    tier: StorageTier = StorageTier.MODERATE

    def __post_init__(self):
        """Auto-calculate tier from storage type."""
        if self.tier == StorageTier.MODERATE:
            self.tier = self._calculate_tier()

    def _calculate_tier(self) -> StorageTier:
        """Calculate storage tier based on type."""
        storage_type_lower = self.storage_type.lower()
        if "nvme" in storage_type_lower:
            return StorageTier.FAST
        elif "ssd" in storage_type_lower or "sata_ssd" in storage_type_lower:
            return StorageTier.MODERATE
        elif "hdd" in storage_type_lower:
            return StorageTier.SLOW
        # Default to moderate for unknown
        return StorageTier.MODERATE

    def can_fit(self, size_gb: float, buffer_gb: float = 10.0) -> bool:
        """
        Check if storage can fit a model with safety buffer.

        Args:
            size_gb: Model size in GB
            buffer_gb: Safety buffer for workspace (default 10GB)

        Returns:
            True if model fits with buffer
        """
        return self.free_gb >= (size_gb + buffer_gb)

    def estimate_load_time(self, size_gb: float) -> float:
        """
        Estimate model load time in seconds.

        Args:
            size_gb: Model size in GB

        Returns:
            Estimated load time in seconds
        """
        size_mb = size_gb * 1024
        return size_mb / self.estimated_read_mbps


@dataclass
class RAMProfile:
    """
    RAM detection profile per HARDWARE_DETECTION.md Section 5.

    Captures RAM characteristics for model layer offloading:
    - Total capacity for baseline
    - Available for current state
    - Usable for offload (conservative calculation)
    - Bandwidth for speed ratio calculation
    """
    total_gb: float               # Total system RAM
    available_gb: float           # Currently available RAM
    usable_for_offload_gb: float  # Conservative estimate for model offload
    bandwidth_gbps: Optional[float] = None  # DDR bandwidth in GB/s (None if unknown)
    memory_type: Optional[str] = None       # "ddr5", "ddr4", "lpddr5", etc.

    def can_offload_model(self, model_ram_requirement_gb: float) -> bool:
        """
        Check if RAM can support offloading a model's layers.

        Args:
            model_ram_requirement_gb: RAM needed for model offload

        Returns:
            True if sufficient RAM available for offload
        """
        return self.usable_for_offload_gb >= model_ram_requirement_gb


@dataclass
class FormFactorProfile:
    """
    Form factor profile per HARDWARE_DETECTION.md Section 2.

    NVIDIA-specific: Detects laptop vs desktop based on power limits.
    Used to calculate sustained performance ratio for thermal constraints.
    """
    is_laptop: bool                           # True if mobile GPU detected
    power_limit_watts: Optional[float] = None # Actual power limit from nvidia-smi
    reference_tdp_watts: Optional[float] = None # Desktop reference TDP
    sustained_performance_ratio: float = 1.0  # sqrt(power_ratio), 1.0 = desktop

    def get_warning(self) -> Optional[str]:
        """
        Get user-facing warning if laptop with significant performance penalty.

        Returns:
            Warning string or None if no warning needed
        """
        if not self.is_laptop:
            return None

        if self.sustained_performance_ratio < 0.8:
            pct = int(self.sustained_performance_ratio * 100)
            return (
                f"Laptop GPU detected - ~{pct}% sustained performance vs desktop "
                f"({self.power_limit_watts}W vs {self.reference_tdp_watts}W reference)"
            )
        return None


@dataclass
class HardwareProfile:
    """
    Comprehensive hardware profile per SPEC_v3 Section 4.5.

    Generated by platform-specific detectors. Used by recommendation
    engine for constraint satisfaction and model filtering.

    Phase 1 Week 2a: Extended with nested profiles for CPU, Storage, RAM,
    and FormFactor detection per HARDWARE_DETECTION.md.
    """
    # Core identification
    platform: PlatformType
    gpu_vendor: str  # "nvidia", "apple", "amd", "none"
    gpu_name: str    # Human-readable GPU name

    # Memory
    vram_gb: float              # Effective VRAM (with ceiling applied for Apple Silicon)
    unified_memory: bool = False  # True for Apple Silicon

    # Nested profiles (Phase 1 Week 2a)
    cpu: Optional[CPUProfile] = None
    storage: Optional[StorageProfile] = None
    ram: Optional[RAMProfile] = None
    form_factor: Optional[FormFactorProfile] = None  # NVIDIA only

    # Compute capabilities (NVIDIA-specific)
    compute_capability: Optional[float] = None  # e.g., 8.9 for RTX 4090
    supports_fp8: bool = False
    supports_bf16: bool = False
    supports_tf32: bool = False
    flash_attention_available: bool = False

    # Apple Silicon-specific
    mps_available: bool = False
    unified_memory_bandwidth_gbps: Optional[float] = None  # Apple Silicon unified memory
    chip_variant: Optional[str] = None  # "M3 Max", "M4 Pro", etc.

    # GPU memory bandwidth (NVIDIA/AMD)
    gpu_bandwidth_gbps: Optional[float] = None  # GDDR bandwidth for speed calculations

    # NVIDIA multi-GPU
    gpu_count: int = 1
    nvlink_available: bool = False

    # AMD ROCm-specific
    rocm_version: Optional[str] = None
    gfx_version: Optional[str] = None  # e.g., "gfx1100"
    officially_supported: bool = True  # False for RDNA2 workaround
    hsa_override_required: Optional[str] = None  # HSA_OVERRIDE_GFX_VERSION value

    # Derived
    tier: HardwareTier = HardwareTier.MINIMAL
    thermal_state: ThermalState = ThermalState.UNKNOWN

    # Warnings/constraints for UI display
    warnings: List[str] = field(default_factory=list)
    platform_constraints: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Auto-calculate tier if not set."""
        if self.tier == HardwareTier.MINIMAL:
            self.tier = self._calculate_tier()
        self._apply_platform_constraints()

    def _calculate_tier(self) -> HardwareTier:
        """
        Calculate hardware tier based on effective VRAM.
        Per SPEC_v3 Section 4.5.
        """
        vram = self.vram_gb

        if vram >= 48:
            return HardwareTier.WORKSTATION
        elif vram >= 16:
            return HardwareTier.PROFESSIONAL
        elif vram >= 12:
            return HardwareTier.PROSUMER
        elif vram >= 8:
            return HardwareTier.CONSUMER
        elif vram >= 4:
            return HardwareTier.ENTRY
        else:
            return HardwareTier.MINIMAL

    def _apply_platform_constraints(self):
        """Apply platform-specific constraints per SPEC_v3 Section 4.2-4.4."""
        if self.platform == PlatformType.APPLE_SILICON:
            self.platform_constraints = [
                "GGUF K-quants not supported (use Q4_0, Q5_0, Q8_0)",
                "FP8 quantization not available",
                "Flash Attention not available",
                "BF16 not hardware-accelerated",
            ]
            if self.vram_gb < 12:
                self.platform_constraints.append(
                    "HunyuanVideo excluded (~16 min/clip impractical)"
                )

        elif self.platform == PlatformType.LINUX_ROCM:
            self.platform_constraints = [
                "Marked as experimental",
                "Some CUDA-specific ComfyUI nodes unavailable",
            ]
            if not self.officially_supported:
                self.platform_constraints.append(
                    f"RDNA2 workaround required: {self.hsa_override_required}"
                )

        elif self.compute_capability and self.compute_capability < 8.0:
            self.platform_constraints = [
                "Flash Attention unavailable (Turing architecture)",
                "BF16 not supported - using FP16",
            ]

    @property
    def can_run_fp8(self) -> bool:
        """Check if hardware supports FP8 precision."""
        return self.supports_fp8

    @property
    def can_run_hunyuan(self) -> bool:
        """Check if HunyuanVideo is practical on this hardware."""
        # Excluded for Apple Silicon < Professional tier
        if self.platform == PlatformType.APPLE_SILICON:
            return self.tier in (HardwareTier.WORKSTATION, HardwareTier.PROFESSIONAL)
        # NVIDIA/AMD: Need at least 12GB
        return self.vram_gb >= 12

    @property
    def allowed_gguf_quants(self) -> List[str]:
        """Return allowed GGUF quantization types for this platform."""
        if self.platform == PlatformType.APPLE_SILICON:
            # K-quants crash on MPS
            return ["Q4_0", "Q5_0", "Q8_0"]
        # All quantizations available on NVIDIA/AMD
        return ["Q4_0", "Q4_K_M", "Q5_0", "Q5_K_M", "Q6_K", "Q8_0"]

    @property
    def ram_gb(self) -> float:
        """
        Get total system RAM in GB.

        Returns RAM from nested RAMProfile if available, otherwise 0.0.
        Provides backward compatibility with code expecting ram_gb attribute.
        """
        if self.ram is not None:
            return self.ram.total_gb
        return 0.0

    @property
    def effective_capacity_with_offload_gb(self) -> float:
        """
        Calculate total usable capacity including CPU offload.

        Per HARDWARE_DETECTION.md Section 5.4:
        - If CPU supports offload (HIGH/MEDIUM tier), add usable RAM
        - Otherwise, return VRAM only

        Returns:
            Effective capacity in GB
        """
        base_capacity = self.vram_gb

        # Check if CPU offload is viable
        if self.cpu is not None and self.cpu.can_offload:
            if self.ram is not None:
                return base_capacity + self.ram.usable_for_offload_gb

        return base_capacity

    @property
    def all_warnings(self) -> List[str]:
        """
        Aggregate warnings from all profiles.

        Combines:
        - Base warnings
        - Form factor warnings (if laptop with performance penalty)
        - Storage warnings (if slow storage)

        Returns:
            Combined list of warning strings
        """
        all_warns = list(self.warnings)

        # Add form factor warning if applicable
        if self.form_factor is not None:
            ff_warning = self.form_factor.get_warning()
            if ff_warning:
                all_warns.append(ff_warning)

        # Add storage warning if slow
        if self.storage is not None and self.storage.tier == StorageTier.SLOW:
            all_warns.append(
                f"Slow storage detected ({self.storage.storage_type}). "
                "Model loading will be significantly slower."
            )

        return all_warns

    @property
    def can_offload_to_cpu(self) -> bool:
        """
        Check if model layer offloading to CPU is viable.

        Requires:
        - CPU tier HIGH or MEDIUM
        - Sufficient RAM for offload
        - For GGUF: AVX2 support (or ARM64)
        """
        if self.cpu is None or self.ram is None:
            return False

        if not self.cpu.can_offload:
            return False

        # Need at least 4GB usable for meaningful offload
        if self.ram.usable_for_offload_gb < 4.0:
            return False

        return True


# Note: DetectionError was moved to src/services/hardware/base.py as an Exception class
# (DetectionFailedError) since errors should be raised, not returned as data.
