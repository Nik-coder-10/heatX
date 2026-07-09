from dataclasses import dataclass, field

from .exceptions import ConfigurationError


@dataclass
class ScenarioConfig:
    default_delta_years: int = 10
    n_simulations: int = 100
    confidence_level: float = 0.95
    monetize_benefits: bool = True
    co2_price_per_ton: float = 50.0
    discount_rate: float = 0.05
    include_uncertainty: bool = True
    generate_visualizations: bool = False
    output_dir: str = "simulations"
    parallel: bool = False
    n_workers: int = 4
    verbose: bool = False
    random_state: int = 42

    @classmethod
    def from_dict(cls, d: dict) -> "ScenarioConfig":
        valid = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def defaults(cls) -> "ScenarioConfig":
        return cls()
