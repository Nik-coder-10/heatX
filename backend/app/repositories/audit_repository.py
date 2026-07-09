"""Repository for AuditLog query operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for audit log data access and query operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, AuditLog)

    def get_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries for a specific user."""
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.user_id == user_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.user_id == user_id)
        )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_by_action(
        self,
        action: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries matching an action pattern."""
        pattern = f"%{action}%"
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.action.ilike(pattern))
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action.ilike(pattern))
        )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_by_resource(
        self,
        resource: str,
        resource_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries for a specific resource."""
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.resource == resource)
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.resource == resource)
        )
        if resource_id:
            base_stmt = base_stmt.where(
                AuditLog.details["resource_id"].as_string() == resource_id
            )
            count_stmt = count_stmt.where(
                AuditLog.details["resource_id"].as_string() == resource_id
            )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_by_ip(
        self,
        ip_address: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries from a specific IP address."""
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.ip_address == ip_address)
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.ip_address == ip_address)
        )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve audit log entries within a date range."""
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.timestamp >= start, AuditLog.timestamp <= end)
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.timestamp >= start, AuditLog.timestamp <= end)
        )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_security_events(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve security-related audit events (login, logout, password changes)."""
        security_actions = [
            "user.login",
            "user.logout",
            "user.login.failed",
            "user.password.change",
            "user.password.reset",
            "user.role.assign",
            "user.role.remove",
        ]
        base_stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .where(AuditLog.action.in_(security_actions))
        )
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action.in_(security_actions))
        )
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(AuditLog.timestamp.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def get_recent_activity(
        self,
        limit: int = 20,
    ) -> list[AuditLog]:
        """Retrieve the most recent audit log entries."""
        stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def log_event(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        resource: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        return self.create({
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details,
        })

    def count_by_action(self, action: str) -> int:
        """Count audit log entries for a specific action pattern."""
        pattern = f"%{action}%"
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action.ilike(pattern))
        )
        return self.db.execute(stmt).scalar() or 0

    def get_distinct_actions(self) -> list[str]:
        """Get a list of distinct actions recorded in audit logs."""
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
        rows = self.db.execute(stmt).all()
        return [row[0] for row in rows]

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[AuditLog], int]:
        """Return a paginated list of audit logs with user eager-loaded."""
        base_stmt = select(AuditLog).options(joinedload(AuditLog.user))
        count_stmt = select(func.count()).select_from(AuditLog)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        if filters:
            for key, value in filters.items():
                if value is not None:
                    column = getattr(AuditLog, key, None)
                    if column is not None:
                        base_stmt = base_stmt.where(column == value)
                        count_stmt = count_stmt.where(column == value)
        if sort_by:
            column = getattr(AuditLog, sort_by, None)
            if column is not None:
                order_fn = column.asc if sort_order == "asc" else column.desc
                base_stmt = base_stmt.order_by(order_fn())
        offset = (page - 1) * page_size
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.offset(offset).limit(page_size)).scalars().all()
        )
        return items, total
