"""Raster transformations — crop, clip, mask, reproject, resample, merge, split, band ops."""

import logging
import os
from typing import Any, Optional

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.merge import merge as rio_merge
from rasterio.warp import (
    reproject as rio_reproject,
    calculate_default_transform,
    transform_geom,
)
from shapely.geometry import shape

from app.raster.exceptions import (
    CorruptedRasterError,
    RasterNotFoundError,
    RasterTransformError,
)
from app.raster.reader import _open_raster
from app.raster.writer import write_geotiff

logger = logging.getLogger("app.raster.transform")


def _abs_path(directory: str, filename: str) -> str:
    os.makedirs(os.path.abspath(directory), exist_ok=True)
    return os.path.join(os.path.abspath(directory), filename)


def crop(
    src_path: str,
    dst_path: str,
    bbox: tuple[float, float, float, float],
    crs: Optional[Any] = None,
    compression: Optional[str] = "lzw",
) -> str:
    """Crop a raster to a bounding box.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        bbox: (left, bottom, right, top) in the CRS of the raster.
        crs: CRS of the bbox if different from raster.
        compression: Compression algorithm.

    Returns:
        Path to the cropped raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            window = src.window(*bbox)
            window = window.round_lengths().crop(src.width, src.height)

            if window.width < 1 or window.height < 1:
                raise RasterTransformError(
                    f"Bounding box {bbox} does not overlap raster extent {src.bounds}"
                )

            transform = src.window_transform(window)
            data = src.read(window=window, masked=True)

            return write_geotiff(
                dst_path,
                data,
                transform=transform,
                crs=src.crs,
                nodata=src.nodata,
                compression=compression,
            )

    except RasterTransformError:
        raise
    except Exception as exc:
        raise RasterTransformError(f"Crop failed for '{src_path}': {exc}") from exc


def clip(
    src_path: str,
    dst_path: str,
    geometry: dict[str, Any],
    dst_crs: Optional[Any] = None,
    compression: Optional[str] = "lzw",
    crop_to_geom: bool = True,
) -> str:
    """Clip a raster to a polygon geometry.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        geometry: GeoJSON-like polygon geometry.
        dst_crs: CRS of the geometry (default: raster CRS).
        compression: Compression algorithm.
        crop_to_geom: If True, crop extent to geometry bounds before clipping.

    Returns:
        Path to the clipped raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            geom = shape(geometry)

            if dst_crs is not None:
                src_crs = src.crs
                if src_crs and str(CRS.from_user_input(dst_crs)) != str(src_crs):
                    geom_proj = transform_geom(
                        CRS.from_user_input(dst_crs), src_crs, geometry
                    )
                    geom = shape(geom_proj)

            data = src.read(masked=True)
            mask = geometry_mask(
                [geom],
                transform=src.transform,
                invert=True,
                out_shape=(src.height, src.width),
            )

            count = data.shape[0]
            for i in range(count):
                data[i] = np.ma.array(data[i], mask=mask)

            out_transform = src.transform
            out_height = src.height
            out_width = src.width

            if crop_to_geom:
                bounds = geom.bounds
                window = src.window(*bounds)
                window = window.round_lengths().crop(src.width, src.height)
                if window.width > 0 and window.height > 0:
                    out_transform = src.window_transform(window)
                    out_height = int(window.height)
                    out_width = int(window.width)
                    data = src.read(
                        window=window,
                        masked=True,
                    )
                    mask_cropped = geometry_mask(
                        [geom],
                        transform=out_transform,
                        invert=True,
                        out_shape=(out_height, out_width),
                    )
                    for i in range(count):
                        data[i] = np.ma.array(data[i], mask=mask_cropped)

            return write_geotiff(
                dst_path,
                data,
                transform=out_transform,
                crs=src.crs,
                nodata=src.nodata,
                compression=compression,
            )

    except RasterTransformError:
        raise
    except Exception as exc:
        raise RasterTransformError(f"Clip failed for '{src_path}': {exc}") from exc


def mask(
    src_path: str,
    dst_path: str,
    geometry: dict[str, Any],
    dst_crs: Optional[Any] = None,
    invert: bool = False,
    compression: Optional[str] = "lzw",
) -> str:
    """Apply a polygon mask to a raster.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        geometry: GeoJSON-like polygon geometry.
        dst_crs: CRS of the geometry.
        invert: If True, mask area outside geometry.
        compression: Compression algorithm.

    Returns:
        Path to the masked raster.
    """
    return clip(
        src_path, dst_path, geometry, dst_crs=dst_crs,
        compression=compression, crop_to_geom=not invert,
    )


def reproject(
    src_path: str,
    dst_path: str,
    dst_crs: Any,
    resolution: Optional[float] = None,
    resampling: str = "bilinear",
    compression: Optional[str] = "lzw",
) -> str:
    """Reproject a raster to a different CRS.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        dst_crs: Target CRS (EPSG code string, CRS object, etc.).
        resolution: Target resolution in destination CRS units.
        resampling: Resampling method.
        compression: Compression algorithm.

    Returns:
        Path to the reprojected raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "average": Resampling.average,
        "lanczos": Resampling.lanczos,
        "mode": Resampling.mode,
        "max": Resampling.max,
        "min": Resampling.min,
        "med": Resampling.med,
        "sum": Resampling.sum,
    }

    resample_enum = resampling_map.get(resampling.lower(), Resampling.bilinear)

    try:
        with _open_raster(src_path) as src:
            dst_crs_obj = CRS.from_user_input(dst_crs)

            transform, width, height = calculate_default_transform(
                src.crs,
                dst_crs_obj,
                src.width,
                src.height,
                resolution=resolution,
                **src.bounds._asdict(),
            )

            profile = src.profile.copy()
            profile.update(
                {
                    "crs": dst_crs_obj,
                    "transform": transform,
                    "width": width,
                    "height": height,
                    "COMPRESS": compression.upper() if compression else None,
                    "driver": "GTiff",
                }
            )

            os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
            with rasterio.open(dst_path, "w", **profile) as dst:
                for i in range(1, src.count + 1):
                    rio_reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs_obj,
                        resampling=resample_enum,
                    )
                dst.update_tags(**src.tags())

        logger.info(
            "Reprojected '%s' -> '%s' (%s -> %s)",
            src_path, dst_path, src.crs, dst_crs_obj,
        )
        return os.path.abspath(dst_path)

    except Exception as exc:
        raise RasterTransformError(
            f"Reprojection failed for '{src_path}': {exc}"
        ) from exc


def resample(
    src_path: str,
    dst_path: str,
    scale_factor: Optional[float] = None,
    resolution: Optional[tuple[float, float]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    resampling: str = "bilinear",
    compression: Optional[str] = "lzw",
) -> str:
    """Resample a raster to a different resolution or dimensions.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        scale_factor: Multiplicative scale factor (<1 = downsample, >1 = upsample).
        resolution: Target (x_res, y_res) in CRS units.
        width: Target width in pixels.
        height: Target height in pixels.
        resampling: Resampling method.
        compression: Compression algorithm.

    Returns:
        Path to the resampled raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    if scale_factor is None and resolution is None and width is None and height is None:
        raise RasterTransformError(
            "Specify at least one of scale_factor, resolution, width, or height"
        )

    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "average": Resampling.average,
        "lanczos": Resampling.lanczos,
        "mode": Resampling.mode,
    }

    resample_enum = resampling_map.get(resampling.lower(), Resampling.bilinear)

    try:
        with _open_raster(src_path) as src:
            if scale_factor is not None:
                out_width = max(1, int(round(src.width * scale_factor)))
                out_height = max(1, int(round(src.height * scale_factor)))
            elif width is not None and height is not None:
                out_width = width
                out_height = height
            elif width is not None:
                ratio = width / src.width
                out_width = width
                out_height = max(1, int(round(src.height * ratio)))
            elif height is not None:
                ratio = height / src.height
                out_height = height
                out_width = max(1, int(round(src.width * ratio)))
            else:
                x_res, y_res = resolution
                out_width = max(1, int(round(abs(src.bounds.right - src.bounds.left) / x_res)))
                out_height = max(1, int(round(abs(src.bounds.top - src.bounds.bottom) / y_res)))

            data = src.read(
                out_shape=(src.count, out_height, out_width),
                resampling=resample_enum,
                masked=True,
            )

            transform = src.transform * src.transform.scale(
                src.width / out_width,
                src.height / out_height,
            )

            return write_geotiff(
                dst_path,
                data,
                transform=transform,
                crs=src.crs,
                nodata=src.nodata,
                compression=compression,
            )

    except Exception as exc:
        raise RasterTransformError(
            f"Resample failed for '{src_path}': {exc}"
        ) from exc


def merge(
    src_paths: list[str],
    dst_path: str,
    compression: Optional[str] = "lzw",
) -> str:
    """Merge multiple rasters into a single raster.

    Args:
        src_paths: List of paths to rasters to merge.
        dst_path: Destination raster path.
        compression: Compression algorithm.

    Returns:
        Path to the merged raster.
    """
    if not src_paths:
        raise RasterTransformError("No source paths provided for merge")

    for p in src_paths:
        if not os.path.isfile(p):
            raise RasterNotFoundError(f"Source file not found: {p}")

    try:
        srcs = [rasterio.open(p) for p in src_paths]
        mosaic, out_transform = rio_merge(srcs)

        crs = srcs[0].crs
        nodata = srcs[0].nodata

        for s in srcs:
            s.close()

        return write_geotiff(
            dst_path,
            mosaic,
            transform=out_transform,
            crs=crs,
            nodata=nodata,
            compression=compression,
        )

    except Exception as exc:
        raise RasterTransformError(f"Merge failed: {exc}") from exc


def split(src_path: str, dst_dir: str, prefix: str = "band") -> list[str]:
    """Split a multi-band raster into individual single-band files.

    Args:
        src_path: Source raster path.
        dst_dir: Output directory for band files.
        prefix: Filename prefix.

    Returns:
        List of paths to the band files.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            paths: list[str] = []
            for i in range(1, src.count + 1):
                band_path = _abs_path(dst_dir, f"{prefix}_{i:02d}.tif")
                band_data = src.read(i, masked=True)
                write_geotiff(
                    band_path,
                    band_data,
                    transform=src.transform,
                    crs=src.crs,
                    nodata=src.nodata,
                )
                paths.append(band_path)

        logger.info("Split '%s' into %d bands in '%s'", src_path, len(paths), dst_dir)
        return paths

    except Exception as exc:
        raise RasterTransformError(f"Split failed for '{src_path}': {exc}") from exc


def extract_band(
    src_path: str,
    dst_path: str,
    band: int,
    compression: Optional[str] = "lzw",
) -> str:
    """Extract a single band from a multi-band raster.

    Args:
        src_path: Source raster path.
        dst_path: Destination raster path.
        band: 1-based band index.
        compression: Compression algorithm.

    Returns:
        Path to the extracted band raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            if band < 1 or band > src.count:
                raise RasterTransformError(
                    f"Band {band} out of range (1-{src.count}) for '{src_path}'"
                )

            band_data = src.read(band, masked=True)

            return write_geotiff(
                dst_path,
                band_data,
                transform=src.transform,
                crs=src.crs,
                nodata=src.nodata,
                compression=compression,
            )

    except Exception as exc:
        raise RasterTransformError(
            f"Failed to extract band {band} from '{src_path}': {exc}"
        ) from exc


def stack_bands(
    src_paths: list[str],
    dst_path: str,
    compression: Optional[str] = "lzw",
) -> str:
    """Stack multiple single-band rasters into a multi-band raster.

    Args:
        src_paths: List of paths to single-band rasters.
        dst_path: Destination multi-band raster path.
        compression: Compression algorithm.

    Returns:
        Path to the stacked raster.
    """
    if not src_paths:
        raise RasterTransformError("No source paths provided for stack")

    for p in src_paths:
        if not os.path.isfile(p):
            raise RasterNotFoundError(f"Source file not found: {p}")

    try:
        srcs = [rasterio.open(p) for p in src_paths]
        ref = srcs[0]

        crs = ref.crs
        transform = ref.transform
        nodata = ref.nodata
        height, width = ref.height, ref.width
        dtype = ref.dtypes[0]

        for s in srcs[1:]:
            if s.crs != crs:
                logger.warning("CRS mismatch in stack: %s vs %s", s.crs, crs)
            if s.height != height or s.width != width:
                raise RasterTransformError(
                    f"Dimension mismatch: {s.height}x{s.width} vs {height}x{width}"
                )

        count = len(srcs)
        data = np.zeros((count, height, width), dtype=dtype)

        for i, s in enumerate(srcs):
            band_data = s.read(1, masked=True)
            data[i] = np.ma.filled(band_data, nodata if nodata is not None else 0)

        for s in srcs:
            s.close()

        return write_geotiff(
            dst_path,
            data,
            transform=transform,
            crs=crs,
            nodata=nodata,
            compression=compression,
        )

    except Exception as exc:
        raise RasterTransformError(f"Stack bands failed: {exc}") from exc
