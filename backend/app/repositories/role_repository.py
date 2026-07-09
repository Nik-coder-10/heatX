"""Repository for Role CRUD and assignment operations."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.base import BaseRepository, DuplicateError, NotFoundError


class RoleRepository(BaseRepository[Role]):
    """Repository for role data access and user-role assignment."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, Role)

    def get_by_name(self, name: str, include_deleted: bool = False) -> Optional[Role]:
        """Retrieve a role by its name."""
        stmt = select(Role).where(Role.name == name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name: str, description: Optional[str] = None) -> Role:
        """Retrieve an existing role by name or create it."""
        role = self.get_by_name(name)
        if role:
            return role
        return self.create({"name": name, "description": description})

    def get_all_roles(self, include_deleted: bool = False) -> list[Role]:
        """Retrieve all roles ordered by name."""
        stmt = select(Role).order_by(Role.name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_users_with_role(
        self, role_id: uuid.UUID, include_deleted: bool = False
    ) -> tuple[list[User], int]:
        """Get all users assigned to a specific role."""
        role = self.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.roles.any(Role.id == role_id))
        )
        count_stmt = (
            select(func.count())
            .select_from(User)
            .where(User.roles.any(Role.id == role_id))
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        users = list(self.db.execute(stmt).scalars().all())
        return users, total

    def assign_to_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> Role:
        """Assign a role to a user. Returns the role."""
        role = self.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        user = self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        existing = self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        ).scalar_one_or_none()
        if not existing:
            user.roles.append(role)
            self.db.commit()
        return role

    def remove_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Remove a role from a user."""
        user = self.db.execute(
            select(User).options(joinedload(User.roles)).where(User.id == user_id)
        ).scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.get_by_id(role_id)
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()

    def get_role_counts(self, include_deleted: bool = False) -> list[dict]:
        """Return a list of roles with user counts."""
        stmt = select(Role.id, Role.name, func.count(UserRole.user_id).label("user_count")).outerjoin(
            UserRole, Role.id == UserRole.role_id
        ).group_by(Role.id, Role.name).order_by(Role.name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        rows = self.db.execute(stmt).all()
        return [
            {"role_id": str(row.id), "name": row.name, "user_count": row.user_count}
            for row in rows
        ]

    def create(self, data: dict) -> Role:
        """Create a new role with duplicate name checking."""
        name = data.get("name")
        if name:
            existing = self.get_by_name(name.value if hasattr(name, "value") else name)
            if existing:
                raise DuplicateError(f"Role with name '{name}' already exists")
        return super().create(data)
