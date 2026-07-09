"""Service layer for SatelliteImage business logic.

Business logic belongs here.
Database queries belong in the repository.
"""
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.enums import ProcessingStatus, SatelliteProvider
from app.models.satellite_image import SatelliteImage
from app.repositories.satellite_image import SatelliteImageRepository


class SatelliteImageError(Exception):
    """Base exception for SatelliteImage service errors."""


class DuplicateSceneIdError(SatelliteImageError):
    """Raised when creating/updating with a scene_id that already exists."""


class ImageNotFoundError(SatelliteImageError):
    """Raised when a requested satellite image does not exist."""


class InvalidStatusTransitionError(SatelliteImageError):
    """Raised when a processing status transition is not allowed."""


class InvalidProviderError(SatelliteImageError):
    """Raised when an invalid provider value is supplied."""


class InvalidMetadataError(SatelliteImageError):
    """Raised when metadata validation fails."""


class InvalidRasterPathError(SatelliteImageError):
    """Raised when a raster path is invalid or malformed."""


_VALID_STATUS_TRANSITIONS: dict[ProcessingStatus, set[ProcessingStatus]] = {
    ProcessingStatus.PENDING: {ProcessingStatus.QUEUED, ProcessingStatus.CANCELLED},
    ProcessingStatus.QUEUED: {ProcessingStatus.RUNNING, ProcessingStatus.CANCELLED},
    ProcessingStatus.RUNNING: {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED},
    ProcessingStatus.COMPLETED: {ProcessingStatus.PENDING},
    ProcessingStatus.FAILED: {ProcessingStatus.PENDING, ProcessingStatus.QUEUED},
    ProcessingStatus.CANCELLED: {ProcessingStatus.PENDING},
}


def _validate_status_transition(current: ProcessingStatus, new: ProcessingStatus) -> None:
    """Raise if the status transition is not allowed."""
    allowed = _VALID_STATUS_TRANSITIONS.get(current)
    if allowed is None or new not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition from '{current.value}' to '{new.value}'. "
            f"Allowed targets from '{current.value}': "
            f"{[s.value for s in (allowed or set())]}"
        )


class SatelliteImageService:
    """Service for satellite image business operations.

    All database access is delegated to SatelliteImageRepository.
    """

    def __init__(self, db: Session) -> None:
        self.repo = SatelliteImageRepository(db)

    # -- CRUD --

    def create_image(self, data: dict) -> SatelliteImage:
        """Create a new satellite image with business validation."""
        self._validate_scene_id_unique(data.get("scene_id"))
        self._validate_provider(data.get("provider"))
        return self.repo.create(data)

    def update_image(self, image_id: uuid.UUID, data: dict) -> SatelliteImage:
        """Update an existing satellite image."""
        image = self._get_or_raise(image_id)
        if "status" in data:
            _validate_status_transition(image.status, data["status"])
        if "scene_id" in data and data["scene_id"] != image.scene_id:
            self._validate_scene_id_unique(data["scene_id"])
        return self.repo.update(image, data)

    def delete_image(self, image_id: uuid.UUID) -> None:
        """Soft-delete a satellite image."""
        image = self._get_or_raise(image_id)
        self.repo.delete(image)

    def restore_image(self, image_id: uuid.UUID) -> SatelliteImage:
        """Restore a soft-deleted satellite image."""
        image = self._get_or_raise(image_id, include_deleted=True)
        if image.deleted_at is None:
            raise ImageNotFoundError(
                f"SatelliteImage with id '{image_id}' is not deleted."
            )
        restored = self.repo.restore(image_id)
        if restored is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return restored

    def get_image(self, image_id: uuid.UUID, include_deleted: bool = False) -> SatelliteImage:
        """Retrieve a single satellite image by ID."""
        return self._get_or_raise(image_id, include_deleted)

    # -- List / Search --

    def list_images(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
    ) -> list[SatelliteImage]:
        """List satellite images with optional filters and sorting."""
        return self.repo.list(filters=filters, sort_by=sort_by, sort_order=sort_order)

    def search_images(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SatelliteImage], int]:
        """Paginated search with filters, sorting, and total count."""
        return self.repo.paginate(
            filters=filters, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset,
        )

    # -- Domain operations --

    def validate_image(self, data: dict) -> bool:
        """Validate satellite image data without persisting."""
        scene_id = data.get("scene_id")
        provider = data.get("provider")
        if scene_id:
            existing = self.repo.get_by_scene_id(scene_id)
            if existing:
                raise DuplicateSceneIdError(f"Scene ID '{scene_id}' already exists.")
        if provider:
            self._validate_provider(provider)
        return True

    def change_processing_status(
        self, image_id: uuid.UUID, new_status: ProcessingStatus
    ) -> SatelliteImage:
        """Change processing status with transition validation."""
        image = self._get_or_raise(image_id)
        _validate_status_transition(image.status, new_status)
        return self.repo.update(image, {"status": new_status})

    def attach_metadata(self, image_id: uuid.UUID, metadata: dict) -> SatelliteImage:
        """Attach or merge metadata to an existing satellite image."""
        self._validate_metadata(metadata)
        image = self._get_or_raise(image_id)
        existing = image.image_metadata or {}
        merged = {**existing, **metadata}
        return self.repo.update(image, {"metadata": merged})

    def update_cloud_cover(self, image_id: uuid.UUID, cloud_cover: float) -> SatelliteImage:
        """Update cloud cover percentage with range validation."""
        if cloud_cover < 0.0 or cloud_cover > 100.0:
            raise SatelliteImageError(
                f"Cloud cover must be between 0 and 100, got {cloud_cover}."
            )
        image = self._get_or_raise(image_id)
        return self.repo.update(image, {"cloud_coverage": cloud_cover})

    def update_raster_path(self, image_id: uuid.UUID, path: str) -> SatelliteImage:
        """Update raster storage path with basic validation."""
        self._validate_raster_path(path)
        image = self._get_or_raise(image_id)
        return self.repo.update(image, {"storage_path": path})

    # -- Aggregates --

    def statistics(self, project_id: Optional[uuid.UUID] = None) -> dict:
        """Return aggregate statistics about satellite images."""
        total = self.repo.count()
        by_status = {
            s.value: self.repo.count_by_status(s)
            for s in ProcessingStatus
        }
        result: dict[str, Any] = {
            "total_images": total,
            "by_status": by_status,
        }
        if project_id:
            result["project_id"] = str(project_id)
            result["project_count"] = self.repo.count_by_project(project_id)
        return result

    # -- Internal helpers --

    def _get_or_raise(self, image_id: uuid.UUID, include_deleted: bool = False) -> SatelliteImage:
        obj = self.repo.get_by_id(image_id, include_deleted=include_deleted)
        if obj is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return obj

    def _validate_scene_id_unique(self, scene_id: Optional[str]) -> None:
        if scene_id is None:
            return
        existing = self.repo.get_by_scene_id(scene_id)
        if existing:
            raise DuplicateSceneIdError(f"Scene ID '{scene_id}' already exists.")

    def _validate_provider(self, provider: Any) -> None:
        if provider is None:
            return
        if not isinstance(provider, SatelliteProvider):
            raise InvalidProviderError(f"Invalid provider: {provider}")

    def _validate_metadata(self, metadata: Any) -> None:
        if not isinstance(metadata, dict):
            raise InvalidMetadataError("Metadata must be a dictionary.")

    def _validate_raster_path(self, path: str) -> None:
        if not path or not isinstance(path, str):
            raise InvalidRasterPathError("Raster path must be a non-empty string.")
