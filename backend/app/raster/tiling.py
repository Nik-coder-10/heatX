"""Raster tiling — create tiles, manage tile indices, read specific tiles."""

import logging
import math
import os
from typing import Any, Optional

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

from app.raster.exceptions import (
    RasterNotFoundError,
    RasterTilingError,
)
from app.raster.reader import _open_raster
from app.raster.writer import write_geotiff

logger = logging.getLogger("app.raster.tiling")


def create_tiles(
    src_path: str,
    output_dir: str,
    tile_size: int = 256,
    overlap: int = 0,
    resampling: str = "bilinear",
    prefix: str = "tile",
    compression: Optional[str] = "lzw",
) -> list[dict[str, Any]]:
    """Split a raster into regularly-sized tiles.

    Args:
        src_path: Source raster path.
        output_dir: Output directory for tiles.
        tile_size: Tile dimensions in pixels.
        overlap: Tile overlap in pixels.
        resampling: Resampling method for out_shape reads.
        prefix: Filename prefix for tiles.
        compression: Compression algorithm for tiles.

    Returns:
        List of dicts with keys: path, col, row, width, height, bounds.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    os.makedirs(os.path.abspath(output_dir), exist_ok=True)

    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "average": Resampling.average,
    }
    resample_enum = resampling_map.get(resampling.lower(), Resampling.bilinear)

    try:
        with _open_raster(src_path) as src:
            stride = tile_size - overlap
            n_cols = max(1, math.ceil((src.width - overlap) / stride))
            n_rows = max(1, math.ceil((src.height - overlap) / stride))

            tiles: list[dict[str, Any]] = []

            for row in range(n_rows):
                for col in range(n_cols):
                    col_off = col * stride
                    row_off = row * stride

                    w = Window(
                        col_off=col_off,
                        row_off=row_off,
                        width=min(tile_size, src.width - col_off),
                        height=min(tile_size, src.height - row_off),
                    )

                    if w.width < 1 or w.height < 1:
                        continue

                    data = src.read(window=w, masked=True, resampling=resample_enum)
                    transform = src.window_transform(w)

                    tile_name = f"{prefix}_r{row:04d}_c{col:04d}.tif"
                    tile_path = os.path.join(os.path.abspath(output_dir), tile_name)

                    write_geotiff(
                        tile_path,
                        data,
                        transform=transform,
                        crs=src.crs,
                        nodata=src.nodata,
                        compression=compression,
                    )

                    left, bottom, right, top = src.window_bounds(w)
                    tiles.append({
                        "path": tile_path,
                        "col": col,
                        "row": row,
                        "col_off": col_off,
                        "row_off": row_off,
                        "width": int(w.width),
                        "height": int(w.height),
                        "bounds": {
                            "left": left,
                            "bottom": bottom,
                            "right": right,
                            "top": top,
                        },
                    })

            logger.info(
                "Created %d tiles from '%s' in '%s'",
                len(tiles), src_path, output_dir,
            )
            return tiles

    except RasterTilingError:
        raise
    except Exception as exc:
        raise RasterTilingError(f"Tiling failed for '{src_path}': {exc}") from exc


def create_tile_index(
    src_path: str,
    tile_size: int = 256,
    overlap: int = 0,
) -> dict[str, Any]:
    """Create a metadata index of the tile grid without generating tiles.

    Args:
        src_path: Source raster path.
        tile_size: Tile dimensions in pixels.
        overlap: Tile overlap in pixels.

    Returns:
        Dict with keys: n_cols, n_rows, tile_size, overlap, tiles, bounds.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            stride = tile_size - overlap
            n_cols = max(1, math.ceil((src.width - overlap) / stride))
            n_rows = max(1, math.ceil((src.height - overlap) / stride))

            tiles = []
            for row in range(n_rows):
                for col in range(n_cols):
                    col_off = col * stride
                    row_off = row * stride

                    w = Window(
                        col_off=col_off,
                        row_off=row_off,
                        width=min(tile_size, src.width - col_off),
                        height=min(tile_size, src.height - row_off),
                    )

                    if w.width < 1 or w.height < 1:
                        continue

                    left, bottom, right, top = src.window_bounds(w)
                    tiles.append({
                        "col": col,
                        "row": row,
                        "col_off": col_off,
                        "row_off": row_off,
                        "width": int(w.width),
                        "height": int(w.height),
                        "bounds": {
                            "left": left,
                            "bottom": bottom,
                            "right": right,
                            "top": top,
                        },
                    })

            return {
                "path": os.path.abspath(src_path),
                "width": src.width,
                "height": src.height,
                "n_cols": n_cols,
                "n_rows": n_rows,
                "tile_size": tile_size,
                "overlap": overlap,
                "tiles": tiles,
                "bounds": {
                    "left": src.bounds.left,
                    "bottom": src.bounds.bottom,
                    "right": src.bounds.right,
                    "top": src.bounds.top,
                },
            }

    except Exception as exc:
        raise RasterTilingError(
            f"Failed to create tile index for '{src_path}': {exc}"
        ) from exc


def read_tile(
    src_path: str,
    tile_x: int,
    tile_y: int,
    tile_size: int = 256,
    overlap: int = 0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read a specific tile from a raster without generating all tiles.

    Args:
        src_path: Source raster path.
        tile_x: Tile column index (0-based).
        tile_y: Tile row index (0-based).
        tile_size: Tile dimensions in pixels.
        overlap: Tile overlap in pixels.

    Returns:
        Tuple of (tile data, metadata dict with transform, crs, bounds).
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            stride = tile_size - overlap
            col_off = tile_x * stride
            row_off = tile_y * stride

            if col_off >= src.width or row_off >= src.height:
                raise RasterTilingError(
                    f"Tile ({tile_x}, {tile_y}) is outside raster dimensions "
                    f"({src.width}x{src.height})"
                )

            w = Window(
                col_off=col_off,
                row_off=row_off,
                width=min(tile_size, src.width - col_off),
                height=min(tile_size, src.height - row_off),
            )

            data = src.read(masked=True, window=w)
            transform = src.window_transform(w)
            left, bottom, right, top = src.window_bounds(w)

            meta = {
                "transform": transform,
                "crs": src.crs,
                "crs_str": str(src.crs) if src.crs else None,
                "width": int(w.width),
                "height": int(w.height),
                "bounds": {
                    "left": left,
                    "bottom": bottom,
                    "right": right,
                    "top": top,
                },
            }

            if data.shape[0] == 1:
                data = data[0]

            return data, meta

    except RasterTilingError:
        raise
    except Exception as exc:
        raise RasterTilingError(
            f"Failed to read tile ({tile_x}, {tile_y}) from '{src_path}': {exc}"
        ) from exc
