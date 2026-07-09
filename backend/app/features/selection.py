import logging
import numpy as np

from .registry import get, list_feature_names

logger = logging.getLogger("app.features.selection")


def variance_threshold(
    features: dict[str, np.ndarray],
    threshold: float = 0.01,
    feature_names: list[str] | None = None,
) -> list[str]:
    names = feature_names or list(features.keys())
    selected = []
    for name in names:
        arr = features.get(name)
        if arr is None:
            continue
        flat = arr.ravel()
        if np.issubdtype(arr.dtype, np.floating):
            valid = flat[np.isfinite(flat)]
            if len(valid) > 0 and np.var(valid) > threshold:
                selected.append(name)
        else:
            if np.var(flat.astype(np.float64)) > threshold:
                selected.append(name)
    return selected


def correlation_filter(
    features: dict[str, np.ndarray],
    threshold: float = 0.85,
    feature_names: list[str] | None = None,
) -> list[str]:
    names = feature_names or list(features.keys())
    if len(names) < 2:
        return names[:]

    data = []
    valid_names = []
    for name in names:
        arr = features.get(name)
        if arr is not None:
            data.append(arr.ravel().astype(np.float64))
            valid_names.append(name)

    if len(data) < 2:
        return valid_names

    n = len(data)
    keep = [True] * n
    for i in range(n):
        if not keep[i]:
            continue
        for j in range(i + 1, n):
            if not keep[j]:
                continue
            mask = np.isfinite(data[i]) & np.isfinite(data[j])
            if mask.sum() < 3:
                continue
            c = abs(np.corrcoef(data[i][mask], data[j][mask])[0, 1])
            if c > threshold:
                keep[j] = False

    return [valid_names[i] for i in range(n) if keep[i]]


def select_features(
    features: dict[str, np.ndarray],
    methods: list[str] | None = None,
    feature_names: list[str] | None = None,
    variance_threshold_val: float = 0.01,
    correlation_threshold: float = 0.85,
) -> dict[str, list[str]]:
    methods = methods or ["variance", "correlation"]
    names = feature_names or list(features.keys())
    result = {}

    if "variance" in methods:
        result["variance"] = variance_threshold(features, variance_threshold_val, names)

    if "correlation" in methods:
        filtered = result.get("variance", names)
        result["correlation"] = correlation_filter(features, correlation_threshold, filtered)

    return result
