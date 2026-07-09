"""Base repository with common CRUD operations.

All domain repositories should inherit from BaseRepository
to ensure consistent query patterns across the codebase.
"""

from __future__ import annotations


import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class RepositoryError(Exception):
    """Base exception for all repository errors."""


class NotFoundError(RepositoryError):
    """Raised when a requested record is not found."""


class DuplicateError(RepositoryError):
    """Raised when a unique constraint would be violated."""


class BaseRepository(Generic[ModelT]):
    """Generic base repository providing common CRUD operations.

    Features:
        - SQLAlchemy 2.x select() syntax
        - Soft-delete awareness (filters deleted records by default)
        - Support for included deleted records when needed
        - Consistent error handling
        - Bulk operations and pagination
    """

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model
        self._soft_delete = hasattr(model, "deleted_at")

    def _apply_exclude_deleted(self, stmt):
        """Exclude soft-deleted records unless the model doesn't support it."""
        if self._soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, id: uuid.UUID, include_deleted: bool = False) -> Optional[ModelT]:
        """Retrieve a record by UUID primary key."""
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self, include_deleted: bool = False) -> list[ModelT]:
        """Retrieve all records with optional soft-delete filtering."""
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def filter(self, include_deleted: bool = False, **kwargs) -> list[ModelT]:
        """Retrieve records matching the given field=value criteria."""
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return list(self.db.execute(stmt).scalars().all())

    def first(self, include_deleted: bool = False, **kwargs) -> Optional[ModelT]:
        """Retrieve the first record matching the given criteria."""
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none()

    def create(self, data: dict) -> ModelT:
        """Create a new record from a dictionary of field values."""
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelT, data: dict) -> ModelT:
        """Update an existing record with partial field data."""
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        """Soft-delete if model supports it, otherwise hard-delete."""
        if self._soft_delete:
            obj.deleted_at = datetime.now(timezone.utc)
            self.db.add(obj)
        else:
            self.db.delete(obj)
        self.db.commit()

    def soft_delete(self, obj: ModelT) -> None:
        """Explicitly soft-delete a record. Raises if model lacks deleted_at."""
        if not self._soft_delete:
            raise RepositoryError(
                f"Model {self.model.__name__} does not support soft delete"
            )
        obj.deleted_at = datetime.now(timezone.utc)
        self.db.add(obj)
        self.db.commit()

    def hard_delete(self, obj: ModelT) -> None:
        """Permanently remove a record from the database."""
        self.db.delete(obj)
        self.db.commit()

    def restore(self, id: uuid.UUID) -> Optional[ModelT]:
        """Restore a soft-deleted record by clearing deleted_at."""
        if not self._soft_delete:
            return None
        obj = self.db.execute(
            select(self.model).where(self.model.id == id)
        ).scalar_one_or_none()
        if obj:
            obj.deleted_at = None
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def count(self, include_deleted: bool = False) -> int:
        """Return the total number of records."""
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def exists(self, id: uuid.UUID, include_deleted: bool = False) -> bool:
        """Check if a record with the given UUID exists."""
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).first() is not None

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        """Return a paginated list of records and total count.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page (max 100).
            filters: Dict of column=value equality filters.
            sort_by: Column name to sort by.
            sort_order: 'asc' or 'desc'.
            include_deleted: Whether to include soft-deleted records.

        Returns:
            Tuple of (items list, total count).
        """
        base_stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        if filters:
            for key, value in filters.items():
                if value is not None:
                    column = getattr(self.model, key, None)
                    if column is not None:
                        base_stmt = base_stmt.where(column == value)
                        count_stmt = count_stmt.where(column == value)
        if sort_by:
            column = getattr(self.model, sort_by, None)
            if column is not None:
                order_fn = column.asc if sort_order == "asc" else column.desc
                base_stmt = base_stmt.order_by(order_fn())
        offset = (page - 1) * page_size
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.offset(offset).limit(page_size)).scalars().all()
        )
        return items, total

    def bulk_create(self, objects: list[dict]) -> list[ModelT]:
        """Create multiple records in a single transaction."""
        instances = [self.model(**data) for data in objects]
        self.db.add_all(instances)
        self.db.commit()
        for obj in instances:
            self.db.refresh(obj)
        return instances

    def bulk_update(self, ids: list[uuid.UUID], data: dict) -> int:
        """Update multiple records identified by UUIDs with the same data.

        Returns the number of updated rows.
        """
        stmt = select(self.model).where(self.model.id.in_(ids))
        if self._soft_delete:
            stmt = self._apply_exclude_deleted(stmt)
        objects = list(self.db.execute(stmt).scalars().all())
        for obj in objects:
            for field, value in data.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)
        self.db.commit()
        return len(objects)

    def bulk_delete(self, ids: list[uuid.UUID]) -> int:
        """Soft-delete multiple records by UUID if supported, else hard-delete.

        Returns the number of affected rows.
        """
        stmt = select(self.model).where(self.model.id.in_(ids))
        if self._soft_delete:
            stmt = self._apply_exclude_deleted(stmt)
        objects = list(self.db.execute(stmt).scalars().all())
        now = datetime.now(timezone.utc)
        for obj in objects:
            if self._soft_delete:
                obj.deleted_at = now
                self.db.add(obj)
            else:
                self.db.delete(obj)
        self.db.commit()
        return len(objects)

    def count_filtered(self, include_deleted: bool = False, **kwargs) -> int:
        """Count records matching the given field=value criteria."""
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None and value is not None:
                stmt = stmt.where(column == value)
        return self.db.execute(stmt).scalar() or 0
