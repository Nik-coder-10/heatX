import logging
import numpy as np

logger = logging.getLogger("app.lst.uncertainty")


def sensor_uncertainty(satellite: str = "landsat8") -> float:
    uncertainties = {
        "landsat8": 0.5,
        "landsat9": 0.5,
        "ecostress": 0.3,
        "modis": 0.5,
        "aster": 0.4,
    }
    return uncertainties.get(satellite.lower(), 1.0)


def emissivity_uncertainty(
    emissivity: np.ndarray,
    delta_emissivity: float = 0.005,
    effective_wavelength: float = 10.895,
    brightness_temp: np.ndarray | None = None,
) -> np.ndarray:
    if brightness_temp is not None:
        bt = brightness_temp.astype(np.float64)
        lam = effective_wavelength
        rho = 14387.7686
        delta_t_emiss = (lam * bt / rho) * (delta_emissivity / np.maximum(emissivity, 0.1))
    else:
        delta_t_emiss = delta_emissivity * 60.0
        delta_t_emiss = np.full_like(emissivity, delta_t_emiss, dtype=np.float64)
    return np.abs(delta_t_emiss)


def atmospheric_uncertainty(
    water_vapor: float | None = None,
    base_uncertainty: float = 0.5,
) -> float:
    if water_vapor is not None:
        return base_uncertainty + 0.3 * water_vapor
    return base_uncertainty


def total_uncertainty(
    sensor_uncert: float | np.ndarray,
    emissivity_uncert: float | np.ndarray,
    atmospheric_uncert: float | np.ndarray,
) -> np.ndarray:
    total = np.sqrt(
        np.array(sensor_uncert, dtype=np.float64) ** 2
        + np.array(emissivity_uncert, dtype=np.float64) ** 2
        + np.array(atmospheric_uncert, dtype=np.float64) ** 2
    )
    return total


def confidence_interval(
    lst: np.ndarray,
    total_uncert: np.ndarray,
    confidence_level: float = 0.95,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z_scores = {0.68: 1.0, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence_level, 1.96)
    lower = lst - z * total_uncert
    upper = lst + z * total_uncert
    return lower, lst, upper


def quality_score_from_uncertainty(
    total_uncert: np.ndarray,
    band_availability: float = 1.0,
    invalid_fraction: float = 0.0,
) -> np.ndarray:
    score = (
        100.0
        - 5.0 * (1.0 - band_availability)
        - 10.0 * invalid_fraction
        - 15.0 * (np.mean(total_uncert) / 2.0)
    )
    return np.clip(score, 0.0, 100.0)
