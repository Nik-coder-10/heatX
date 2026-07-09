import logging
import numpy as np

from .configuration import UHIDetectionConfig

logger = logging.getLogger("app.uhi.classification")

DEFAULT_SEVERITY_CLASSES: list[tuple[str, float, float]] = [
    ("Very Low", 0.0, 1.0),
    ("Low", 1.0, 2.0),
    ("Moderate", 2.0, 3.0),
    ("High", 3.0, 4.0),
    ("Very High", 4.0, 5.0),
    ("Extreme", 5.0, float("inf")),
]

SEVERITY_ORDER = ["Very Low", "Low", "Moderate", "High", "Very High", "Extreme"]


def classify_severity(
    lst_celsius: np.ndarray,
    hotspot_mask: np.ndarray,
    rural_mean: float | None = None,
    config: UHIDetectionConfig | None = None,
) -> tuple[str, float]:
    cfg = config or UHIDetectionConfig.defaults()
    classes = cfg.severity_classes or DEFAULT_SEVERITY_CLASSES

    hot_data = lst_celsius.astype(np.float64)[hotspot_mask > 0]
    valid = np.isfinite(hot_data)
    if not valid.any():
        return "Unknown", 0.0

    mean_lst = float(np.mean(hot_data[valid]))
    if rural_mean is None:
        all_data = lst_celsius.astype(np.float64)[np.isfinite(lst_celsius)]
        rural_mean = float(np.percentile(all_data, 50))

    sigma = float(np.std(lst_celsius[np.isfinite(lst_celsius)]))
    if sigma == 0:
        sigma = 1.0

    severity_score = (mean_lst - rural_mean) / sigma

    for label, low, high in classes:
        if low <= severity_score < high:
            return label, severity_score

    return classes[-1][0], severity_score


def classify_severity_map(
    lst_celsius: np.ndarray,
    rural_mean: float | None = None,
    config: UHIDetectionConfig | None = None,
) -> np.ndarray:
    cfg = config or UHIDetectionConfig.defaults()
    classes = cfg.severity_classes or DEFAULT_SEVERITY_CLASSES

    data = lst_celsius.astype(np.float64)
    valid = np.isfinite(data)
    if not valid.any():
        return np.zeros(data.shape, dtype=np.int32)

    if rural_mean is None:
        rural_mean = float(np.percentile(data[valid], 50))

    sigma = float(np.std(data[valid]))
    if sigma == 0:
        sigma = 1.0

    severity_score = (data - rural_mean) / sigma
    severity_map = np.zeros(data.shape, dtype=np.int32)

    for idx, (_, low, high) in enumerate(classes):
        mask = valid & (severity_score >= low) & (severity_score < high)
        severity_map[mask] = idx

    return severity_map
