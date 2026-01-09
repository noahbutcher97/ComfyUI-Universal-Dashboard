"""
Unit tests for SpaceConstrainedAdjustment.

Tests priority-based fitting of recommendations to available storage.
Per SPEC_v3 Section 6.7.5 and HARDWARE_DETECTION.md Section 4.4.
"""

import pytest

from src.services.recommendation.space_adjustment import (
    SpaceConstrainedAdjustment,
    SpaceAdjustedModel,
    SpaceConstrainedResult,
    DEFAULT_USE_CASE_PRIORITIES,
    WORKSPACE_BUFFER_GB,
    create_space_adjustment,
)
from src.schemas.hardware import StorageProfile, StorageTier


# --- Test Fixtures ---


def create_mock_storage(
    free_gb: float = 200.0,
    total_gb: float = 500.0,
    tier: StorageTier = StorageTier.FAST,
) -> StorageProfile:
    """Create a mock StorageProfile for testing."""
    return StorageProfile(
        path="C:\\",
        total_gb=total_gb,
        free_gb=free_gb,
        storage_type="nvme_gen4",
        estimated_read_mbps=5000,
        tier=tier,
    )


def create_mock_model(
    model_id: str = "test_model",
    model_name: str = "Test Model",
    size_gb: float = 10.0,
    use_case: str = "image_generation",
    has_cloud: bool = True,
) -> SpaceAdjustedModel:
    """Create a mock SpaceAdjustedModel for testing."""
    return SpaceAdjustedModel(
        model_id=model_id,
        model_name=model_name,
        size_gb=size_gb,
        use_case=use_case,
        has_cloud_alternative=has_cloud,
    )


# --- Dataclass Tests ---


class TestSpaceAdjustedModel:
    """Tests for SpaceAdjustedModel dataclass."""

    def test_fields(self):
        """Should have all expected fields."""
        model = SpaceAdjustedModel(
            model_id="flux",
            model_name="Flux Dev",
            size_gb=25.0,
            use_case="image_generation",
            has_cloud_alternative=True,
        )
        assert model.model_id == "flux"
        assert model.model_name == "Flux Dev"
        assert model.size_gb == 25.0
        assert model.use_case == "image_generation"
        assert model.has_cloud_alternative is True

    def test_default_cloud(self):
        """Should default to no cloud alternative."""
        model = SpaceAdjustedModel(
            model_id="test",
            model_name="Test",
            size_gb=10.0,
            use_case="test",
        )
        assert model.has_cloud_alternative is False


class TestSpaceConstrainedResult:
    """Tests for SpaceConstrainedResult dataclass."""

    def test_fields(self):
        """Should have all expected fields."""
        result = SpaceConstrainedResult(
            fits=False,
            adjusted_models=[],
            removed_models=[],
            cloud_fallback_models=[],
            space_needed_gb=100.0,
            space_available_gb=50.0,
            space_short_gb=60.0,  # 100 - 50 + 10 buffer
            suggestions=["Free up space"],
        )
        assert result.fits is False
        assert result.space_short_gb == 60.0

    def test_default_suggestions(self):
        """Should have empty suggestions by default."""
        result = SpaceConstrainedResult(
            fits=True,
            adjusted_models=[],
            removed_models=[],
            cloud_fallback_models=[],
            space_needed_gb=0,
            space_available_gb=100.0,
            space_short_gb=0,
        )
        assert result.suggestions == []


# --- Priority Tests ---


class TestDefaultPriorities:
    """Tests for default use case priorities."""

    def test_image_generation_highest(self):
        """Image generation should be highest priority."""
        assert DEFAULT_USE_CASE_PRIORITIES["image_generation"] == 1

    def test_video_before_text(self):
        """Video should be prioritized before text."""
        assert (
            DEFAULT_USE_CASE_PRIORITIES["video_generation"]
            < DEFAULT_USE_CASE_PRIORITIES["text_generation"]
        )

    def test_all_use_cases_defined(self):
        """Should have all common use cases defined."""
        expected = [
            "image_generation",
            "video_generation",
            "audio_generation",
            "text_generation",
            "upscaling",
            "inpainting",
            "controlnet",
            "lora",
        ]
        for use_case in expected:
            assert use_case in DEFAULT_USE_CASE_PRIORITIES


# --- SpaceConstrainedAdjustment Tests ---


class TestSpaceConstrainedAdjustmentInit:
    """Tests for SpaceConstrainedAdjustment initialization."""

    def test_default_init(self):
        """Should initialize with default priorities."""
        adjuster = SpaceConstrainedAdjustment()
        assert adjuster.priorities == DEFAULT_USE_CASE_PRIORITIES
        assert adjuster.buffer_gb == WORKSPACE_BUFFER_GB

    def test_custom_priorities(self):
        """Should accept custom priorities."""
        custom = {"custom_case": 1}
        adjuster = SpaceConstrainedAdjustment(priorities=custom)
        assert adjuster.priorities == custom

    def test_custom_buffer(self):
        """Should accept custom buffer size."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=20.0)
        assert adjuster.buffer_gb == 20.0


class TestAdjustForSpaceFits:
    """Tests for when all recommendations fit."""

    def test_empty_recommendations(self):
        """Should handle empty recommendations."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=100.0)

        result = adjuster.adjust_for_space([], storage)

        assert result.fits is True
        assert result.adjusted_models == []
        assert result.removed_models == []
        assert result.space_needed_gb == 0

    def test_single_model_fits(self):
        """Should fit single model with plenty of space."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=100.0)
        models = [create_mock_model(size_gb=20.0)]

        result = adjuster.adjust_for_space(models, storage)

        assert result.fits is True
        assert len(result.adjusted_models) == 1
        assert len(result.removed_models) == 0

    def test_multiple_models_fit(self):
        """Should fit multiple models when space permits."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=100.0)
        models = [
            create_mock_model(model_id="a", size_gb=20.0),
            create_mock_model(model_id="b", size_gb=30.0),
            create_mock_model(model_id="c", size_gb=25.0),
        ]

        result = adjuster.adjust_for_space(models, storage)

        # 75GB needed + 10GB buffer = 85GB < 100GB available
        assert result.fits is True
        assert len(result.adjusted_models) == 3
        assert result.space_needed_gb == 75.0

    def test_accounts_for_buffer(self):
        """Should account for workspace buffer."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=10.0)
        storage = create_mock_storage(free_gb=50.0)
        models = [create_mock_model(size_gb=40.0)]

        result = adjuster.adjust_for_space(models, storage)

        # 40GB + 10GB buffer = 50GB = exactly available
        assert result.fits is True


class TestAdjustForSpaceRemoves:
    """Tests for when models must be removed."""

    def test_removes_low_priority_first(self):
        """Should remove low priority models first."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=50.0)
        models = [
            create_mock_model(
                model_id="image",
                size_gb=30.0,
                use_case="image_generation",
            ),
            create_mock_model(
                model_id="lora",
                size_gb=20.0,
                use_case="lora",  # Lower priority
            ),
        ]

        result = adjuster.adjust_for_space(models, storage)

        # 50GB - 10GB buffer = 40GB available
        # image (30GB) fits, lora (20GB) doesn't
        assert result.fits is False
        assert len(result.adjusted_models) == 1
        assert result.adjusted_models[0].model_id == "image"
        assert len(result.removed_models) == 1
        assert result.removed_models[0].model_id == "lora"

    def test_keeps_high_priority(self):
        """Should keep high priority models."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=50.0)
        models = [
            create_mock_model(
                model_id="upscale",
                size_gb=15.0,
                use_case="upscaling",  # Lower priority
            ),
            create_mock_model(
                model_id="image",
                size_gb=30.0,
                use_case="image_generation",  # Higher priority
            ),
        ]

        result = adjuster.adjust_for_space(models, storage)

        # Even though upscale is smaller, image has priority
        assert result.adjusted_models[0].model_id == "image"
        assert result.removed_models[0].model_id == "upscale"

    def test_calculates_space_short(self):
        """Should correctly calculate space shortage."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=10.0)
        storage = create_mock_storage(free_gb=50.0)
        models = [
            create_mock_model(size_gb=30.0),
            create_mock_model(size_gb=40.0),
        ]

        result = adjuster.adjust_for_space(models, storage)

        # Total needed: 70GB, available: 50GB, buffer: 10GB
        # Short: 70 - 50 + 10 = 30GB
        assert result.space_short_gb == 30.0
        assert result.space_needed_gb == 70.0


class TestCloudFallback:
    """Tests for cloud fallback functionality."""

    def test_identifies_cloud_fallback(self):
        """Should identify removed models with cloud alternatives."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=30.0)
        models = [
            create_mock_model(
                model_id="cloud",
                size_gb=25.0,
                has_cloud=True,
                use_case="lora",
            ),
            create_mock_model(
                model_id="local_only",
                size_gb=25.0,
                has_cloud=False,
                use_case="controlnet",
            ),
        ]

        result = adjuster.adjust_for_space(models, storage)

        # Both models should be in removed
        assert len(result.removed_models) == 2
        # Only cloud model should be in cloud_fallback
        assert len(result.cloud_fallback_models) == 1
        assert result.cloud_fallback_models[0].model_id == "cloud"

    def test_cloud_fallback_empty_when_all_fit(self):
        """Should have empty cloud fallback when all fit."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=100.0)
        models = [create_mock_model(size_gb=20.0, has_cloud=True)]

        result = adjuster.adjust_for_space(models, storage)

        assert result.fits is True
        assert result.cloud_fallback_models == []


class TestSuggestions:
    """Tests for suggestion generation."""

    def test_suggests_free_space(self):
        """Should suggest freeing up space."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=30.0)
        models = [create_mock_model(size_gb=50.0)]

        result = adjuster.adjust_for_space(models, storage)

        space_suggestions = [
            s for s in result.suggestions
            if "Free up" in s
        ]
        assert len(space_suggestions) == 1

    def test_suggests_cloud_alternatives(self):
        """Should suggest cloud alternatives when available."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=20.0)
        models = [
            create_mock_model(
                model_id="a",
                model_name="Model A",
                size_gb=30.0,
                has_cloud=True,
            ),
        ]

        result = adjuster.adjust_for_space(models, storage)

        cloud_suggestions = [
            s for s in result.suggestions
            if "cloud" in s.lower()
        ]
        assert len(cloud_suggestions) >= 1

    def test_warns_no_cloud_alternative(self):
        """Should warn when model has no cloud alternative."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=20.0)
        models = [
            create_mock_model(
                model_id="local_only",
                size_gb=30.0,
                has_cloud=False,
            ),
        ]

        result = adjuster.adjust_for_space(models, storage)

        no_cloud_warnings = [
            s for s in result.suggestions
            if "no cloud alternative" in s.lower()
        ]
        assert len(no_cloud_warnings) == 1


class TestReorderByPriority:
    """Tests for priority reordering."""

    def test_reorders_by_priority(self):
        """Should reorder models by use case priority."""
        adjuster = SpaceConstrainedAdjustment()
        models = [
            create_mock_model(model_id="c", use_case="lora"),
            create_mock_model(model_id="a", use_case="image_generation"),
            create_mock_model(model_id="b", use_case="video_generation"),
        ]

        reordered = adjuster.reorder_by_priority(models)

        assert reordered[0].model_id == "a"  # image_generation = 1
        assert reordered[1].model_id == "b"  # video_generation = 2
        assert reordered[2].model_id == "c"  # lora = 8

    def test_handles_unknown_use_case(self):
        """Should handle unknown use cases (low priority)."""
        adjuster = SpaceConstrainedAdjustment()
        models = [
            create_mock_model(model_id="unknown", use_case="unknown_case"),
            create_mock_model(model_id="known", use_case="image_generation"),
        ]

        reordered = adjuster.reorder_by_priority(models)

        # Known use case should come first
        assert reordered[0].model_id == "known"
        assert reordered[1].model_id == "unknown"


class TestEstimateFit:
    """Tests for fit estimation."""

    def test_all_fit(self):
        """Should correctly estimate when all fit."""
        adjuster = SpaceConstrainedAdjustment()
        models = [
            create_mock_model(model_id="a", size_gb=20.0),
            create_mock_model(model_id="b", size_gb=30.0),
        ]

        estimate = adjuster.estimate_fit(models, 100.0)

        assert estimate["fits_all"] is True
        assert estimate["total_models"] == 2
        assert estimate["models_that_fit"] == 2
        assert estimate["models_removed"] == 0
        assert estimate["total_size_gb"] == 50.0

    def test_partial_fit(self):
        """Should correctly estimate partial fit."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=10.0)
        models = [
            create_mock_model(model_id="a", size_gb=30.0, use_case="image_generation"),
            create_mock_model(model_id="b", size_gb=40.0, use_case="video_generation"),
            create_mock_model(model_id="c", size_gb=50.0, use_case="lora"),
        ]

        estimate = adjuster.estimate_fit(models, 70.0)

        # 70 - 10 buffer = 60 available
        # a (30) + b (40) = 70 > 60, so only a fits
        assert estimate["fits_all"] is False
        assert estimate["models_that_fit"] == 1
        assert estimate["models_removed"] == 2


class TestFactoryFunction:
    """Tests for factory function."""

    def test_create_space_adjustment(self):
        """Should create instance with defaults."""
        adjuster = create_space_adjustment()
        assert isinstance(adjuster, SpaceConstrainedAdjustment)
        assert adjuster.priorities == DEFAULT_USE_CASE_PRIORITIES

    def test_create_with_custom_priorities(self):
        """Should create instance with custom priorities."""
        custom = {"custom": 1}
        adjuster = create_space_adjustment(priorities=custom)
        assert adjuster.priorities == custom


class TestEdgeCases:
    """Edge case tests."""

    def test_zero_size_models(self):
        """Should handle zero-size models."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=10.0)
        models = [create_mock_model(size_gb=0.0)]

        result = adjuster.adjust_for_space(models, storage)

        assert result.fits is True
        assert len(result.adjusted_models) == 1

    def test_exact_fit_with_buffer(self):
        """Should handle exact fit with buffer."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=10.0)
        storage = create_mock_storage(free_gb=60.0)
        models = [create_mock_model(size_gb=50.0)]

        result = adjuster.adjust_for_space(models, storage)

        # 50 + 10 buffer = 60 = exactly available
        assert result.fits is True

    def test_just_under_buffer(self):
        """Should not fit when just under buffer threshold."""
        adjuster = SpaceConstrainedAdjustment(buffer_gb=10.0)
        storage = create_mock_storage(free_gb=59.0)
        models = [create_mock_model(size_gb=50.0)]

        result = adjuster.adjust_for_space(models, storage)

        # 50 + 10 buffer = 60 > 59 available
        assert result.fits is False

    def test_many_small_models(self):
        """Should handle many small models correctly."""
        adjuster = SpaceConstrainedAdjustment()
        storage = create_mock_storage(free_gb=50.0)
        models = [
            create_mock_model(model_id=f"model_{i}", size_gb=5.0)
            for i in range(10)
        ]

        result = adjuster.adjust_for_space(models, storage)

        # 50GB total, 40GB available after buffer
        # Each model is 5GB, so 8 should fit
        assert len(result.adjusted_models) == 8
        assert len(result.removed_models) == 2
