import logging
from datetime import datetime, timezone
from typing import Any

from .registry import get_satellite, get_thermal_band

logger = logging.getLogger("app.lst.metadata")


def build_lst_metadata(
    satellite: str,
    thermal_band: str = "Band10",
    algorithm: str = "SingleChannel",
    emissivity_method: str = "NDVI Threshold (Sobrino et al. 2004)",
    units: str = "Kelvin",
    additional_params: dict[str, Any] | None = None,
) -> dict:
    sat = get_satellite(satellite)
    band_info = get_thermal_band(satellite, thermal_band)

    alg_to_formula = {
        "SingleChannel": (
            "LST = T_b / [1 + (λ * T_b / ρ) * ln(ε)]"
        ),
        "SingleChannelRTE": (
            "B(T_s) = (L_sensor - L↑ - τ*(1-ε)*L↓) / (τ*ε)"
        ),
        "SplitWindow": (
            "LST = a0 + a1*T_i + a2*(T_i - T_j) + a3*(T_i - T_j)^2"
        ),
        "TES": "NEM + RAT + MMD (Gillespie et al. 1998)",
    }

    emissivity_to_formula = {
        "NDVI Threshold (Sobrino et al. 2004)": (
            "ε_w=0.991, ε_s=0.966+0.004*FVC, ε_m=0.973+0.047*FVC, ε_v=0.985+0.005*FVC"
        ),
        "Fixed": "User-provided fixed emissivity value",
    }

    meta = {
        "algorithm": algorithm,
        "algorithm_formula": alg_to_formula.get(algorithm, "Unknown"),
        "satellite": sat.full_name,
        "satellite_name": sat.name,
        "thermal_band": band_info.band_name,
        "effective_wavelength_um": band_info.effective_wavelength,
        "k1": band_info.k1,
        "k2": band_info.k2,
        "ml": band_info.ml,
        "al": band_info.al,
        "resolution_m": band_info.resolution,
        "emissivity_method": emissivity_method,
        "emissivity_formula": emissivity_to_formula.get(emissivity_method, "Unknown"),
        "units": units,
        "brightness_temperature_formula": "T_b = K2 / ln(K1 / L + 1)",
        "reference": sat.reference,
        "processing_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "processing_chain": [
            {"step": "thermal_radiance", "method": "DN * ML + AL"},
            {"step": "brightness_temperature", "method": "Planck inversion"},
            {"step": "ndvi_computation", "method": "(NIR - RED) / (NIR + RED)"},
            {"step": "emissivity", "method": emissivity_method},
            {"step": "lst", "method": f"{algorithm} atmospheric correction"},
            {"step": "quality_assessment", "method": "uint8 bitfield flags"},
            {"step": "uncertainty", "method": "Quadrature sum (sensor + emissivity + atmospheric)"},
        ],
        "version": "1.0.0",
    }

    if additional_params:
        meta["additional_params"] = additional_params

    logger.debug(
        "LST metadata built: satellite=%s, band=%s, algorithm=%s, emissivity=%s",
        satellite, thermal_band, algorithm, emissivity_method,
    )
    return meta
