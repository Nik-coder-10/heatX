"""Compression utilities for raster files."""

import logging
import os
from typing import Any, Optional

import rasterio

from app.raster.exceptions import (
    CorruptedRasterError,
    RasterCompressionError,
    RasterNotFoundError,
    UnsupportedFormatError,
)
from app.raster.writer import _validate_compression

logger = logging.getLogger("app.raster.compression")

_SUPPORTED_ALGORITHMS = {"lzw", "deflate", "zstd"}
_DEFAULT_LEVELS = {"lzw": None, "deflate": 6, "zstd": 6}


def get_compression_info(path: str) -> dict[str, Any]:
    """Get compression details for a raster file.

    Args:
        path: Path to the raster file.

    Returns:
        Dict with keys: algorithm, level, ratio, original_size, compressed_size.
    """
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    compressed_size = os.path.getsize(path)

    try:
        with rasterio.open(path) as src:
            compression = src.compression
            algorithm = compression.value if compression else None
            level = None

            tags = src.tags()
            zstd_level = tags.get("ZSTD_LEVEL")
            if zstd_level:
                level = int(zstd_level)
    except Exception as exc:
        raise RasterCompressionError(
            f"Failed to read compression info from '{path}': {exc}"
        ) from exc

    raw_size = compressed_size

    return {
        "path": os.path.abspath(path),
        "algorithm": algorithm,
        "level": level,
        "compressed_size_bytes": compressed_size,
        "compression_ratio": raw_size / compressed_size if compressed_size > 0 else 1.0,
    }


def compress(
    src_path: str,
    dst_path: str,
    algorithm: str = "lzw",
    level: Optional[int] = None,
    **kwargs: Any,
) -> str:
    """Compress a raster file using the specified algorithm.

    Args:
        src_path: Source raster path.
        dst_path: Destination path for compressed raster.
        algorithm: Compression algorithm ('lzw', 'deflate', 'zstd').
        level: Compression level (algorithm-specific).
        kwargs: Additional GDAL creation options.

    Returns:
        Path to the compressed raster.
    """
    algorithm_lower = algorithm.lower()
    if algorithm_lower not in _SUPPORTED_ALGORITHMS:
        raise UnsupportedFormatError(
            f"Unsupported compression algorithm '{algorithm}'. "
            f"Supported: {sorted(_SUPPORTED_ALGORITHMS)}"
        )

    if level is None:
        level = _DEFAULT_LEVELS.get(algorithm_lower)

    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        from app.raster.writer import copy_with_compression

        extra = {}
        if level is not None:
            if algorithm_lower == "deflate":
                extra["ZLEVEL"] = level
            elif algorithm_lower == "zstd":
                extra["ZSTD_LEVEL"] = level

        extra.update(kwargs)
        return copy_with_compression(src_path, dst_path, compression=algorithm_lower, **extra)

    except Exception as exc:
        raise RasterCompressionError(
            f"Failed to compress '{src_path}' with {algorithm}: {exc}"
        ) from exc


def estimate_compression_ratio(
    path: str,
    algorithm: str = "lzw",
    sample_window: Optional[tuple[tuple[int, int], tuple[int, int]]] = None,
) -> float:
    """Estimate compression ratio by compressing a sample window.

    Args:
        path: Path to the raster file.
        algorithm: Compression algorithm to test.
        sample_window: Pixel window to use for estimation.

    Returns:
        Estimated compression ratio (uncompressed / compressed).
    """
    import tempfile

    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")

    try:
        with rasterio.open(path) as src:
            if sample_window:
                window = sample_window
            else:
                window = (
                    (0, min(512, src.height)),
                    (0, min(512, src.width)),
                )

            data = src.read(window=window)
            profile = src.profile.copy()
            profile.update(
                {"height": data.shape[1], "width": data.shape[2], "COMPRESS": algorithm.upper()}
            )

            with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
                tmp_path = tmp.name

            with rasterio.open(tmp_path, "w", **profile) as dst:
                for i in range(data.shape[0]):
                    dst.write(data[i], i + 1)

            compressed = os.path.getsize(tmp_path)
            raw = data.shape[0] * data.shape[1] * data.shape[2] * data.dtype.itemsize
            os.unlink(tmp_path)

            return raw / compressed if compressed > 0 else 1.0

    except Exception as exc:
        raise RasterCompressionError(
            f"Failed to estimate compression ratio for '{path}': {exc}"
        ) from exc


def decompress(src_path: str, dst_path: str) -> str:
    """Decompress a raster file (remove compression).

    Args:
        src_path: Source compressed raster path.
        dst_path: Destination path.

    Returns:
        Path to the decompressed raster.
    """
    if not os.path.isfile(src_path):
        raise RasterNotFoundError(f"Source file not found: {src_path}")

    try:
        with rasterio.open(src_path) as src:
            profile = src.profile.copy()
            profile["COMPRESS"] = "NONE"
            profile["driver"] = "GTiff"

            os.makedirs(os.path.dirname(os.path.abspath(dst_path)) or ".", exist_ok=True)
            with rasterio.open(dst_path, "w", **profile) as dst:
                for i in range(1, src.count + 1):
                    dst.write(src.read(i), i)
                if src.tags():
                    dst.update_tags(**src.tags())

        logger.info("Decompressed '%s' -> '%s'", src_path, dst_path)
        return os.path.abspath(dst_path)

    except Exception as exc:
        raise RasterCompressionError(
            f"Failed to decompress '{src_path}': {exc}"
        ) from exc
