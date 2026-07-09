import logging
import numpy as np

from .registry import get, list_feature_names
from .exceptions import MissingDependencyError

logger = logging.getLogger("app.features.urban")


def compute_urban_morphology_features(
    ndbi: np.ndarray | None = None,
    ndvi: np.ndarray | None = None,
    lst_kelvin: np.ndarray | None = None,
    window: int = 5,
) -> dict[str, np.ndarray]:
    result = {}
    if ndbi is not None and ndvi is not None:
        ndvi_urban = np.where(ndbi > 0.1, ndvi, np.nan)
        result["urban_vegetation_contrast"] = np.nan_to_num(
            ndbi.astype(np.float32) - ndvi_urban.astype(np.float32), nan=0.0
        )
    if lst_kelvin is not None and ndbi is not None:
        lst_urban = np.where(ndbi > 0.1, lst_kelvin, np.nan)
        lst_rural = np.where(ndbi <= 0.1, lst_kelvin, np.nan)
        rural_mean = np.nanmean(lst_rural)
        result["uhi_intensity"] = np.where(
            ndbi > 0.1, (lst_kelvin - rural_mean).astype(np.float32), 0.0
        )
    if ndbi is not None:
        from scipy.ndimage import uniform_filter
        result["urban_density_local"] = uniform_filter(
            (ndbi > 0.1).astype(np.float64), size=window
        ).astype(np.float32)
    return result
