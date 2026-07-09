import logging
import numpy as np

from .exceptions import ValidationError
from .registry import get_satellite, get_thermal_band

logger = logging.getLogger("app.lst.validator")


def validate_thermal_data(
    thermal_data: np.ndarray | None,
    satellite: str | None = None,
    thermal_band: str = "Band10",
) -> None:
    if thermal_data is None:
        raise ValidationError("Thermal band data is required")
    if thermal_data.size == 0:
        raise ValidationError("Thermal band data is empty")
    if not np.isfinite(thermal_data).any():
        raise ValidationError("Thermal band data contains no finite values")
    if np.all(thermal_data <= 0):
        raise ValidationError("Thermal band data has no positive values")


def validate_supporting_bands(
    ndvi: np.ndarray | None = None,
    red: np.ndarray | None = None,
    nir: np.ndarray | None = None,
) -> None:
    if ndvi is not None and ndvi.size == 0:
        raise ValidationError("NDVI array is empty")
    if ndvi is not None and not np.isfinite(ndvi).any():
        raise ValidationError("NDVI array contains no finite values")


def validate_dimensions(
    arrays: list[tuple[np.ndarray | None, str]],
) -> None:
    ref_shape = None
    for arr, name in arrays:
        if arr is None:
            continue
        if ref_shape is None:
            ref_shape = arr.shape
        elif arr.shape != ref_shape:
            raise ValidationError(
                f"Dimension mismatch: {name} shape {arr.shape} != expected {ref_shape}"
            )


def validate_crs(crs: str | object | None) -> None:
    if crs is None:
        raise ValidationError("CRS is required")
    try:
        from rasterio.crs import CRS
        CRS.from_user_input(crs)
    except Exception as e:
        raise ValidationError(f"Invalid CRS: {e}")


def validate_nodata(
    data: np.ndarray,
    nodata: float | None = None,
    max_invalid_fraction: float = 0.5,
) -> float:
    if nodata is None or not np.isfinite(nodata):
        return 0.0
    invalid_count = int(np.sum(data == nodata))
    invalid_frac = invalid_count / data.size
    if invalid_frac > max_invalid_fraction:
        logger.warning(
            "High fraction of NoData pixels: %.1f%% (threshold %.1f%%)",
            invalid_frac * 100, max_invalid_fraction * 100,
        )
    return invalid_frac


def validate_value_range(
    data: np.ndarray,
    min_val: float = -100.0,
    max_val: float = 20000.0,
    name: str = "data",
) -> None:
    if data.min() < min_val:
        logger.warning("%s has values below %.1f: min=%.2f", name, min_val, data.min())
    if data.max() > max_val:
        logger.warning("%s has values above %.1f: max=%.2f", name, max_val, data.max())
