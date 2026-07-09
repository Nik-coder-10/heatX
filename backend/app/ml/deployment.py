import logging
import os
from dataclasses import dataclass, field

from .exceptions import SerializationError, ModelNotFoundError
from .serialization import (
    save_joblib, load_joblib,
    save_pickle, load_pickle,
    save_onnx, save_torchscript, save_savedmodel,
)
from .model_registry import register_model, get_model, get_git_commit

logger = logging.getLogger("app.ml.deployment")


@dataclass
class DeploymentPackage:
    model_id: str
    model_path: str
    format: str
    metadata_path: str | None = None
    pipeline_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_path": self.model_path,
            "format": self.format,
        }


def export_model(
    model,
    model_id: str,
    model_type: str,
    output_dir: str = "models",
    format: str = "joblib",
    hyperparameters: dict | None = None,
    metrics: dict | None = None,
    feature_set: list[str] | None = None,
    task: str = "regression",
    pipeline=None,
    X_sample=None,
) -> DeploymentPackage:
    os.makedirs(output_dir, exist_ok=True)

    model_path = os.path.join(output_dir, f"{model_id}.{format}")
    if format == "joblib":
        save_joblib(model, model_path)
    elif format == "pickle":
        save_pickle(model, model_path)
    elif format == "onnx":
        save_onnx(model, model_path, X_sample)
    elif format == "torchscript":
        save_torchscript(model, model_path, X_sample)
    elif format == "savedmodel":
        save_savedmodel(model, model_path)
    else:
        raise SerializationError(f"Unsupported export format: {format}")

    pipeline_path = None
    if pipeline is not None:
        pipeline_path = os.path.join(output_dir, f"{model_id}_pipeline.joblib")
        save_joblib(pipeline, pipeline_path)

    git_commit = get_git_commit()
    register_model(
        model_id=model_id,
        model_type=model_type,
        model_version="1.0.0",
        hyperparameters=hyperparameters or {},
        metrics=metrics or {},
        git_commit=git_commit,
        feature_set=feature_set or [],
        task=task,
        path=model_path,
    )

    return DeploymentPackage(
        model_id=model_id,
        model_path=model_path,
        format=format,
        pipeline_path=pipeline_path,
    )


def load_model(model_id: str, format: str = "joblib") -> object:
    record = get_model(model_id)
    if not record.path:
        raise ModelNotFoundError(f"No path for model {model_id}")

    if format == "joblib":
        return load_joblib(record.path)
    elif format == "pickle":
        return load_pickle(record.path)
    else:
        raise SerializationError(f"Unsupported load format: {format}")


def deploy_model(
    model,
    model_id: str,
    model_type: str,
    output_dir: str = "models",
    formats: list[str] = None,
    **kwargs,
) -> list[DeploymentPackage]:
    formats = formats or ["joblib"]
    packages = []
    for fmt in formats:
        pkg = export_model(model, model_id, model_type, output_dir, fmt, **kwargs)
        packages.append(pkg)
    return packages
