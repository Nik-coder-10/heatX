import logging
from dataclasses import dataclass, field

import numpy as np

from .metrics import (
    MetricsResult,
    compute_regression_metrics,
    compute_classification_metrics,
    compute_calibration_error,
)

logger = logging.getLogger("app.ml.evaluation")


@dataclass
class EvaluationResult:
    train_metrics: MetricsResult | None = None
    test_metrics: MetricsResult | None = None
    cv_scores: list[float] | None = None
    cv_mean: float = 0.0
    cv_std: float = 0.0
    feature_importance: dict[str, float] | None = None
    n_train: int = 0
    n_test: int = 0
    additional: dict | None = None

    def summary(self) -> dict:
        s: dict = {}
        if self.train_metrics:
            s["train"] = self.train_metrics.to_dict()
        if self.test_metrics:
            s["test"] = self.test_metrics.to_dict()
        s["cv_mean"] = round(self.cv_mean, 4)
        s["cv_std"] = round(self.cv_std, 4)
        s["n_train"] = self.n_train
        s["n_test"] = self.n_test
        if self.feature_importance:
            top = sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            s["top_features"] = top
        return s


def evaluate_regression(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> EvaluationResult:
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    train_metrics = compute_regression_metrics(y_train, train_pred)
    test_metrics = compute_regression_metrics(y_test, test_pred)

    fi = _extract_feature_importance(model, feature_names)

    return EvaluationResult(
        train_metrics=train_metrics,
        test_metrics=test_metrics,
        n_train=len(y_train),
        n_test=len(y_test),
        feature_importance=fi,
    )


def evaluate_classification(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> EvaluationResult:
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    train_prob = _predict_proba_safe(model, X_train)
    test_prob = _predict_proba_safe(model, X_test)

    train_metrics = compute_classification_metrics(y_train, train_pred, train_prob)
    test_metrics = compute_classification_metrics(y_test, test_pred, test_prob)

    if test_prob is not None and len(np.unique(y_test)) >= 2:
        cal_error = compute_calibration_error(y_test, test_prob)
        test_metrics.calibration_error = cal_error

    fi = _extract_feature_importance(model, feature_names)

    return EvaluationResult(
        train_metrics=train_metrics,
        test_metrics=test_metrics,
        n_train=len(y_train),
        n_test=len(y_test),
        feature_importance=fi,
    )


def _extract_feature_importance(model, feature_names: list[str] | None) -> dict[str, float] | None:
    if feature_names is None:
        return None
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
        if importances is not None and len(importances) == len(feature_names):
            return dict(zip(feature_names, importances.tolist()))
    if hasattr(model, "coef_"):
        coef = model.coef_
        if coef is not None and len(coef) == len(feature_names):
            return dict(zip(feature_names, np.abs(coef).tolist()))
    return None


def _predict_proba_safe(model, X):
    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X)
            if proba.shape[1] >= 2:
                return proba[:, 1]
        except Exception:
            pass
    return None
