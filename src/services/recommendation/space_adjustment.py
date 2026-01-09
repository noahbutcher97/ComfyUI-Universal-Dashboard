"""
Space-Constrained Recommendation Adjustment.

When total recommended models exceed available storage, applies priority-based
fitting to select which models to install locally vs recommend for cloud.

Per SPEC_v3 Section 6.7.5 and HARDWARE_DETECTION.md Section 4.4.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from src.schemas.hardware import StorageProfile


@dataclass
class SpaceAdjustedModel:
    """A model with its storage requirements."""
    model_id: str
    model_name: str
    size_gb: float
    use_case: str
    has_cloud_alternative: bool = False


@dataclass
class SpaceConstrainedResult:
    """Result of space-constrained adjustment."""
    # Whether all recommendations fit
    fits: bool
    # Models that fit within available space
    adjusted_models: List[SpaceAdjustedModel]
    # Models that were removed due to space
    removed_models: List[SpaceAdjustedModel]
    # Removed models that have cloud alternatives
    cloud_fallback_models: List[SpaceAdjustedModel]
    # Total space needed by all original recommendations
    space_needed_gb: float
    # Available free space
    space_available_gb: float
    # How much space is short (0 if fits)
    space_short_gb: float
    # Suggestions for the user
    suggestions: List[str] = field(default_factory=list)


# Default use case priorities (lower = more important)
# Users can override these based on their preferences
DEFAULT_USE_CASE_PRIORITIES: Dict[str, int] = {
    "image_generation": 1,      # Most users want image gen first
    "video_generation": 2,      # Video is popular but resource-heavy
    "audio_generation": 3,      # Audio models are smaller
    "text_generation": 4,       # LLMs often used via cloud
    "upscaling": 5,             # Nice to have but not essential
    "inpainting": 6,            # Specialized use case
    "controlnet": 7,            # Advanced users
    "lora": 8,                  # Enhancements, smaller files
}

# Workspace buffer to reserve for model operations
# This accounts for temp files during generation, safetensors loading, etc.
WORKSPACE_BUFFER_GB = 10


class SpaceConstrainedAdjustment:
    """
    Adjusts recommendations to fit available storage space.

    When the total size of recommended models exceeds free disk space,
    this class applies priority-based fitting to determine which models
    to install locally and which to recommend for cloud execution.
    """

    def __init__(
        self,
        priorities: Optional[Dict[str, int]] = None,
        buffer_gb: float = WORKSPACE_BUFFER_GB,
    ):
        """
        Initialize with use case priorities.

        Args:
            priorities: Dict mapping use_case -> priority (lower = more important).
                       If None, uses DEFAULT_USE_CASE_PRIORITIES.
            buffer_gb: Space to reserve for workspace operations.
        """
        self.priorities = priorities or DEFAULT_USE_CASE_PRIORITIES
        self.buffer_gb = buffer_gb

    def adjust_for_space(
        self,
        recommendations: List[SpaceAdjustedModel],
        storage: StorageProfile,
    ) -> SpaceConstrainedResult:
        """
        Fit recommendations to available space by priority.

        Models are sorted by use case priority and greedily fitted
        until storage is full. Remaining models are marked for removal
        or cloud fallback if available.

        Args:
            recommendations: List of models with storage requirements
            storage: User's storage profile

        Returns:
            SpaceConstrainedResult with fitted and removed models
        """
        if not recommendations:
            return SpaceConstrainedResult(
                fits=True,
                adjusted_models=[],
                removed_models=[],
                cloud_fallback_models=[],
                space_needed_gb=0,
                space_available_gb=storage.free_gb,
                space_short_gb=0,
                suggestions=[],
            )

        total_needed = sum(m.size_gb for m in recommendations)
        available_with_buffer = storage.free_gb - self.buffer_gb

        # Check if everything fits
        if available_with_buffer >= total_needed:
            return SpaceConstrainedResult(
                fits=True,
                adjusted_models=list(recommendations),
                removed_models=[],
                cloud_fallback_models=[],
                space_needed_gb=total_needed,
                space_available_gb=storage.free_gb,
                space_short_gb=0,
                suggestions=[],
            )

        # Sort by priority (lower priority number = more important)
        sorted_models = sorted(
            recommendations,
            key=lambda m: self.priorities.get(m.use_case, 99)
        )

        # Greedily fit models
        fitted: List[SpaceAdjustedModel] = []
        removed: List[SpaceAdjustedModel] = []
        cloud_fallback: List[SpaceAdjustedModel] = []
        current_size = 0.0

        for model in sorted_models:
            if current_size + model.size_gb <= available_with_buffer:
                fitted.append(model)
                current_size += model.size_gb
            else:
                removed.append(model)
                if model.has_cloud_alternative:
                    cloud_fallback.append(model)

        # Calculate space shortage
        space_short = total_needed - storage.free_gb + self.buffer_gb
        space_short = max(0, space_short)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            removed, cloud_fallback, space_short
        )

        return SpaceConstrainedResult(
            fits=False,
            adjusted_models=fitted,
            removed_models=removed,
            cloud_fallback_models=cloud_fallback,
            space_needed_gb=total_needed,
            space_available_gb=storage.free_gb,
            space_short_gb=space_short,
            suggestions=suggestions,
        )

    def _generate_suggestions(
        self,
        removed: List[SpaceAdjustedModel],
        cloud_fallback: List[SpaceAdjustedModel],
        space_short_gb: float,
    ) -> List[str]:
        """Generate user-facing suggestions based on adjustment result."""
        suggestions = []

        if space_short_gb > 0:
            suggestions.append(
                f"Free up {space_short_gb:.0f} GB of disk space to install all "
                f"recommended models."
            )

        if cloud_fallback:
            model_names = ", ".join(m.model_name for m in cloud_fallback[:3])
            if len(cloud_fallback) > 3:
                model_names += f", and {len(cloud_fallback) - 3} more"
            suggestions.append(
                f"Use cloud APIs for: {model_names}. "
                "These models work with ComfyUI Partner Nodes."
            )

        removed_without_cloud = [m for m in removed if not m.has_cloud_alternative]
        if removed_without_cloud:
            suggestions.append(
                f"{len(removed_without_cloud)} model(s) have no cloud alternative. "
                "Consider prioritizing storage for these."
            )

        return suggestions

    def reorder_by_priority(
        self,
        models: List[SpaceAdjustedModel],
    ) -> List[SpaceAdjustedModel]:
        """
        Reorder models by use case priority.

        Useful for displaying recommendations in priority order.

        Args:
            models: List of models to reorder

        Returns:
            Models sorted by priority (most important first)
        """
        return sorted(
            models,
            key=lambda m: self.priorities.get(m.use_case, 99)
        )

    def estimate_fit(
        self,
        models: List[SpaceAdjustedModel],
        free_gb: float,
    ) -> Dict[str, any]:
        """
        Quick estimate of how many models will fit.

        Useful for preview without full adjustment.

        Args:
            models: Models to evaluate
            free_gb: Available free space in GB

        Returns:
            Dict with fit statistics
        """
        total_size = sum(m.size_gb for m in models)
        available = free_gb - self.buffer_gb

        # Quick greedy count
        fitted_count = 0
        fitted_size = 0.0
        for m in sorted(models, key=lambda x: self.priorities.get(x.use_case, 99)):
            if fitted_size + m.size_gb <= available:
                fitted_count += 1
                fitted_size += m.size_gb
            else:
                break

        return {
            "total_models": len(models),
            "models_that_fit": fitted_count,
            "models_removed": len(models) - fitted_count,
            "total_size_gb": total_size,
            "fitted_size_gb": fitted_size,
            "space_available_gb": free_gb,
            "fits_all": fitted_count == len(models),
        }


def create_space_adjustment(
    priorities: Optional[Dict[str, int]] = None,
) -> SpaceConstrainedAdjustment:
    """Factory function to create SpaceConstrainedAdjustment instance."""
    return SpaceConstrainedAdjustment(priorities=priorities)
