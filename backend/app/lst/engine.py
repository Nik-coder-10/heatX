import logging
from typing import Any

import numpy as np

from .exceptions import ComputationError, ValidationError
from .registry import get_satellite, get_thermal_band, SatelliteDefinition, ThermalBandInfo
from .brightness_temperature import calculate_brightness_temperature
from .emissivity import ndvi_threshold_emissivity
from .atmospheric import (
    SingleChannelCorrection,
    SingleChannelRTECorrection,
    SplitWindowCorrection,
    AtmosphericCorrection,
)
from .uncertainty import (
    sensor_uncertainty,
    emissivity_uncertainty,
    atmospheric_uncertainty,
    total_uncertainty,
    confidence_interval,
)
from .quality import create_quality_mask, describe_qa_mask
from .validator import (
    validate_thermal_data,
    validate_supporting_bands,
    validate_dimensions,
)
from .metadata import build_lst_metadata
from .statistics import compute_lst_statistics

logger = logging.getLogger("app.lst.engine")

WINDOW_SIZE_DEFAULT = 2048


class LSTEngine:
    def __init__(
        self,
        satellite: str = "landsat8",
        thermal_band: str = "Band10",
        algorithm: str = "SingleChannel",
        window_size: int = WINDOW_SIZE_DEFAULT,
        **config,
    ):
        self.satellite = satellite
        self.thermal_band = thermal_band
        self.sat_def: SatelliteDefinition = get_satellite(satellite)
        self.band_info: ThermalBandInfo = get_thermal_band(satellite, thermal_band)

        self.algorithm = algorithm
        self.window_size = max(256, window_size)
        self.config = config

        self._atmospheric: AtmosphericCorrection | None = None
        self._setup_atmospheric()

    def _setup_atmospheric(self) -> None:
        alg = self.algorithm.lower().replace(" ", "_").replace("-", "_")
        if alg in ("single_channel", "sc", "singlechannel"):
            wv = self.config.get("water_vapor")
            self._atmospheric = SingleChannelCorrection(water_vapor=wv)
        elif alg in ("single_channel_rte", "rte"):
            self._atmospheric = SingleChannelRTECorrection(
                transmissivity=self.config.get("transmissivity"),
                upwelling_radiance=self.config.get("upwelling_radiance"),
                downwelling_radiance=self.config.get("downwelling_radiance"),
            )
        elif alg in ("split_window", "sw"):
            self._atmospheric = SplitWindowCorrection(
                coefficients=self.config.get("coefficients"),
            )
        else:
            self._atmospheric = SingleChannelCorrection()

    def compute_lst(
        self,
        thermal_data: np.ndarray,
        ndvi: np.ndarray,
        **kwargs,
    ) -> dict[str, Any]:
        validate_thermal_data(thermal_data, self.satellite, self.thermal_band)
        if ndvi is None:
            raise ValidationError("NDVI data is required")
        validate_supporting_bands(ndvi=ndvi)
        validate_dimensions([(thermal_data, "thermal_data"), (ndvi, "ndvi")])

        nodata = kwargs.get("nodata")
        window_size = kwargs.get("window_size", self.window_size)

        result = self._process(thermal_data, ndvi, nodata, window_size, kwargs)
        return result

    def _process(
        self,
        thermal_data: np.ndarray,
        ndvi: np.ndarray,
        nodata: Any,
        window_size: int,
        extra: dict,
    ) -> dict:
        rows, cols = thermal_data.shape[:2]
        bt_kelvin = np.full((rows, cols), np.nan, dtype=np.float64)
        bt_celsius = np.full((rows, cols), np.nan, dtype=np.float64)
        emissivity_arr = np.full((rows, cols), np.nan, dtype=np.float64)
        lst_kelvin = np.full((rows, cols), np.nan, dtype=np.float64)
        uncertainty_arr = np.full((rows, cols), np.nan, dtype=np.float64)
        quality_arr = np.zeros((rows, cols), dtype=np.uint8)
        radiance_arr = np.full((rows, cols), np.nan, dtype=np.float64)

        for i in range(0, rows, min(window_size, rows)):
            for j in range(0, cols, min(window_size, cols)):
                i_end = min(i + window_size, rows)
                j_end = min(j + window_size, cols)
                window = (slice(i, i_end), slice(j, j_end))

                self._process_window(
                    window, thermal_data, ndvi,
                    bt_kelvin, bt_celsius, emissivity_arr,
                    lst_kelvin, uncertainty_arr, quality_arr, radiance_arr,
                    nodata, extra,
                )

        stats = compute_lst_statistics(lst_kelvin, quality_arr, nodata)
        meta = build_lst_metadata(
            satellite=self.satellite,
            thermal_band=self.thermal_band,
            algorithm=self.algorithm,
            emissivity_method=extra.get("emissivity_method", "NDVI Threshold (Sobrino et al. 2004)"),
            units=extra.get("units", "Kelvin"),
        )

        return {
            "lst_kelvin": lst_kelvin,
            "lst_celsius": lst_kelvin - 273.15,
            "brightness_temperature_kelvin": bt_kelvin,
            "brightness_temperature_celsius": bt_celsius,
            "emissivity": emissivity_arr,
            "radiance": radiance_arr,
            "uncertainty": uncertainty_arr,
            "quality_mask": quality_arr,
            "statistics": stats,
            "metadata": meta,
            "shape": (rows, cols),
            "satellite": self.satellite,
            "thermal_band": self.thermal_band,
            "algorithm": self.algorithm,
        }

    def _process_window(
        self,
        window: tuple[slice, slice],
        thermal_data: np.ndarray,
        ndvi: np.ndarray,
        bt_kelvin: np.ndarray,
        bt_celsius: np.ndarray,
        emissivity_arr: np.ndarray,
        lst_kelvin: np.ndarray,
        uncertainty_arr: np.ndarray,
        quality_arr: np.ndarray,
        radiance_arr: np.ndarray,
        nodata: Any,
        extra: dict,
    ) -> None:
        th_win = thermal_data[window]
        ndvi_win = ndvi[window]
        if th_win.ndim == 3:
            th_win = th_win[0]
        elif th_win.ndim > 3:
            th_win = th_win.squeeze()

        valid = np.isfinite(th_win) & np.isfinite(ndvi_win)
        if nodata is not None:
            valid &= (th_win != nodata)

        if not valid.any():
            return

        th_win_safe = th_win.copy()
        if nodata is not None:
            th_win_safe[th_win == nodata] = 0

        ml = extra.get("ml", self.band_info.ml)
        al = extra.get("al", self.band_info.al)
        k1 = extra.get("k1", self.band_info.k1)
        k2 = extra.get("k2", self.band_info.k2)

        bt_result = calculate_brightness_temperature(th_win_safe, k1, k2, ml, al)
        bt_k_win = bt_result["bt_kelvin"]
        bt_c_win = bt_result["bt_celsius"]
        rad_win = bt_result["radiance"]

        emiss_win = ndvi_threshold_emissivity(
            ndvi_win,
            emissivity_water=extra.get("emissivity_water", 0.991),
            emissivity_soil=extra.get("emissivity_soil", 0.966),
            emissivity_veg=extra.get("emissivity_veg", 0.985),
        )

        lst_win = self._atmospheric.correct(
            rad_win, bt_k_win, emiss_win,
            effective_wavelength=self.band_info.effective_wavelength,
            **extra,
        )

        sensor_u = sensor_uncertainty(self.satellite)
        emiss_u = emissivity_uncertainty(
            emiss_win, effective_wavelength=self.band_info.effective_wavelength,
            brightness_temp=bt_k_win,
        )
        wv = self.config.get("water_vapor")
        atmo_u = atmospheric_uncertainty(water_vapor=wv)
        uncert_win = total_uncertainty(sensor_u, emiss_u, atmo_u)

        qa_win = create_quality_mask(
            th_win.shape,
            cloud_mask=np.zeros_like(th_win, dtype=np.uint8),
            ndvi=ndvi_win,
            uncertainty=uncert_win,
            lst=lst_win,
        )

        bt_kelvin[window][valid] = bt_k_win[valid]
        bt_celsius[window][valid] = bt_c_win[valid]
        emissivity_arr[window][valid] = emiss_win[valid]
        lst_kelvin[window][valid] = lst_win[valid]
        uncertainty_arr[window][valid] = uncert_win[valid]
        quality_arr[window] |= qa_win
        radiance_arr[window][valid] = rad_win[valid]
