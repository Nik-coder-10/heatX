"""Raster metadata extraction — the single source of truth for raster properties."""

import logging
from typing import Any, Optional

import rasterio

from app.raster.exceptions import RasterNotFoundError, RasterReadError

logger = logging.getLogger("app.raster.metadata")


def extract_metadata(path: str, detailed: bool = False) -> dict[str, Any]:
    """Extract all metadata from a raster file.

    Args:
        path: Path to the raster file.
        detailed: If True, include per-band details (tags, descriptions).

    Returns:
        Dict with keys: width, height, count, resolutions, crs, transform,
        bounds, driver, dtype, nodata, compression, tiled, block_size,
        color_interp, overviews, tags.
    """
    import os
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"Raster file not found: {path}")

    try:
        with rasterio.open(path) as src:
            width = src.width
            height = src.height
            count = src.count
            crs = src.crs
            transform = src.transform
            bounds = src.bounds
            driver = src.driver
            dtype = src.dtypes[0] if src.dtypes else "unknown"
            nodata = src.nodata
            compression = src.compression.value if src.compression else None
            tiled = src.profile.get("tiled", False)
            bs = src.profile.get("blockxsize", 256)
            block_size = [bs, src.profile.get("blockysize", bs)]

            resolutions = (
                abs(transform.a),
                abs(transform.e),
            ) if transform else (0.0, 0.0)

            try:
                color_interp = [c.name for c in src.colorinterp]
            except Exception:
                color_interp = [f"band_{i}" for i in range(1, count + 1)]

            overviews = []

            tags = src.tags()

            result: dict[str, Any] = {
                "path": os.path.abspath(path),
                "width": width,
                "height": height,
                "count": count,
                "resolutions": resolutions,
                "crs": str(crs) if crs else None,
                "crs_wkt": str(crs.to_wkt()) if crs else None,
                "transform": list(transform) if transform else None,
                "bounds": {
                    "left": bounds.left,
                    "bottom": bounds.bottom,
                    "right": bounds.right,
                    "top": bounds.top,
                },
                "driver": driver,
                "dtype": dtype,
                "nodata": nodata,
                "compression": compression,
                "tiled": tiled,
                "block_size": block_size,
                "color_interp": color_interp,
                "overviews": overviews,
                "overview_count": len(overviews),
                "tags": tags,
                "file_size_bytes": os.path.getsize(path),
            }

            if detailed:
                per_band = []
                for i in range(1, count + 1):
                    band_tags = src.tags(i)
                    band_meta = {
                        "band": i,
                        "dtype": src.dtypes[i - 1] if i - 1 < len(src.dtypes) else None,
                        "nodata": src.nodata if src.nodata is not None else None,
                        "color_interp": color_interp[i - 1] if color_interp and i - 1 < len(color_interp) else None,
                        "block_size": [src.profile.get("blockxsize", 256), src.profile.get("blockysize", 256)],
                        "tags": band_tags,
                        "descriptions": src.descriptions[i - 1] if src.descriptions and i - 1 < len(src.descriptions) else None,
                    }
                    per_band.append(band_meta)
                result["bands"] = per_band

            return result

    except RasterNotFoundError:
        raise
    except Exception as exc:
        raise RasterReadError(f"Failed to read metadata from '{path}': {exc}") from exc
