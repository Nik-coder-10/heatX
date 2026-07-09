import logging
import numpy as np

logger = logging.getLogger("app.features.terrain")


def compute_slope(elevation: np.ndarray, resolution: float = 30.0) -> np.ndarray:
    elev = elevation.astype(np.float64)
    dy, dx = np.gradient(elev, resolution)
    slope = np.degrees(np.arctan(np.sqrt(dx ** 2 + dy ** 2)))
    return np.clip(slope, 0.0, 90.0).astype(np.float32)


def compute_aspect(elevation: np.ndarray, resolution: float = 30.0) -> np.ndarray:
    elev = elevation.astype(np.float64)
    dy, dx = np.gradient(elev, resolution)
    aspect = np.degrees(np.arctan2(-dx, dy))
    aspect = np.where(aspect < 0, aspect + 360, aspect)
    return np.clip(aspect, 0.0, 360.0).astype(np.float32)


def extract_terrain_features(
    elevation: np.ndarray | None = None,
    resolution: float = 30.0,
    compute_slope_feature: bool = True,
    compute_aspect_feature: bool = True,
) -> dict[str, np.ndarray]:
    result = {}
    if elevation is not None:
        result["elevation"] = elevation.astype(np.float32)
        if compute_slope_feature:
            result["slope"] = compute_slope(elevation, resolution)
        if compute_aspect_feature:
            result["aspect"] = compute_aspect(elevation, resolution)
    return result
