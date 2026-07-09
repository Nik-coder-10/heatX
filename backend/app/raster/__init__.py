"""Raster Management Subsystem.

Production-grade raster operations for GeoTIFF and Cloud Optimized GeoTIFF (COG)
files. Provides reading, writing, validation, metadata extraction, transformations,
compression, tiling, statistics, and preview generation.

Designed for large raster support (>10 GiB) with windowed I/O, lazy loading,
chunk processing, and memory safety.
"""

from app.raster.exceptions import (
    CorruptedRasterError,
    MemoryLimitError,
    RasterCompressionError,
    RasterCRSError,
    RasterError,
    RasterNotFoundError,
    RasterPreviewError,
    RasterReadError,
    RasterStatisticsError,
    RasterTilingError,
    RasterTransformError,
    RasterValidationError,
    RasterWriteError,
    UnsupportedFormatError,
)
from app.raster.manager import RasterManager
from app.raster.metadata import extract_metadata
from app.raster.reader import (
    get_raster_info,
    read_aoi,
    read_bands,
    read_bbox,
    read_memmap,
    read_window,
    stream_blocks,
)
from app.raster.validator import validate_all
from app.raster.writer import copy_with_compression, write_cog, write_geotiff
from app.raster.transform import (
    clip,
    crop,
    extract_band,
    mask,
    merge,
    reproject,
    resample,
    split,
    stack_bands,
)
from app.raster.statistics import (
    compute_all_statistics,
    compute_histogram,
    compute_nodata_percentage,
    compute_percentiles,
    compute_statistics,
)
from app.raster.compression import compress, decompress, get_compression_info
from app.raster.preview import (
    create_false_color_composite,
    create_jpeg_preview,
    create_png_preview,
    create_thumbnail,
)
from app.raster.tiling import create_tile_index, create_tiles, read_tile

__all__ = [
    "RasterManager",
    "extract_metadata",
    "get_raster_info",
    "read_bands",
    "read_bbox",
    "read_aoi",
    "read_window",
    "read_memmap",
    "stream_blocks",
    "validate_all",
    "write_geotiff",
    "write_cog",
    "copy_with_compression",
    "crop",
    "clip",
    "mask",
    "reproject",
    "resample",
    "merge",
    "split",
    "extract_band",
    "stack_bands",
    "compress",
    "decompress",
    "get_compression_info",
    "compute_statistics",
    "compute_all_statistics",
    "compute_histogram",
    "compute_percentiles",
    "compute_nodata_percentage",
    "create_png_preview",
    "create_jpeg_preview",
    "create_thumbnail",
    "create_false_color_composite",
    "create_tiles",
    "create_tile_index",
    "read_tile",
    "RasterError",
    "RasterNotFoundError",
    "RasterReadError",
    "RasterWriteError",
    "RasterValidationError",
    "RasterCRSError",
    "RasterTransformError",
    "RasterCompressionError",
    "RasterPreviewError",
    "RasterStatisticsError",
    "RasterTilingError",
    "UnsupportedFormatError",
    "CorruptedRasterError",
    "MemoryLimitError",
]
