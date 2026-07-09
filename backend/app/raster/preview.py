"""Raster preview generation — PNG, JPEG, thumbnails, false-color composites."""

import logging
import os
from typing import Any, Optional

import numpy as np
import rasterio
from rasterio.enums import Resampling

from app.raster.exceptions import (
    RasterNotFoundError,
    RasterPreviewError,
)
from app.raster.reader import _open_raster

logger = logging.getLogger("app.raster.preview")

_MAX_PREVIEW_DIMENSION = 2048
_DEFAULT_THUMBNAIL_SIZE = (256, 256)


def _scale_to_uint8(data: np.ndarray, nodata: Optional[float] = None) -> np.ndarray:
    """Scale any numeric array to 0-255 uint8 for image output.

    Handles NaN, Inf, and NoData values. Uses 2nd-98th percentile
    stretch for robust scaling.
    """
    if isinstance(data, np.ma.MaskedArray):
        fill_value = nodata if nodata is not None else 0
        data = np.ma.filled(data, fill_value)

    data = np.nan_to_num(data, nan=0.0, posinf=255.0, neginf=0.0)

    p2, p98 = np.percentile(data, [2, 98])
    if p98 - p2 < 1e-10:
        p2 = data.min()
        p98 = data.max()
    if p98 - p2 < 1e-10:
        return np.zeros(data.shape, dtype=np.uint8)

    scaled = (data - p2) / (p98 - p2) * 255.0
    scaled = np.clip(scaled, 0, 255)
    return scaled.astype(np.uint8)


def _compute_out_shape(
    src_width: int,
    src_height: int,
    scale_factor: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> tuple[int, int]:
    """Compute output dimensions respecting max preview dimension."""
    if scale_factor is not None:
        out_w = max(1, int(round(src_width * scale_factor)))
        out_h = max(1, int(round(src_height * scale_factor)))
    elif width is not None and height is not None:
        out_w = width
        out_h = height
    elif width is not None:
        ratio = width / src_width
        out_w = width
        out_h = max(1, int(round(src_height * ratio)))
    elif height is not None:
        ratio = height / src_height
        out_h = height
        out_w = max(1, int(round(src_width * ratio)))
    else:
        if src_width > _MAX_PREVIEW_DIMENSION or src_height > _MAX_PREVIEW_DIMENSION:
            ratio = _MAX_PREVIEW_DIMENSION / max(src_width, src_height)
            out_w = max(1, int(round(src_width * ratio)))
            out_h = max(1, int(round(src_height * ratio)))
        else:
            out_w = src_width
            out_h = src_height

    if out_w > _MAX_PREVIEW_DIMENSION or out_h > _MAX_PREVIEW_DIMENSION:
        ratio = _MAX_PREVIEW_DIMENSION / max(out_w, out_h)
        out_w = max(1, int(round(out_w * ratio)))
        out_h = max(1, int(round(out_h * ratio)))

    return out_w, out_h


def create_png_preview(
    src_path: str,
    dst_path: str,
    band: int = 1,
    scale_factor: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """Create a PNG preview of a single raster band.

    Args:
        src_path: Source raster path.
        dst_path: Output PNG path.
        band: 1-based band index.
        scale_factor: Scale factor for downsampling.
        width: Output width in pixels.
        height: Output height in pixels.

    Returns:
        Path to the generated PNG.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            if band < 1 or band > src.count:
                raise RasterPreviewError(
                    f"Band {band} out of range (1-{src.count})"
                )

            out_w, out_h = _compute_out_shape(
                src.width, src.height, scale_factor, width, height
            )

            data = src.read(band, out_shape=(out_h, out_w), masked=True,
                           resampling=Resampling.bilinear)
            img = _scale_to_uint8(data, src.nodata)

        from PIL import Image
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
        Image.fromarray(img, mode="L").save(dst_path, format="PNG")

        logger.info(
            "Created PNG preview '%s' (%dx%d)", dst_path, out_w, out_h
        )
        return os.path.abspath(dst_path)

    except ImportError:
        raise RasterPreviewError("PIL/Pillow is required for PNG preview generation")
    except Exception as exc:
        raise RasterPreviewError(
            f"Failed to create PNG preview for '{src_path}': {exc}"
        ) from exc


def create_jpeg_preview(
    src_path: str,
    dst_path: str,
    quality: int = 85,
    band: int = 1,
    scale_factor: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """Create a JPEG preview of a single raster band.

    Args:
        src_path: Source raster path.
        dst_path: Output JPEG path.
        quality: JPEG quality (1-100).
        band: 1-based band index.
        scale_factor: Scale factor for downsampling.
        width: Output width in pixels.
        height: Output height in pixels.

    Returns:
        Path to the generated JPEG.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            if band < 1 or band > src.count:
                raise RasterPreviewError(
                    f"Band {band} out of range (1-{src.count})"
                )

            out_w, out_h = _compute_out_shape(
                src.width, src.height, scale_factor, width, height
            )

            data = src.read(band, out_shape=(out_h, out_w), masked=True,
                           resampling=Resampling.bilinear)
            img = _scale_to_uint8(data, src.nodata)

        from PIL import Image
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
        Image.fromarray(img, mode="L").save(
            dst_path, format="JPEG", quality=quality
        )

        logger.info(
            "Created JPEG preview '%s' (%dx%d, q=%d)", dst_path, out_w, out_h, quality
        )
        return os.path.abspath(dst_path)

    except ImportError:
        raise RasterPreviewError("PIL/Pillow is required for JPEG preview generation")
    except Exception as exc:
        raise RasterPreviewError(
            f"Failed to create JPEG preview for '{src_path}': {exc}"
        ) from exc


def create_thumbnail(
    src_path: str,
    dst_path: str,
    size: tuple[int, int] = _DEFAULT_THUMBNAIL_SIZE,
    band: int = 1,
) -> str:
    """Create a small thumbnail of a raster band.

    Args:
        src_path: Source raster path.
        dst_path: Output thumbnail path.
        size: (width, height) in pixels.
        band: 1-based band index.

    Returns:
        Path to the generated thumbnail.
    """
    return create_png_preview(
        src_path, dst_path, band=band, width=size[0], height=size[1],
    )


def create_false_color_composite(
    src_path: str,
    dst_path: str,
    red_band: int = 3,
    green_band: int = 2,
    blue_band: int = 1,
    scale_factor: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """Create a false-color RGB composite from three bands.

    Typical band assignments:
    - NIR (4), Red (3), Green (2) — vegetation analysis
    - SWIR (5), NIR (4), Red (3) — moisture analysis

    Args:
        src_path: Source raster path.
        dst_path: Output image path (PNG recommended).
        red_band: 1-based band index for the red channel.
        green_band: 1-based band index for the green channel.
        blue_band: 1-based band index for the blue channel.
        scale_factor: Scale factor for downsampling.
        width: Output width in pixels.
        height: Output height in pixels.

    Returns:
        Path to the generated composite image.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with _open_raster(src_path) as src:
            max_band = max(red_band, green_band, blue_band)
            if max_band > src.count:
                raise RasterPreviewError(
                    f"Band {max_band} out of range (1-{src.count})"
                )

            out_w, out_h = _compute_out_shape(
                src.width, src.height, scale_factor, width, height
            )

            red = _scale_to_uint8(
                src.read(red_band, out_shape=(out_h, out_w), masked=True,
                        resampling=Resampling.bilinear),
                src.nodata,
            )
            green = _scale_to_uint8(
                src.read(green_band, out_shape=(out_h, out_w), masked=True,
                        resampling=Resampling.bilinear),
                src.nodata,
            )
            blue = _scale_to_uint8(
                src.read(blue_band, out_shape=(out_h, out_w), masked=True,
                        resampling=Resampling.bilinear),
                src.nodata,
            )

        rgb = np.stack([red, green, blue], axis=-1)

        from PIL import Image
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
        Image.fromarray(rgb, mode="RGB").save(dst_path, format="PNG")

        logger.info(
            "Created false-color composite '%s' (R=%d, G=%d, B=%d)",
            dst_path, red_band, green_band, blue_band,
        )
        return os.path.abspath(dst_path)

    except ImportError:
        raise RasterPreviewError(
            "PIL/Pillow is required for false-color composite generation"
        )
    except Exception as exc:
        raise RasterPreviewError(
            f"Failed to create false-color composite for '{src_path}': {exc}"
        ) from exc
