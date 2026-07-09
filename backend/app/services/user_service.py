"""User management service — CRUD, role assignment, admin queries."""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.password import get_password_hash
from app.models.user import User
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.base import DuplicateError, NotFoundError
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger("app.services.user")


class UserService:
    """Coordinates user lifecycle operations across repositories."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditLogRepository(db)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_user(
        self,
        user_in: UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """Create a new user account (admin endpoint).

        Flow:
            1. Validate email uniqueness
            2. Validate username uniqueness
            3. Validate phone uniqueness (if provided)
            4. Hash password
            5. Create user
            6. Assign default role (viewer)
            7. Audit log

        Returns:
            The created User ORM object.

        Raises:
            DuplicateError: If email, username, or phone already exists.
        """
        if self.user_repo.get_by_email(user_in.email):
            raise DuplicateError(f"Email '{user_in.email}' is already registered")

        if self.user_repo.get_by_username(user_in.username):
            raise DuplicateError(f"Username '{user_in.username}' is already taken")

        if user_in.phone:
            existing = self.user_repo.first(phone=user_in.phone)
            if existing:
                raise DuplicateError(f"Phone '{user_in.phone}' is already registered")

        hashed = get_password_hash(user_in.password)
        user = self.user_repo.create({
            "email": user_in.email,
            "username": user_in.username,
            "hashed_password": hashed,
            "first_name": user_in.first_name,
            "last_name": user_in.last_name,
            "phone": user_in.phone,
            "is_active": True,
            "is_verified": False,
        })

        default_role = self.role_repo.get_by_name("viewer")
        if default_role:
            self.user_repo.assign_role(user.id, default_role.id)

        self.audit_repo.log_event(
            user_id=user.id,
            action="user.create",
            resource="user",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user_in.email, "username": user_in.username},
        )
        logger.info("User created", extra={"user_id": str(user.id)})
        return user

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_user(
        self,
        user_id: uuid.UUID,
        user_in: UserUpdate,
        ip_address: Optional[str] = None,
    ) -> User:
        """Update a user's profile fields.

        Flow:
            1. Lookup user
            2. Build update dict from non-None fields
            3. If email changed, verify uniqueness
            4. If username changed, verify uniqueness
            5. If phone changed, verify uniqueness
            6. Apply update
            7. Audit log

        Returns:
            Updated User ORM object.

        Raises:
            NotFoundError: If user does not exist.
            DuplicateError: If email, username, or phone is taken.
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        update_data = {}
        for field in ("first_name", "last_name", "email", "username", "phone", "is_verified", "is_active"):
            value = getattr(user_in, field, None)
            if value is not None:
                update_data[field] = value

        if "email" in update_data and update_data["email"] != user.email:
            existing = self.user_repo.get_by_email(update_data["email"])
            if existing and existing.id != user_id:
                raise DuplicateError(f"Email '{update_data['email']}' is already registered")

        if "username" in update_data and update_data["username"] != user.username:
            existing = self.user_repo.get_by_username(update_data["username"])
            if existing and existing.id != user_id:
                raise DuplicateError(f"Username '{update_data['username']}' is already taken")

        if "phone" in update_data and update_data["phone"] != user.phone:
            existing = self.user_repo.first(phone=update_data["phone"])
            if existing and existing.id != user_id:
                raise DuplicateError(f"Phone '{update_data['phone']}' is already registered")

        updated = self.user_repo.update(user, update_data)

        changed_fields = list(update_data.keys())
        if changed_fields:
            self.audit_repo.log_event(
                user_id=user_id,
                action="user.update",
                resource="user",
                ip_address=ip_address,
                details={"fields": changed_fields},
            )
            logger.info("User updated", extra={"user_id": str(user_id), "fields": changed_fields})

        return updated

    # ------------------------------------------------------------------
    # Delete / Restore
    # ------------------------------------------------------------------

    def soft_delete_user(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> None:
        """Soft-delete a user account.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        self.user_repo.delete(user)
        self.audit_repo.log_event(
            user_id=user_id,
            action="user.delete.soft",
            resource="user",
            ip_address=ip_address,
        )
        logger.info("User soft-deleted", extra={"user_id": str(user_id)})

    def delete_user(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> None:
        """Permanently delete a user account (admin).

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.get_by_id(user_id, include_deleted=True)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        self.user_repo.hard_delete(user)
        self.audit_repo.log_event(
            user_id=user_id,
            action="user.delete.hard",
            resource="user",
            ip_address=ip_address,
        )
        logger.info("User hard-deleted", extra={"user_id": str(user_id)})

    def restore_user(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> User:
        """Restore a soft-deleted user.

        Returns:
            The restored User ORM object.

        Raises:
            NotFoundError: If user does not exist or was not soft-deleted.
        """
        user = self.user_repo.restore(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found or not soft-deleted")

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.restore",
            resource="user",
            ip_address=ip_address,
        )
        logger.info("User restored", extra={"user_id": str(user_id)})
        return user

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def activate_user(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> User:
        """Activate a user account.

        Returns:
            The activated User ORM object.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.activate(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.activate",
            resource="user",
            ip_address=ip_address,
        )
        logger.info("User activated", extra={"user_id": str(user_id)})
        return user

    def deactivate_user(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> User:
        """Deactivate a user account.

        Returns:
            The deactivated User ORM object.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.deactivate(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")

        self.audit_repo.log_event(
            user_id=user_id,
            action="user.deactivate",
            resource="user",
            ip_address=ip_address,
        )
        logger.info("User deactivated", extra={"user_id": str(user_id)})
        return user

    # ------------------------------------------------------------------
    # Role management
    # ------------------------------------------------------------------

    def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> User:
        """Assign a role to a user.

        Returns:
            The updated User ORM object with roles eager-loaded.

        Raises:
            NotFoundError: If user or role does not exist.
        """
        user = self.user_repo.assign_role(user_id, role_id)
        self.audit_repo.log_event(
            user_id=user_id,
            action="user.role.assign",
            resource="user",
            ip_address=ip_address,
            details={"role_id": str(role_id)},
        )
        logger.info("Role assigned", extra={"user_id": str(user_id), "role_id": str(role_id)})
        return user

    def remove_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> User:
        """Remove a role from a user.

        Returns:
            The updated User ORM object.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.remove_role(user_id, role_id)
        self.audit_repo.log_event(
            user_id=user_id,
            action="user.role.remove",
            resource="user",
            ip_address=ip_address,
            details={"role_id": str(role_id)},
        )
        logger.info("Role removed", extra={"user_id": str(user_id), "role_id": str(role_id)})
        return user

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_profile(self, user_id: uuid.UUID) -> User:
        """Get a user's full profile with roles.

        Raises:
            NotFoundError: If user does not exist.
        """
        user = self.user_repo.get_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        return user

    def search_users(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[User], int]:
        """Search users by email, username, or name.

        Returns:
            Tuple of (user list, total count).

        Raises:
            ValueError: If query is empty.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        offset = (page - 1) * page_size
        return self.user_repo.search(
            query=query.strip(),
            include_deleted=include_deleted,
            limit=page_size,
            offset=offset,
        )
