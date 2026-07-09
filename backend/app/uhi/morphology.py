import logging
import numpy as np
from scipy import ndimage

from .configuration import UHIDetectionConfig

logger = logging.getLogger("app.uhi.morphology")


def morphological_open(binary: np.ndarray, pixels: int = 2) -> np.ndarray:
    struct = ndimage.generate_binary_structure(2, 2)
    struct = ndimage.iterate_structure(struct, pixels)
    return ndimage.binary_opening(binary, structure=struct).astype(np.uint8)


def morphological_close(binary: np.ndarray, pixels: int = 3) -> np.ndarray:
    struct = ndimage.generate_binary_structure(2, 2)
    struct = ndimage.iterate_structure(struct, pixels)
    return ndimage.binary_closing(binary, structure=struct).astype(np.uint8)


def fill_holes(binary: np.ndarray) -> np.ndarray:
    if binary.sum() == 0:
        return np.zeros_like(binary)
    return ndimage.binary_fill_holes(binary).astype(np.uint8)


def remove_small_objects(binary: np.ndarray, min_size_pixels: int = 10) -> np.ndarray:
    labeled, n = ndimage.label(binary)
    if n == 0:
        return np.zeros_like(binary)
    sizes = np.bincount(labeled.ravel())
    mask_sizes = np.ones(len(sizes), dtype=bool)
    for i in range(1, len(sizes)):
        mask_sizes[i] = sizes[i] >= min_size_pixels
    mask_sizes[0] = True
    return mask_sizes[labeled].astype(np.uint8)


def smooth_boundary(binary: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    if binary.sum() == 0:
        return np.zeros_like(binary)
    from scipy.ndimage import gaussian_filter
    smoothed = gaussian_filter(binary.astype(np.float64), sigma=sigma)
    return (smoothed > 0.5).astype(np.uint8)


def apply_morphology(
    binary: np.ndarray,
    config: UHIDetectionConfig | None = None,
) -> np.ndarray:
    cfg = config or UHIDetectionConfig.defaults()
    result = binary.copy()
    if cfg.morphology_opening_pixels > 0:
        result = morphological_open(result, cfg.morphology_opening_pixels)
    if cfg.morphology_closing_pixels > 0:
        result = morphological_close(result, cfg.morphology_closing_pixels)
    if cfg.fill_holes:
        result = fill_holes(result)
    if cfg.remove_small_objects:
        min_px = max(1, int(cfg.min_hotspot_area_m2 / (cfg.resolution ** 2)))
        result = remove_small_objects(result, min_px)
    if cfg.smooth_boundary:
        result = smooth_boundary(result, cfg.smooth_sigma)
    return result
