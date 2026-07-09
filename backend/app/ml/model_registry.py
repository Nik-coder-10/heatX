import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .exceptions import ModelNotFoundError

logger = logging.getLogger("app.ml.model_registry")

_registry_store: dict[str, "ModelRecord"] = {}


@dataclass
class ModelRecord:
    model_id: str
    model_type: str
    model_version: str
    training_date: str
    hyperparameters: dict
    metrics: dict
    dataset_version: str
    git_commit: str
    feature_set: list[str]
    task: str
    path: str | None = None
    description: str = ""
    author: str = ""
    tags: dict | None = None

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "training_date": self.training_date,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "dataset_version": self.dataset_version,
            "git_commit": self.git_commit,
            "feature_set": self.feature_set,
            "task": self.task,
            "path": self.path,
            "description": self.description,
        }


def register_model(
    model_id: str,
    model_type: str,
    model_version: str,
    hyperparameters: dict,
    metrics: dict,
    dataset_version: str = "1.0.0",
    git_commit: str = "",
    feature_set: list[str] | None = None,
    task: str = "regression",
    path: str | None = None,
    description: str = "",
    author: str = "",
    tags: dict | None = None,
) -> ModelRecord:
    record = ModelRecord(
        model_id=model_id,
        model_type=model_type,
        model_version=model_version,
        training_date=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        hyperparameters=hyperparameters,
        metrics=metrics,
        dataset_version=dataset_version,
        git_commit=git_commit,
        feature_set=feature_set or [],
        task=task,
        path=path,
        description=description,
        author=author,
        tags=tags,
    )
    _registry_store[model_id] = record
    logger.info("Model registered: %s v%s", model_id, model_version)
    return record


def get_model(model_id: str) -> ModelRecord:
    if model_id not in _registry_store:
        raise ModelNotFoundError(f"Model '{model_id}' not found in registry")
    return _registry_store[model_id]


def list_models() -> list[ModelRecord]:
    return list(_registry_store.values())


def get_latest_version(model_type: str) -> ModelRecord | None:
    candidates = [r for r in _registry_store.values() if r.model_type == model_type]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.training_date)


def get_models_by_metric(metric: str, threshold: float) -> list[ModelRecord]:
    results = []
    for record in _registry_store.values():
        val = record.metrics.get(metric, -1)
        if val >= threshold:
            results.append(record)
    return results


def get_git_commit() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"
