import logging
from typing import Any

import numpy as np

from .exceptions import BandMathError

logger = logging.getLogger("app.preprocessing.band_math")


_BAND_MAP = {
    "red": "red",
    "green": "green",
    "blue": "blue",
    "nir": "nir",
    "swir1": "swir1",
    "swir2": "swir2",
}


def resolve_band(
    bands: dict[str, np.ndarray],
    key: str,
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    if key in bands:
        return bands[key]
    if alias_map and key in alias_map:
        alias = alias_map[key]
        if alias in bands:
            return bands[alias]
    raise BandMathError(
        f"Required band '{key}' not found. Available: {list(bands.keys())}"
    )


def ndvi(
    bands: dict[str, np.ndarray],
    nir_key: str = "nir",
    red_key: str = "red",
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    nir = resolve_band(bands, nir_key, alias_map)
    red = resolve_band(bands, red_key, alias_map)
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    denominator = nir + red
    mask = np.abs(denominator) < 1e-15
    result = np.divide(
        nir - red, denominator, out=np.zeros_like(denominator), where=~mask
    )
    result = np.clip(result, -1.0, 1.0)
    return result


def ndbi(
    bands: dict[str, np.ndarray],
    swir1_key: str = "swir1",
    nir_key: str = "nir",
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    swir1 = resolve_band(bands, swir1_key, alias_map)
    nir = resolve_band(bands, nir_key, alias_map)
    swir1 = swir1.astype(np.float64)
    nir = nir.astype(np.float64)
    denominator = swir1 + nir
    mask = np.abs(denominator) < 1e-15
    result = np.divide(
        swir1 - nir, denominator, out=np.zeros_like(denominator), where=~mask
    )
    result = np.clip(result, -1.0, 1.0)
    return result


def ndwi(
    bands: dict[str, np.ndarray],
    green_key: str = "green",
    nir_key: str = "nir",
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    green = resolve_band(bands, green_key, alias_map)
    nir = resolve_band(bands, nir_key, alias_map)
    green = green.astype(np.float64)
    nir = nir.astype(np.float64)
    denominator = green + nir
    mask = np.abs(denominator) < 1e-15
    result = np.divide(
        green - nir, denominator, out=np.zeros_like(denominator), where=~mask
    )
    result = np.clip(result, -1.0, 1.0)
    return result


def savi(
    bands: dict[str, np.ndarray],
    nir_key: str = "nir",
    red_key: str = "red",
    L: float = 0.5,
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    nir = resolve_band(bands, nir_key, alias_map)
    red = resolve_band(bands, red_key, alias_map)
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    denominator = nir + red + L
    mask = np.abs(denominator) < 1e-15
    result = np.divide(
        nir - red,
        denominator,
        out=np.zeros_like(denominator),
        where=~mask,
    )
    result *= 1.0 + L
    result = np.clip(result, -1.0, 1.0)
    return result


def evi(
    bands: dict[str, np.ndarray],
    nir_key: str = "nir",
    red_key: str = "red",
    blue_key: str = "blue",
    alias_map: dict[str, str] | None = None,
) -> np.ndarray:
    nir = resolve_band(bands, nir_key, alias_map)
    red = resolve_band(bands, red_key, alias_map)
    blue = resolve_band(bands, blue_key, alias_map)
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    blue = blue.astype(np.float64)
    denominator = nir + 6.0 * red - 7.5 * blue + 1.0
    mask = np.abs(denominator) < 1e-15
    result = np.divide(
        nir - red,
        denominator,
        out=np.zeros_like(denominator),
        where=~mask,
    )
    result *= 2.5
    result = np.clip(result, -1.0, 1.0)
    return result


def compute_indices(
    bands: dict[str, np.ndarray],
    indices: list[str],
    alias_map: dict[str, str] | None = None,
) -> dict[str, np.ndarray]:
    results: dict[str, np.ndarray] = {}
    for idx_name in indices:
        name_lower = idx_name.lower()
        if name_lower == "ndvi":
            results[idx_name] = ndvi(bands, alias_map=alias_map)
        elif name_lower == "ndbi":
            results[idx_name] = ndbi(bands, alias_map=alias_map)
        elif name_lower == "ndwi":
            results[idx_name] = ndwi(bands, alias_map=alias_map)
        elif name_lower == "savi":
            results[idx_name] = savi(bands, alias_map=alias_map)
        elif name_lower == "evi":
            results[idx_name] = evi(bands, alias_map=alias_map)
        else:
            logger.warning("Unknown index '%s', skipping", idx_name)
    return results
