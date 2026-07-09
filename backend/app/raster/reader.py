"""Raster reader — GeoTIFF and COG reading with windowed, bbox, polygon, and streaming support."""

import logging
import math
import os
from typing import Any, Generator, Optional, Union

import numpy as np
import rasterio
from rasterio import windows
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.warp import transform_bounds
from shapely.geometry import shape

from app.raster.exceptions import (
    CorruptedRasterError,
    MemoryLimitError,
    RasterNotFoundError,
    RasterReadError,
)

logger = logging.getLogger("app.raster.reader")

_MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB default


def _open_raster(path: str) -> rasterio.DatasetReader:
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"Raster file not found: {path}")
    try:
        return rasterio.open(path)
    except rasterio.errors.RasterioIOError as exc:
        raise CorruptedRasterError(f"Cannot open raster '{path}': {exc}") from exc
    except Exception as exc:
        raise RasterReadError(f"Failed to open raster '{path}': {exc}") from exc


def _check_memory(height: int, width: int, count: int, dtype: np.dtype) -> None:
    total = height * width * count * dtype.itemsize
    if total > _MEMORY_LIMIT_BYTES:
        raise MemoryLimitError(
            f"Read would require {total / (1024**3):.2f} GiB, "
            f"exceeding limit of {_MEMORY_LIMIT_BYTES / (1024**3):.2f} GiB. "
            f"Use windowed reading or out_shape parameter."
        )


def read_bands(
    path: str,
    bands: Optional[list[int]] = None,
    window: Optional[tuple[tuple[int, int], tuple[int, int]]] = None,
    out_shape: Optional[tuple[int, int]] = None,
    masked: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read selected bands from a raster file.

    Args:
        path: Path to the raster file.
        bands: 1-based band indices (default: all bands).
        window: Pixel window ((row_start, row_stop), (col_start, col_stop)).
        out_shape: (height, width) for downsampled/upsampled read.
        masked: If True, return a masked array with NoData masked.

    Returns:
        Tuple of (data array, metadata dict).
        Data shape: (bands, height, width) or (height, width) for single band.
    """
    with _open_raster(path) as src:
        if bands is None:
            bands = list(range(1, src.count + 1))
        if bands and (max(bands) > src.count or min(bands) < 1):
            raise RasterReadError(
                f"Band(s) {bands} out of range (1-{src.count}) for '{path}'"
            )

        meta = {
            "driver": src.driver,
            "dtype": src.dtypes[0],
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "bounds": src.bounds,
        }

        data = src.read(
            bands,
            window=window,
            out_shape=out_shape,
            masked=masked,
            resampling=Resampling.bilinear,
        )

        if out_shape:
            meta["transform"] = src.window_transform(window) if window else src.transform

        if len(bands) == 1:
            data = data[0]

        return data, meta


def read_bbox(
    path: str,
    bbox: tuple[float, float, float, float],
    dst_crs: Optional[str] = None,
    bands: Optional[list[int]] = None,
    out_shape: Optional[tuple[int, int]] = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read raster data intersecting a bounding box.

    Args:
        path: Path to the raster file.
        bbox: (left, bottom, right, top) in geographic coordinates.
        dst_crs: CRS of the bbox (default: raster CRS).
        bands: 1-based band indices.
        out_shape: Optional output shape for resampling.

    Returns:
        Tuple of (data array, metadata dict).
    """
    with _open_raster(path) as src:
        src_crs = src.crs
        if dst_crs is not None and src_crs is not None:
            try:
                from rasterio.crs import CRS
                target_crs = CRS.from_user_input(dst_crs)
                if str(target_crs) != str(src_crs):
                    bbox_src = transform_bounds(target_crs, src_crs, *bbox)
                else:
                    bbox_src = bbox
            except Exception:
                bbox_src = bbox
        else:
            bbox_src = bbox

        window = windows.from_bounds(*bbox_src, transform=src.transform)
        window = window.round_lengths().crop(src.width, src.height)

        if window.width < 1 or window.height < 1:
            raise RasterReadError(
                f"Bounding box {bbox} does not overlap raster extent {src.bounds}"
            )

        meta = {
            "driver": src.driver,
            "dtype": src.dtypes[0],
            "crs": src.crs,
            "nodata": src.nodata,
            "bounds": src.bounds,
        }

        if bands is None:
            bands = list(range(1, src.count + 1))

        window_transform = src.window_transform(window)

        data = src.read(
            bands,
            window=window,
            out_shape=out_shape,
            masked=True,
            resampling=Resampling.bilinear,
        )

        meta["transform"] = window_transform

        if len(bands) == 1:
            data = data[0]

        return data, meta


def read_aoi(
    path: str,
    geometry: dict[str, Any],
    dst_crs: Optional[str] = None,
    bands: Optional[list[int]] = None,
    invert: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read raster data masked to a polygon AOI.

    Args:
        path: Path to the raster file.
        geometry: GeoJSON-like geometry dict (Polygon, MultiPolygon).
        dst_crs: CRS of the geometry (default: raster CRS).
        bands: 1-based band indices.
        invert: If True, mask the area outside the polygon instead.

    Returns:
        Tuple of (masked data array, metadata dict).
    """
    with _open_raster(path) as src:
        src_crs = src.crs
        geom = shape(geometry)

        if dst_crs is not None and src_crs is not None:
            from rasterio.crs import CRS
            from rasterio.warp import transform_geom
            target_crs = CRS.from_user_input(dst_crs)
            if str(target_crs) != str(src_crs):
                geom_proj = transform_geom(target_crs, src_crs, geometry)
                geom = shape(geom_proj)

        if bands is None:
            bands = list(range(1, src.count + 1))

        mask = geometry_mask(
            [geom],
            transform=src.transform,
            invert=not invert,
            out_shape=(src.height, src.width),
        )

        data = src.read(bands, masked=True)
        if len(bands) == 1:
            data = data[0]

        if data.ndim == 2:
            data = np.ma.array(data, mask=mask)
        else:
            data = np.ma.array(data, mask=np.broadcast_to(mask, data.shape))

        meta = {
            "driver": src.driver,
            "dtype": src.dtypes[0],
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "bounds": src.bounds,
        }

        return data, meta


def read_window(
    path: str,
    window: tuple[tuple[int, int], tuple[int, int]],
    bands: Optional[list[int]] = None,
    out_shape: Optional[tuple[int, int]] = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read a specific pixel window from a raster.

    Args:
        path: Path to the raster file.
        window: ((row_start, row_stop), (col_start, col_stop)).
        bands: 1-based band indices.
        out_shape: Output shape for resampling within the window.

    Returns:
        Tuple of (data array, metadata dict).
    """
    return read_bands(path, bands=bands, window=window, out_shape=out_shape)


def read_memmap(path: str, band: int = 1) -> np.ndarray:
    """Memory-map a raster band for efficient random access.

    Args:
        path: Path to the raster file.
        band: 1-based band index.

    Returns:
        Numpy array for the band (memory mapping via GDAL internal caching).
    """
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterReadError(
                f"Band {band} out of range (1-{src.count}) for '{path}'"
            )
        data = src.read(band)
        return data


def stream_blocks(
    path: str,
    band: int = 1,
    block_size: int = 256,
) -> Generator[tuple[np.ndarray, tuple[int, int], dict[str, Any]], None, None]:
    """Stream raster data in blocks, yielding each block with its metadata.

    Args:
        path: Path to the raster file.
        band: 1-based band index.
        block_size: Size of each block in pixels.

    Yields:
        Tuple of (block_data, (row_offset, col_offset), metadata_dict).
    """
    with _open_raster(path) as src:
        if band < 1 or band > src.count:
            raise RasterReadError(
                f"Band {band} out of range (1-{src.count}) for '{path}'"
            )

        meta = {
            "driver": src.driver,
            "dtype": src.dtypes[0],
            "crs": src.crs,
            "transform": src.transform,
            "nodata": src.nodata,
            "band": band,
        }

        n_cols = math.ceil(src.width / block_size)
        n_rows = math.ceil(src.height / block_size)

        for row in range(n_rows):
            for col in range(n_cols):
                col_off = col * block_size
                row_off = row * block_size
                w = windows.Window(
                    col_off=col_off,
                    row_off=row_off,
                    width=min(block_size, src.width - col_off),
                    height=min(block_size, src.height - row_off),
                )
                block = src.read(band, window=w, masked=True)
                yield block, (row_off, col_off), meta


def get_raster_info(path: str) -> dict[str, Any]:
    """Return a lightweight info dict without reading pixel data.

    Args:
        path: Path to the raster file.

    Returns:
        Dict with key metadata fields.
    """
    with _open_raster(path) as src:
        return {
            "path": os.path.abspath(path),
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtype": src.dtypes[0] if src.dtypes else None,
            "crs": str(src.crs) if src.crs else None,
            "transform": list(src.transform) if src.transform else None,
            "bounds": {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top,
            },
            "driver": src.driver,
            "nodata": src.nodata,
            "compression": src.compression.value if src.compression else None,
            "tiled": src.profile.get("tiled", False),
            "overviews": [],
        }
