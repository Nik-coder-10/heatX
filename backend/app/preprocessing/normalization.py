import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from .exceptions import NormalizationError
from .configuration import NormalizationConfig

logger = logging.getLogger("app.preprocessing.normalization")


def min_max_normalize(
    data: np.ndarray,
    per_band: bool = True,
    min_val: float | None = None,
    max_val: float | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    result = data.copy().astype(np.float64)
    params: dict[str, float] = {}

    if data.ndim == 3 and per_band:
        for i in range(data.shape[0]):
            band = data[i]
            bmin = float(band.min()) if min_val is None else min_val
            bmax = float(band.max()) if max_val is None else max_val
            if abs(bmax - bmin) < 1e-15:
                result[i] = 0.0
            else:
                result[i] = (band.astype(np.float64) - bmin) / (bmax - bmin)
            params[f"min_{i}"] = bmin
            params[f"max_{i}"] = bmax
    else:
        bmin = float(data.min()) if min_val is None else min_val
        bmax = float(data.max()) if max_val is None else max_val
        if abs(bmax - bmin) < 1e-15:
            result = np.zeros_like(result)
        else:
            result = (data.astype(np.float64) - bmin) / (bmax - bmin)
        params["min"] = bmin
        params["max"] = bmax

    return result, params


def zscore_normalize(
    data: np.ndarray,
    per_band: bool = True,
    mean_val: float | None = None,
    std_val: float | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    result = data.copy().astype(np.float64)
    params: dict[str, float] = {}

    if data.ndim == 3 and per_band:
        for i in range(data.shape[0]):
            band = data[i]
            bmean = float(band.mean()) if mean_val is None else mean_val
            bstd = float(band.std()) if std_val is None else std_val
            if bstd < 1e-15:
                result[i] = 0.0
            else:
                result[i] = (band.astype(np.float64) - bmean) / bstd
            params[f"mean_{i}"] = bmean
            params[f"std_{i}"] = bstd
    else:
        bmean = float(data.mean()) if mean_val is None else mean_val
        bstd = float(data.std()) if std_val is None else std_val
        if bstd < 1e-15:
            result = np.zeros_like(result)
        else:
            result = (data.astype(np.float64) - bmean) / bstd
        params["mean"] = bmean
        params["std"] = bstd

    return result, params


def percentile_clip_normalize(
    data: np.ndarray,
    low_pct: float = 2.0,
    high_pct: float = 98.0,
    per_band: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    result = data.copy().astype(np.float64)
    params: dict[str, Any] = {}

    if data.ndim == 3 and per_band:
        for i in range(data.shape[0]):
            band = data[i]
            plow = float(np.percentile(band, low_pct))
            phigh = float(np.percentile(band, high_pct))
            clipped = np.clip(band.astype(np.float64), plow, phigh)
            if abs(phigh - plow) < 1e-15:
                result[i] = 0.0
            else:
                result[i] = (clipped - plow) / (phigh - plow)
            params[f"p{low_pct}_{i}"] = plow
            params[f"p{high_pct}_{i}"] = phigh
    else:
        plow = float(np.percentile(data, low_pct))
        phigh = float(np.percentile(data, high_pct))
        clipped = np.clip(data.astype(np.float64), plow, phigh)
        if abs(phigh - plow) < 1e-15:
            result = np.zeros_like(result)
        else:
            result = (clipped - plow) / (phigh - plow)
        params[f"p{low_pct}"] = plow
        params[f"p{high_pct}"] = phigh

    return result, params


def reflectance_scale(
    data: np.ndarray,
    scale_factor: float = 0.0001,
    scale_offset: float = 0.0,
) -> tuple[np.ndarray, dict[str, float]]:
    result = data.astype(np.float64) * scale_factor + scale_offset
    return result, {"scale_factor": scale_factor, "scale_offset": scale_offset}


def denormalize(data: np.ndarray, params: dict[str, float], method: str) -> np.ndarray:
    if method == "min_max":
        result = data.copy().astype(np.float64)
        n_bands = data.shape[0] if data.ndim == 3 else 1
        for i in range(n_bands):
            key_min = f"min_{i}" if n_bands > 1 else "min"
            key_max = f"max_{i}" if n_bands > 1 else "max"
            bmin = params.get(key_min, 0.0)
            bmax = params.get(key_max, 1.0)
            if data.ndim == 3:
                result[i] = data[i] * (bmax - bmin) + bmin
            else:
                result = data * (bmax - bmin) + bmin
        return result
    elif method == "zscore":
        result = data.copy().astype(np.float64)
        n_bands = data.shape[0] if data.ndim == 3 else 1
        for i in range(n_bands):
            key_mean = f"mean_{i}" if n_bands > 1 else "mean"
            key_std = f"std_{i}" if n_bands > 1 else "std"
            bmean = params.get(key_mean, 0.0)
            bstd = params.get(key_std, 1.0)
            if data.ndim == 3:
                result[i] = data[i] * bstd + bmean
            else:
                result = data * bstd + bmean
        return result
    else:
        raise NormalizationError(
            f"Denormalization not supported for method '{method}'"
        )


def write_normalized(
    data: np.ndarray,
    path: str | Path,
    profile: dict,
    dtype: str = "float32",
) -> str:
    path = Path(path)
    out_profile = profile.copy()
    out_profile.update(dtype=dtype, compress="lzw", bigtiff="IF_SAFER")
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(data.astype(np.dtype(dtype)))
    return str(path)


class NormalizationStage:
    def __init__(self, config: NormalizationConfig | None = None):
        self.config = config or NormalizationConfig()

    @property
    def name(self) -> str:
        return "Normalization"

    def execute(
        self,
        input_paths: dict[str, str],
        output_dir: str,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("Normalization stage started (method=%s)", self.config.method)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = {}
        norm_params: dict[str, Any] = {}

        for band_name, band_path in input_paths.items():
            with rasterio.open(band_path) as src:
                data = src.read()
                profile = src.profile

            method = self.config.method
            if method == "min_max":
                normalized, params = min_max_normalize(
                    data, per_band=self.config.per_band
                )
            elif method == "zscore":
                normalized, params = zscore_normalize(
                    data, per_band=self.config.per_band
                )
            elif method == "percentile_clip":
                normalized, params = percentile_clip_normalize(
                    data,
                    low_pct=self.config.percentile_low,
                    high_pct=self.config.percentile_high,
                    per_band=self.config.per_band,
                )
            elif method == "reflectance":
                normalized, params = reflectance_scale(
                    data,
                    scale_factor=(
                        self.config.scale_factor if self.config.scale_factor is not None
                        else 0.0001
                    ),
                    scale_offset=(
                        self.config.scale_offset if self.config.scale_offset is not None
                        else 0.0
                    ),
                )
            else:
                raise NormalizationError(
                    f"Unknown normalization method '{method}'. "
                    f"Supported: min_max, zscore, percentile_clip, reflectance"
                )

            dst_path = output_dir / f"{band_name}_normalized.tif"
            write_normalized(normalized, dst_path, profile, self.config.dtype)
            output_paths[band_name] = str(dst_path)
            norm_params[band_name] = params

            logger.info(
                "Normalized band '%s' using %s -> %s", band_name, method, dst_path
            )

        elapsed = time.time() - t0
        logger.info("Normalization stage completed in %.2fs", elapsed)

        return {
            "output_paths": output_paths,
            "norm_params": norm_params,
            "elapsed_s": elapsed,
        }
