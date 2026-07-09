import logging
import numpy as np

from .exceptions import EmissivityError

logger = logging.getLogger("app.lst.emissivity")


DEFAULT_EMISSIVITY_WATER = 0.991
DEFAULT_EMISSIVITY_SOIL = 0.966
DEFAULT_EMISSIVITY_VEGETATION = 0.985
DEFAULT_EMISSIVITY_URBAN = 0.970
DEFAULT_EMISSIVITY_SNOW = 0.990

EMISSIVITY_COEFFICIENTS: dict[str, dict[str, float]] = {
    "water": {"base": 0.991, "slope": 0.0},
    "soil": {"base": 0.966, "slope": 0.004},
    "mixed": {"base": 0.973, "slope": 0.047},
    "vegetation": {"base": 0.985, "slope": 0.005},
}


def ndvi_threshold_emissivity(
    ndvi: np.ndarray,
    ndvi_soil: float = 0.2,
    ndvi_veg: float = 0.5,
    emissivity_water: float = DEFAULT_EMISSIVITY_WATER,
    emissivity_soil: float = DEFAULT_EMISSIVITY_SOIL,
    emissivity_veg: float = DEFAULT_EMISSIVITY_VEGETATION,
) -> np.ndarray:
    ndvi = ndvi.astype(np.float64)

    fvc = np.zeros_like(ndvi)
    mask_veg = ndvi > ndvi_soil
    fvc[mask_veg] = ((ndvi[mask_veg] - ndvi_soil) / (ndvi_veg - ndvi_soil)) ** 2
    fvc = np.clip(fvc, 0.0, 1.0)

    emissivity = np.zeros_like(ndvi)

    water_mask = ndvi < 0
    bare_mask = (ndvi >= 0) & (ndvi < ndvi_soil)
    mixed_mask = (ndvi >= ndvi_soil) & (ndvi < ndvi_veg)
    dense_veg_mask = ndvi >= ndvi_veg

    emissivity[water_mask] = emissivity_water
    emissivity[bare_mask] = emissivity_soil + EMISSIVITY_COEFFICIENTS["soil"]["slope"] * fvc[bare_mask]
    emissivity[mixed_mask] = EMISSIVITY_COEFFICIENTS["mixed"]["base"] + EMISSIVITY_COEFFICIENTS["mixed"]["slope"] * fvc[mixed_mask]
    emissivity[dense_veg_mask] = emissivity_veg + EMISSIVITY_COEFFICIENTS["vegetation"]["slope"] * fvc[dense_veg_mask]

    emissivity = np.clip(emissivity, 0.9, 1.0)

    logger.debug(
        "Emissivity: water=%.0fpx, bare=%.0fpx, mixed=%.0fpx, dense_veg=%.0fpx",
        water_mask.sum(), bare_mask.sum(), mixed_mask.sum(), dense_veg_mask.sum(),
    )
    return emissivity


def vegetation_fraction(ndvi: np.ndarray, ndvi_soil: float = 0.2, ndvi_veg: float = 0.5) -> np.ndarray:
    ndvi = ndvi.astype(np.float64)
    fvc = np.zeros_like(ndvi)
    mask = ndvi > ndvi_soil
    fvc[mask] = ((ndvi[mask] - ndvi_soil) / (ndvi_veg - ndvi_soil)) ** 2
    return np.clip(fvc, 0.0, 1.0)


def emissivity_water(shape: tuple[int, ...]) -> np.ndarray:
    return np.full(shape, DEFAULT_EMISSIVITY_WATER, dtype=np.float64)


def emissivity_bare_soil(shape: tuple[int, ...]) -> np.ndarray:
    return np.full(shape, DEFAULT_EMISSIVITY_SOIL, dtype=np.float64)


def emissivity_urban(
    ndvi: np.ndarray | None = None,
    impervious_fraction: np.ndarray | None = None,
) -> np.ndarray:
    if impervious_fraction is not None:
        return DEFAULT_EMISSIVITY_URBAN + 0.0 * impervious_fraction
    if ndvi is not None:
        return ndvi_threshold_emissivity(ndvi)
    raise EmissivityError("Need NDVI or impervious fraction for urban emissivity")
