"""
Layer 2: Content-Based Filtering Layer.

Cosine similarity matching between user preferences and model capabilities
per SPEC_v3 Section 6.3.

Computes similarity scores based on:
- User's 5 aggregated factors (from onboarding)
- Model's capability vectors
- Style tag matching
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

from src.schemas.recommendation import UserProfile, ContentPreferences
from src.services.recommendation.constraint_layer import PassingCandidate
from src.services.model_database import ModelEntry


@dataclass
class FeatureMatch:
    """A feature that matches between user and model."""
    feature_id: str
    user_value: float
    model_value: float
    contribution: float  # How much this contributed to similarity


@dataclass
class ScoredCandidate:
    """A candidate with content-based similarity score."""
    passing_candidate: PassingCandidate
    similarity_score: float  # 0.0 - 1.0
    matching_features: List[FeatureMatch] = field(default_factory=list)
    style_match_bonus: float = 0.0


class ContentBasedLayer:
    """
    Layer 2: Content-Based Filtering.

    Computes cosine similarity between user preference vectors and model
    capability vectors. Returns candidates ranked by similarity.

    SPEC_v3 Section 6.3:
    - User vector: 5 aggregated factors from onboarding
    - Model vector: Capability scores from models_database.yaml
    - Similarity: cosine(user_vector, model_vector)
    - Bonus: Style tag matches
    """

    # Weights for different capability dimensions
    DIMENSION_WEIGHTS = {
        "photorealism": 1.0,
        "artistic_quality": 1.0,
        "speed": 0.8,
        "text_rendering": 0.7,
        "consistency": 0.6,
        "motion_quality": 1.0,
        "temporal_coherence": 0.9,
    }

    # Style tag match bonus (per matching tag, capped)
    STYLE_TAG_BONUS = 0.05
    STYLE_TAG_MAX_BONUS = 0.20

    def __init__(self):
        """Initialize the content layer."""
        pass

    def score(
        self,
        candidates: List[PassingCandidate],
        user_profile: UserProfile,
        use_case: str,
    ) -> List[ScoredCandidate]:
        """
        Score candidates by similarity to user preferences.

        Args:
            candidates: Candidates that passed constraint satisfaction
            user_profile: User's preferences from onboarding
            use_case: The primary use case being evaluated

        Returns:
            List of ScoredCandidate, sorted by similarity (highest first)
        """
        # TODO: Implement full logic in Phase 3
        # Stub implementation

        # Get user's content preferences for this use case
        content_prefs = user_profile.content_preferences.get(use_case)
        if content_prefs is None:
            content_prefs = ContentPreferences()  # Default preferences

        # Build user feature vector
        user_vector = self._build_user_vector(content_prefs)

        scored = []
        for candidate in candidates:
            # Build model feature vector
            model_vector = self._build_model_vector(candidate.model)

            # Compute cosine similarity
            similarity = self._cosine_similarity(user_vector, model_vector)

            # Compute style tag bonus
            style_bonus = self._compute_style_bonus(
                content_prefs.style_tags,
                candidate.model.capabilities.style_strengths,
            )

            # Identify matching features for explainability
            matching_features = self._identify_matches(
                user_vector, model_vector, candidate.model
            )

            scored.append(ScoredCandidate(
                passing_candidate=candidate,
                similarity_score=similarity,
                matching_features=matching_features,
                style_match_bonus=style_bonus,
            ))

        # Sort by total score (similarity + bonus)
        scored.sort(
            key=lambda s: s.similarity_score + s.style_match_bonus,
            reverse=True
        )

        return scored

    def _build_user_vector(self, prefs: ContentPreferences) -> Dict[str, float]:
        """
        Build normalized user preference vector.

        Maps 1-5 scale preferences to 0.0-1.0 scores.
        """
        return {
            "photorealism": (prefs.photorealism - 1) / 4.0,
            "artistic_quality": (prefs.artistic_stylization - 1) / 4.0,
            "speed": (prefs.generation_speed - 1) / 4.0,
            "consistency": (prefs.consistency - 1) / 4.0,
            "motion_quality": ((prefs.motion_intensity or 3) - 1) / 4.0,
            "temporal_coherence": ((prefs.temporal_coherence or 3) - 1) / 4.0,
        }

    def _build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """
        Build model capability vector from model entry.

        Uses scores from models_database.yaml capabilities.scores.
        """
        scores = model.capabilities.scores
        return {
            "photorealism": scores.get("photorealism", 0.5),
            "artistic_quality": scores.get("artistic_quality", 0.5),
            "speed": scores.get("speed", 0.5),
            "consistency": scores.get("consistency", 0.5),
            "motion_quality": scores.get("motion_quality", 0.0),
            "temporal_coherence": scores.get("temporal_coherence", 0.0),
        }

    def _cosine_similarity(
        self,
        vec_a: Dict[str, float],
        vec_b: Dict[str, float],
    ) -> float:
        """
        Compute cosine similarity between two vectors.

        Returns value between 0.0 and 1.0.
        """
        # Get common dimensions
        dimensions = set(vec_a.keys()) & set(vec_b.keys())

        if not dimensions:
            return 0.0

        # Compute dot product and magnitudes
        dot_product = 0.0
        mag_a = 0.0
        mag_b = 0.0

        for dim in dimensions:
            weight = self.DIMENSION_WEIGHTS.get(dim, 1.0)
            a = vec_a[dim] * weight
            b = vec_b[dim] * weight

            dot_product += a * b
            mag_a += a * a
            mag_b += b * b

        # Avoid division by zero
        if mag_a == 0 or mag_b == 0:
            return 0.0

        similarity = dot_product / (math.sqrt(mag_a) * math.sqrt(mag_b))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))

    def _compute_style_bonus(
        self,
        user_styles: List[str],
        model_styles: List[str],
    ) -> float:
        """
        Compute bonus for matching style tags.

        Each matching tag adds STYLE_TAG_BONUS, up to STYLE_TAG_MAX_BONUS.
        """
        if not user_styles or not model_styles:
            return 0.0

        user_set = set(s.lower() for s in user_styles)
        model_set = set(s.lower() for s in model_styles)

        matches = len(user_set & model_set)
        bonus = matches * self.STYLE_TAG_BONUS

        return min(bonus, self.STYLE_TAG_MAX_BONUS)

    def _identify_matches(
        self,
        user_vector: Dict[str, float],
        model_vector: Dict[str, float],
        model: ModelEntry,
    ) -> List[FeatureMatch]:
        """
        Identify which features contributed most to the match.

        Used for explainability in recommendations.
        """
        matches = []

        for dim in user_vector:
            if dim not in model_vector:
                continue

            user_val = user_vector[dim]
            model_val = model_vector[dim]

            # Compute contribution (simplified)
            contribution = user_val * model_val

            if contribution > 0.1:  # Only significant contributions
                matches.append(FeatureMatch(
                    feature_id=dim,
                    user_value=user_val,
                    model_value=model_val,
                    contribution=contribution,
                ))

        # Sort by contribution
        matches.sort(key=lambda m: m.contribution, reverse=True)

        return matches[:5]  # Top 5 matches
