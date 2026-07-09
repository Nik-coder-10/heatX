"""Role management service — CRUD, user assignment, queries."""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.database.enums import UserRole
from app.models.role import Role
from app.models.user import User
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.base import DuplicateError, NotFoundError
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger("app.services.role")


class RoleService:
    """Coordinates role lifecycle and user-role assignment."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_role(
        self,
        name: UserRole,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Role:
        """Create a new role.

        Flow:
            1. Check for duplicate name
            2. Create role
            3. Audit log

        Returns:
            The created Role ORM object.

        Raises:
            DuplicateError: If a role with this name already exists.
        """
        existing = self.role_repo.get_by_name(name)
        if existing:
            raise DuplicateError(f"Role with name '{name}' already exists")

        role = self.role_repo.create({"name": name, "description": description})
        self.audit_repo.log_event(
            user_id=None,
            action="role.create",
            resource="role",
            ip_address=ip_address,
            details={"name": name.value if hasattr(name, "value") else name},
        )
        logger.info("Role created", extra={"role_id": str(role.id), "name": str(name)})
        return role

    def rename_role(
        self,
        role_id: uuid.UUID,
        new_name: UserRole,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Role:
        """Rename a role.

        Flow:
            1. Lookup role
            2. Check new name is not taken
            3. Update role name and optional description
            4. Audit log

        Returns:
            The updated Role ORM object.

        Raises:
            NotFoundError: If role does not exist.
            DuplicateError: If new name is already taken by another role.
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")

        if new_name != role.name:
            existing = self.role_repo.get_by_name(new_name)
            if existing:
                raise DuplicateError(f"Role with name '{new_name}' already exists")

        update_data = {"name": new_name}
        if description is not None:
            update_data["description"] = description

        updated = self.role_repo.update(role, update_data)
        self.audit_repo.log_event(
            user_id=None,
            action="role.update",
            resource="role",
            ip_address=ip_address,
            details={"role_id": str(role_id), "old_name": str(role.name), "new_name": str(new_name)},
        )
        logger.info("Role renamed", extra={"role_id": str(role_id), "new_name": str(new_name)})
        return updated

    def delete_role(
        self,
        role_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> None:
        """Soft-delete a role.

        Flow:
            1. Lookup role
            2. Soft-delete
            3. Audit log

        Raises:
            NotFoundError: If role does not exist.
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")

        self.role_repo.delete(role)
        self.audit_repo.log_event(
            user_id=None,
            action="role.delete",
            resource="role",
            ip_address=ip_address,
            details={"role_id": str(role_id), "name": str(role.name)},
        )
        logger.info("Role deleted", extra={"role_id": str(role_id)})

    # ------------------------------------------------------------------
    # User assignment
    # ------------------------------------------------------------------

    def assign_users(
        self,
        role_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        ip_address: Optional[str] = None,
    ) -> Role:
        """Assign multiple users to a role.

        Flow:
            1. Validate role exists
            2. For each user, validate existence and assign
            3. Audit log

        Returns:
            The Role ORM object.

        Raises:
            NotFoundError: If role or any user does not exist.
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")

        assigned = []
        for uid in user_ids:
            try:
                self.user_repo.assign_role(uid, role_id)
                assigned.append(str(uid))
            except NotFoundError:
                raise NotFoundError(f"User with id {uid} not found")

        self.audit_repo.log_event(
            user_id=None,
            action="role.assign.users",
            resource="role",
            ip_address=ip_address,
            details={"role_id": str(role_id), "user_ids": assigned},
        )
        logger.info("Users assigned to role", extra={"role_id": str(role_id), "count": len(assigned)})
        return role

    def remove_users(
        self,
        role_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        ip_address: Optional[str] = None,
    ) -> Role:
        """Remove multiple users from a role.

        Flow:
            1. Validate role exists
            2. For each user, validate existence and remove
            3. Audit log

        Returns:
            The Role ORM object.

        Raises:
            NotFoundError: If role or any user does not exist.
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")

        removed = []
        for uid in user_ids:
            try:
                self.user_repo.remove_role(uid, role_id)
                removed.append(str(uid))
            except NotFoundError:
                raise NotFoundError(f"User with id {uid} not found")

        self.audit_repo.log_event(
            user_id=None,
            action="role.remove.users",
            resource="role",
            ip_address=ip_address,
            details={"role_id": str(role_id), "user_ids": removed},
        )
        logger.info("Users removed from role", extra={"role_id": str(role_id), "count": len(removed)})
        return role

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_users(
        self,
        role_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[User], int]:
        """Get all users assigned to a specific role (paginated).

        Flow:
            1. Validate role exists
            2. Query users with this role
            3. Return paginated results

        Returns:
            Tuple of (user list, total count).

        Raises:
            NotFoundError: If role does not exist.
        """
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")

        offset = (page - 1) * page_size
        users, total = self.role_repo.get_users_with_role(
            role_id=role_id,
            include_deleted=include_deleted,
        )

        start = offset
        end = offset + page_size
        return users[start:end], total
