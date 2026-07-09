from dataclasses import dataclass, field

from .exceptions import ConfigurationError


@dataclass
class XAIConfig:
    method: str = "shap"
    n_samples: int = 100
    max_features: int = 20
    background_size: int = 50
    confidence_threshold: float = 0.7
    uncertainty_alpha: float = 0.05
    counterfactual_steps: int = 10
    counterfactual_max_changes: int = 5
    parallel: bool = False
    n_workers: int = 4
    cache_enabled: bool = True
    cache_size: int = 128
    lazy_loading: bool = False
    batch_size: int = 1000
    visualization_format: str = "png"
    visualization_dpi: int = 150
    random_state: int = 42
    verbose: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "XAIConfig":
        valid = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def defaults(cls) -> "XAIConfig":
        return cls()
