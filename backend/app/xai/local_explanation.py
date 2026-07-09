import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import ExplanationError

logger = logging.getLogger("app.xai.local_explanation")


@dataclass
class LocalExplanation:
    instance_id: str
    feature_names: list[str]
    feature_values: np.ndarray
    shap_values: np.ndarray | None = None
    contribution_scores: np.ndarray | None = None
    top_contributing_features: list[str] | None = None
    positive_factors: list[tuple[str, float]] | None = None
    negative_factors: list[tuple[str, float]] | None = None
    confidence: float = 1.0
    predicted_value: float | None = None
    expected_value: float | None = None
    alternative_explanation: str | None = None
    method: str = "shap"
    metadata: dict | None = None

    def __post_init__(self):
        if self.contribution_scores is not None and self.top_contributing_features is None:
            self._compute_top_features()

    def _compute_top_features(self, n: int = 10):
        if self.contribution_scores is None:
            return
        scores = np.abs(self.contribution_scores)
        idx = np.argsort(scores)[::-1][:n]
        self.top_contributing_features = [self.feature_names[i] for i in idx]
        self.positive_factors = []
        self.negative_factors = []
        for i in idx:
            val = float(self.contribution_scores[i])
            if val >= 0:
                self.positive_factors.append((self.feature_names[i], val))
            else:
                self.negative_factors.append((self.feature_names[i], abs(val)))

    def to_dict(self) -> dict:
        def _to_list(v):
            return v.tolist() if hasattr(v, "tolist") else v
        return {
            "instance_id": self.instance_id,
            "feature_names": self.feature_names,
            "feature_values": _to_list(self.feature_values),
            "shap_values": _to_list(self.shap_values),
            "contribution_scores": _to_list(self.contribution_scores),
            "top_contributing_features": self.top_contributing_features,
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "confidence": self.confidence,
            "predicted_value": self.predicted_value,
            "expected_value": self.expected_value,
            "method": self.method,
        }


def explain_instance(
    model,
    X_row: np.ndarray,
    feature_names: list[str],
    background: np.ndarray | None = None,
    method: str = "shap",
    instance_id: str = "0",
    n_samples: int = 100,
) -> LocalExplanation:
    if X_row.ndim == 1:
        X_row = X_row.reshape(1, -1)

    if method == "shap":
        return _explain_instance_shap(model, X_row, feature_names, background, instance_id, n_samples)
    elif method == "permutation":
        return _explain_instance_permutation(model, X_row, feature_names, instance_id)
    else:
        raise ExplanationError(f"Unsupported local explanation method: {method}")


def _explain_instance_shap(
    model, X_row, feature_names, background, instance_id, n_samples
) -> LocalExplanation:
    try:
        import shap
    except ImportError:
        raise ExplanationError("SHAP library is required")

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_row)
        is_list = isinstance(shap_values, list)
        if is_list:
            shap_values = shap_values[0]
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 1]
        expected = explainer.expected_value
        if isinstance(expected, np.ndarray):
            expected = float(expected.item()) if expected.size <= 1 else float(expected[0])
        elif isinstance(expected, list):
            expected = float(expected[0]) if len(expected) > 1 else float(expected[0])
        else:
            expected = float(expected)
    except Exception:
        bg = background if background is not None else np.random.randn(50, X_row.shape[1])
        explainer = shap.KernelExplainer(model.predict, bg)
        shap_values = explainer.shap_values(X_row, nsamples=n_samples)
        expected = float(explainer.expected_value)

    if shap_values.ndim == 2:
        shap_values = shap_values[0]
    shap_values = shap_values.ravel()

    pred = model.predict(X_row)
    if hasattr(pred, "__len__"):
        pred = float(pred[0])
    else:
        pred = float(pred)

    contrib = shap_values.copy()
    abs_contrib = np.abs(contrib)
    idx = np.argsort(abs_contrib)[::-1]

    positive = []
    negative = []
    for i in idx:
        if contrib[i] >= 0:
            positive.append((feature_names[i], float(contrib[i])))
        else:
            negative.append((feature_names[i], float(abs(contrib[i]))))

    return LocalExplanation(
        instance_id=instance_id,
        feature_names=list(feature_names),
        feature_values=X_row[0],
        shap_values=shap_values,
        contribution_scores=contrib,
        top_contributing_features=[feature_names[i] for i in idx],
        positive_factors=positive[:10],
        negative_factors=negative[:10],
        confidence=1.0,
        predicted_value=pred,
        expected_value=expected,
        method="shap",
    )


def _explain_instance_permutation(
    model, X_row, feature_names, instance_id
) -> LocalExplanation:
    pred = float(model.predict(X_row)[0])
    contributions = []
    n_features = X_row.shape[1]
    for col in range(n_features):
        X_perturbed = X_row.copy()
        X_perturbed[0, col] = 0
        pert_pred = float(model.predict(X_perturbed)[0])
        contributions.append(pred - pert_pred)
    contributions = np.array(contributions)

    return LocalExplanation(
        instance_id=instance_id,
        feature_names=list(feature_names),
        feature_values=X_row[0],
        contribution_scores=contributions,
        top_contributing_features=None,
        positive_factors=None,
        negative_factors=None,
        confidence=0.8,
        predicted_value=pred,
        method="permutation",
    )
