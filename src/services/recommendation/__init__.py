"""
3-Layer Recommendation Engine.

This module implements the SPEC_v3 Section 6 recommendation architecture:
- Layer 1: Constraint Satisfaction (CSP) - Binary elimination
- Layer 2: Content-Based Filtering - Cosine similarity
- Layer 3: TOPSIS Multi-Criteria Ranking - Final scoring

Usage:
    from src.services.recommendation import RecommendationEngine

    engine = RecommendationEngine()
    results = engine.recommend(user_profile, hardware_profile, model_database)
"""

from src.services.recommendation.constraint_layer import ConstraintSatisfactionLayer
from src.services.recommendation.content_layer import ContentBasedLayer
from src.services.recommendation.topsis_layer import TOPSISLayer

__all__ = [
    "ConstraintSatisfactionLayer",
    "ContentBasedLayer",
    "TOPSISLayer",
]
