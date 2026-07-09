"""Raster writer — GeoTIFF and COG creation with compression support."""

import logging
import os
from typing import Any, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from app.raster.exceptions import (
    CorruptedRasterError,
    RasterWriteError,
    UnsupportedFormatError,
)

logger = logging.getLogger("app.raster.writer")

_SUPPORTED_COMPRESSION = {"lzw", "deflate", "zstd", None}
_COG_PROFILE = {
    "driver": "GTiff",
    "tiled": True,
    "blockxsize": 256,
    "blockysize": 256,
    "interleave": "pixel",
    "BIGTIFF": "IF_NEEDED",
}


def _validate_compression(compression: Optional[str]) -> None:
    if compression is not None and compression.lower() not in _SUPPORTED_COMPRESSION:
        raise UnsupportedFormatError(
            f"Unsupported compression '{compression}'. "
            f"Supported: {sorted(s for s in _SUPPORTED_COMPRESSION if s)}"
        )


def _prepare_profile(
    driver: str = "GTiff",
    width: Optional[int] = None,
    height: Optional[int] = None,
    count: int = 1,
    dtype: str = "float32",
    crs: Optional[Any] = None,
    transform: Optional[Any] = None,
    nodata: Optional[float] = None,
    compression: Optional[str] = None,
    tiled: bool = False,
    cog: bool = False,
    block_size: int = 256,
    bigtiff: bool = False,
    **extra_kwargs: Any,
) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "driver": driver,
        "height": height,
        "width": width,
        "count": count,
        "dtype": dtype,
    }

    if crs is not None:
        if isinstance(crs, str):
            profile["crs"] = CRS.from_user_input(crs)
        else:
            profile["crs"] = crs

    if transform is not None:
        profile["transform"] = transform

    if nodata is not None:
        profile["nodata"] = nodata

    if cog:
        profile.update(_COG_PROFILE)
        if block_size:
            profile["blockxsize"] = block_size
            profile["blockysize"] = block_size

    if tiled and not cog:
        profile["tiled"] = True
        profile["blockxsize"] = block_size
        profile["blockysize"] = block_size

    if compression is not None:
        profile["COMPRESS"] = compression.upper()
        if compression.lower() == "zstd":
            try:
                profile["ZSTD_LEVEL"] = extra_kwargs.pop("compression_level", 6)
            except KeyError:
                pass

    if bigtiff or cog:
        profile["BIGTIFF"] = "YES" if bigtiff else "IF_SAFER"

    profile.update(extra_kwargs)
    return profile


def write_geotiff(
    path: str,
    data: np.ndarray,
    transform: Any,
    crs: Any,
    nodata: Optional[float] = None,
    compression: Optional[str] = "lzw",
    tiled: bool = True,
    block_size: int = 256,
    **kwargs: Any,
) -> str:
    """Write a numpy array to a GeoTIFF file.

    Args:
        path: Output file path.
        data: Numpy array (height, width) or (bands, height, width).
        transform: Affine transform.
        crs: Coordinate Reference System.
        nodata: NoData value.
        compression: Compression algorithm ('lzw', 'deflate', 'zstd', or None).
        tiled: If True, create tiled GeoTIFF.
        block_size: Tile/block size in pixels.
        kwargs: Additional GTiff creation options.

    Returns:
        Path to the written file.
    """
    _validate_compression(compression)

    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    count, height, width = data.shape

    profile = _prepare_profile(
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype=str(data.dtype),
        crs=crs,
        transform=transform,
        nodata=nodata,
        compression=compression,
        tiled=tiled,
        block_size=block_size,
        **kwargs,
    )

    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with rasterio.open(path, "w", **profile) as dst:
            for i in range(count):
                dst.write(data[i], i + 1)
        logger.info("Wrote %s: %dx%dx%d (%s)", path, width, height, count)
    except Exception as exc:
        raise RasterWriteError(f"Failed to write GeoTIFF '{path}': {exc}") from exc

    return os.path.abspath(path)


def write_cog(
    path: str,
    data: np.ndarray,
    transform: Any,
    crs: Any,
    nodata: Optional[float] = None,
    compression: str = "lzw",
    block_size: int = 256,
    overview_levels: Optional[list[int]] = None,
    **kwargs: Any,
) -> str:
    """Write a Cloud Optimized GeoTIFF (COG).

    Uses the GTiff driver with COG-compatible settings (tiled, pixel interleave,
    overviews, BIGTIFF=IF_SAFER).

    Args:
        path: Output file path.
        data: Numpy array (height, width) or (bands, height, width).
        transform: Affine transform.
        crs: Coordinate Reference System.
        nodata: NoData value.
        compression: Compression algorithm.
        block_size: Internal tile size.
        overview_levels: List of overview decimation factors (e.g. [2, 4, 8]).
        kwargs: Additional creation options.

    Returns:
        Path to the written COG.
    """
    _validate_compression(compression)

    if data.ndim == 2:
        data = data[np.newaxis, :, :]

    count, height, width = data.shape

    profile = _prepare_profile(
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype=str(data.dtype),
        crs=crs,
        transform=transform,
        nodata=nodata,
        compression=compression,
        cog=True,
        block_size=block_size,
        **kwargs,
    )

    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with rasterio.open(path, "w", **profile) as dst:
            for i in range(count):
                dst.write(data[i], i + 1)

            if overview_levels:
                dst.build_overviews(overview_levels, rasterio.enums.Resampling.average)

            dst.update_tags(ns="rio_overview", RESAMPLING="average")

        logger.info(
            "Wrote COG %s: %dx%dx%d, compression=%s",
            path, width, height, count, compression,
        )
    except Exception as exc:
        raise RasterWriteError(f"Failed to write COG '{path}': {exc}") from exc

    return os.path.abspath(path)


def copy_with_compression(
    src_path: str,
    dst_path: str,
    compression: str = "lzw",
    **kwargs: Any,
) -> str:
    """Copy a raster file with a different compression algorithm.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        compression: Target compression.
        kwargs: Additional creation options.

    Returns:
        Path to the compressed copy.
    """
    _validate_compression(compression)

    try:
        with rasterio.open(src_path) as src:
            profile = src.profile.copy()
            profile["COMPRESS"] = compression.upper()
            profile["driver"] = "GTiff"
            profile.update(kwargs)

            if compression.lower() == "zstd":
                profile.setdefault("ZSTD_LEVEL", 6)

            os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
            with rasterio.open(dst_path, "w", **profile) as dst:
                for i in range(1, src.count + 1):
                    band_data = src.read(i)
                    dst.write(band_data, i)

                if src.tags():
                    dst.update_tags(**src.tags())

        logger.info(
            "Copied %s -> %s with compression=%s", src_path, dst_path, compression,
        )
        return os.path.abspath(dst_path)

    except Exception as exc:
        raise RasterWriteError(
            f"Failed to copy with compression from '{src_path}' to '{dst_path}': {exc}"
        ) from exc
