from datetime import datetime, timezone

XAI_VERSION = "1.0.0"


def build_xai_metadata(
    model_name: str = "unknown",
    model_version: str = "1.0.0",
    feature_set: list[str] | None = None,
    algorithm: str = "shap",
    n_features: int = 0,
    n_instances: int = 0,
    execution_time_ms: float | None = None,
    additional: dict | None = None,
) -> dict:
    metadata = {
        "model": model_name,
        "model_version": model_version,
        "feature_set": feature_set or [],
        "n_features": n_features,
        "n_instances": n_instances,
        "algorithm": algorithm,
        "xai_version": XAI_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "processing_history": [
            {
                "step": "explanation_generation",
                "algorithm": algorithm,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        ],
    }
    if execution_time_ms is not None:
        metadata["execution_time_ms"] = round(execution_time_ms, 2)
    if additional:
        metadata.update(additional)
    return metadata
