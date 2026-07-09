import logging
import time
from typing import Any

import numpy as np

from .exceptions import StatisticsError

logger = logging.getLogger("app.indices.statistics")


def compute_statistics(
    array: np.ndarray,
    nodata: float | None = None,
) -> dict[str, float]:
    flat = array.astype(np.float64).ravel()
    if nodata is not None:
        if np.isnan(nodata):
            valid_mask = ~np.isnan(flat)
        elif np.isinf(nodata):
            valid_mask = ~np.isinf(flat)
        else:
            valid_mask = np.abs(flat - nodata) > 1e-8
    else:
        valid_mask = ~np.isnan(flat) & ~np.isinf(flat)

    valid = flat[valid_mask]
    total = flat.size
    valid_count = int(valid_mask.sum())
    invalid_count = total - valid_count
    invalid_pct = float(invalid_count) / float(total) * 100.0 if total > 0 else 0.0

    if valid_count == 0:
        return {
            "min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0,
            "std": 0.0, "variance": 0.0,
            "pixel_count": 0, "valid_pixel_count": 0,
            "invalid_pixel_count": 0,
            "valid_pct": 0.0, "invalid_pct": 100.0,
            "nodata_value": nodata,
        }

    stats = {
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
        "median": float(np.median(valid)),
        "std": float(valid.std()),
        "variance": float(valid.var()),
        "pixel_count": int(total),
        "valid_pixel_count": int(valid_count),
        "invalid_pixel_count": int(invalid_count),
        "valid_pct": float(valid_count) / float(total) * 100.0,
        "invalid_pct": invalid_pct,
        "nodata_value": nodata,
    }

    return stats


def compute_histogram(
    array: np.ndarray,
    bins: int = 256,
    range_min: float | None = None,
    range_max: float | None = None,
    nodata: float | None = None,
) -> dict[str, Any]:
    flat = array.astype(np.float64).ravel()
    if nodata is not None:
        if np.isnan(nodata):
            valid = flat[~np.isnan(flat)]
        else:
            valid = flat[np.abs(flat - nodata) > 1e-8]
    else:
        valid = flat[~np.isnan(flat) & ~np.isinf(flat)]

    if len(valid) == 0:
        return {"counts": np.zeros(bins, dtype=int).tolist(),
                "bin_edges": np.linspace(-1, 1, bins + 1).tolist(),
                "bins": bins}

    rmin = range_min if range_min is not None else float(valid.min())
    rmax = range_max if range_max is not None else float(valid.max())

    counts, bin_edges = np.histogram(valid, bins=bins, range=(rmin, rmax))
    return {
        "counts": counts.tolist(),
        "bin_edges": bin_edges.tolist(),
        "bins": bins,
        "range": (rmin, rmax),
    }


def compute_percentiles(
    array: np.ndarray,
    percentiles: list[float] | None = None,
    nodata: float | None = None,
) -> dict[float, float]:
    if percentiles is None:
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]

    flat = array.astype(np.float64).ravel()
    if nodata is not None:
        if np.isnan(nodata):
            valid = flat[~np.isnan(flat)]
        else:
            valid = flat[np.abs(flat - nodata) > 1e-8]
    else:
        valid = flat[~np.isnan(flat) & ~np.isinf(flat)]

    result: dict[float, float] = {}
    if len(valid) == 0:
        for p in percentiles:
            result[p] = 0.0
        return result

    computed = np.percentile(valid, percentiles)
    for p, val in zip(percentiles, computed):
        result[p] = float(val)

    return result


def band_statistics(
    band_arrays: dict[str, np.ndarray],
    nodata_values: dict[str, float | None] | None = None,
) -> dict[str, dict[str, float]]:
    nodata_values = nodata_values or {}
    result: dict[str, dict[str, float]] = {}
    for name, array in band_arrays.items():
        nd = nodata_values.get(name)
        result[name] = compute_statistics(array, nd)
    return result
