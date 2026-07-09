from dataclasses import dataclass, field

from .exceptions import ConfigurationError


@dataclass
class MLForecastConfig:
    model_type: str = "random_forest"
    prediction_task: str = "regression"
    test_size: float = 0.2
    random_state: int = 42
    n_estimators: int = 100
    max_depth: int | None = None
    learning_rate: float = 0.1
    batch_size: int = 256
    epochs: int = 100
    early_stopping_rounds: int = 10
    cv_folds: int = 5
    cv_strategy: str = "kfold"
    scoring: str = "r2"
    n_trials: int = 50
    hyperparameter_method: str = "optuna"
    ensemble_method: str = "weighted"
    drift_alert_threshold: float = 0.05
    normalization: str = "standard"
    feature_selection: str = "none"
    max_features: int = 50
    missing_strategy: str = "mean"
    checkpoint_dir: str = "checkpoints"
    export_dir: str = "models"
    parallel: bool = False
    n_workers: int = 4
    gpu_enabled: bool = False
    use_mixed_precision: bool = False
    cache_enabled: bool = True
    verbose: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "MLForecastConfig":
        valid = set(cls.__dataclass_fields__)
        for k in d:
            if k not in valid:
                raise ConfigurationError(f"Unknown config key: {k}")
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def defaults(cls) -> "MLForecastConfig":
        return cls()
