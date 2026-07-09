"""Abstract base class for all satellite data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ProviderCapabilities:
    """Describes what a provider supports."""
    name: str
    display_name: str
    missions: list[str] = field(default_factory=list)
    bands: dict[str, list[str]] = field(default_factory=dict)
    resolutions: dict[str, list[float]] = field(default_factory=dict)
    products: list[str] = field(default_factory=list)
    max_cloud_cover: float = 100.0
    supports_polygon_search: bool = False
    supports_checksum: bool = False
    requires_api_key: bool = False


class BaseSatelliteProvider(ABC):
    """Abstract interface every satellite provider must implement.

    All methods raise ``ProviderError`` or a subclass on failure.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'sentinel_2')."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return the static capabilities descriptor for this provider."""

    @abstractmethod
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
        """Search for imagery matching the given criteria.

        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat].
            polygon: GeoJSON Polygon dict.
            date_from: Start of acquisition date range.
            date_to: End of acquisition date range.
            max_cloud_cover: Maximum cloud cover percentage.
            resolution: Maximum ground resolution in meters.
            bands: Required spectral bands.
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            List of result dicts with keys matching ``SearchResult`` fields.
        """

    @abstractmethod
    def download(
        self,
        scene_id: str,
        download_urls: dict[str, str],
        destination: str,
        bands: list[str] | None = None,
        progress_callback: Any = None,
    ) -> dict[str, str]:
        """Download imagery for a scene.

        Args:
            scene_id: Provider scene identifier.
            download_urls: Dict mapping band/sensor -> URL.
            destination: Directory to write files into.
            bands: Specific bands to download (None = all).
            progress_callback: Optional ``callable(downloaded, total)``.

        Returns:
            Dict mapping band -> local file path.
        """

    @abstractmethod
    def validate(self, scene_id: str, file_paths: dict[str, str]) -> bool:
        """Validate downloaded imagery for a scene.

        Args:
            scene_id: Provider scene identifier.
            file_paths: Dict mapping band -> local file path.

        Returns:
            True if valid.
        """

    @abstractmethod
    def extract_metadata(self, scene_id: str, file_paths: dict[str, str]) -> dict:
        """Extract and normalize metadata from downloaded files.

        Args:
            scene_id: Provider scene identifier.
            file_paths: Dict mapping band -> local file path.

        Returns:
            Normalized metadata dict compatible with ``MetadataExtractor``.
        """

    @abstractmethod
    def estimate_size(self, scene_id: str, bands: list[str] | None = None) -> int:
        """Estimate download size in bytes for a scene.

        Args:
            scene_id: Provider scene identifier.
            bands: Specific bands (None = all).

        Returns:
            Estimated size in bytes.
        """

    @abstractmethod
    def available_bands(self, scene_id: str) -> list[str]:
        """List available spectral bands for a given scene."""

    @abstractmethod
    def supported_resolutions(self) -> list[float]:
        """List ground resolutions (meters) this provider supports."""

    @abstractmethod
    def supported_products(self) -> list[str]:
        """List processing products this provider offers."""
