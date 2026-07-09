from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime, timezone
from typing import Optional


class UUIDPrimaryKeyMixin:
    """Mixin for a UUID primary key."""
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Mixin for timestamp columns."""
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        """Return timestamp fields as a dictionary."""
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    __abstract__ = True

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def soft_delete(self) -> None:
        """Set the deleted_at timestamp to now."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft-deleted record by setting deleted_at to None."""
        self.deleted_at = None

    def is_deleted(self) -> bool:
        """Return True if the record is soft-deleted."""
        return self.deleted_at is not None

    def is_active_record(self) -> bool:
        """Return True if the record is not soft-deleted."""
        return self.deleted_at is None

    def mark_deleted(self) -> None:
        """Alias for soft_delete()."""
        self.soft_delete()

    def restore_record(self) -> None:
        """Alias for restore()."""
        self.restore()


class AuditMixin:
    """Mixin for audit trail fields (created_by, updated_by).

    Only creates the columns; relationships should be added in concrete models.
    """
    __abstract__ = True

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Note: Relationships are left for future implementation as per requirements.
    # Example (to be implemented in models that use this mixin):
    # creator: Mapped[Optional["User"]] = relationship(
    #     foreign_keys=[created_by],
    #     post_update=True,
    # )
    # updater: Mapped[Optional["User"]] = relationship(
    #     foreign_keys=[updated_by],
    #     post_update=True,
    # )


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Base model with UUID primary key, timestamps, and soft delete."""
    __abstract__ = True