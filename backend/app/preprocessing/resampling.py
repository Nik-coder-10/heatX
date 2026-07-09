import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling as RioResampling
from rasterio.warp import reproject

from .exceptions import ResamplingError
from .configuration import ResamplingConfig

logger = logging.getLogger("app.preprocessing.resampling")


_RESAMPLING_MAP = {
    "nearest": RioResampling.nearest,
    "bilinear": RioResampling.bilinear,
    "cubic": RioResampling.cubic,
    "lanczos": RioResampling.lanczos,
    "average": RioResampling.average,
}


def get_resampling_method(name: str) -> RioResampling:
    if name not in _RESAMPLING_MAP:
        raise ResamplingError(
            f"Unknown resampling method '{name}'. "
            f"Supported: {', '.join(sorted(_RESAMPLING_MAP))}"
        )
    return _RESAMPLING_MAP[name]


def resample_to_resolution(
    src_path: str | Path,
    dst_path: str | Path,
    target_resolution: tuple[float, float],
    method: str = "bilinear",
) -> str:
    dst_path = Path(dst_path)
    rio_method = get_resampling_method(method)

    with rasterio.open(src_path) as src:
        left, bottom, right, top = src.bounds
        src_crs = src.crs
        src_nodata = src.nodata

        res_x, res_y = target_resolution
        if res_x <= 0 or res_y <= 0:
            raise ResamplingError(
                f"Target resolution must be positive, got ({res_x}, {res_y})"
            )

        dst_width = max(1, int(round((right - left) / res_x)))
        dst_height = max(1, int(round((top - bottom) / res_y)))

        dst_transform = rasterio.transform.from_bounds(
            left, bottom, right, top, dst_width, dst_height
        )

        dst_profile = src.profile.copy()
        dst_profile.update(
            width=dst_width,
            height=dst_height,
            transform=dst_transform,
            compress="lzw",
            bigtiff="IF_SAFER",
        )

        with rasterio.open(dst_path, "w", **dst_profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=src_crs,
                    resampling=rio_method,
                    src_nodata=src_nodata,
                    dst_nodata=src_nodata,
                )

    logger.info(
        "Resampled %s -> %s (%d x %d, resolution=%.6f, %.6f, method=%s)",
        src_path,
        dst_path,
        dst_width,
        dst_height,
        res_x,
        res_y,
        method,
    )
    return str(dst_path)


def resample_to_dimensions(
    src_path: str | Path,
    dst_path: str | Path,
    target_width: int,
    target_height: int,
    method: str = "bilinear",
) -> str:
    dst_path = Path(dst_path)
    rio_method = get_resampling_method(method)

    with rasterio.open(src_path) as src:
        dst_transform = rasterio.transform.from_bounds(
            *src.bounds, target_width, target_height
        )
        dst_profile = src.profile.copy()
        dst_profile.update(
            width=target_width,
            height=target_height,
            transform=dst_transform,
            compress="lzw",
            bigtiff="IF_SAFER",
        )

        with rasterio.open(dst_path, "w", **dst_profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=src.crs,
                    resampling=rio_method,
                    src_nodata=src.nodata,
                    dst_nodata=src.nodata,
                )

    logger.info(
        "Resampled %s -> %s (%d x %d, method=%s)",
        src_path,
        dst_path,
        target_width,
        target_height,
        method,
    )
    return str(dst_path)


class ResamplingStage:
    def __init__(self, config: ResamplingConfig | None = None):
        self.config = config or ResamplingConfig()

    @property
    def name(self) -> str:
        return "Resampling"

    def execute(
        self,
        input_paths: dict[str, str],
        output_dir: str,
    ) -> dict[str, Any]:
        t0 = time.time()
        logger.info("Resampling stage started")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = {}
        for band_name, band_path in input_paths.items():
            if self.config.target_resolution:
                dst = output_dir / f"{band_name}_resampled.tif"
                resample_to_resolution(
                    band_path,
                    dst,
                    self.config.target_resolution,
                    method=self.config.method,
                )
                output_paths[band_name] = str(dst)
            elif self.config.target_width and self.config.target_height:
                dst = output_dir / f"{band_name}_resampled.tif"
                resample_to_dimensions(
                    band_path,
                    dst,
                    self.config.target_width,
                    self.config.target_height,
                    method=self.config.method,
                )
                output_paths[band_name] = str(dst)
            else:
                output_paths[band_name] = band_path

        elapsed = time.time() - t0
        logger.info("Resampling stage completed in %.2fs", elapsed)
        return {
            "output_paths": output_paths,
            "elapsed_s": elapsed,
        }
