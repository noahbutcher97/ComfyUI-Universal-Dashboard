"""
Unit tests for RecommendationExplainer.

Tests human-readable explanation generation per SPEC_v3 Section 6.6.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from src.services.recommendation.recommendation_explainer import (
    RecommendationExplainer,
    ExplanationType,
    ExplanationItem,
    ModelExplanation,
    RecommendationReport,
)
from src.services.recommendation.constraint_layer import (
    PassingCandidate,
    RejectedCandidate,
    RejectionReason,
)
from src.services.recommendation.content_layer import ScoredCandidate, FeatureMatch
from src.services.recommendation.topsis_layer import RankedCandidate, CriterionScore
from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    FormFactorProfile,
    StorageProfile,
    StorageTier,
    RAMProfile,
)


# --- Mock Objects ---


@dataclass
class MockCapabilities:
    """Mock model capabilities."""
    scores: Dict[str, float] = field(default_factory=dict)
    style_strengths: List[str] = field(default_factory=list)


@dataclass
class MockModelVariant:
    """Mock model variant."""
    id: str = "fp16"
    precision: str = "fp16"
    vram_min_mb: int = 8000
    vram_recommended_mb: int = 12000


@dataclass
class MockModelEntry:
    """Mock model entry."""
    id: str = "test_model"
    name: str = "Test Model"
    family: str = "sdxl"
    variants: List[MockModelVariant] = field(default_factory=list)


def create_mock_hardware(
    vram_gb: float = 12.0,
    gpu_name: str = "NVIDIA GeForce RTX 4080",
    platform: PlatformType = PlatformType.WINDOWS_NVIDIA,
    ram_gb: float = 32.0,
    storage_free_gb: float = 200.0,
    storage_tier: StorageTier = StorageTier.FAST,
) -> HardwareProfile:
    """Create a mock HardwareProfile for testing."""
    return HardwareProfile(
        platform=platform,
        gpu_vendor="nvidia" if "NVIDIA" in platform.value else "apple",
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        compute_capability=8.9,
        form_factor=FormFactorProfile(
            is_laptop=False,
            sustained_performance_ratio=1.0,
        ),
        storage=StorageProfile(
            path="C:\\",
            total_gb=500.0,
            free_gb=storage_free_gb,
            storage_type="nvme_gen4",
            estimated_read_mbps=5000,
            tier=storage_tier,
        ),
        ram=RAMProfile(
            total_gb=ram_gb,
            available_gb=ram_gb * 0.75,
            usable_for_offload_gb=ram_gb * 0.5,
        ),
    )


def create_mock_ranked_candidate(
    model_id: str = "test_model",
    model_name: str = "Test Model",
    closeness: float = 0.85,
    execution_mode: str = "native",
    warnings: List[str] = None,
    criterion_scores: Dict[str, CriterionScore] = None,
    feature_matches: List[FeatureMatch] = None,
) -> RankedCandidate:
    """Create a mock RankedCandidate for testing."""
    model = MockModelEntry(id=model_id, name=model_name)
    variant = MockModelVariant()

    passing = PassingCandidate(
        model=model,
        variant=variant,
        execution_mode=execution_mode,
        warnings=warnings or [],
    )

    scored = ScoredCandidate(
        passing_candidate=passing,
        similarity_score=0.8,
        matching_features=feature_matches or [
            FeatureMatch(
                feature_id="photorealism",
                user_value=0.9,
                model_value=0.85,
                contribution=0.15,
            ),
        ],
        style_match_bonus=0.05,
    )

    default_scores = {
        "content_similarity": CriterionScore(
            criterion_id="content_similarity",
            raw_score=0.85,
            weight=0.35,
            weighted_score=0.2975,
        ),
        "hardware_fit": CriterionScore(
            criterion_id="hardware_fit",
            raw_score=0.9,
            weight=0.25,
            weighted_score=0.225,
        ),
        "speed_fit": CriterionScore(
            criterion_id="speed_fit",
            raw_score=0.8,
            weight=0.15,
            weighted_score=0.12,
        ),
        "ecosystem_maturity": CriterionScore(
            criterion_id="ecosystem_maturity",
            raw_score=0.75,
            weight=0.15,
            weighted_score=0.1125,
        ),
        "approach_fit": CriterionScore(
            criterion_id="approach_fit",
            raw_score=0.7,
            weight=0.10,
            weighted_score=0.07,
        ),
    }

    return RankedCandidate(
        scored_candidate=scored,
        closeness_coefficient=closeness,
        final_rank=1,
        criterion_scores=criterion_scores or default_scores,
        explanation="Test explanation",
    )


def create_mock_rejected_candidate(
    model_id: str = "rejected_model",
    model_name: str = "Rejected Model",
    reason: RejectionReason = RejectionReason.VRAM_INSUFFICIENT,
    details: str = "Requires 24GB VRAM, only 12GB available",
    vram_min_mb: int = 24000,
) -> RejectedCandidate:
    """Create a mock RejectedCandidate for testing."""
    model = MockModelEntry(
        id=model_id,
        name=model_name,
        variants=[MockModelVariant(vram_min_mb=vram_min_mb)],
    )

    return RejectedCandidate(
        model_id=model_id,
        model_name=model_name,
        reason=reason,
        details=details,
        model=model,  # Include model for explainer access to variants
    )


# --- Enum Tests ---


class TestExplanationType:
    """Tests for ExplanationType enum."""

    def test_all_types_defined(self):
        """Should have all explanation types."""
        assert ExplanationType.RECOMMENDATION.value == "recommendation"
        assert ExplanationType.REJECTION.value == "rejection"
        assert ExplanationType.TRADE_OFF.value == "trade_off"
        assert ExplanationType.IMPROVEMENT.value == "improvement"
        assert ExplanationType.WARNING.value == "warning"

    def test_type_count(self):
        """Should have exactly 5 types."""
        assert len(ExplanationType) == 5


# --- Dataclass Tests ---


class TestExplanationItem:
    """Tests for ExplanationItem dataclass."""

    def test_fields(self):
        """Should have all expected fields."""
        item = ExplanationItem(
            type=ExplanationType.RECOMMENDATION,
            title="Test Title",
            description="Test description",
            details="Extra details",
            priority=80,
        )
        assert item.type == ExplanationType.RECOMMENDATION
        assert item.title == "Test Title"
        assert item.description == "Test description"
        assert item.details == "Extra details"
        assert item.priority == 80

    def test_default_values(self):
        """Should have sensible defaults."""
        item = ExplanationItem(
            type=ExplanationType.WARNING,
            title="Warning",
            description="Something happened",
        )
        assert item.details is None
        assert item.priority == 0


class TestModelExplanation:
    """Tests for ModelExplanation dataclass."""

    def test_fields(self):
        """Should have all expected fields."""
        explanation = ModelExplanation(
            model_id="test",
            model_name="Test Model",
            rank=1,
            score=0.85,
            summary="Great model",
            is_recommended=True,
        )
        assert explanation.model_id == "test"
        assert explanation.rank == 1
        assert explanation.score == 0.85

    def test_default_items(self):
        """Should have empty items list by default."""
        explanation = ModelExplanation(
            model_id="test",
            model_name="Test",
            rank=1,
            score=0.8,
        )
        assert explanation.items == []
        assert explanation.summary == ""
        assert explanation.is_recommended is True


class TestRecommendationReport:
    """Tests for RecommendationReport dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        report = RecommendationReport()
        assert report.primary_recommendation is None
        assert report.alternatives == []
        assert report.rejected_models == []
        assert report.hardware_summary == ""
        assert report.improvement_suggestions == []


# --- Explainer Tests ---


class TestRecommendationExplainer:
    """Tests for RecommendationExplainer class."""

    def test_initialization(self):
        """Should initialize without error."""
        explainer = RecommendationExplainer()
        assert explainer is not None


class TestHardwareSummary:
    """Tests for hardware summary generation."""

    def test_summarize_nvidia_hardware(self):
        """Should summarize NVIDIA hardware correctly."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(
            vram_gb=24.0,
            gpu_name="NVIDIA GeForce RTX 4090",
        )

        summary = explainer._summarize_hardware(hardware)

        assert "RTX 4090" in summary
        assert "24GB" in summary
        assert "VRAM" in summary

    def test_summarize_includes_ram(self):
        """Should include RAM in summary."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(ram_gb=64.0)

        summary = explainer._summarize_hardware(hardware)

        assert "64GB RAM" in summary

    def test_summarize_includes_storage(self):
        """Should include storage info in summary."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(
            storage_free_gb=500.0,
            storage_tier=StorageTier.FAST,
        )

        summary = explainer._summarize_hardware(hardware)

        assert "500GB" in summary
        assert "NVMe" in summary or "Fast" in summary

    def test_summarize_unknown_gpu(self):
        """Should handle unknown GPU gracefully."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(gpu_name="Unknown")

        summary = explainer._summarize_hardware(hardware)

        assert "No dedicated GPU" in summary


class TestExplainRankedModel:
    """Tests for ranked model explanation."""

    def test_explains_primary_recommendation(self):
        """Should explain primary recommendation with summary."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate(
            model_name="Flux Dev",
            closeness=0.92,
        )

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        assert explanation.model_name == "Flux Dev"
        assert explanation.rank == 1
        assert explanation.score == 0.92
        assert "best match" in explanation.summary.lower()
        assert "92%" in explanation.summary

    def test_explains_alternative(self):
        """Should explain alternative with different summary."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate(closeness=0.75)

        explanation = explainer._explain_ranked_model(ranked, rank=3, is_primary=False)

        assert explanation.rank == 3
        assert "alternative" in explanation.summary.lower()

    def test_includes_criterion_scores(self):
        """Should include top criterion scores."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate()

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        # Should have items for top criteria
        criteria_items = [
            i for i in explanation.items
            if i.type == ExplanationType.RECOMMENDATION
        ]
        assert len(criteria_items) >= 3

    def test_includes_feature_matches(self):
        """Should include feature matches from content layer."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate(
            feature_matches=[
                FeatureMatch(
                    feature_id="photorealism",
                    user_value=0.9,
                    model_value=0.95,
                    contribution=0.2,
                ),
            ]
        )

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        # Should have feature match items
        feature_items = [
            i for i in explanation.items
            if "Photorealism" in i.title
        ]
        assert len(feature_items) >= 1

    def test_includes_warnings(self):
        """Should include warnings from passing candidate."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate(
            warnings=["Performance may vary on laptop GPUs"]
        )

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        warning_items = [
            i for i in explanation.items
            if i.type == ExplanationType.WARNING
        ]
        assert len(warning_items) >= 1

    def test_explains_cpu_offload(self):
        """Should explain CPU offload when active."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate(execution_mode="gpu_offload")

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        offload_items = [
            i for i in explanation.items
            if "offload" in i.title.lower() or "offload" in i.description.lower()
        ]
        assert len(offload_items) >= 1

    def test_items_sorted_by_priority(self):
        """Should sort items by priority descending."""
        explainer = RecommendationExplainer()
        ranked = create_mock_ranked_candidate()

        explanation = explainer._explain_ranked_model(ranked, rank=1, is_primary=True)

        priorities = [i.priority for i in explanation.items]
        assert priorities == sorted(priorities, reverse=True)


class TestExplainRejection:
    """Tests for rejection explanation."""

    def test_explains_vram_rejection(self):
        """Should explain VRAM rejection."""
        explainer = RecommendationExplainer()
        rejected = create_mock_rejected_candidate(
            reason=RejectionReason.VRAM_INSUFFICIENT,
        )

        explanation = explainer._explain_rejection(rejected)

        assert explanation.is_recommended is False
        assert explanation.rank == 0
        assert "VRAM" in explanation.summary or "memory" in explanation.summary.lower()

    def test_explains_platform_rejection(self):
        """Should explain platform incompatibility."""
        explainer = RecommendationExplainer()
        rejected = create_mock_rejected_candidate(
            reason=RejectionReason.PLATFORM_UNSUPPORTED,
            details="Requires CUDA, Apple Silicon detected",
        )

        explanation = explainer._explain_rejection(rejected)

        assert "operating system" in explanation.summary.lower() or "compatible" in explanation.summary.lower()

    def test_explains_mps_kquant_rejection(self):
        """Should explain MPS K-quant crash issue."""
        explainer = RecommendationExplainer()
        rejected = create_mock_rejected_candidate(
            reason=RejectionReason.MPS_KQUANT_CRASH,
        )

        explanation = explainer._explain_rejection(rejected)

        assert "Apple Silicon" in explanation.summary or "crash" in explanation.summary.lower()

    def test_includes_details(self):
        """Should include rejection details."""
        explainer = RecommendationExplainer()
        rejected = create_mock_rejected_candidate(
            details="Specific technical details here",
        )

        explanation = explainer._explain_rejection(rejected)

        detail_items = [
            i for i in explanation.items
            if i.details or "Specific" in str(i.description)
        ]
        assert len(detail_items) >= 1


class TestImprovementSuggestions:
    """Tests for improvement suggestion generation."""

    def test_suggests_gpu_upgrade_for_vram_rejections(self):
        """Should suggest GPU upgrade when VRAM is limiting."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(vram_gb=8.0)
        rejected = [
            create_mock_rejected_candidate(
                reason=RejectionReason.VRAM_INSUFFICIENT,
            ),
            create_mock_rejected_candidate(
                model_id="another",
                reason=RejectionReason.VRAM_INSUFFICIENT,
            ),
        ]

        suggestions = explainer._generate_improvement_suggestions([], rejected, hardware)

        gpu_suggestions = [
            s for s in suggestions
            if "GPU" in s.title or "VRAM" in s.description
        ]
        assert len(gpu_suggestions) >= 1

    def test_suggests_storage_for_storage_rejections(self):
        """Should suggest more storage when space is limiting."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(storage_free_gb=50.0)
        rejected = [
            create_mock_rejected_candidate(
                reason=RejectionReason.STORAGE_INSUFFICIENT,
                details="Needs 100GB",
            ),
        ]

        suggestions = explainer._generate_improvement_suggestions([], rejected, hardware)

        storage_suggestions = [
            s for s in suggestions
            if "storage" in s.title.lower() or "disk" in s.title.lower()
        ]
        assert len(storage_suggestions) >= 1

    def test_warns_about_offload_usage(self):
        """Should warn when models use CPU offload."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [
            create_mock_ranked_candidate(execution_mode="gpu_offload"),
        ]

        suggestions = explainer._generate_improvement_suggestions(ranked, [], hardware)

        offload_warnings = [
            s for s in suggestions
            if "offload" in s.title.lower() or "offload" in s.description.lower()
        ]
        assert len(offload_warnings) >= 1

    def test_apple_silicon_kquant_warning(self):
        """Should warn about K-quant limitations on Apple Silicon."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(
            platform=PlatformType.APPLE_SILICON,
            gpu_name="Apple M3 Max",
        )
        rejected = [
            create_mock_rejected_candidate(
                reason=RejectionReason.MPS_KQUANT_CRASH,
            ),
        ]

        suggestions = explainer._generate_improvement_suggestions([], rejected, hardware)

        kquant_warnings = [
            s for s in suggestions
            if "K-Quant" in s.title or "quant" in s.description.lower()
        ]
        assert len(kquant_warnings) >= 1


class TestScoreToStrength:
    """Tests for score-to-strength conversion."""

    def test_excellent_score(self):
        """Should return 'Excellent' for high scores."""
        explainer = RecommendationExplainer()
        assert explainer._score_to_strength(0.9) == "Excellent"
        assert explainer._score_to_strength(0.8) == "Excellent"

    def test_good_score(self):
        """Should return 'Good' for medium-high scores."""
        explainer = RecommendationExplainer()
        assert explainer._score_to_strength(0.7) == "Good"
        assert explainer._score_to_strength(0.6) == "Good"

    def test_moderate_score(self):
        """Should return 'Moderate' for medium scores."""
        explainer = RecommendationExplainer()
        assert explainer._score_to_strength(0.5) == "Moderate"
        assert explainer._score_to_strength(0.4) == "Moderate"

    def test_limited_score(self):
        """Should return 'Limited' for low scores."""
        explainer = RecommendationExplainer()
        assert explainer._score_to_strength(0.3) == "Limited"
        assert explainer._score_to_strength(0.2) == "Limited"

    def test_poor_score(self):
        """Should return 'Poor' for very low scores."""
        explainer = RecommendationExplainer()
        assert explainer._score_to_strength(0.1) == "Poor"
        assert explainer._score_to_strength(0.0) == "Poor"


class TestFullExplanation:
    """Tests for complete explanation generation."""

    def test_explain_recommendations_returns_report(self):
        """Should return RecommendationReport."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [create_mock_ranked_candidate()]
        rejected = []

        report = explainer.explain_recommendations(ranked, rejected, hardware, "txt2img")

        assert isinstance(report, RecommendationReport)
        assert report.primary_recommendation is not None
        assert report.hardware_summary != ""

    def test_includes_alternatives(self):
        """Should include alternative recommendations."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [
            create_mock_ranked_candidate(model_id="first", closeness=0.9),
            create_mock_ranked_candidate(model_id="second", closeness=0.8),
            create_mock_ranked_candidate(model_id="third", closeness=0.7),
        ]

        report = explainer.explain_recommendations(ranked, [], hardware, "txt2img")

        assert len(report.alternatives) == 2  # Positions 2-3

    def test_includes_rejected_models(self):
        """Should include rejected model explanations."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        rejected = [
            create_mock_rejected_candidate(model_id="rej1"),
            create_mock_rejected_candidate(model_id="rej2"),
        ]

        report = explainer.explain_recommendations([], rejected, hardware, "txt2img")

        assert len(report.rejected_models) == 2

    def test_handles_empty_ranked(self):
        """Should handle no recommendations gracefully."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()

        report = explainer.explain_recommendations([], [], hardware, "txt2img")

        assert report.primary_recommendation is None
        assert report.alternatives == []


class TestTextFormatting:
    """Tests for text output formatting."""

    def test_format_as_text_returns_string(self):
        """Should return formatted string."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [create_mock_ranked_candidate()]

        report = explainer.explain_recommendations(ranked, [], hardware, "txt2img")
        text = explainer.format_as_text(report)

        assert isinstance(text, str)
        assert len(text) > 0

    def test_format_includes_hardware_section(self):
        """Should include hardware profile section."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(gpu_name="RTX 4090")
        ranked = [create_mock_ranked_candidate()]

        report = explainer.explain_recommendations(ranked, [], hardware, "txt2img")
        text = explainer.format_as_text(report)

        assert "HARDWARE" in text
        assert "RTX 4090" in text

    def test_format_includes_recommendation_section(self):
        """Should include top recommendation section."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [create_mock_ranked_candidate(model_name="Flux Schnell")]

        report = explainer.explain_recommendations(ranked, [], hardware, "txt2img")
        text = explainer.format_as_text(report)

        assert "RECOMMENDATION" in text
        assert "Flux Schnell" in text

    def test_format_includes_alternatives_section(self):
        """Should include alternatives section."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware()
        ranked = [
            create_mock_ranked_candidate(model_name="Primary"),
            create_mock_ranked_candidate(model_name="Alternative"),
        ]

        report = explainer.explain_recommendations(ranked, [], hardware, "txt2img")
        text = explainer.format_as_text(report)

        assert "ALTERNATIVE" in text

    def test_format_includes_suggestions_section(self):
        """Should include suggestions when present."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(vram_gb=8.0)
        rejected = [
            create_mock_rejected_candidate(reason=RejectionReason.VRAM_INSUFFICIENT),
        ]

        report = explainer.explain_recommendations([], rejected, hardware, "txt2img")
        text = explainer.format_as_text(report)

        assert "SUGGESTION" in text or "IMPROVEMENT" in text


class TestCriterionNames:
    """Tests for criterion name mapping."""

    def test_all_criteria_have_friendly_names(self):
        """Should have friendly names for all criteria."""
        explainer = RecommendationExplainer()

        expected_criteria = [
            "content_similarity",
            "hardware_fit",
            "speed_fit",
            "ecosystem_maturity",
            "approach_fit",
        ]

        for criterion in expected_criteria:
            assert criterion in explainer.CRITERION_NAMES
            assert explainer.CRITERION_NAMES[criterion] != criterion  # Not just the ID


class TestRejectionMessages:
    """Tests for rejection message mapping."""

    def test_all_reasons_have_friendly_messages(self):
        """Should have friendly messages for all rejection reasons."""
        explainer = RecommendationExplainer()

        # Check common rejection reasons
        expected_reasons = [
            RejectionReason.VRAM_INSUFFICIENT,
            RejectionReason.PLATFORM_UNSUPPORTED,
            RejectionReason.COMPUTE_CAPABILITY,
            RejectionReason.STORAGE_INSUFFICIENT,
            RejectionReason.CPU_CANNOT_OFFLOAD,
            RejectionReason.QUANTIZATION_UNAVAILABLE,
            RejectionReason.PAIRED_MODEL_MISSING,
            RejectionReason.MPS_KQUANT_CRASH,
            RejectionReason.APPLE_SILICON_EXCLUDED,
        ]

        for reason in expected_reasons:
            assert reason in explainer.REJECTION_MESSAGES
            message = explainer.REJECTION_MESSAGES[reason]
            assert len(message) > 10  # Meaningful message


class TestGpuTiers:
    """Tests for GPU tier classification."""

    def test_gpu_tiers_defined(self):
        """Should have all GPU tiers defined."""
        explainer = RecommendationExplainer()
        assert "consumer" in explainer.GPU_TIERS
        assert "prosumer" in explainer.GPU_TIERS
        assert "professional" in explainer.GPU_TIERS
        assert "multi_gpu" in explainer.GPU_TIERS

    def test_consumer_tier(self):
        """Should return consumer tier for <= 24GB."""
        explainer = RecommendationExplainer()
        assert explainer._get_upgrade_tier(8) == "consumer"
        assert explainer._get_upgrade_tier(16) == "consumer"
        assert explainer._get_upgrade_tier(24) == "consumer"

    def test_prosumer_tier(self):
        """Should return prosumer tier for 25-48GB."""
        explainer = RecommendationExplainer()
        assert explainer._get_upgrade_tier(32) == "prosumer"
        assert explainer._get_upgrade_tier(48) == "prosumer"

    def test_professional_tier(self):
        """Should return professional tier for 49-80GB."""
        explainer = RecommendationExplainer()
        assert explainer._get_upgrade_tier(64) == "professional"
        assert explainer._get_upgrade_tier(80) == "professional"

    def test_multi_gpu_tier(self):
        """Should return multi_gpu tier for > 80GB."""
        explainer = RecommendationExplainer()
        assert explainer._get_upgrade_tier(96) == "multi_gpu"
        assert explainer._get_upgrade_tier(160) == "multi_gpu"

    def test_tier_examples_not_empty(self):
        """Each tier should have example hardware."""
        explainer = RecommendationExplainer()
        for tier_name, tier_info in explainer.GPU_TIERS.items():
            assert "examples" in tier_info
            assert len(tier_info["examples"]) > 10

    def test_tiered_suggestion_for_large_models(self):
        """Should suggest appropriate tier for large model requirements."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(vram_gb=8.0)

        # Create rejection requiring 48GB (prosumer tier)
        rejected = [
            create_mock_rejected_candidate(
                reason=RejectionReason.VRAM_INSUFFICIENT,
                vram_min_mb=48000,  # 48GB requirement
            ),
        ]

        suggestions = explainer._generate_improvement_suggestions([], rejected, hardware)

        gpu_suggestions = [s for s in suggestions if "GPU" in s.title]
        assert len(gpu_suggestions) >= 1
        # Should suggest prosumer tier (A6000/RTX 6000 Ada)
        assert "A6000" in gpu_suggestions[0].details or "6000" in gpu_suggestions[0].details

    def test_tiered_suggestion_for_huge_models(self):
        """Should suggest professional tier for very large model requirements."""
        explainer = RecommendationExplainer()
        hardware = create_mock_hardware(vram_gb=24.0)

        # Create rejection requiring 80GB (professional tier)
        rejected = [
            create_mock_rejected_candidate(
                reason=RejectionReason.VRAM_INSUFFICIENT,
                vram_min_mb=80000,  # 80GB requirement
            ),
        ]

        suggestions = explainer._generate_improvement_suggestions([], rejected, hardware)

        gpu_suggestions = [s for s in suggestions if "GPU" in s.title]
        assert len(gpu_suggestions) >= 1
        # Should suggest professional tier (A100/H100)
        assert "A100" in gpu_suggestions[0].details or "H100" in gpu_suggestions[0].details
