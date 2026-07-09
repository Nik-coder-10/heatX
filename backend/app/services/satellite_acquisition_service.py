"""Service layer for satellite data acquisition orchestration.

Coordinates search, download, validation, metadata extraction, storage,
and persistence of satellite imagery using the acquisition subsystem.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.enums import ProcessingStatus, SatelliteProvider
from app.services.satellite_image import (
    DuplicateSceneIdError,
    ImageNotFoundError,
    SatelliteImageService,
)
from app.satellite import (
    DownloadCancelledError,
    DownloadError,
    MetadataExtractor,
    ProviderNotFoundError,
    SatelliteCache,
    SatelliteSearch,
    SatelliteValidator,
    SearchError,
    StorageError,
    StorageManager,
)
from app.satellite.download_manager import DownloadManager
from app.satellite.provider_registry import get_registry

logger = logging.getLogger("app.services.satellite_acquisition")


class SatelliteAcquisitionError(Exception):
    """Base exception for acquisition service errors."""


class SceneDownloadError(SatelliteAcquisitionError):
    """Raised when scene download fails."""


class SceneImportError(SatelliteAcquisitionError):
    """Raised when scene import to database fails."""


class ProviderLookupError(SatelliteAcquisitionError):
    """Raised when provider lookup fails."""


class SatelliteAcquisitionService:
    """Orchestrates the satellite image acquisition pipeline.

    Coordinates search, download, validation, metadata extraction,
    storage management, and database persistence.
    """

    def __init__(
        self,
        db: Session,
        storage_dir: Optional[str] = None,
    ) -> None:
        self.db = db
        self._satellite_service = SatelliteImageService(db)
        self._registry = get_registry()
        self._cache = SatelliteCache(
            max_size=getattr(settings, "SATELLITE_CACHE_SIZE", 500),
            default_ttl=getattr(settings, "SATELLITE_CACHE_TTL", 3600),
        )
        self._storage = StorageManager(
            base_dir=storage_dir or getattr(settings, "SATELLITE_STORAGE_DIR", None)
        )
        self._download_manager = DownloadManager(
            storage=self._storage,
            cache=self._cache,
            max_concurrent=getattr(settings, "SATELLITE_MAX_CONCURRENT_DOWNLOADS", 4),
        )
        self._search = SatelliteSearch(registry=self._registry, cache=self._cache)
        self._validator = SatelliteValidator()
        self._metadata_extractor = MetadataExtractor()

    # -- Search --

    def search_catalog(
        self,
        bbox: Optional[list[float]] = None,
        city: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_cloud_cover: Optional[float] = None,
        resolution: Optional[float] = None,
        missions: Optional[list[str]] = None,
        bands: Optional[list[str]] = None,
        providers: Optional[list[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search for satellite imagery across registered providers."""
        try:
            return self._search.search(
                bbox=bbox,
                city=city,
                date_from=date_from,
                date_to=date_to,
                max_cloud_cover=max_cloud_cover,
                resolution=resolution,
                missions=missions,
                bands=bands,
                providers=providers,
                limit=limit,
                offset=offset,
            )
        except SearchError as exc:
            logger.error("Catalog search failed: %s", exc)
            raise SatelliteAcquisitionError(str(exc)) from exc

    # -- Download --

    def download_scene(
        self,
        scene_id: str,
        provider: str,
        mission: str,
        acquisition_date: str,
        bands: Optional[list[str]] = None,
        download_urls: Optional[dict[str, str]] = None,
        checksum: Optional[str] = None,
    ) -> str:
        """Queue a scene for download.

        Returns:
            Task ID for tracking download progress.
        """
        try:
            provider_instance = self._registry.get(provider)
        except ProviderNotFoundError as exc:
            raise ProviderLookupError(str(exc)) from exc

        if not download_urls:
            result = self._search.search(
                bbox=None,
                city=None,
                providers=[provider],
                limit=1,
            )
            matching = [
                r for r in result.get("results", [])
                if r.get("scene_id") == scene_id
            ]
            if not matching:
                raise SceneDownloadError(
                    f"Scene '{scene_id}' not found via provider '{provider}'"
                )
            download_urls = matching[0].get("download_urls", {})

        destination = str(
            self._storage.scene_path(
                provider=provider,
                mission=mission,
                acquisition_date=acquisition_date,
                scene_id=scene_id,
            )
        )

        task_id = self._download_manager.enqueue(
            scene_id=scene_id,
            provider=provider,
            download_urls=download_urls,
            destination=destination,
            bands=bands,
            checksum=checksum,
        )

        logger.info(
            "Queued download: task='%s' scene='%s' provider='%s'",
            task_id, scene_id, provider,
        )
        return task_id

    def get_download_tasks(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List download tasks, optionally filtered by status."""
        return self._download_manager.list_tasks(status=status)

    def get_download_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get the status of a specific download task."""
        return self._download_manager.get_task(task_id)

    def cancel_download(self, task_id: str) -> bool:
        """Cancel a queued or in-progress download."""
        return self._download_manager.cancel_task(task_id)

    # -- Import (validate + metadata + persist) --

    def import_scene(
        self,
        scene_id: str,
        provider: str,
        mission: str,
        acquisition_date: str,
        project_id: str,
        bands: Optional[list[str]] = None,
        download_urls: Optional[dict[str, str]] = None,
        checksum: Optional[str] = None,
    ) -> dict[str, Any]:
        """Download, validate, extract metadata, store, and persist a scene.

        Returns:
            Dict with keys: image_id, scene_id, provider, status.
        """
        task_id = self.download_scene(
            scene_id=scene_id,
            provider=provider,
            mission=mission,
            acquisition_date=acquisition_date,
            bands=bands,
            download_urls=download_urls,
            checksum=checksum,
        )

        task = self._download_manager.get_task(task_id)
        if task is None:
            raise SceneDownloadError(f"Task '{task_id}' not found after enqueue")

        if task["status"] == "failed":
            raise SceneDownloadError(
                f"Download failed for scene '{scene_id}': {task.get('error')}"
            )

        destination = task.get("downloaded_bytes", {})
        file_paths: dict[str, str] = {}
        if bands:
            scene_dir = str(
                self._storage.scene_path(
                    provider=provider,
                    mission=mission,
                    acquisition_date=acquisition_date,
                    scene_id=scene_id,
                )
            )
            import os
            for band in bands:
                band_file = os.path.join(scene_dir, f"{scene_id}_{band}.tif")
                if os.path.isfile(band_file):
                    file_paths[band] = band_file

        if not file_paths:
            raise SceneImportError(
                f"No downloaded files found for scene '{scene_id}'"
            )

        provider_instance = self._registry.get(provider)
        raw_metadata = provider_instance.extract_metadata(scene_id, file_paths)
        normalized = self._metadata_extractor.normalize(raw_metadata)

        storage_dir = str(
            self._storage.scene_path(
                provider=provider,
                mission=mission,
                acquisition_date=acquisition_date,
                scene_id=scene_id,
            )
        )

        validated_bands = ",".join(sorted(normalized["bands"]))

        try:
            provider_enum = SatelliteProvider(provider)
        except ValueError:
            provider_enum = SatelliteProvider.OTHER

        image_data = {
            "project_id": project_id,
            "provider": provider_enum,
            "sensor": normalized.get("sensor", "unknown"),
            "capture_date": self._metadata_extractor.normalize_date(
                normalized["acquisition_date"]
            ),
            "resolution": normalized["resolution"],
            "cloud_coverage": normalized["cloud_cover"],
            "scene_id": scene_id,
            "bands_available": validated_bands,
            "crs": self._metadata_extractor.normalize_crs(normalized["crs"]),
            "storage_path": storage_dir,
            "status": ProcessingStatus.PENDING,
            "metadata": {
                "mission": mission,
                "processing_level": normalized.get("processing_level", ""),
                "provider_name": normalized.get("provider_name", provider),
                "file_size_bytes": normalized.get("file_size_bytes", 0),
                "bounding_box": normalized.get("bounding_box", []),
            },
        }

        try:
            image = self._satellite_service.create_image(image_data)
        except DuplicateSceneIdError:
            logger.warning("Scene '%s' already imported, skipping", scene_id)
            existing = self._satellite_service.repo.get_by_scene_id(scene_id)
            if existing is None:
                raise SceneImportError(
                    f"Duplicate scene_id '{scene_id}' but record not found"
                ) from None
            image = existing
        except Exception as exc:
            raise SceneImportError(
                f"Failed to persist satellite image for scene '{scene_id}': {exc}"
            ) from exc

        logger.info(
            "Imported scene '%s' as image '%s' (project=%s)",
            scene_id, image.id, project_id,
        )

        return {
            "image_id": image.id,
            "scene_id": scene_id,
            "provider": provider,
            "status": image.status.value,
            "storage_path": storage_dir,
            "bands_available": validated_bands,
            "capture_date": image.capture_date.isoformat() if image.capture_date else "",
        }

    # -- Providers --

    def list_providers(self) -> list[dict[str, Any]]:
        """Return all registered providers with their capabilities."""
        return self._search.list_providers()

    # -- Storage --

    def get_storage_stats(self) -> dict[str, Any]:
        """Return storage usage statistics."""
        return self._storage.disk_usage()

    # -- Cache --

    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache hit/miss/eviction statistics."""
        return {
            "hits": self._cache.stats["hits"],
            "misses": self._cache.stats["misses"],
            "evictions": self._cache.stats["evictions"],
            "expirations": self._cache.stats["expirations"],
            "invalidations": self._cache.stats["invalidations"],
            "size": self._cache.size,
            "hit_rate": self._cache.hit_rate,
        }

    def clear_cache(self) -> None:
        """Clear the entire search result cache."""
        self._cache.clear()

    # -- Cleanup --

    def shutdown(self) -> None:
        """Shut down the download manager."""
        self._download_manager.shutdown(wait=True)
