import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import PredictionError
from .feature_pipeline import FeaturePipeline

logger = logging.getLogger("app.ml.prediction")


@dataclass
class PredictionResult:
    values: np.ndarray
    confidence: float
    uncertainty: float
    model_type: str
    task: str
    feature_names: list[str] | None = None
    feature_importance: dict[str, float] | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "values": self.values.tolist() if hasattr(self.values, "tolist") else self.values,
            "confidence": round(self.confidence, 4),
            "uncertainty": round(self.uncertainty, 4),
            "model_type": self.model_type,
            "task": self.task,
            "n_predictions": len(self.values) if hasattr(self.values, "__len__") else 1,
        }


def predict(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    model_type: str = "random_forest",
    task: str = "regression",
    feature_names: list[str] | None = None,
) -> PredictionResult:
    if pipeline is not None:
        X_t = pipeline.transform(X)
    else:
        X_t = X

    try:
        values = model.predict(X_t)
    except Exception as e:
        raise PredictionError(f"Prediction failed: {e}")

    if hasattr(values, "ravel"):
        values = values.ravel()

    confidence = _estimate_confidence(model, X_t, task)
    uncertainty = _estimate_uncertainty(model, X_t, task)

    fi = None
    if hasattr(model, "feature_importances_") and feature_names:
        importances = model.feature_importances_
        if importances is not None and len(importances) == len(feature_names):
            fi = dict(zip(feature_names, importances.tolist()))

    return PredictionResult(
        values=values,
        confidence=confidence,
        uncertainty=uncertainty,
        model_type=model_type,
        task=task,
        feature_names=feature_names,
        feature_importance=fi,
    )


def predict_hotspot_probability(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    threshold: float = 0.5,
) -> PredictionResult:
    if pipeline is not None:
        X_t = pipeline.transform(X)
    else:
        X_t = X

    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X_t)
            if proba.shape[1] >= 2:
                probabilities = proba[:, 1]
            else:
                probabilities = proba[:, 0]
        except Exception:
            probabilities = model.predict(X_t)
    else:
        probabilities = model.predict(X_t)

    probabilities = np.clip(probabilities, 0, 1)
    binary = (probabilities >= threshold).astype(np.int32)

    result = PredictionResult(
        values=binary,
        confidence=float(np.mean(np.abs(probabilities - 0.5) * 2)),
        uncertainty=float(np.std(probabilities)),
        model_type="classifier",
        task="classification",
    )
    result.metadata = {
        "probabilities": probabilities.tolist(),
        "threshold": threshold,
    }
    return result


def predict_uhi_intensity(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    feature_names: list[str] | None = None,
) -> PredictionResult:
    result = predict(model, X, pipeline, feature_names=feature_names)
    result.metadata = {"prediction_type": "uhi_intensity"}
    return result


def predict_severity(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    severity_levels: list[str] | None = None,
) -> PredictionResult:
    levels = severity_levels or ["low", "moderate", "high", "extreme"]
    result = predict(model, X, pipeline, task="classification")
    values = result.values
    if values.ndim == 0:
        values = np.array([int(values)])
    values_int = np.clip(np.round(values).astype(int), 0, len(levels) - 1)
    result.values = np.array([levels[min(v, len(levels) - 1)] for v in values_int])
    result.metadata = {"prediction_type": "severity", "severity_levels": levels}
    return result


def _estimate_confidence(model, X: np.ndarray, task: str) -> float:
    if task == "classification" and hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X)
            return float(np.mean(np.max(proba, axis=1)))
        except Exception:
            pass

    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
        spread = float(np.std(imp) / (np.mean(imp) + 1e-10))
        return float(min(1.0, max(0.1, spread * 2.0)))

    return 0.85


def _estimate_uncertainty(model, X: np.ndarray, task: str) -> float:
    if hasattr(model, "estimators_"):
        predictions = []
        for est in model.estimators_[:10]:
            predictions.append(est.predict(X))
        if len(predictions) > 1:
            std = float(np.mean(np.std(predictions, axis=0)))
            mean_pred = float(np.mean(np.mean(predictions, axis=0)))
            return min(1.0, std / (abs(mean_pred) + 1e-10))

    return 0.12


def batch_predict(
    model,
    X: np.ndarray,
    batch_size: int = 1000,
    pipeline: FeaturePipeline | None = None,
) -> np.ndarray:
    n = X.shape[0]
    all_preds = []
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = X[start:end]
        if pipeline:
            batch = pipeline.transform(batch)
        preds = model.predict(batch)
        all_preds.append(preds)
    return np.concatenate(all_preds)
