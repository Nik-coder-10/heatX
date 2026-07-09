import logging
import numpy as np

logger = logging.getLogger("app.lst.statistics")


def compute_lst_statistics(
    lst: np.ndarray,
    quality_mask: np.ndarray | None = None,
    nodata_value: float | None = None,
    urban_hotspot_percentile: float = 90.0,
) -> dict:
    data = lst.astype(np.float64).copy()

    valid_mask = np.isfinite(data)
    if nodata_value is not None:
        valid_mask &= (data != nodata_value)

    if quality_mask is not None:
        invalid_qa = (
            (quality_mask & 1) | (quality_mask & 4) | (quality_mask & 16)
        ) > 0
        valid_mask &= ~invalid_qa

    valid_data = data[valid_mask]

    if valid_data.size == 0:
        return {
            "mean": 0.0, "median": 0.0, "std": 0.0,
            "min": 0.0, "max": 0.0, "valid_pixels": 0,
            "total_pixels": int(data.size),
            "percent_valid": 0.0,
        }

    sorted_data = np.sort(valid_data)
    cumulative = np.cumsum(sorted_data)
    total = cumulative[-1]

    n = valid_data.size
    result = {
        "mean": float(np.mean(valid_data)),
        "median": float(np.median(valid_data)),
        "std": float(np.std(valid_data)),
        "min": float(np.min(valid_data)),
        "max": float(np.max(valid_data)),
        "p5": float(np.percentile(valid_data, 5)),
        "p10": float(np.percentile(valid_data, 10)),
        "p25": float(np.percentile(valid_data, 25)),
        "p50": float(np.percentile(valid_data, 50)),
        "p75": float(np.percentile(valid_data, 75)),
        "p90": float(np.percentile(valid_data, 90)),
        "p95": float(np.percentile(valid_data, 95)),
        "valid_pixels": int(n),
        "total_pixels": int(data.size),
        "percent_valid": round(n / data.size * 100, 2),
        "urban_hotspot_threshold": float(np.percentile(valid_data, urban_hotspot_percentile)),
    }

    result["histogram"] = {
        "counts": np.histogram(valid_data, bins=20)[0].tolist(),
        "edges": np.histogram(valid_data, bins=20)[1].tolist(),
    }

    return result
