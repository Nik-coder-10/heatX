"""Repository for User CRUD and domain-specific queries."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.base import BaseRepository, NotFoundError


class UserRepository(BaseRepository[User]):
    """Repository for user data access.

    Extends BaseRepository with user-specific lookups,
    role management, and search capabilities.
    """

    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    # -- Lookup methods --

    def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by email address."""
        stmt = select(User).where(User.email == email)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(
            stmt.options(joinedload(User.roles))
        ).scalar_one_or_none()

    def get_by_username(self, username: str, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by username."""
        stmt = select(User).where(User.username == username)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(
            stmt.options(joinedload(User.roles))
        ).scalar_one_or_none()

    def get_with_roles(self, id: uuid.UUID, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user with roles eagerly loaded."""
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.id == id)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    # -- Search --

    def search(
        self,
        query: str,
        include_deleted: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """Search users by email, username, first name, or last name."""
        pattern = f"%{query}%"
        base_stmt = select(User).options(joinedload(User.roles)).where(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )
        count_stmt = select(func.count()).select_from(User).where(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(User.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).scalars().all()
        )
        return items, total

    def search_by_email(self, email_query: str, limit: int = 20) -> list[User]:
        """Search users by partial email match."""
        pattern = f"%{email_query}%"
        stmt = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email.ilike(pattern))
            .limit(limit)
        )
        return list(self.db.execute(self._apply_exclude_deleted(stmt)).scalars().all())

    # -- Role management --

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        """Assign a role to a user. Raises NotFoundError if user or role is missing."""
        user = self.get_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.db.execute(
            select(Role).where(Role.id == role_id)
        ).scalar_one_or_none()
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        existing = self.db.execute(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        ).scalar_one_or_none()
        if not existing:
            user.roles.append(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        """Remove a role from a user."""
        user = self.get_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.db.execute(
            select(Role).where(Role.id == role_id)
        ).scalar_one_or_none()
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def get_roles(self, user_id: uuid.UUID) -> list[Role]:
        """Get all roles assigned to a user."""
        user = self.get_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        return list(user.roles)

    def has_role(self, user_id: uuid.UUID, role_name: str) -> bool:
        """Check if a user has a specific role by name."""
        user = self.get_with_roles(user_id)
        if not user:
            return False
        return any(role.name == role_name for role in user.roles)

    # -- Status mutations --

    def update_last_login(self, user_id: uuid.UUID) -> Optional[User]:
        """Update the last_login timestamp to now."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.last_login = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def verify_email(self, user_id: uuid.UUID) -> Optional[User]:
        """Mark a user's email as verified."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.is_verified = True
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user_id: uuid.UUID, new_hashed_password: str) -> Optional[User]:
        """Update a user's password hash."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.hashed_password = new_hashed_password
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate(self, user_id: uuid.UUID) -> Optional[User]:
        """Activate a user account."""
        user = self.get_by_id(user_id, include_deleted=True)
        if not user:
            return None
        user.is_active = True
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user_id: uuid.UUID) -> Optional[User]:
        """Deactivate a user account."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = False
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # -- Admin queries --

    def get_all_users(
        self,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """Retrieve all users with total count."""
        base_stmt = select(User).options(joinedload(User.roles))
        count_stmt = select(func.count()).select_from(User)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(
                base_stmt.order_by(User.created_at.desc())
                .offset(offset).limit(limit)
            ).scalars().all()
        )
        return items, total

    def count_active(self) -> int:
        """Count users with is_active=True."""
        return self.count_filtered(is_active=True)

    def count_verified(self) -> int:
        """Count users with is_verified=True."""
        return self.count_filtered(is_verified=True)

    def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[dict] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[User], int]:
        """Return a paginated list of users with roles eager-loaded."""
        base_stmt = select(User).options(joinedload(User.roles))
        count_stmt = select(func.count()).select_from(User)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        if filters:
            for key, value in filters.items():
                if value is not None:
                    column = getattr(User, key, None)
                    if column is not None:
                        base_stmt = base_stmt.where(column == value)
                        count_stmt = count_stmt.where(column == value)
        if sort_by:
            column = getattr(User, sort_by, None)
            if column is not None:
                order_fn = column.asc if sort_order == "asc" else column.desc
                base_stmt = base_stmt.order_by(order_fn())
        offset = (page - 1) * page_size
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.offset(offset).limit(page_size)).scalars().all()
        )
        return items, total
