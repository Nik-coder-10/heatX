from dataclasses import dataclass, field

from .exceptions import ConfigurationError


@dataclass
class RecommenderConfig:
    max_recommendations: int = 5
    min_temperature_reduction: float = 0.5
    max_budget_per_hectare: float = 500000.0
    prioritization_method: str = "cost_effectiveness"
    include_rationale: bool = True
    include_feasibility: bool = True
    feasibility_model: str = "rule_based"
    cost_overrride: dict | None = None
    budget_constraint: float | None = None
    min_feasibility_score: float = 0.2
    co2_price_per_ton: float = 50.0
    discount_rate: float = 0.05
    time_horizon_years: int = 20
    verbose: bool = False
    random_state: int = 42

    @classmethod
    def from_dict(cls, d: dict) -> "RecommenderConfig":
        valid = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def defaults(cls) -> "RecommenderConfig":
        return cls()
