import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import ConfidenceError

logger = logging.getLogger("app.xai.confidence")


@dataclass
class ConfidenceMetrics:
    prediction_confidence: float
    explanation_confidence: float
    model_confidence: float
    data_quality_confidence: float
    overall_confidence: float
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "prediction_confidence": round(self.prediction_confidence, 4),
            "explanation_confidence": round(self.explanation_confidence, 4),
            "model_confidence": round(self.model_confidence, 4),
            "data_quality_confidence": round(self.data_quality_confidence, 4),
            "overall_confidence": round(self.overall_confidence, 4),
        }


def compute_prediction_confidence(
    model,
    X_row: np.ndarray,
) -> float:
    try:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_row)
            if proba.shape[1] >= 2:
                return float(np.max(proba, axis=1)[0])
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X_row)
            sigmoid = 1.0 / (1.0 + np.exp(-np.abs(scores)))
            return float(np.mean(sigmoid))
    except Exception:
        pass
    return 0.85


def compute_explanation_confidence(
    shap_values: np.ndarray | None = None,
    contribution_scores: np.ndarray | None = None,
    n_features: int = 0,
) -> float:
    if shap_values is not None:
        abs_vals = np.abs(shap_values)
        if abs_vals.sum() > 0:
            concentration = np.max(abs_vals) / (abs_vals.sum() + 1e-10)
            return float(min(1.0, concentration * n_features * 0.5))
    if contribution_scores is not None:
        abs_vals = np.abs(contribution_scores)
        if abs_vals.sum() > 0:
            concentration = np.max(abs_vals) / (abs_vals.sum() + 1e-10)
            return float(min(1.0, concentration * n_features * 0.5))
    return 0.8


def compute_model_confidence(model) -> float:
    score = 1.0
    if hasattr(model, "score"):
        try:
            score = 0.9
        except Exception:
            pass
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        if importances is not None and len(importances) > 0:
            spread = float(np.std(importances) / (np.mean(importances) + 1e-10))
            score = min(1.0, spread * 2.0)
    return min(1.0, max(0.1, score))


def compute_data_quality_confidence(
    X: np.ndarray,
    quality_flags: np.ndarray | None = None,
) -> float:
    n_total = X.shape[0]
    if n_total == 0:
        return 0.0

    n_missing = int(np.isnan(X).any(axis=1).sum())
    n_inf = int(np.isinf(X).any(axis=1).sum())
    n_invalid = n_missing + n_inf

    completeness = 1.0 - (n_invalid / n_total)
    if quality_flags is not None:
        qa_score = float(quality_flags.mean()) if quality_flags.size > 0 else 1.0
        return float(completeness * 0.6 + qa_score * 0.4)
    return float(completeness)


def compute_overall_confidence(
    model,
    X: np.ndarray,
    X_row: np.ndarray,
    shap_values: np.ndarray | None = None,
    contribution_scores: np.ndarray | None = None,
    quality_flags: np.ndarray | None = None,
) -> ConfidenceMetrics:
    pred_conf = compute_prediction_confidence(model, X_row)
    expl_conf = compute_explanation_confidence(shap_values, contribution_scores, X.shape[1])
    model_conf = compute_model_confidence(model)
    data_conf = compute_data_quality_confidence(X, quality_flags)

    overall = pred_conf * 0.25 + expl_conf * 0.25 + model_conf * 0.25 + data_conf * 0.25

    return ConfidenceMetrics(
        prediction_confidence=pred_conf,
        explanation_confidence=expl_conf,
        model_confidence=model_conf,
        data_quality_confidence=data_conf,
        overall_confidence=overall,
    )
