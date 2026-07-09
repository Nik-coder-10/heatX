import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import ExplainabilityError
from .feature_importance import (
    FeatureImportanceResult,
    compute_shap_importance,
    compute_permutation_importance,
    compute_importance,
)

logger = logging.getLogger("app.xai.global_explanation")


@dataclass
class GlobalExplanation:
    feature_importance: FeatureImportanceResult
    n_instances: int = 0
    correlation_matrix: np.ndarray | None = None
    interaction_matrix: np.ndarray | None = None
    feature_names: list[str] | None = None
    shap_summary: dict | None = None
    metadata: dict | None = None

    def __post_init__(self):
        if self.feature_names is None:
            self.feature_names = self.feature_importance.feature_names

    def top_features(self, n: int = 10) -> list[tuple[str, float]]:
        return self.feature_importance.top_features(n)

    def to_dict(self) -> dict:
        return {
            "feature_importance": self.feature_importance.to_dict(),
            "n_instances": self.n_instances,
            "correlation_matrix": self.correlation_matrix.tolist() if self.correlation_matrix is not None else None,
            "interaction_matrix": self.interaction_matrix.tolist() if self.interaction_matrix is not None else None,
            "feature_names": self.feature_names,
        }


def compute_global_explanation(
    model,
    X: np.ndarray,
    y: np.ndarray | None = None,
    feature_names: list[str] | None = None,
    method: str = "shap",
    compute_correlations: bool = True,
    compute_interactions: bool = False,
    **kwargs,
) -> GlobalExplanation:
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

    fi = compute_importance(
        model=model, X=X, y=y, feature_names=feature_names, method=method, **kwargs
    )

    corr_matrix = None
    if compute_correlations and X.shape[1] > 1:
        corr_matrix = np.corrcoef(X.T)

    interaction_matrix = None
    if compute_interactions and hasattr(model, "feature_importances_"):
        try:
            interaction_matrix = np.zeros((X.shape[1], X.shape[1]))
            fi_vals = fi.importance_values
            for i in range(X.shape[1]):
                for j in range(X.shape[1]):
                    interaction_matrix[i, j] = fi_vals[i] * fi_vals[j] / 100.0
        except Exception:
            pass

    result = GlobalExplanation(
        feature_importance=fi,
        n_instances=X.shape[0],
        correlation_matrix=corr_matrix,
        interaction_matrix=interaction_matrix,
        feature_names=list(feature_names),
        metadata={"method": method, "n_features": X.shape[1]},
    )

    return result
