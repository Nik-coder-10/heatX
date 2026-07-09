class RecommendationError(Exception):
    pass

class ConfigurationError(RecommendationError):
    pass

class InvalidHotspotError(RecommendationError):
    pass

class NoRecommendationsError(RecommendationError):
    pass

class OptimizationError(RecommendationError):
    pass

class ScoringError(RecommendationError):
    pass

class BudgetExceededError(RecommendationError):
    pass
