from .exceptions import (
    RecommendationError,
    ConfigurationError,
    InvalidHotspotError,
    NoRecommendationsError,
    OptimizationError,
    ScoringError,
    BudgetExceededError,
)
from .configuration import RecommenderConfig
from .rules import apply_rules, RECOMMENDATION_PROFILES
from .scoring import ScoredRecommendation, score_candidates, compute_cost_effectiveness, compute_feasibility
from .optimization import OptimizationResult, optimize_with_budget, generate_scenarios
from .engine import RecommenderEngine, RecommendationBundle, create_recommender

__all__ = [
    "RecommendationError", "ConfigurationError", "InvalidHotspotError",
    "NoRecommendationsError", "OptimizationError", "ScoringError",
    "BudgetExceededError",
    "RecommenderConfig",
    "apply_rules", "RECOMMENDATION_PROFILES",
    "ScoredRecommendation", "score_candidates",
    "compute_cost_effectiveness", "compute_feasibility",
    "OptimizationResult", "optimize_with_budget", "generate_scenarios",
    "RecommenderEngine", "RecommendationBundle", "create_recommender",
]
