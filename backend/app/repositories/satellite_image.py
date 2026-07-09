"""Repository for SatelliteImage CRUD and query operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.enums import ProcessingStatus, SatelliteProvider
from app.models.satellite_image import SatelliteImage
from app.repositories.base import BaseRepository

_FILTER_MAP: dict[str, Any] = {
    "project_id": SatelliteImage.project_id,
    "provider": SatelliteImage.provider,
    "status": SatelliteImage.status,
    "scene_id": SatelliteImage.scene_id,
    "sensor": SatelliteImage.sensor,
    "crs": SatelliteImage.crs,
}

_SORT_MAP: dict[str, Any] = {
    "capture_date": SatelliteImage.capture_date,
    "created_at": SatelliteImage.created_at,
    "cloud_coverage": SatelliteImage.cloud_coverage,
    "resolution": SatelliteImage.resolution,
    "scene_id": SatelliteImage.scene_id,
}


def _build_filters(stmt, filters: Optional[dict]) -> Any:
    """Apply dynamic filters to a select statement."""
    if not filters:
        return stmt
    for key, value in filters.items():
        if value is None:
            continue
        if key == "capture_date_from" and isinstance(value, datetime):
            stmt = stmt.where(SatelliteImage.capture_date >= value)
        elif key == "capture_date_to" and isinstance(value, datetime):
            stmt = stmt.where(SatelliteImage.capture_date <= value)
        elif key == "cloud_coverage_max":
            stmt = stmt.where(SatelliteImage.cloud_coverage <= value)
        elif key == "resolution_max":
            stmt = stmt.where(SatelliteImage.resolution <= value)
        elif key in _FILTER_MAP:
            column = _FILTER_MAP[key]
            stmt = stmt.where(column == value)
    return stmt


def _build_sort(stmt, sort_by: str, sort_order: str) -> Any:
    """Apply sorting to a select statement."""
    column = _SORT_MAP.get(sort_by)
    if column is None:
        return stmt
    if sort_order == "asc":
        return stmt.order_by(column.asc())
    return stmt.order_by(column.desc())

print("list =", list)
print("tuple =", tuple)
print("type(list) =", type(list))
print("type(tuple) =", type(tuple))


class SatelliteImageRepository(BaseRepository[SatelliteImage]):
    """Repository for satellite image data access.

    Provides standard CRUD via BaseRepository and adds domain-specific
    query methods for filtering, sorting, and pagination.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db, SatelliteImage)

    # -- Domain-specific lookups --

    def get_by_scene_id(self, scene_id: str, include_deleted: bool = False) -> Optional[SatelliteImage]:
        """Retrieve a satellite image by its provider scene identifier."""
        stmt = select(SatelliteImage).where(SatelliteImage.scene_id == scene_id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_project(self, project_id: uuid.UUID, include_deleted: bool = False) -> list[SatelliteImage]:
        """Retrieve all satellite images for a given project."""
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.project_id == project_id)
            .order_by(SatelliteImage.capture_date.desc())
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_provider(
        self, provider: SatelliteProvider, include_deleted: bool = False
    ) -> list[SatelliteImage]:
        """Retrieve all satellite images from a given provider."""
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.provider == provider)
            .order_by(SatelliteImage.capture_date.desc())
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(
        self, status: ProcessingStatus, include_deleted: bool = False
    ) -> list[SatelliteImage]:
        """Retrieve all satellite images with a given processing status."""
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.status == status)
            .order_by(SatelliteImage.capture_date.desc())
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    # -- List / Filter / Paginate --

    def list(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> list[SatelliteImage]:
        """Return all satellite images matching filters, with sorting."""
        stmt = select(SatelliteImage)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        stmt = _build_filters(stmt, filters)
        stmt = _build_sort(stmt, sort_by, sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def paginate(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> tuple[list[SatelliteImage], int]:
        """Return a paginated list of satellite images and total count.

        Args:
            filters: Dict of filter criteria (see _FILTER_MAP keys).
            sort_by: Field to sort by (default: capture_date).
            sort_order: 'asc' or 'desc' (default: desc).
            limit: Maximum items per page.
            offset: Number of items to skip.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Tuple of (items list, total count).
        """
        base_stmt = select(SatelliteImage)
        count_stmt = select(func.count()).select_from(SatelliteImage)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        base_stmt = _build_filters(base_stmt, filters)
        count_stmt = _build_filters(count_stmt, filters)
        base_stmt = _build_sort(base_stmt, sort_by, sort_order)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    # -- Aggregates --

    def count_by_project(self, project_id: uuid.UUID, include_deleted: bool = False) -> int:
        """Count satellite images belonging to a project."""
        stmt = (
            select(func.count())
            .select_from(SatelliteImage)
            .where(SatelliteImage.project_id == project_id)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def count_by_status(self, status: ProcessingStatus, include_deleted: bool = False) -> int:
        """Count satellite images with a given processing status."""
        stmt = (
            select(func.count())
            .select_from(SatelliteImage)
            .where(SatelliteImage.status == status)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0
