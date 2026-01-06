"""
Layer 1: Constraint Satisfaction Layer (CSP).

Binary elimination based on hard constraints per SPEC_v3 Section 6.2.
Filters out models that cannot run on the user's hardware.

Constraints checked:
- VRAM requirements (with quantization fallback paths)
- Platform compatibility (Apple Silicon exclusions)
- Compute capability (FP8 on CC 8.9+)
- CPU offload viability
- Storage space
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from src.schemas.hardware import HardwareProfile, CPUTier
from src.services.model_database import ModelEntry, ModelVariant, ModelDatabase


class RejectionReason(Enum):
    """Reasons a model candidate was rejected."""
    VRAM_INSUFFICIENT = "vram_insufficient"
    PLATFORM_UNSUPPORTED = "platform_unsupported"
    COMPUTE_CAPABILITY = "compute_capability"
    STORAGE_INSUFFICIENT = "storage_insufficient"
    CPU_CANNOT_OFFLOAD = "cpu_cannot_offload"
    QUANTIZATION_UNAVAILABLE = "quantization_unavailable"
    PAIRED_MODEL_MISSING = "paired_model_missing"


@dataclass
class RejectedCandidate:
    """A model that was rejected with explanation."""
    model_id: str
    model_name: str
    reason: RejectionReason
    details: str
    suggestion: Optional[str] = None  # e.g., "Consider GGUF Q4 variant"


@dataclass
class PassingCandidate:
    """A model that passed constraint satisfaction."""
    model: ModelEntry
    variant: ModelVariant
    execution_mode: str = "native"  # "native", "quantized", "gpu_offload"
    warnings: List[str] = field(default_factory=list)


class ConstraintSatisfactionLayer:
    """
    Layer 1: Constraint Satisfaction.

    Performs binary elimination on model candidates based on hardware constraints.
    Returns only models that CAN run on the hardware, along with rejected candidates
    and reasons for rejection.

    SPEC_v3 Section 6.2:
    - VRAM constraint: model.vram_min_mb <= hardware.vram_mb
    - Platform constraint: variant.platform_support[platform].supported == True
    - Compute capability: variant.min_compute_capability <= hardware.compute_capability
    - Storage constraint: model.download_size_gb <= hardware.free_storage_gb
    """

    def __init__(self, model_db: ModelDatabase):
        """
        Initialize the constraint layer.

        Args:
            model_db: The model database to query
        """
        self.model_db = model_db

    def filter(
        self,
        hardware: HardwareProfile,
        categories: Optional[List[str]] = None,
        commercial_only: bool = False,
    ) -> Tuple[List[PassingCandidate], List[RejectedCandidate]]:
        """
        Filter models by hardware constraints.

        Args:
            hardware: The user's hardware profile
            categories: Model categories to consider (None = all)
            commercial_only: Only include commercially-licensed models

        Returns:
            Tuple of (passing_candidates, rejected_candidates)
        """
        # TODO: Implement in Phase 3
        # This is a stub implementation
        passing: List[PassingCandidate] = []
        rejected: List[RejectedCandidate] = []

        # Get platform key
        platform = self._get_platform_key(hardware)

        # Get VRAM in MB
        vram_mb = int(hardware.vram_gb * 1024)

        # Get compute capability
        compute_cap = hardware.compute_capability

        # Iterate through all models
        for model in self.model_db.iter_models():
            # Skip cloud-only models
            if not model.variants:
                continue

            # Category filter
            if categories and model.category not in categories:
                continue

            # Commercial filter
            if commercial_only and not model.commercial_use:
                continue

            # Try to find a viable variant
            result = self._check_model(model, platform, vram_mb, compute_cap, hardware)

            if isinstance(result, PassingCandidate):
                passing.append(result)
            else:
                rejected.append(result)

        return passing, rejected

    def _check_model(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_cap: Optional[float],
        hardware: HardwareProfile,
    ) -> PassingCandidate | RejectedCandidate:
        """
        Check if a model can run on the hardware.

        Tries variants in order of quality retention (highest first).
        If native variant fails, tries quantized variants.
        If all variants fail, returns a RejectedCandidate.
        """
        # TODO: Implement full logic in Phase 3
        # Stub: Use ModelDatabase's compatibility filtering

        variants = self.model_db.get_compatible_variants(
            model, platform, vram_mb, compute_cap
        )

        if variants:
            # Return best compatible variant
            best = variants[0]
            execution_mode = "native"

            # Check if this is a quantized variant
            if "gguf" in best.precision.lower() or "fp8" in best.precision.lower():
                execution_mode = "quantized"

            warnings = []
            # Add warnings for edge cases
            if best.quality_retention_percent < 90:
                warnings.append(
                    f"Using quantized variant ({best.precision}) - "
                    f"{best.quality_retention_percent}% quality retention"
                )

            return PassingCandidate(
                model=model,
                variant=best,
                execution_mode=execution_mode,
                warnings=warnings,
            )

        # No compatible variant found
        return self._generate_rejection(model, platform, vram_mb, compute_cap)

    def _generate_rejection(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_cap: Optional[float],
    ) -> RejectedCandidate:
        """Generate a rejection with helpful details."""
        # Find the minimum VRAM variant to give useful feedback
        min_vram = float('inf')
        for variant in model.variants:
            if variant.vram_min_mb < min_vram:
                min_vram = variant.vram_min_mb

        if min_vram > vram_mb:
            return RejectedCandidate(
                model_id=model.id,
                model_name=model.name,
                reason=RejectionReason.VRAM_INSUFFICIENT,
                details=f"Requires {min_vram}MB VRAM, you have {vram_mb}MB",
                suggestion=model.explanation.rejected_vram if model.explanation else None,
            )

        # Platform issue
        return RejectedCandidate(
            model_id=model.id,
            model_name=model.name,
            reason=RejectionReason.PLATFORM_UNSUPPORTED,
            details=f"Not supported on {platform}",
            suggestion=model.explanation.rejected_platform if model.explanation else None,
        )

    def _get_platform_key(self, hardware: HardwareProfile) -> str:
        """Get the platform key for model compatibility checks."""
        from src.services.model_database import normalize_platform
        return normalize_platform(hardware.gpu_vendor, hardware.platform)

    def _check_vram_constraint(
        self,
        variant: ModelVariant,
        vram_mb: int,
    ) -> bool:
        """Check if variant fits in VRAM."""
        return variant.vram_min_mb <= vram_mb

    def _check_platform_constraint(
        self,
        variant: ModelVariant,
        platform: str,
    ) -> bool:
        """Check platform support."""
        ps = variant.platform_support.get(platform)
        return ps is not None and ps.supported

    def _check_compute_capability(
        self,
        variant: ModelVariant,
        platform: str,
        compute_cap: Optional[float],
    ) -> bool:
        """Check compute capability requirement."""
        ps = variant.platform_support.get(platform)
        if not ps or not ps.min_compute_capability:
            return True
        if compute_cap is None:
            return False
        return compute_cap >= ps.min_compute_capability

    def _check_storage_constraint(
        self,
        variant: ModelVariant,
        free_storage_gb: float,
    ) -> bool:
        """Check storage space."""
        return variant.download_size_gb <= free_storage_gb

    def _can_offload_to_cpu(
        self,
        hardware: HardwareProfile,
        model: ModelEntry,
    ) -> bool:
        """
        Check if CPU offload is viable for this model.

        Requirements per SPEC:
        - CPU tier >= MEDIUM (8+ cores)
        - AVX2 support (for GGUF/llama.cpp)
        - Sufficient RAM for offload
        """
        if hardware.cpu is None:
            return False

        # Check CPU tier
        if hardware.cpu.tier.value < CPUTier.MEDIUM.value:
            return False

        # Check AVX2 for x86
        if hardware.cpu.architecture == "x86_64" and not hardware.cpu.supports_avx2:
            return False

        # Check RAM availability
        if hardware.ram is None:
            return False

        usable_ram = hardware.ram.usable_for_offload_gb
        if usable_ram < 4.0:  # Minimum 4GB for meaningful offload
            return False

        return True
