"""
Cloud Recommendation Layer.

Per PLAN: Cloud API Integration - This layer scores and ranks cloud API models
using hybrid criteria (shared content criteria + cloud-specific criteria).

Cloud models are scored differently from local models:
- Shared criteria: content_similarity, style_fit, approach_fit, ecosystem_maturity
- Cloud-specific (replace hardware_fit): cost_efficiency, provider_reliability, rate_limits, latency

Cost sensitivity (1-5) acts as a counterweight to quality, similar to how
hardware constraints work for local models:
- Primary: Adjusts weights (high sensitivity → cost dominates)
- Secondary: Suggests cheaper alternatives
- Tertiary: Soft filter on expensive models for cost_sensitivity=5
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

from src.schemas.recommendation import (
    UserProfile,
    CloudAPIPreferences,
    CloudRankedCandidate,
    UseCaseDefinition,
    SharedQualityPrefs,
)
from src.services.model_database import ModelDatabase, ModelEntry, get_model_database
from src.utils.logger import log


# =============================================================================
# Constants
# =============================================================================

# Major providers get higher reliability scores (stable APIs, good docs)
MAJOR_PROVIDERS = frozenset([
    "openai",
    "anthropic",
    "google",
    "stability_ai",
    "black_forest_labs",
    "midjourney",
    "runway",
])

# Cost thresholds for soft filtering (per generation)
COST_THRESHOLDS = {
    1: float("inf"),  # No limit
    2: float("inf"),  # No limit
    3: 0.50,          # $0.50/generation max
    4: 0.20,          # $0.20/generation max
    5: 0.10,          # $0.10/generation max (soft filter expensive)
}

# Weight distributions based on cost sensitivity (1-5)
# Per PLAN: Cloud API Integration - Weights shift from quality → cost
WEIGHT_DISTRIBUTIONS = {
    # cost_sensitivity=1: Quality dominates
    1: {
        "content_similarity": 0.25,
        "style_fit": 0.15,
        "approach_fit": 0.10,
        "ecosystem_maturity": 0.10,
        "cost_efficiency": 0.05,
        "provider_reliability": 0.15,
        "rate_limits": 0.10,
        "latency": 0.10,
    },
    # cost_sensitivity=2: Quality-leaning balance
    2: {
        "content_similarity": 0.23,
        "style_fit": 0.13,
        "approach_fit": 0.08,
        "ecosystem_maturity": 0.09,
        "cost_efficiency": 0.12,
        "provider_reliability": 0.15,
        "rate_limits": 0.10,
        "latency": 0.10,
    },
    # cost_sensitivity=3: Balanced (DEFAULT)
    3: {
        "content_similarity": 0.20,
        "style_fit": 0.12,
        "approach_fit": 0.08,
        "ecosystem_maturity": 0.08,
        "cost_efficiency": 0.17,
        "provider_reliability": 0.15,
        "rate_limits": 0.10,
        "latency": 0.10,
    },
    # cost_sensitivity=4: Cost-leaning balance
    4: {
        "content_similarity": 0.18,
        "style_fit": 0.10,
        "approach_fit": 0.06,
        "ecosystem_maturity": 0.06,
        "cost_efficiency": 0.25,
        "provider_reliability": 0.15,
        "rate_limits": 0.10,
        "latency": 0.10,
    },
    # cost_sensitivity=5: Cost dominates
    5: {
        "content_similarity": 0.20,
        "style_fit": 0.10,
        "approach_fit": 0.05,
        "ecosystem_maturity": 0.05,
        "cost_efficiency": 0.30,
        "provider_reliability": 0.15,
        "rate_limits": 0.05,
        "latency": 0.10,
    },
}

# Storage boost parameters
STORAGE_BOOST_THRESHOLD_GB = 50  # Boost starts when free space < 50GB
STORAGE_BOOST_MAX = 0.20         # Max 20% boost to cloud scores

# Cost efficiency scale: Models at or above this cost score 0.0
COST_EFFICIENCY_THRESHOLD = 0.10  # $0.10/generation marks the "expensive" end

# Cost penalty multiplier for soft filtering expensive models
COST_PENALTY_MULTIPLIER = 0.3  # 70% score reduction for over-threshold models

# Monthly generation estimates based on batch_frequency scale (1-5)
# Scale definition per PLAN:
#   1 (Rarely): ~2-3 times per month → 10 generations
#   2 (Occasionally): ~1-2 per week → 50 generations
#   3 (Moderate): ~3-4 per week → 100 generations
#   4 (Frequently): ~10 per week → 300 generations
#   5 (Constantly): Daily batches → 1000 generations
MONTHLY_GENERATION_ESTIMATES = {
    1: 10,    # Rarely: 2-3x/month
    2: 50,    # Occasionally: 1-2x/week
    3: 100,   # Moderate: 3-4x/week (DEFAULT)
    4: 300,   # Frequently: ~10x/week
    5: 1000,  # Constantly: daily batches
}


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class CloudScoringResult:
    """Intermediate result with all scoring components."""
    model: ModelEntry
    content_score: float = 0.0
    style_score: float = 0.0
    approach_score: float = 0.0
    ecosystem_score: float = 0.0
    cost_score: float = 0.0
    provider_score: float = 0.0
    rate_limit_score: float = 0.0
    latency_score: float = 0.0
    overall_score: float = 0.0
    reasoning: List[str] = field(default_factory=list)


# =============================================================================
# Cloud Recommendation Layer
# =============================================================================

class CloudRecommendationLayer:
    """
    Scores and ranks cloud API models using hybrid criteria.

    Per PLAN: Cloud API Integration - This layer implements the cloud pathway
    of the parallel recommendation architecture.

    Attributes:
        model_db: ModelDatabase instance for accessing cloud models
    """

    def __init__(self, model_db: Optional[ModelDatabase] = None):
        """
        Initialize the cloud recommendation layer.

        Args:
            model_db: Optional ModelDatabase instance. If None, uses singleton.
        """
        self.model_db = model_db or get_model_database()

    def recommend(
        self,
        user_profile: UserProfile,
        categories: Optional[List[str]] = None,
        storage_free_gb: Optional[float] = None,
    ) -> List[CloudRankedCandidate]:
        """
        Generate cloud model recommendations.

        Args:
            user_profile: User's preferences including cloud_api_preferences
            categories: Optional list of categories to filter (None = all)
            storage_free_gb: Free storage space for boost calculation

        Returns:
            List of CloudRankedCandidate, sorted by overall_score (highest first)
        """
        cloud_prefs = user_profile.cloud_api_preferences
        cost_sensitivity = cloud_prefs.cost_sensitivity

        # Validate cost sensitivity is in expected range
        if cost_sensitivity not in WEIGHT_DISTRIBUTIONS:
            log.warning(
                f"Invalid cost_sensitivity {cost_sensitivity}, using default (3). "
                f"Expected range: 1-5"
            )
            cost_sensitivity = 3

        # Get weights for this cost sensitivity level
        weights = WEIGHT_DISTRIBUTIONS[cost_sensitivity]

        # Get cloud models from database
        cloud_models = self._get_cloud_models(categories)

        if not cloud_models:
            log.warning("No cloud models found for recommendation")
            return []

        # Score each model
        scored_results: List[CloudScoringResult] = []

        for model in cloud_models:
            result = self._score_model(model, user_profile, weights)

            # Apply soft filter for high cost sensitivity
            if cost_sensitivity >= 4:
                cost = self._get_estimated_cost(model)
                threshold = COST_THRESHOLDS.get(cost_sensitivity, float("inf"))

                if cost > threshold:
                    result.reasoning.append(
                        f"Filtered: ${cost:.2f}/gen exceeds budget threshold ${threshold:.2f}"
                    )
                    result.overall_score *= COST_PENALTY_MULTIPLIER

            scored_results.append(result)

        # Apply storage boost if constrained
        if storage_free_gb is not None and storage_free_gb < STORAGE_BOOST_THRESHOLD_GB:
            boost = self._calculate_storage_boost(storage_free_gb)
            for result in scored_results:
                result.overall_score *= (1 + boost)
                if boost > 0:
                    result.reasoning.append(
                        f"Storage boost: +{boost*100:.0f}% (only {storage_free_gb:.0f}GB free)"
                    )

        # Sort by overall score
        scored_results.sort(key=lambda r: r.overall_score, reverse=True)

        # Convert to CloudRankedCandidate
        candidates = []
        for result in scored_results:
            candidates.append(self._to_ranked_candidate(
                result,
                user_profile,
                storage_boosted=(
                    storage_free_gb is not None and
                    storage_free_gb < STORAGE_BOOST_THRESHOLD_GB
                ),
            ))

        log.info(f"Scored {len(candidates)} cloud models for recommendation")
        return candidates

    def _get_cloud_models(
        self,
        categories: Optional[List[str]] = None,
    ) -> List[ModelEntry]:
        """
        Get cloud models from database, optionally filtered by category.

        Args:
            categories: Optional list of categories to filter

        Returns:
            List of ModelEntry objects that are cloud APIs
        """
        all_cloud = self.model_db.get_cloud_models()

        if categories is None:
            return all_cloud

        # Filter by category
        return [m for m in all_cloud if m.category in categories]

    def _score_model(
        self,
        model: ModelEntry,
        user_profile: UserProfile,
        weights: Dict[str, float],
    ) -> CloudScoringResult:
        """
        Score a single cloud model using hybrid criteria.

        Args:
            model: Model to score
            user_profile: User's preferences
            weights: Weight distribution for criteria

        Returns:
            CloudScoringResult with all component scores
        """
        result = CloudScoringResult(model=model)

        # Shared criteria (same as local pathway)
        result.content_score = self._score_content_similarity(model, user_profile)
        result.style_score = self._score_style_fit(model, user_profile)
        result.approach_score = self._score_approach_fit(model, user_profile)
        result.ecosystem_score = self._score_ecosystem_maturity(model)

        # Cloud-specific criteria
        result.cost_score = self._score_cost_efficiency(model)
        result.provider_score = self._score_provider_reliability(model)
        result.rate_limit_score = self._score_rate_limits(model)
        result.latency_score = self._score_latency(model)

        # Calculate weighted overall score
        result.overall_score = (
            weights["content_similarity"] * result.content_score +
            weights["style_fit"] * result.style_score +
            weights["approach_fit"] * result.approach_score +
            weights["ecosystem_maturity"] * result.ecosystem_score +
            weights["cost_efficiency"] * result.cost_score +
            weights["provider_reliability"] * result.provider_score +
            weights["rate_limits"] * result.rate_limit_score +
            weights["latency"] * result.latency_score
        )

        # Add reasoning
        self._add_scoring_reasoning(result, weights)

        return result

    def _score_content_similarity(
        self,
        model: ModelEntry,
        user_profile: UserProfile,
    ) -> float:
        """
        Score how well the model matches the user's use case.

        Uses capability scores from the model to match against user's
        primary use cases.
        """
        # Get model's primary capabilities
        primary_caps = model.capabilities.primary
        user_cases = user_profile.primary_use_cases

        if not primary_caps or not user_cases:
            return 0.5  # Neutral if no data

        # Check for capability overlap
        cap_set = set(c.lower() for c in primary_caps)
        case_set = set(c.lower() for c in user_cases)

        # Map use cases to capabilities
        case_to_cap = {
            "content_generation": {"t2i", "i2i", "text_to_image", "image_generation"},
            "video_generation": {"t2v", "i2v", "text_to_video", "video_generation"},
            "productivity": {"text", "chat", "coding", "writing"},
            "full_stack": {"t2i", "t2v", "text", "chat"},
        }

        relevant_caps = set()
        for case in case_set:
            relevant_caps.update(case_to_cap.get(case, set()))

        # Calculate overlap
        overlap = len(cap_set & relevant_caps)
        if overlap > 0:
            return min(1.0, 0.5 + (overlap * 0.2))

        # Check direct capability match
        if cap_set & case_set:
            return 0.8

        return 0.4  # No direct match

    def _score_style_fit(
        self,
        model: ModelEntry,
        user_profile: UserProfile,
    ) -> float:
        """
        Score how well the model's style capabilities match user preferences.
        """
        model_styles = model.capabilities.style_strengths
        if not model_styles:
            return 0.5  # Neutral if no style data

        # Check user's content preferences for style tags
        for prefs in user_profile.content_preferences.values():
            if prefs.style_tags:
                user_set = set(s.lower() for s in prefs.style_tags)
                model_set = set(s.lower() for s in model_styles)
                overlap = len(user_set & model_set)
                if overlap > 0:
                    return min(1.0, 0.5 + (overlap * 0.15))

        return 0.5  # Neutral

    def _score_approach_fit(
        self,
        model: ModelEntry,
        user_profile: UserProfile,
    ) -> float:
        """
        Score how well the model fits the user's preferred workflow approach.
        """
        # Cloud models are inherently "simple" from user perspective
        # Users who prefer simple setup should score cloud higher
        prefer_simple = user_profile.prefer_simple_setup

        if prefer_simple >= 4:
            return 0.9  # Cloud is very simple
        elif prefer_simple >= 3:
            return 0.7
        else:
            return 0.5  # User prefers complexity/control

    def _score_ecosystem_maturity(self, model: ModelEntry) -> float:
        """
        Score based on documentation, support, and API stability.
        """
        score = 0.5  # Base score

        # Partner node indicates good integration
        if model.cloud.partner_node:
            score += 0.3

        # Major providers have better docs/support
        provider = (model.provider or "").lower()
        if provider in MAJOR_PROVIDERS:
            score += 0.2

        # Check for features list (indicates maturity)
        if model.capabilities.features:
            score += 0.1

        return min(1.0, score)

    def _score_cost_efficiency(self, model: ModelEntry) -> float:
        """
        Score based on estimated cost per generation.

        Per PLAN: Cloud API Integration -
        Unknown/missing cost = 0.5 score (neutral, don't penalize or reward)
        $0.00/gen = 1.0 score (linear scale from threshold)
        $COST_EFFICIENCY_THRESHOLD/gen = 0.0 score (expensive)
        """
        cost = self._get_estimated_cost(model)

        if cost == 0:
            return 0.5  # Unknown cost = neutral (not free, just unknown)

        # Linear scale: threshold = 0.0, $0/gen = 1.0
        score = max(0.0, 1.0 - (cost / COST_EFFICIENCY_THRESHOLD))
        return score

    def _get_estimated_cost(self, model: ModelEntry) -> float:
        """
        Get estimated cost per generation from model data.

        Handles multiple pricing formats:
        1. cloud.estimated_cost_per_generation (local models with cloud option)
        2. pricing.estimated_cost_per_generation (cloud APIs with single price)
        3. pricing.standard_1024 etc. (resolution-specific pricing, use default)
        """
        # Try cloud info first (for local models with cloud variant)
        if model.cloud.estimated_cost_per_generation is not None:
            return model.cloud.estimated_cost_per_generation

        # Try pricing dict (for cloud APIs)
        if model.pricing:
            # Direct estimated cost
            if "estimated_cost_per_generation" in model.pricing:
                return model.pricing["estimated_cost_per_generation"]

            # Resolution-specific pricing (DALL-E, etc.) - use standard_1024 as default
            if "standard_1024" in model.pricing:
                return model.pricing["standard_1024"]

            # HD pricing as fallback
            if "hd_1024" in model.pricing:
                return model.pricing["hd_1024"]

            # Any numeric value as last resort
            for key, value in model.pricing.items():
                if isinstance(value, (int, float)) and value > 0:
                    return value

        return 0.0  # Unknown

    def _score_provider_reliability(self, model: ModelEntry) -> float:
        """
        Score based on provider type and Partner Node availability.

        Per PLAN: Cloud API Integration -
        Partner Node = 1.0 (unified billing, reliable)
        Major providers = 0.8 (stable APIs)
        Others = 0.5 (less certain)
        """
        if model.cloud.partner_node:
            return 1.0

        provider = (model.provider or "").lower()
        if provider in MAJOR_PROVIDERS:
            return 0.8

        return 0.5

    def _score_rate_limits(self, model: ModelEntry) -> float:
        """
        Score based on rate limits and quota availability.

        Higher score = more headroom for usage.
        """
        # Partner nodes typically have better rate limits
        if model.cloud.partner_node:
            return 0.9

        # Major providers have published limits
        provider = (model.provider or "").lower()
        if provider in MAJOR_PROVIDERS:
            return 0.7

        # Unknown limits
        return 0.5

    def _score_latency(self, model: ModelEntry) -> float:
        """
        Score based on expected API latency / generation wait time.

        For image generation, this is the time to receive the result.
        """
        scores = model.capabilities.scores

        # Check for speed-related scores
        speed = scores.get("speed", scores.get("generation_speed", 0.0))
        if speed > 0:
            return speed

        # Partner nodes have optimized routing
        if model.cloud.partner_node:
            return 0.7

        return 0.5  # Unknown latency

    def _calculate_storage_boost(self, storage_free_gb: float) -> float:
        """
        Calculate storage boost for cloud recommendations.

        Per PLAN: Cloud API Integration -
        50GB free → no boost
        10GB free → 20% boost (max)
        """
        if storage_free_gb >= STORAGE_BOOST_THRESHOLD_GB:
            return 0.0

        # Linear interpolation: 50GB = 0%, 0GB = 20%
        shortage = STORAGE_BOOST_THRESHOLD_GB - storage_free_gb
        ratio = shortage / STORAGE_BOOST_THRESHOLD_GB
        boost = ratio * STORAGE_BOOST_MAX

        return min(STORAGE_BOOST_MAX, boost)

    def _add_scoring_reasoning(
        self,
        result: CloudScoringResult,
        weights: Dict[str, float],
    ) -> None:
        """Add human-readable reasoning for the score."""
        model = result.model
        reasoning = result.reasoning

        # Content match
        if result.content_score >= 0.7:
            reasoning.append(f"Good use case match for {model.name}")

        # Cost efficiency
        cost = self._get_estimated_cost(model)
        if cost > 0:
            reasoning.append(f"~${cost:.3f}/generation")

        # Provider reliability
        if model.cloud.partner_node:
            reasoning.append("Via ComfyUI Partner Node (unified billing)")
        elif result.provider_score >= 0.8:
            reasoning.append(f"Reliable provider: {model.provider}")

        # Overall assessment
        if result.overall_score >= 0.7:
            reasoning.append("Highly recommended for your preferences")
        elif result.overall_score >= 0.5:
            reasoning.append("Good match for your preferences")

    def _to_ranked_candidate(
        self,
        result: CloudScoringResult,
        user_profile: UserProfile,
        storage_boosted: bool = False,
    ) -> CloudRankedCandidate:
        """Convert scoring result to CloudRankedCandidate."""
        model = result.model
        cost = self._get_estimated_cost(model)

        # Estimate monthly cost based on batch frequency
        # Get batch_frequency from content preferences (1=rarely, 5=constantly)
        # Use the maximum across all content types for monthly cost estimate
        batch_freq = 3  # Default: moderate usage
        if user_profile.content_preferences:
            batch_freq = max(
                (prefs.batch_frequency for prefs in user_profile.content_preferences.values()),
                default=3
            )

        # Ensure batch_freq is in valid range (1-5)
        batch_freq = min(5, max(1, batch_freq))

        # Map frequency to estimated generations per month
        monthly_gens = MONTHLY_GENERATION_ESTIMATES.get(batch_freq, 100)
        monthly_cost = cost * monthly_gens

        return CloudRankedCandidate(
            model_id=model.id,
            display_name=model.name,
            provider=model.provider or "unknown",
            category=model.category,  # For modality filtering in UI
            content_score=result.content_score,
            style_score=result.style_score,
            approach_score=result.approach_score,
            ecosystem_score=result.ecosystem_score,
            cost_score=result.cost_score,
            provider_score=result.provider_score,
            rate_limit_score=result.rate_limit_score,
            latency_score=result.latency_score,
            overall_score=result.overall_score,
            estimated_cost_per_use=cost,
            estimated_monthly_cost=monthly_cost,
            setup_type="partner_node" if model.cloud.partner_node else "api_key",
            storage_boost_applied=storage_boosted,
            reasoning=result.reasoning.copy(),
        )


# =============================================================================
# Module-level accessor
# =============================================================================

_cloud_layer_instance: Optional[CloudRecommendationLayer] = None


def get_cloud_layer() -> CloudRecommendationLayer:
    """Get or create the singleton CloudRecommendationLayer instance."""
    global _cloud_layer_instance
    if _cloud_layer_instance is None:
        _cloud_layer_instance = CloudRecommendationLayer()
    return _cloud_layer_instance
