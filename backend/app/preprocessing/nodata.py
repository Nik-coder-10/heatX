import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.windows import Window

from .exceptions import NoDataError
from .configuration import NoDataConfig

logger = logging.getLogger("app.preprocessing.nodata")


def detect_nodata_pixels(
    data: np.ndarray,
    nodata_value: float | None = None,
) -> np.ndarray:
    mask = np.zeros(data.shape[-2:], dtype=bool)
    if data.ndim == 3:
        bands = data
    elif data.ndim == 2:
        bands = data[np.newaxis, ...]
    else:
        bands = data

    for i in range(bands.shape[0]):
        band = bands[i]
        if nodata_value is not None:
            if np.isnan(nodata_value):
                mask |= np.isnan(band)
            elif np.isinf(nodata_value) or np.isneginf(nodata_value):
                mask |= np.isinf(band)
            else:
                mask |= np.abs(band.astype(np.float64) - nodata_value) < 1e-8
        mask |= np.isnan(band) | np.isinf(band)

    return mask


def detect_invalid_values(data: np.ndarray) -> np.ndarray:
    mask = np.zeros(data.shape[-2:], dtype=bool)
    if data.ndim == 3:
        bands = data
    elif data.ndim == 2:
        bands = data[np.newaxis, ...]
    else:
        bands = data

    for i in range(bands.shape[0]):
        band = bands[i]
        mask |= np.isnan(band) | np.isinf(band)
    return mask


def fill_constant(
    data: np.ndarray, mask: np.ndarray, fill_value: float = 0.0
) -> np.ndarray:
    result = data.copy().astype(np.float64)
    if result.ndim == 3:
        for i in range(result.shape[0]):
            result[i][mask] = fill_value
    else:
        result[mask] = fill_value
    return result


def fill_nearest_valid(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    result = data.copy().astype(np.float64)
    if data.ndim == 3:
        for i in range(result.shape[0]):
            band = result[i]
            band[mask] = np.nan
            indices = ndimage.distance_transform_edt(
                mask, return_distances=False, return_indices=True
            )
            band[:] = band[tuple(indices)]
        return result

    result[mask] = np.nan
    indices = ndimage.distance_transform_edt(
        mask, return_distances=False, return_indices=True
    )
    result[:] = result[tuple(indices)]
    return result


def fill_linear(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    result = data.copy().astype(np.float64)
    ny, nx = mask.shape

    if data.ndim == 3:
        for b in range(result.shape[0]):
            band = result[b]
            band[mask] = np.nan
            _interpolate_2d(band, mask)
        return result

    result[mask] = np.nan
    _interpolate_2d(result, mask)
    return result


def _interpolate_2d(arr: np.ndarray, mask: np.ndarray) -> None:
    ny, nx = arr.shape
    x, y = np.meshgrid(np.arange(nx), np.arange(ny))
    x_valid = x[~mask]
    y_valid = y[~mask]
    z_valid = arr[~mask]

    if len(z_valid) == 0:
        return

    x_miss = x[mask]
    y_miss = y[mask]

    from scipy.interpolate import LinearNDInterpolator

    interpolator = LinearNDInterpolator(
        np.column_stack([x_valid.ravel(), y_valid.ravel()]),
        z_valid.ravel(),
        fill_value=0.0,
    )
    arr[mask] = interpolator(np.column_stack([x_miss.ravel(), y_miss.ravel()]))


def fill_cubic(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    result = data.copy().astype(np.float64)
    if data.ndim == 3:
        for i in range(result.shape[0]):
            band = result[i].copy()
            band[mask] = np.nan
            valid_mean = np.nanmean(band)
            if np.isnan(valid_mean):
                band[:] = 0.0
            else:
                band[mask] = valid_mean
            band = ndimage.gaussian_filter(band, sigma=3, mode="reflect")
            result[i][mask] = band[mask]
        return result

    band_c = result.copy()
    band_c[mask] = np.nan
    valid_mean = np.nanmean(band_c)
    if np.isnan(valid_mean):
        band_c[:] = 0.0
    else:
        band_c[mask] = valid_mean
    band_c = ndimage.gaussian_filter(band_c, sigma=3, mode="reflect")
    result[mask] = band_c[mask]
    return result


def apply_nodata_handling(
    data: np.ndarray,
    mask: np.ndarray,
    strategy: str = "interpolate",
    method: str = "linear",
    fill_value: float = 0.0,
) -> np.ndarray:
    if strategy == "constant":
        return fill_constant(data, mask, fill_value)
    elif strategy == "interpolate":
        if method == "nearest":
            return fill_nearest_valid(data, mask)
        elif method == "linear":
            return fill_linear(data, mask)
        elif method == "cubic":
            return fill_cubic(data, mask)
        else:
            raise NoDataError(f"Unknown interpolation method: {method}")
    else:
        raise NoDataError(f"Unknown fill strategy: {strategy}")


def write_nodata_mask(
    mask: np.ndarray,
    path: str | Path,
    profile: dict,
) -> str:
    path = Path(path)
    out_profile = profile.copy()
    out_profile.update(dtype="uint8", count=1, compress="lzw", nodata=255)
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(mask.astype(np.uint8) * 255, 1)
    return str(path)


class NoDataStage:
    def __init__(self, config: NoDataConfig | None = None):
        self.config = config or NoDataConfig()

    @property
    def name(self) -> str:
        return "NoData"

    def execute(
        self,
        input_paths: dict[str, str],
        output_dir: str,
        nodata_values: dict[str, float | None] | None = None,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("NoData stage started")

        merged_nodata = {**self.config.nodata_values}
        if nodata_values:
            merged_nodata.update(nodata_values)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = {}
        combined_nodata_mask = None

        for band_name, band_path in input_paths.items():
            if any(
                kw in band_name.lower()
                for kw in ("qa60", "qa_pixel", "cloud", "mask")
            ):
                logger.debug("Skipping NoData check for QA band: %s", band_name)
                continue

            with rasterio.open(band_path) as src:
                data = src.read()
                profile = src.profile
                nodata = merged_nodata.get(band_name, src.nodata)

            band_mask = detect_nodata_pixels(data, nodata)
            nodata_pct = float(band_mask.sum()) / float(band_mask.size) * 100.0
            logger.info(
                "Band '%s': nodata pixels = %.2f%%", band_name, nodata_pct
            )

            if combined_nodata_mask is None:
                combined_nodata_mask = band_mask.copy()
            else:
                ny, nx = combined_nodata_mask.shape
                bh, bw = band_mask.shape
                combined_nodata_mask[: min(ny, bh), : min(nx, bw)] |= band_mask[
                    : min(ny, bh), : min(nx, bw)
                ]

            if band_mask.any():
                filled = apply_nodata_handling(
                    data,
                    band_mask,
                    strategy=self.config.fill_strategy,
                    method=self.config.interpolation_method,
                    fill_value=self.config.constant_fill_value,
                )
                out_path = output_dir / f"{band_name}_nodata_filled.tif"
                out_profile = profile.copy()
                out_profile.update(dtype="float64", nodata=None)
                with rasterio.open(out_path, "w", **out_profile) as dst:
                    dst.write(filled)
                output_paths[band_name] = str(out_path)
                logger.info("Filled nodata for band '%s' -> %s", band_name, out_path)
            else:
                output_paths[band_name] = band_path
                logger.debug("No nodata pixels in band '%s', keeping original", band_name)

        if self.config.output_nodata_mask and combined_nodata_mask is not None:
            mask_path = output_dir / "nodata_mask.tif"
            first_profile = None
            for band_path in input_paths.values():
                with rasterio.open(band_path) as src:
                    first_profile = src.profile
                    break
            if first_profile:
                write_nodata_mask(combined_nodata_mask, mask_path, first_profile)
                output_paths["nodata_mask"] = str(mask_path)

        elapsed = time.time() - t0
        logger.info("NoData stage completed in %.2fs", elapsed)

        return {
            "output_paths": output_paths,
            "combined_nodata_mask": combined_nodata_mask,
            "elapsed_s": elapsed,
        }
