import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("app.ml.metrics")


@dataclass
class MetricsResult:
    mae: float = 0.0
    rmse: float = 0.0
    r2: float = 0.0
    mape: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    roc_auc: float = 0.0
    pr_auc: float = 0.0
    accuracy: float = 0.0
    calibration_error: float = 0.0
    n_samples: int = 0
    additional: dict | None = None

    def to_dict(self) -> dict:
        d = {
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "r2": round(self.r2, 4),
            "mape": round(self.mape, 4),
            "n_samples": self.n_samples,
        }
        if self.additional:
            d.update(self.additional)
        return d

    def classification_report(self) -> dict:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "roc_auc": round(self.roc_auc, 4),
            "pr_auc": round(self.pr_auc, 4),
            "accuracy": round(self.accuracy, 4),
        }


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> MetricsResult:
    y_true = y_true.ravel().astype(np.float64)
    y_pred = y_pred.ravel().astype(np.float64)
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    if not valid.any():
        return MetricsResult(n_samples=0)

    y_t, y_p = y_true[valid], y_pred[valid]
    n = len(y_t)
    errors = y_t - y_p
    abs_errors = np.abs(errors)
    sq_errors = errors ** 2

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(sq_errors)))
    ss_res = float(np.sum(sq_errors))
    ss_tot = float(np.sum((y_t - np.mean(y_t)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0

    nonzero = np.abs(y_t) > 1e-10
    mape = float(np.mean(np.abs(errors[nonzero] / y_t[nonzero]))) * 100 if nonzero.any() else 0.0

    return MetricsResult(
        mae=mae, rmse=rmse, r2=r2, mape=mape, n_samples=n,
    )


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
) -> MetricsResult:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, average_precision_score,
    )

    y_true = y_true.ravel()
    y_pred = y_pred.ravel()

    accuracy = float(accuracy_score(y_true, y_pred))

    if len(np.unique(y_true)) >= 2:
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
    else:
        precision = recall = f1 = 0.0

    roc_auc = 0.0
    pr_auc = 0.0
    if y_prob is not None and len(np.unique(y_true)) >= 2:
        y_prob = y_prob.ravel()
        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            pass
        try:
            pr_auc = float(average_precision_score(y_true, y_prob))
        except Exception:
            pass

    return MetricsResult(
        accuracy=accuracy, precision=precision, recall=recall, f1=f1,
        roc_auc=roc_auc, pr_auc=pr_auc, n_samples=len(y_true),
    )


def compute_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    y_true = y_true.ravel()
    y_prob = y_prob.ravel()
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_prob, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    error = 0.0
    for i in range(n_bins):
        mask = bin_indices == i
        if mask.sum() == 0:
            continue
        avg_prob = float(y_prob[mask].mean())
        pos_rate = float(y_true[mask].mean())
        error += abs(avg_prob - pos_rate) * mask.sum()

    return error / len(y_true)
