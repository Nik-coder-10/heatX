import logging
from dataclasses import dataclass, field

import numpy as np
from scipy import stats as sp_stats

from .exceptions import UncertaintyError

logger = logging.getLogger("app.xai.uncertainty")


@dataclass
class UncertaintyMetrics:
    model_uncertainty: float
    input_uncertainty: float
    feature_uncertainty: float
    measurement_uncertainty: float
    confidence_interval: tuple[float, float]
    overall_uncertainty: float
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "model_uncertainty": round(self.model_uncertainty, 4),
            "input_uncertainty": round(self.input_uncertainty, 4),
            "feature_uncertainty": round(self.feature_uncertainty, 4),
            "measurement_uncertainty": round(self.measurement_uncertainty, 4),
            "confidence_interval": [round(self.confidence_interval[0], 4), round(self.confidence_interval[1], 4)],
            "overall_uncertainty": round(self.overall_uncertainty, 4),
        }


def compute_model_uncertainty(
    model,
    X: np.ndarray,
    n_bootstrap: int = 20,
    random_state: int = 42,
) -> float:
    if hasattr(model, "estimators_"):
        predictions = []
        for est in model.estimators_:
            try:
                pred = est.predict(X)
                predictions.append(pred)
            except Exception:
                continue
        if len(predictions) > 1:
            stds = np.std(predictions, axis=0)
            return float(np.mean(stds) / (np.mean(np.abs(np.mean(predictions, axis=0))) + 1e-10))
    try:
        rng = np.random.RandomState(random_state)
        n = X.shape[0]
        preds = []
        for _ in range(min(n_bootstrap, 50)):
            idx = rng.choice(n, n, replace=True)
            try:
                preds.append(model.predict(X[idx]))
            except Exception:
                continue
        if len(preds) > 1:
            stds = np.std(preds, axis=0)
            return float(np.mean(stds) / (np.mean(np.abs(np.mean(preds, axis=0))) + 1e-10))
    except Exception:
        pass
    return 0.15


def compute_input_uncertainty(X: np.ndarray) -> float:
    if X.size == 0:
        return 1.0
    nan_frac = float(np.isnan(X).mean())
    inf_frac = float(np.isinf(X).mean())
    zero_var = 0.0
    for col in range(X.shape[1]):
        col_data = X[:, col]
        valid = col_data[np.isfinite(col_data)]
        if len(valid) > 1 and np.std(valid) < 1e-10:
            zero_var += 1.0
    zero_var_frac = zero_var / max(1, X.shape[1])
    return float(min(1.0, nan_frac + inf_frac + zero_var_frac * 0.5))


def compute_feature_uncertainty(
    X: np.ndarray,
    feature_names: list[str] | None = None,
) -> float:
    if X.size == 0:
        return 1.0
    uncertainties = []
    for col in range(X.shape[1]):
        col_data = X[:, col]
        valid = col_data[np.isfinite(col_data)]
        if len(valid) < 2:
            uncertainties.append(1.0)
            continue
        cv = float(np.std(valid) / (np.abs(np.mean(valid)) + 1e-10))
        uncertainties.append(min(1.0, cv))
    return float(np.mean(uncertainties)) if uncertainties else 0.5


def compute_measurement_uncertainty(
    quality_flags: np.ndarray | None = None,
    sensor_accuracy: float = 0.02,
) -> float:
    if quality_flags is not None and quality_flags.size > 0:
        qa_degradation = 1.0 - float(quality_flags.mean())
        return float(min(1.0, sensor_accuracy + qa_degradation * 0.5))
    return float(sensor_accuracy)


def compute_confidence_interval(
    model,
    X_row: np.ndarray,
    alpha: float = 0.05,
    n_samples: int = 100,
) -> tuple[float, float]:
    if hasattr(model, "estimators_"):
        predictions = []
        for est in model.estimators_:
            try:
                pred = float(est.predict(X_row)[0])
                predictions.append(pred)
            except Exception:
                continue
        if len(predictions) >= 3:
            mean = np.mean(predictions)
            se = np.std(predictions) / np.sqrt(len(predictions))
            t_val = sp_stats.t.ppf(1 - alpha / 2, len(predictions) - 1)
            margin = t_val * se
            return (float(mean - margin), float(mean + margin))

    try:
        rng = np.random.RandomState(42)
        preds = []
        for _ in range(min(n_samples, 500)):
            noise = rng.normal(0, 0.01, X_row.shape)
            try:
                p = float(model.predict(X_row + noise)[0])
                preds.append(p)
            except Exception:
                continue
        if len(preds) >= 3:
            mean = np.mean(preds)
            se = np.std(preds) / np.sqrt(len(preds))
            t_val = sp_stats.t.ppf(1 - alpha / 2, len(preds) - 1)
            margin = t_val * se
            return (float(mean - margin), float(mean + margin))
    except Exception:
        pass

    pred = float(model.predict(X_row)[0])
    return (pred - 0.1 * abs(pred), pred + 0.1 * abs(pred))


def compute_uncertainty(
    model,
    X: np.ndarray,
    X_row: np.ndarray | None = None,
    feature_names: list[str] | None = None,
    quality_flags: np.ndarray | None = None,
    alpha: float = 0.05,
) -> UncertaintyMetrics:
    if X_row is None:
        X_row = X[:1]

    model_unc = compute_model_uncertainty(model, X)
    input_unc = compute_input_uncertainty(X)
    feat_unc = compute_feature_uncertainty(X, feature_names)
    meas_unc = compute_measurement_uncertainty(quality_flags)

    ci = compute_confidence_interval(model, X_row, alpha)

    overall = model_unc * 0.3 + input_unc * 0.2 + feat_unc * 0.2 + meas_unc * 0.3

    return UncertaintyMetrics(
        model_uncertainty=model_unc,
        input_uncertainty=input_unc,
        feature_uncertainty=feat_unc,
        measurement_uncertainty=meas_unc,
        confidence_interval=ci,
        overall_uncertainty=overall,
    )
