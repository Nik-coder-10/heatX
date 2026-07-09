import logging
import numpy as np

logger = logging.getLogger("app.features.spatial")


def compute_latitude(transform, height: int, width: int) -> np.ndarray:
    lat = np.zeros((height, width), dtype=np.float64)
    for row in range(height):
        y = transform[5] + row * transform[4] + 0.5 * transform[4]
        lat[row, :] = y
    return lat


def compute_longitude(transform, height: int, width: int) -> np.ndarray:
    lon = np.zeros((height, width), dtype=np.float64)
    for col in range(width):
        x = transform[2] + col * transform[0] + 0.5 * transform[0]
        lon[:, col] = x
    return lon


def compute_pixel_area(transform, height: int, width: int) -> np.ndarray:
    pixel_width = abs(transform[0])
    pixel_height = abs(transform[4])
    area = pixel_width * pixel_height
    return np.full((height, width), area, dtype=np.float64)


def extract_spatial_features(
    transform,
    height: int,
    width: int,
    compute_lat: bool = True,
    compute_lon: bool = True,
    compute_area: bool = True,
) -> dict[str, np.ndarray]:
    result = {}
    if compute_lat:
        result["latitude"] = compute_latitude(transform, height, width)
    if compute_lon:
        result["longitude"] = compute_longitude(transform, height, width)
    if compute_area:
        result["pixel_area"] = compute_pixel_area(transform, height, width)
    return result
