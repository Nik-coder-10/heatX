import logging
import numpy as np

from .exceptions import RadianceConversionError, BrightnessTemperatureError

logger = logging.getLogger("app.lst.brightness_temperature")

PLANCK_C2 = 14387.7686


def dn_to_radiance(
    dn: np.ndarray,
    ml: float = 3.3420e-4,
    al: float = 0.1,
) -> np.ndarray:
    dn = dn.astype(np.float64)
    radiance = dn * ml + al
    return radiance


def radiance_to_brightness_temperature(
    radiance: np.ndarray,
    k1: float,
    k2: float,
) -> np.ndarray:
    radiance = radiance.astype(np.float64)
    if np.any(radiance <= 0):
        raise BrightnessTemperatureError(
            "Non-positive radiance values detected. Radiance must be > 0."
        )
    brightness_temp = k2 / np.log(k1 / radiance + 1.0)
    return brightness_temp


def brightness_temperature_celsius(brightness_temp_kelvin: np.ndarray) -> np.ndarray:
    return brightness_temp_kelvin - 273.15


def calculate_brightness_temperature(
    thermal_data: np.ndarray,
    k1: float,
    k2: float,
    ml: float | None = None,
    al: float | None = None,
) -> dict[str, np.ndarray]:
    if thermal_data.ndim == 3:
        data = thermal_data[0]
    else:
        data = thermal_data

    if ml is not None and al is not None:
        radiance = dn_to_radiance(data, ml, al)
        logger.debug("Radiance computed: min=%.6f, max=%.6f", radiance.min(), radiance.max())
    else:
        radiance = data.astype(np.float64)

    bt_kelvin = radiance_to_brightness_temperature(radiance, k1, k2)
    bt_celsius = brightness_temperature_celsius(bt_kelvin)

    return {
        "bt_kelvin": bt_kelvin,
        "bt_celsius": bt_celsius,
        "radiance": radiance,
    }
