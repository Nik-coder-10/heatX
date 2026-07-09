"""Landsat-9 Collection 2 provider implementation.

Landsat-9 is nearly identical to Landsat-8 (same OLI/TIRS instruments).
Uses separate scene ID prefix (LC09) and mission string.
"""

import logging
from datetime import date
from typing import Any

from app.satellite.base_provider import BaseSatelliteProvider, ProviderCapabilities
from app.satellite.exceptions import ValidationError

logger = logging.getLogger("app.satellite.providers.landsat9")

_LANDSAT_9_BANDS: dict[str, list[str]] = {
    "30m": [
        "coastal", "blue", "green", "red", "nir",
        "swir1", "swir2", "cirrus", "tirs1", "tirs2",
    ],
    "15m": ["pan"],
}

_ALL_L9_BANDS: list[str] = sorted(
    b for bands in _LANDSAT_9_BANDS.values() for b in bands
)

_L9_PRODUCTS: list[str] = ["L2SP", "L1TP"]


class Landsat9Provider(BaseSatelliteProvider):
    """Provider for USGS Landsat-9 OLI/TIRS Collection 2 imagery."""

    @property
    def provider_id(self) -> str:
        return "landsat_9"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="landsat_9",
            display_name="Landsat-9 OLI/TIRS Collection 2",
            missions=["landsat_9"],
            bands=_LANDSAT_9_BANDS,
            resolutions={"L2SP": [15.0, 30.0], "L1TP": [15.0, 30.0]},
            products=_L9_PRODUCTS,
            max_cloud_cover=100.0,
            supports_polygon_search=True,
            supports_checksum=True,
            requires_api_key=True,
        )

    def search(
        self,
        bbox: list[float] | None = None,
        polygon: dict | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        max_cloud_cover: float | None = None,
        resolution: float | None = None,
        bands: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs: Any,
    ) -> list[dict]:
        results: list[dict] = []
        for i in range(offset, offset + limit):
            cloud = 8.0 + (i * 2.1) % 90.0
            if max_cloud_cover is not None and cloud > max_cloud_cover:
                continue
            results.append({
                "scene_id": f"LC09_L2SP_{i:06d}",
                "provider": "landsat_9",
                "mission": "landsat_9",
                "sensor": "OLI_TIRS",
                "acquisition_date": "2025-08-15T05:30:00Z",
                "cloud_cover": cloud,
                "resolution": 30.0,
                "crs": "EPSG:32644",
                "bounding_box": [77.0, 12.5, 78.0, 13.5],
                "bands": _ALL_L9_BANDS,
                "processing_level": "L2SP",
                "size_bytes": 1_200_000_000,
                "download_urls": {
                    band: f"https://landsat.example.com/LC09/{i:06d}/{band}.tif"
                    for band in _ALL_L9_BANDS
                },
                "checksum": f"def456checksum{i}",
            })
        return results

    def download(
        self,
        scene_id: str,
        download_urls: dict[str, str],
        destination: str,
        bands: list[str] | None = None,
        progress_callback: Any = None,
    ) -> dict[str, str]:
        from pathlib import Path

        bands_to_dl = bands if bands else list(download_urls.keys())
        result: dict[str, str] = {}
        total = len(bands_to_dl)

        for idx, band in enumerate(bands_to_dl):
            url = download_urls.get(band)
            if url is None:
                continue
            dest_path = str(Path(destination) / f"{scene_id}_{band}.tif")
            _simulate_download(dest_path, band, idx, total, progress_callback)
            result[band] = dest_path

        logger.info("Downloaded %d bands for scene '%s'", len(result), scene_id)
        return result

    def validate(self, scene_id: str, file_paths: dict[str, str]) -> bool:
        import os

        for band, path in file_paths.items():
            if not os.path.isfile(path):
                raise ValidationError(f"Band '{band}' file missing: {path}")
            size = os.path.getsize(path)
            if size == 0:
                raise ValidationError(f"Band '{band}' file empty: {path}")
        return True

    def extract_metadata(self, scene_id: str, file_paths: dict[str, str]) -> dict:
        import os

        first_path = next(iter(file_paths.values()), "")
        file_size = os.path.getsize(first_path) if first_path and os.path.isfile(first_path) else 0

        return {
            "scene_id": scene_id,
            "provider": "landsat_9",
            "mission": "landsat_9",
            "sensor": "OLI_TIRS",
            "acquisition_date": "2025-08-15T05:30:00Z",
            "processing_level": "L2SP",
            "cloud_cover": 8.0,
            "crs": "EPSG:32644",
            "resolution": 30.0,
            "bands": list(file_paths.keys()),
            "bounding_box": [77.0, 12.5, 78.0, 13.5],
            "file_size_bytes": file_size * len(file_paths),
            "provider_name": "USGS",
        }

    def estimate_size(self, scene_id: str, bands: list[str] | None = None) -> int:
        n = len(bands) if bands else len(_ALL_L9_BANDS)
        return n * 85_000_000

    def available_bands(self, scene_id: str) -> list[str]:
        return _ALL_L9_BANDS

    def supported_resolutions(self) -> list[float]:
        return [15.0, 30.0]

    def supported_products(self) -> list[str]:
        return _L9_PRODUCTS


register = Landsat9Provider


def _simulate_download(
    path: str, band: str, idx: int, total: int, progress_callback: Any = None
) -> None:
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00" * 1024)
    if progress_callback:
        progress_callback(idx + 1, total)
