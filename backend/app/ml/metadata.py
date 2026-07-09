from datetime import datetime, timezone

ML_VERSION = "1.0.0"


def build_ml_metadata(
    model_type: str = "unknown",
    model_version: str = "1.0.0",
    task: str = "regression",
    feature_set: list[str] | None = None,
    n_features: int = 0,
    n_samples: int = 0,
    hyperparameters: dict | None = None,
    metrics: dict | None = None,
    training_time_s: float | None = None,
    framework: str = "sklearn",
    additional: dict | None = None,
) -> dict:
    metadata = {
        "model_type": model_type,
        "model_version": model_version,
        "task": task,
        "framework": framework,
        "feature_set": feature_set or [],
        "n_features": n_features,
        "n_samples": n_samples,
        "ml_version": ML_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "processing_history": [
            {
                "step": "model_training",
                "model_type": model_type,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        ],
    }
    if hyperparameters:
        metadata["hyperparameters"] = hyperparameters
    if metrics:
        metadata["metrics"] = metrics
    if training_time_s is not None:
        metadata["training_time_s"] = round(training_time_s, 2)
    if additional:
        metadata.update(additional)
    return metadata
