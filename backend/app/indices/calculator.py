import numpy as np

from .exceptions import ComputationError


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    denom = nir + red
    mask = np.abs(denom) < 1e-15
    result = np.divide(nir - red, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def savi(nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    denom = nir + red + L
    mask = np.abs(denom) < 1e-15
    result = np.divide(nir - red, denom, out=np.zeros_like(denom), where=~mask)
    result *= 1.0 + L
    return np.clip(result, -1.0, 1.0)


def evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    blue = blue.astype(np.float64)
    denom = nir + 6.0 * red - 7.5 * blue + 1.0
    mask = np.abs(denom) < 1e-15
    result = np.divide(nir - red, denom, out=np.zeros_like(denom), where=~mask)
    result *= 2.5
    return np.clip(result, -1.0, 1.0)


def msavi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    nir = nir.astype(np.float64)
    red = red.astype(np.float64)
    numerator = 2.0 * nir + 1.0
    radicand = numerator ** 2 - 8.0 * (nir - red)
    radicand = np.maximum(radicand, 0.0)
    result = (numerator - np.sqrt(radicand)) / 2.0
    return np.clip(result, -1.0, 1.0)


def ndbi(swir1: np.ndarray, nir: np.ndarray) -> np.ndarray:
    swir1 = swir1.astype(np.float64)
    nir = nir.astype(np.float64)
    denom = swir1 + nir
    mask = np.abs(denom) < 1e-15
    result = np.divide(swir1 - nir, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def ibi(nir: np.ndarray, red: np.ndarray, swir1: np.ndarray, green: np.ndarray) -> np.ndarray:
    ndbi_val = ndbi(swir1, nir)
    savi_val = savi(nir, red)
    ndwi_val = ndwi(green, nir)
    avg = (savi_val + ndwi_val) / 2.0
    denom = ndbi_val + avg
    mask = np.abs(denom) < 1e-15
    result = np.divide(ndbi_val - avg, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def ui(swir2: np.ndarray, nir: np.ndarray) -> np.ndarray:
    swir2 = swir2.astype(np.float64)
    nir = nir.astype(np.float64)
    denom = swir2 + nir
    mask = np.abs(denom) < 1e-15
    result = np.divide(swir2 - nir, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    green = green.astype(np.float64)
    nir = nir.astype(np.float64)
    denom = green + nir
    mask = np.abs(denom) < 1e-15
    result = np.divide(green - nir, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def mndwi(green: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    green = green.astype(np.float64)
    swir1 = swir1.astype(np.float64)
    denom = green + swir1
    mask = np.abs(denom) < 1e-15
    result = np.divide(green - swir1, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    nir = nir.astype(np.float64)
    swir1 = swir1.astype(np.float64)
    denom = nir + swir1
    mask = np.abs(denom) < 1e-15
    result = np.divide(nir - swir1, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def bsi(swir1: np.ndarray, red: np.ndarray, nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
    swir1 = swir1.astype(np.float64)
    red = red.astype(np.float64)
    nir = nir.astype(np.float64)
    blue = blue.astype(np.float64)
    numerator = (swir1 + red) - (nir + blue)
    denom = (swir1 + red) + (nir + blue)
    mask = np.abs(denom) < 1e-15
    result = np.divide(numerator, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def ndisi(tir: np.ndarray, nir: np.ndarray, swir1: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    tir = tir.astype(np.float64)
    nir = nir.astype(np.float64)
    swir1 = swir1.astype(np.float64)
    swir2 = swir2.astype(np.float64)
    mean_vis = (nir + swir1 + swir2) / 3.0
    numerator = tir - mean_vis
    denom = tir + mean_vis
    mask = np.abs(denom) < 1e-15
    result = np.divide(numerator, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


def gndvi(nir: np.ndarray, green: np.ndarray) -> np.ndarray:
    nir = nir.astype(np.float64)
    green = green.astype(np.float64)
    denom = nir + green
    mask = np.abs(denom) < 1e-15
    result = np.divide(nir - green, denom, out=np.zeros_like(denom), where=~mask)
    return np.clip(result, -1.0, 1.0)


_COMPUTATION_REGISTRY: dict[str, dict] = {
    "ndvi": {"func": ndvi, "required": ["nir", "red"]},
    "savi": {"func": savi, "required": ["nir", "red"], "optional": ["L"]},
    "evi": {"func": evi, "required": ["nir", "red", "blue"]},
    "msavi": {"func": msavi, "required": ["nir", "red"]},
    "ndbi": {"func": ndbi, "required": ["swir1", "nir"]},
    "ibi": {"func": ibi, "required": ["nir", "red", "swir1", "green"]},
    "ui": {"func": ui, "required": ["swir2", "nir"]},
    "ndwi": {"func": ndwi, "required": ["green", "nir"]},
    "mndwi": {"func": mndwi, "required": ["green", "swir1"]},
    "ndmi": {"func": ndmi, "required": ["nir", "swir1"]},
    "bsi": {"func": bsi, "required": ["swir1", "red", "nir", "blue"]},
    "ndisi": {"func": ndisi, "required": ["tir", "nir", "swir1", "swir2"]},
    "gndvi": {"func": gndvi, "required": ["nir", "green"]},
}


def compute_index(name: str, band_arrays: dict[str, np.ndarray], **kwargs) -> np.ndarray:
    key = name.lower()
    if key not in _COMPUTATION_REGISTRY:
        raise ComputationError(
            f"Unknown index '{name}'. Available: {', '.join(sorted(_COMPUTATION_REGISTRY))}"
        )
    entry = _COMPUTATION_REGISTRY[key]
    required = entry["required"]
    missing = [b for b in required if b not in band_arrays]
    if missing:
        raise ComputationError(
            f"Missing required bands for '{name}': {missing}. "
            f"Provided: {list(band_arrays)}"
        )
    args = [band_arrays[b] for b in required]
    if "optional" in entry:
        for opt in entry["optional"]:
            if opt in kwargs:
                args.append(kwargs[opt])
    return entry["func"](*args)
