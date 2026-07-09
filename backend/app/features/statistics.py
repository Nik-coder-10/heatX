import logging
import numpy as np

from .registry import get, list_feature_names

logger = logging.getLogger("app.features.statistics")


def compute_feature_statistics(
    features: dict[str, np.ndarray],
    feature_names: list[str] | None = None,
) -> dict:
    names = feature_names or list(features.keys())
    stats = {}
    for name in names:
        arr = features.get(name)
        if arr is None:
            continue
        flat = arr.ravel()
        stat = {}
        if np.issubdtype(arr.dtype, np.floating):
            valid = flat[np.isfinite(flat)]
            if len(valid) > 0:
                stat["mean"] = float(np.mean(valid))
                stat["std"] = float(np.std(valid))
                stat["min"] = float(np.min(valid))
                stat["max"] = float(np.max(valid))
                stat["p5"] = float(np.percentile(valid, 5))
                stat["p25"] = float(np.percentile(valid, 25))
                stat["p50"] = float(np.median(valid))
                stat["p75"] = float(np.percentile(valid, 75))
                stat["p95"] = float(np.percentile(valid, 95))
                stat["missing"] = int(arr.size - len(valid))
            else:
                stat["mean"] = 0.0
                stat["missing"] = int(arr.size)
        else:
            stat["mean"] = float(np.mean(flat))
            stat["std"] = float(np.std(flat))
            stat["min"] = float(np.min(flat))
            stat["max"] = float(np.max(flat))
            stat["missing"] = 0

        stats[name] = stat

    return stats


def compute_correlation_matrix(
    features: dict[str, np.ndarray],
    feature_names: list[str] | None = None,
) -> dict:
    names = feature_names or list(features.keys())
    n = len(names)
    if n == 0:
        return {"features": [], "matrix": []}

    data = []
    valid_names = []
    for name in names:
        arr = features.get(name)
        if arr is not None:
            flat = arr.ravel().astype(np.float64)
            mask = np.isfinite(flat)
            if mask.sum() > 0:
                data.append(flat)
                valid_names.append(name)

    if len(data) < 2:
        return {"features": valid_names, "matrix": [[1.0]]}

    mat = np.zeros((len(data), len(data)), dtype=np.float64)
    for i in range(len(data)):
        mat[i, i] = 1.0
        for j in range(i + 1, len(data)):
            mask = np.isfinite(data[i]) & np.isfinite(data[j])
            if mask.sum() > 2:
                c = np.corrcoef(data[i][mask], data[j][mask])[0, 1]
            else:
                c = 0.0
            mat[i, j] = c
            mat[j, i] = c

    return {"features": valid_names, "matrix": mat.tolist()}


def detect_outliers(
    features: dict[str, np.ndarray],
    feature_names: list[str] | None = None,
    n_std: float = 3.0,
) -> dict:
    names = feature_names or list(features.keys())
    outliers = {}
    for name in names:
        arr = features.get(name)
        if arr is None or not np.issubdtype(arr.dtype, np.floating):
            continue
        flat = arr.ravel()
        valid = flat[np.isfinite(flat)]
        if len(valid) == 0:
            continue
        mean = np.mean(valid)
        std = np.std(valid)
        if std == 0:
            continue
        z = np.abs((flat - mean) / std)
        outliers[name] = int(np.sum(z > n_std))
    return outliers
