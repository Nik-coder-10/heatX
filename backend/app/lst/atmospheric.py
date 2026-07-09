import logging
from typing import Any, Callable

import numpy as np

from .exceptions import AtmosphericError

logger = logging.getLogger("app.lst.atmospheric")

PLANCK_C2 = 14387.7686
PLANCK_C1 = 1.191042e8


class AtmosphericCorrection:
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__

    def correct(
        self,
        radiance: np.ndarray,
        brightness_temp: np.ndarray,
        emissivity: np.ndarray,
        effective_wavelength: float = 10.895,
        **params,
    ) -> np.ndarray:
        raise NotImplementedError


def _single_channel_kernel(
    bt_kelvin: np.ndarray,
    emissivity: np.ndarray,
    effective_wavelength: float,
) -> np.ndarray:
    eps = emissivity.astype(np.float64)
    bt = bt_kelvin.astype(np.float64)
    lam = effective_wavelength
    rho = PLANCK_C2

    eps_safe = np.maximum(eps, 0.1)
    lst = bt / (1.0 + (lam * bt / rho) * np.log(eps_safe))
    return lst


class SingleChannelCorrection(AtmosphericCorrection):
    def __init__(self, water_vapor: float | None = None):
        super().__init__("SingleChannel")
        self.water_vapor = water_vapor

    def correct(
        self,
        radiance: np.ndarray,
        brightness_temp: np.ndarray,
        emissivity: np.ndarray,
        effective_wavelength: float = 10.895,
        **params,
    ) -> np.ndarray:
        bt_kelvin = brightness_temp.astype(np.float64)
        emiss = emissivity.astype(np.float64)
        wv = params.get("water_vapor", self.water_vapor)

        lst = _single_channel_kernel(bt_kelvin, emiss, effective_wavelength)

        if wv is not None:
            correction = 0.5 * wv * (lst - bt_kelvin)
            lst = lst + correction

        lst = np.clip(lst, 200.0, 400.0)

        logger.debug(
            "SingleChannel: BT range=[%.1f, %.1f] K, LST range=[%.1f, %.1f] K, wv=%s",
            bt_kelvin.min(), bt_kelvin.max(),
            lst.min(), lst.max(),
            str(wv),
        )
        return lst


class SingleChannelRTECorrection(AtmosphericCorrection):
    def __init__(
        self,
        transmissivity: float | np.ndarray | None = None,
        upwelling_radiance: float | np.ndarray | None = None,
        downwelling_radiance: float | np.ndarray | None = None,
    ):
        super().__init__("SingleChannelRTE")
        self.transmissivity = transmissivity
        self.upwelling_radiance = upwelling_radiance
        self.downwelling_radiance = downwelling_radiance

    def correct(
        self,
        radiance: np.ndarray,
        brightness_temp: np.ndarray,
        emissivity: np.ndarray,
        effective_wavelength: float = 10.895,
        **params,
    ) -> np.ndarray:
        rad = radiance.astype(np.float64)
        emiss = emissivity.astype(np.float64)
        lam = effective_wavelength

        tau = params.get("transmissivity", self.transmissivity)
        lup = params.get("upwelling_radiance", self.upwelling_radiance)
        ldown = params.get("downwelling_radiance", self.downwelling_radiance)

        if any(p is None for p in [tau, lup, ldown]):
            raise AtmosphericError(
                "SingleChannelRTE requires transmissivity, upwelling_radiance, "
                "and downwelling_radiance"
            )

        tau_arr = np.full_like(rad, tau) if np.isscalar(tau) else tau.astype(np.float64)
        lup_arr = np.full_like(rad, lup) if np.isscalar(lup) else lup.astype(np.float64)
        ldown_arr = np.full_like(rad, ldown) if np.isscalar(ldown) else ldown.astype(np.float64)

        rad_surface = (rad - lup_arr - tau_arr * (1.0 - emiss) * ldown_arr) / (tau_arr * emiss)
        rad_surface = np.maximum(rad_surface, 1e-10)

        c1 = PLANCK_C1
        c2 = PLANCK_C2
        lst = c2 / (lam * np.log(c1 / (lam ** 5 * rad_surface) + 1.0))
        lst = np.clip(lst, 200.0, 400.0)

        return lst


class SplitWindowCorrection(AtmosphericCorrection):
    def __init__(self, coefficients: dict[str, float] | None = None):
        super().__init__("SplitWindow")
        self.coefficients = coefficients or {
            "a0": -0.41, "a1": 1.0, "a2": 1.8, "a3": -0.5,
        }

    def correct(
        self,
        radiance: np.ndarray,
        brightness_temp: np.ndarray,
        emissivity: np.ndarray,
        effective_wavelength: float = 10.895,
        **params,
    ) -> np.ndarray:
        bt_i = params.get("bt_band_i", brightness_temp)
        bt_j = params.get("bt_band_j")
        eps_i = params.get("emissivity_i", emissivity)
        eps_j = params.get("emissivity_j")
        if bt_j is None or eps_j is None:
            raise AtmosphericError("SplitWindow requires two thermal bands (bt_band_j, emissivity_j)")

        c = self.coefficients
        lst = (c["a0"]
               + c["a1"] * bt_i
               + c["a2"] * (bt_i - bt_j)
               + c["a3"] * (bt_i - bt_j) ** 2)
        return lst


def create_atmospheric_correction(
    algorithm: str = "single_channel",
    **params,
) -> AtmosphericCorrection:
    alg = algorithm.lower().replace(" ", "_").replace("-", "_")
    if alg in ("single_channel", "sc", "singlechannel"):
        return SingleChannelCorrection(**{k: v for k, v in params.items()
                                          if k in ("water_vapor",)})
    elif alg in ("single_channel_rte", "rte", "sc_rte"):
        return SingleChannelRTECorrection(**{k: v for k, v in params.items()
                                              if k in ("transmissivity", "upwelling_radiance",
                                                       "downwelling_radiance")})
    elif alg in ("split_window", "sw"):
        return SplitWindowCorrection(**{k: v for k, v in params.items()
                                         if k == "coefficients"})
    else:
        raise AtmosphericError(f"Unknown atmospheric correction algorithm: {algorithm}")
