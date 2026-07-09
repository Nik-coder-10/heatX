import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger("app.ml.drift_detection")


@dataclass
class DriftReport:
    input_drift: float
    feature_drift: list[dict]
    prediction_drift: float
    concept_drift: float
    overall_drift: float
    alert_triggered: bool
    timestamp: str = ""
    details: dict | None = None

    def summary(self) -> dict:
        return {
            "overall_drift": round(self.overall_drift, 4),
            "alert_triggered": self.alert_triggered,
            "input_drift": round(self.input_drift, 4),
            "prediction_drift": round(self.prediction_drift, 4),
            "concept_drift": round(self.concept_drift, 4),
            "n_features_drifting": len([f for f in self.feature_drift if f.get("drift_score", 0) > 0.05]),
        }


def detect_input_drift(
    X_reference: np.ndarray,
    X_current: np.ndarray,
    threshold: float = 0.05,
) -> float:
    if X_reference.shape[1] != X_current.shape[1]:
        logger.warning("Feature dimension mismatch in drift detection")
        return 1.0

    drift_scores = []
    for col in range(X_reference.shape[1]):
        ref = X_reference[:, col]
        cur = X_current[:, col]
        ref_valid = ref[np.isfinite(ref)]
        cur_valid = cur[np.isfinite(cur)]
        if len(ref_valid) < 2 or len(cur_valid) < 2:
            continue
        from scipy import stats
        stat, pval = stats.ks_2samp(ref_valid, cur_valid)
        drift_scores.append(float(pval))

    return (1.0 - np.mean(drift_scores)) if drift_scores else 0.0


def detect_feature_drift(
    X_reference: np.ndarray,
    X_current: np.ndarray,
    feature_names: list[str] | None = None,
    threshold: float = 0.05,
) -> list[dict]:
    if feature_names is None:
        feature_names = [f"f{i}" for i in range(X_reference.shape[1])]

    results = []
    from scipy import stats
    for col in range(min(X_reference.shape[1], X_current.shape[1])):
        ref = X_reference[:, col]
        cur = X_current[:, col]
        ref_valid = ref[np.isfinite(ref)]
        cur_valid = cur[np.isfinite(cur)]
        if len(ref_valid) < 2 or len(cur_valid) < 2:
            continue
        stat, pval = stats.ks_2samp(ref_valid, cur_valid)
        drift_score = 1.0 - float(pval)
        results.append({
            "feature": feature_names[col] if col < len(feature_names) else f"f{col}",
            "drift_score": drift_score,
            "p_value": float(pval),
            "drifting": drift_score > threshold,
            "ref_mean": float(np.mean(ref_valid)),
            "cur_mean": float(np.mean(cur_valid)),
        })

    return results


def detect_prediction_drift(
    pred_reference: np.ndarray,
    pred_current: np.ndarray,
    threshold: float = 0.05,
) -> float:
    from scipy import stats
    ref = pred_reference[np.isfinite(pred_reference)]
    cur = pred_current[np.isfinite(pred_current)]
    if len(ref) < 2 or len(cur) < 2:
        return 0.0
    stat, pval = stats.ks_2samp(ref, cur)
    return 1.0 - float(pval)


def detect_concept_drift(
    y_true_reference: np.ndarray,
    y_pred_reference: np.ndarray,
    y_true_current: np.ndarray,
    y_pred_current: np.ndarray,
    threshold: float = 0.1,
) -> float:
    ref_errors = np.abs(y_true_reference.ravel() - y_pred_reference.ravel())
    cur_errors = np.abs(y_true_current.ravel() - y_pred_current.ravel())

    ref_valid = ref_errors[np.isfinite(ref_errors)]
    cur_valid = cur_errors[np.isfinite(cur_errors)]

    if len(ref_valid) < 2 or len(cur_valid) < 2:
        return 0.0

    from scipy import stats
    stat, pval = stats.ks_2samp(ref_valid, cur_valid)
    drift = 1.0 - float(pval)

    ref_mean_error = float(np.mean(ref_valid))
    cur_mean_error = float(np.mean(cur_valid))
    if cur_mean_error > ref_mean_error * 1.5:
        drift = min(1.0, drift + 0.3)

    return drift


def generate_drift_report(
    X_reference: np.ndarray,
    X_current: np.ndarray,
    pred_reference: np.ndarray,
    pred_current: np.ndarray,
    y_true_reference: np.ndarray,
    y_pred_reference: np.ndarray,
    y_true_current: np.ndarray,
    y_pred_current: np.ndarray,
    feature_names: list[str] | None = None,
    alert_threshold: float = 0.05,
) -> DriftReport:
    input_drift = detect_input_drift(X_reference, X_current)
    feature_drift = detect_feature_drift(X_reference, X_current, feature_names)
    prediction_drift = detect_prediction_drift(pred_reference, pred_current)
    concept_drift = detect_concept_drift(
        y_true_reference, y_pred_reference,
        y_true_current, y_pred_current,
    )

    overall_drift = input_drift * 0.2 + prediction_drift * 0.3 + concept_drift * 0.3
    feature_drift_score = np.mean([f["drift_score"] for f in feature_drift]) if feature_drift else 0
    overall_drift += feature_drift_score * 0.2

    alert_triggered = (
        input_drift > alert_threshold
        or prediction_drift > alert_threshold
        or concept_drift > alert_threshold
        or overall_drift > alert_threshold
    )

    return DriftReport(
        input_drift=input_drift,
        feature_drift=feature_drift,
        prediction_drift=prediction_drift,
        concept_drift=concept_drift,
        overall_drift=float(overall_drift),
        alert_triggered=alert_triggered,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
