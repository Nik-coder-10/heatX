import logging
import numpy as np
from scipy import ndimage

logger = logging.getLogger("app.uhi.spatial_analysis")


def compute_compactness(area_sq_km: float, perimeter_km: float) -> float:
    if perimeter_km == 0:
        return 0.0
    return 4.0 * np.pi * area_sq_km / (perimeter_km ** 2)


def compute_elongation(mask: np.ndarray, resolution: float = 30.0) -> float:
    ys, xs = np.where(mask > 0)
    if len(ys) < 3:
        return 0.0
    coords = np.column_stack([xs, ys]) * resolution
    cov = np.cov(coords.T)
    if np.isnan(cov).any() or np.isinf(cov).any():
        return 0.0
    try:
        eigvals = np.linalg.eigvalsh(cov)
        eigvals = eigvals[eigvals > 0]
        if len(eigvals) < 2:
            return 0.0
        return float(np.sqrt(eigvals[1] / max(eigvals[0], 1e-10)))
    except Exception:
        return 0.0


def compute_nearest_neighbor_distance(
    centroids: list[tuple[float, float]],
    idx: int,
) -> float | None:
    if len(centroids) < 2:
        return None
    cx, cy = centroids[idx]
    min_dist = float("inf")
    for j, (ox, oy) in enumerate(centroids):
        if j == idx:
            continue
        d = np.sqrt((cx - ox) ** 2 + (cy - oy) ** 2)
        min_dist = min(min_dist, d)
    return min_dist if min_dist < float("inf") else None
