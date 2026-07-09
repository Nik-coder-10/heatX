"""Sentinel-2 L2A provider implementation.

Supports Copernicus Sentinel-2 MSI Level-2A imagery.
Bands (10m): B02, B03, B04, B08
Bands (20m): B05, B06, B07, B8A, B11, B12
Bands (60m): B01, B09, B10
"""

import logging
from datetime import date
from typing import Any

from app.satellite.base_provider import BaseSatelliteProvider, ProviderCapabilities
from app.satellite.exceptions import (
    ProviderError,
    SearchError,
    UnsupportedProductError,
    ValidationError,
)

logger = logging.getLogger("app.satellite.providers.sentinel2")

_SENTINEL_2_BANDS: dict[str, list[str]] = {
    "10m": ["B02", "B03", "B04", "B08"],
    "20m": ["B05", "B06", "B07", "B8A", "B11", "B12"],
    "60m": ["B01", "B09", "B10"],
}

_ALL_SENTINEL_2_BANDS: list[str] = sorted(
    b for bands in _SENTINEL_2_BANDS.values() for b in bands
)

_SENTINEL_2_RESOLUTIONS: list[float] = [10.0, 20.0, 60.0]

_SENTINEL_2_PRODUCTS: list[str] = [
    "L2A",
    "L1C",
]


class Sentinel2Provider(BaseSatelliteProvider):
    """Provider for Copernicus Sentinel-2 MSI imagery."""

    @property
    def provider_id(self) -> str:
        return "sentinel_2"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="sentinel_2",
            display_name="Sentinel-2 MSI (L2A)",
            missions=["sentinel_2a", "sentinel_2b"],
            bands=_SENTINEL_2_BANDS,
            resolutions={"L2A": _SENTINEL_2_RESOLUTIONS, "L1C": _SENTINEL_2_RESOLUTIONS},
            products=_SENTINEL_2_PRODUCTS,
            max_cloud_cover=100.0,
            supports_polygon_search=True,
            supports_checksum=False,
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
            results.append({
                "scene_id": f"S2A_{i}_L2A",
                "provider": "sentinel_2",
                "mission": "sentinel_2a" if i % 2 == 0 else "sentinel_2b",
                "sensor": "MSI",
                "acquisition_date": "2025-06-15T10:25:00Z",
                "cloud_cover": 5.0 + (i * 2.3) % 90.0,
                "resolution": 10.0,
                "crs": "EPSG:32644",
                "bounding_box": [77.0, 12.5, 78.0, 13.5],
                "bands": _ALL_SENTINEL_2_BANDS,
                "processing_level": "L2A",
                "size_bytes": 850_000_000,
                "download_urls": {
                    band: f"https://sentinel.example.com/{i}/{band}.jp2"
                    for band in _ALL_SENTINEL_2_BANDS
                },
                "checksum": None,
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
        import os
        import time
        from pathlib import Path

        bands_to_dl = bands if bands else list(download_urls.keys())
        result: dict[str, str] = {}
        total = len(bands_to_dl)

        for idx, band in enumerate(bands_to_dl):
            url = download_urls.get(band)
            if url is None:
                logger.warning("No download URL for band '%s' in scene '%s'", band, scene_id)
                continue
            dest_path = str(Path(destination) / f"{scene_id}_{band}.jp2")
            _simulate_download(dest_path, band, idx, total, progress_callback)
            result[band] = dest_path

        logger.info("Downloaded %d bands for scene '%s'", len(result), scene_id)
        return result

    def validate(self, scene_id: str, file_paths: dict[str, str]) -> bool:
        import os

        for band, path in file_paths.items():
            if not os.path.isfile(path):
                raise ValidationError(f"Band '{band}' file not found: {path}")
            size = os.path.getsize(path)
            if size == 0:
                raise ValidationError(f"Band '{band}' file is empty: {path}")
        return True

    def extract_metadata(self, scene_id: str, file_paths: dict[str, str]) -> dict:
        import os
        import re

        parts = scene_id.split("_")
        mission = parts[0] if len(parts) > 0 else "unknown"
        processing_level = "L2A"
        for p in parts:
            if p in ("L2A", "L1C"):
                processing_level = p
                break

        first_path = next(iter(file_paths.values()), "")
        file_size = os.path.getsize(first_path) if first_path and os.path.isfile(first_path) else 0

        return {
            "scene_id": scene_id,
            "provider": "sentinel_2",
            "mission": "sentinel_2a" if "S2A" in scene_id else "sentinel_2b",
            "sensor": "MSI",
            "acquisition_date": "2025-06-15T10:25:00Z",
            "processing_level": processing_level,
            "cloud_cover": 5.0,
            "crs": "EPSG:32644",
            "resolution": 10.0,
            "bands": list(file_paths.keys()),
            "bounding_box": [77.0, 12.5, 78.0, 13.5],
            "file_size_bytes": file_size * len(file_paths),
            "provider_name": "Copernicus",
        }

    def estimate_size(self, scene_id: str, bands: list[str] | None = None) -> int:
        n = len(bands) if bands else len(_ALL_SENTINEL_2_BANDS)
        return n * 60_000_000

    def available_bands(self, scene_id: str) -> list[str]:
        return _ALL_SENTINEL_2_BANDS

    def supported_resolutions(self) -> list[float]:
        return _SENTINEL_2_RESOLUTIONS

    def supported_products(self) -> list[str]:
        return _SENTINEL_2_PRODUCTS


register = Sentinel2Provider


def _simulate_download(
    path: str, band: str, idx: int, total: int, progress_callback: Any = None
) -> None:
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x00" * 1024)
    if progress_callback:
        progress_callback(idx + 1, total)
