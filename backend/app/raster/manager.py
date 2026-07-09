"""RasterManager — unified orchestration for all raster operations."""

import logging
import os
from typing import Any, Optional

import numpy as np

from app.raster import (
    reader,
    writer,
    metadata,
    validator,
    transform,
    compression,
    tiling,
    statistics,
    preview,
)

logger = logging.getLogger("app.raster.manager")

_DEFAULT_COMPRESSION = "lzw"
_DEFAULT_TILE_SIZE = 256


class RasterManager:
    """Unified API for reading, writing, transforming, and analyzing rasters.

    Attributes:
        compression: Default compression algorithm.
        tile_size: Default tile/block size.
        storage_dir: Base directory for raster storage.
    """

    def __init__(
        self,
        compression: str = _DEFAULT_COMPRESSION,
        tile_size: int = _DEFAULT_TILE_SIZE,
        storage_dir: Optional[str] = None,
    ) -> None:
        self.compression = compression
        self.tile_size = tile_size
        self.storage_dir = storage_dir

    # -- Info --

    def info(self, path: str) -> dict[str, Any]:
        """Return quick raster info without reading pixel data."""
        return reader.get_raster_info(path)

    def metadata(self, path: str, detailed: bool = False) -> dict[str, Any]:
        """Extract full metadata from a raster file, including per-band details."""
        return metadata.extract_metadata(path, detailed=detailed)

    # -- Validation --

    def validate(
        self,
        path: str,
        expected_bands: Optional[int] = None,
        expected_crs: Optional[str] = None,
    ) -> dict[str, Any]:
        """Run all validation checks on a raster file."""
        return validator.validate_all(
            path,
            expected_bands=expected_bands,
            expected_crs=expected_crs,
        )

    # -- Reading --

    def read(
        self,
        path: str,
        bands: Optional[list[int]] = None,
        window: Optional[tuple[tuple[int, int], tuple[int, int]]] = None,
        out_shape: Optional[tuple[int, int]] = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Read bands from a raster file."""
        return reader.read_bands(path, bands=bands, window=window, out_shape=out_shape)

    def read_bbox(
        self,
        path: str,
        bbox: tuple[float, float, float, float],
        dst_crs: Optional[str] = None,
        bands: Optional[list[int]] = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Read raster data intersecting a bounding box."""
        return reader.read_bbox(path, bbox, dst_crs=dst_crs, bands=bands)

    def read_aoi(
        self,
        path: str,
        geometry: dict[str, Any],
        dst_crs: Optional[str] = None,
        bands: Optional[list[int]] = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Read raster data masked to a polygon AOI."""
        return reader.read_aoi(path, geometry, dst_crs=dst_crs, bands=bands)

    def stream_blocks(
        self,
        path: str,
        band: int = 1,
        block_size: Optional[int] = None,
    ):
        """Stream raster blocks for memory-safe processing."""
        return reader.stream_blocks(
            path, band=band, block_size=block_size or self.tile_size
        )

    # -- Writing --

    def write(
        self,
        path: str,
        data: np.ndarray,
        transform: Any,
        crs: Any,
        nodata: Optional[float] = None,
        compression: Optional[str] = None,
    ) -> str:
        """Write a numpy array to a GeoTIFF file."""
        return writer.write_geotiff(
            path, data, transform, crs,
            nodata=nodata,
            compression=compression or self.compression,
            tiled=True,
            block_size=self.tile_size,
        )

    def write_cog(
        self,
        path: str,
        data: np.ndarray,
        transform: Any,
        crs: Any,
        nodata: Optional[float] = None,
        compression: Optional[str] = None,
    ) -> str:
        """Write a Cloud Optimized GeoTIFF."""
        return writer.write_cog(
            path, data, transform, crs,
            nodata=nodata,
            compression=compression or self.compression,
            block_size=self.tile_size,
        )

    # -- Transformations --

    def crop(
        self,
        src_path: str,
        dst_path: str,
        bbox: tuple[float, float, float, float],
    ) -> str:
        """Crop a raster to a bounding box."""
        return transform.crop(src_path, dst_path, bbox, compression=self.compression)

    def clip(
        self,
        src_path: str,
        dst_path: str,
        geometry: dict[str, Any],
        dst_crs: Optional[Any] = None,
    ) -> str:
        """Clip a raster to a polygon geometry."""
        return transform.clip(src_path, dst_path, geometry, dst_crs=dst_crs, compression=self.compression)

    def reproject(
        self,
        src_path: str,
        dst_path: str,
        dst_crs: Any,
        resampling: str = "bilinear",
    ) -> str:
        """Reproject a raster to a different CRS."""
        return transform.reproject(src_path, dst_path, dst_crs, resampling=resampling, compression=self.compression)

    def resample(
        self,
        src_path: str,
        dst_path: str,
        scale_factor: Optional[float] = None,
        resolution: Optional[tuple[float, float]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        resampling: str = "bilinear",
    ) -> str:
        """Resample a raster."""
        return transform.resample(
            src_path, dst_path,
            scale_factor=scale_factor, resolution=resolution,
            width=width, height=height, resampling=resampling,
            compression=self.compression,
        )

    def merge(self, src_paths: list[str], dst_path: str) -> str:
        """Merge multiple rasters into one."""
        return transform.merge(src_paths, dst_path, compression=self.compression)

    def extract_band(self, src_path: str, dst_path: str, band: int) -> str:
        """Extract a single band from a multi-band raster."""
        return transform.extract_band(src_path, dst_path, band, compression=self.compression)

    def split(self, src_path: str, dst_dir: str, prefix: str = "band") -> list[str]:
        """Split a multi-band raster into individual band files."""
        return transform.split(src_path, dst_dir, prefix=prefix)

    def stack_bands(self, src_paths: list[str], dst_path: str) -> str:
        """Stack single-band rasters into a multi-band raster."""
        return transform.stack_bands(src_paths, dst_path, compression=self.compression)

    # -- Compression --

    def compress(
        self, src_path: str, dst_path: str,
        algorithm: Optional[str] = None,
        level: Optional[int] = None,
    ) -> str:
        """Compress a raster file."""
        return compression.compress(
            src_path, dst_path,
            algorithm=algorithm or self.compression,
            level=level,
        )

    def decompress(self, src_path: str, dst_path: str) -> str:
        """Decompress a raster file."""
        return compression.decompress(src_path, dst_path)

    def compression_info(self, path: str) -> dict[str, Any]:
        """Get compression details."""
        return compression.get_compression_info(path)

    def estimate_compression_ratio(self, path: str, algorithm: Optional[str] = None) -> float:
        """Estimate compression ratio."""
        return compression.estimate_compression_ratio(path, algorithm=algorithm or self.compression)

    # -- Tiling --

    def create_tiles(
        self,
        src_path: str,
        output_dir: str,
        tile_size: Optional[int] = None,
        overlap: int = 0,
        prefix: str = "tile",
    ) -> list[dict[str, Any]]:
        """Split a raster into tiles."""
        return tiling.create_tiles(
            src_path, output_dir,
            tile_size=tile_size or self.tile_size,
            overlap=overlap,
            prefix=prefix,
            compression=self.compression,
        )

    def tile_index(
        self,
        src_path: str,
        tile_size: Optional[int] = None,
        overlap: int = 0,
    ) -> dict[str, Any]:
        """Get tile grid metadata without generating tiles."""
        return tiling.create_tile_index(
            src_path, tile_size=tile_size or self.tile_size, overlap=overlap,
        )

    def read_tile(
        self,
        src_path: str,
        tile_x: int,
        tile_y: int,
        tile_size: Optional[int] = None,
        overlap: int = 0,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Read a specific tile."""
        return tiling.read_tile(
            src_path, tile_x, tile_y,
            tile_size=tile_size or self.tile_size,
            overlap=overlap,
        )

    # -- Statistics --

    def statistics(
        self,
        path: str,
        band: int = 1,
        approx: bool = True,
        windowed: bool = False,
    ) -> dict[str, Any]:
        """Compute band statistics."""
        return statistics.compute_statistics(path, band, approx=approx, windowed=windowed)

    def all_statistics(
        self,
        path: str,
        approx: bool = True,
        windowed: bool = False,
    ) -> dict[str, Any]:
        """Compute statistics for all bands."""
        return statistics.compute_all_statistics(path, approx=approx, windowed=windowed)

    def histogram(
        self, path: str, band: int = 1, bins: int = 256, windowed: bool = False
    ) -> dict[str, Any]:
        """Compute histogram."""
        return statistics.compute_histogram(path, band, bins=bins, windowed=windowed)

    def percentiles(
        self,
        path: str,
        band: int = 1,
        percentiles: Optional[list[float]] = None,
        windowed: bool = False,
    ) -> dict[str, Any]:
        """Compute percentiles."""
        return statistics.compute_percentiles(path, band, percentiles, windowed=windowed)

    def nodata_percentage(self, path: str, band: int = 1) -> dict[str, Any]:
        """Compute NoData percentage."""
        return statistics.compute_nodata_percentage(path, band)

    # -- Preview --

    def create_png_preview(
        self,
        src_path: str,
        dst_path: str,
        band: int = 1,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> str:
        """Create a PNG preview."""
        return preview.create_png_preview(
            src_path, dst_path, band=band, width=width, height=height,
        )

    def create_jpeg_preview(
        self,
        src_path: str,
        dst_path: str,
        quality: int = 85,
        band: int = 1,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> str:
        """Create a JPEG preview."""
        return preview.create_jpeg_preview(
            src_path, dst_path, quality=quality, band=band,
            width=width, height=height,
        )

    def create_thumbnail(
        self,
        src_path: str,
        dst_path: str,
        size: tuple[int, int] = (256, 256),
        band: int = 1,
    ) -> str:
        """Create a thumbnail."""
        return preview.create_thumbnail(src_path, dst_path, size=size, band=band)

    def create_false_color(
        self,
        src_path: str,
        dst_path: str,
        red_band: int = 3,
        green_band: int = 2,
        blue_band: int = 1,
    ) -> str:
        """Create a false-color composite."""
        return preview.create_false_color_composite(
            src_path, dst_path,
            red_band=red_band, green_band=green_band, blue_band=blue_band,
        )

    # -- Health --

    def health_report(self) -> dict[str, Any]:
        """Generate a Raster Management Health Report.

        Returns:
            Dict with health metrics, capabilities, and readiness score.
        """
        import importlib.metadata as ilm

        scores = []
        checks = []

        # Module availability
        modules = {
            "rasterio": False,
            "numpy": False,
            "PIL": False,
            "shapely": False,
        }
        for mod_name in modules:
            try:
                __import__(mod_name)
                modules[mod_name] = True
            except ImportError:
                pass

        rasterio_ok = modules.get("rasterio", False)
        numpy_ok = modules.get("numpy", False)
        pillow_ok = modules.get("PIL", False)
        shapely_ok = modules.get("shapely", False)

        if all(modules.values()):
            scores.append(100)
            checks.append({"check": "dependencies", "status": "pass", "detail": "All core modules available"})
        else:
            missing = [k for k, v in modules.items() if not v]
            scores.append(50)
            checks.append({"check": "dependencies", "status": "warn", "detail": f"Missing: {missing}"})

        if rasterio_ok:
            _, supported_formats = self._check_formats()
            score_val = 100 if "GTiff" in supported_formats else 50
            scores.append(score_val)
            checks.append({
                "check": "formats",
                "status": "pass" if score_val == 100 else "warn",
                "detail": f"Supported: {sorted(supported_formats)}",
            })
        else:
            scores.append(0)
            checks.append({"check": "formats", "status": "fail", "detail": "rasterio not available"})

        if rasterio_ok and numpy_ok:
            scores.append(100)
            checks.append({"check": "windowed_io", "status": "pass", "detail": "Windowed reads/writes available"})
        else:
            scores.append(0)
            checks.append({"check": "windowed_io", "status": "fail", "detail": "Missing dependencies"})

        if rasterio_ok:
            scores.append(100)
            checks.append({"check": "cog_writing", "status": "pass", "detail": "COG-compatible GTiff writer available"})
        else:
            scores.append(0)
            checks.append({"check": "cog_writing", "status": "fail", "detail": "rasterio not available"})

        if compression:
            scores.append(100)
            checks.append({"check": "compression", "status": "pass", "detail": f"Default: {self.compression}"})
        else:
            scores.append(0)
            checks.append({"check": "compression", "status": "fail", "detail": "No compression configured"})

        if rasterio_ok:
            scores.append(100)
            checks.append({"check": "memory_mapping", "status": "pass", "detail": "Memory-mapped reads available"})
        else:
            scores.append(0)
            checks.append({"check": "memory_mapping", "status": "fail", "detail": "rasterio not available"})

        if rasterio_ok and numpy_ok:
            scores.append(100)
            checks.append({"check": "statistics", "status": "pass", "detail": "Windowed stats, histogram, percentiles"})
        else:
            scores.append(0)
            checks.append({"check": "statistics", "status": "fail", "detail": "Missing dependencies"})

        if pillow_ok and rasterio_ok:
            scores.append(100)
            checks.append({"check": "preview", "status": "pass", "detail": "PNG/JPEG/thumbnail/composite"})
        else:
            scores.append(0)
            checks.append({"check": "preview", "status": "fail", "detail": "PIL not available"})

        if rasterio_ok and shapely_ok:
            scores.append(100)
            checks.append({"check": "geospatial", "status": "pass", "detail": "CRS/transform/geometry ops"})
        else:
            scores.append(0)
            checks.append({"check": "geospatial", "status": "fail", "detail": "Missing shapely"})

        if scores:
            readiness = int(sum(scores) / len(scores))
        else:
            readiness = 0

        return {
            "readiness_score": readiness,
            "readiness_label": "PRODUCTION" if readiness >= 90 else "BETA" if readiness >= 70 else "DEVELOPMENT",
            "status": "healthy" if readiness >= 80 else "degraded",
            "checks": checks,
            "config": {
                "compression": self.compression,
                "tile_size": self.tile_size,
                "storage_dir": self.storage_dir,
            },
            "capabilities": {
                "formats": ["GTiff", "COG"],
                "compression_algorithms": ["lzw", "deflate", "zstd"],
                "reading": ["windowed", "bbox", "polygon_aoi", "pixel_window", "memmap", "streaming"],
                "writing": ["geotiff", "cog"],
                "transformations": ["crop", "clip", "mask", "reproject", "resample", "merge", "split", "band_extraction", "band_stacking"],
                "statistics": ["min", "max", "mean", "median", "std", "histogram", "percentiles", "nodata_pct"],
                "preview": ["png", "jpeg", "thumbnail", "false_color"],
                "tiling": ["create", "index", "read_by_index"],
                "validation": ["format", "crs", "transform", "band_count", "nodata", "resolution_consistency", "extent", "corruption"],
            },
            "dependencies": {
                "rasterio": rasterio_ok,
                "numpy": numpy_ok,
                "pillow": pillow_ok,
                "shapely": shapely_ok,
            },
        }

    def _check_formats(self) -> tuple[bool, set[str]]:
        """Check available raster drivers."""
        try:
            import rasterio
            drv = rasterio.drivers.raster_driver_ids()
            return True, set(drv.keys())
        except Exception:
            return False, set()
