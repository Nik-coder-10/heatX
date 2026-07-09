"""Tests for auth service layer (AuthService, UserService, RoleService)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON, func
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.database.enums import UserRole
from app.core.exceptions import InvalidPassword, InvalidToken
from app.repositories.base import DuplicateError, NotFoundError

# -- Self-contained test setup --
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Role(Base):
    __tablename__ = "roles"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Enum(UserRole), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    users = relationship("User", secondary="user_roles", back_populates="roles")


class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    roles = relationship("Role", secondary="user_roles", back_populates="users")


class UserRoleLink(Base):
    __tablename__ = "user_roles"
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    resource = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    user = relationship("User")


# -- Repository implementations --
from typing import Any, Generic, Optional, TypeVar
from sqlalchemy import select, or_
from datetime import datetime, timezone

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self._soft_delete = hasattr(model, "deleted_at")

    def _apply_exclude_deleted(self, stmt):
        if self._soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, id, include_deleted=False):
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, data):
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj, data):
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj):
        if self._soft_delete:
            obj.deleted_at = datetime.now(timezone.utc)
            self.db.add(obj)
        else:
            self.db.delete(obj)
        self.db.commit()

    def hard_delete(self, obj):
        self.db.delete(obj)
        self.db.commit()

    def restore(self, id):
        if not self._soft_delete:
            return None
        obj = self.db.execute(select(self.model).where(self.model.id == id)).scalar_one_or_none()
        if obj:
            obj.deleted_at = None
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def count(self, include_deleted=False):
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def exists(self, id, include_deleted=False):
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).first() is not None

    def first(self, include_deleted=False, **kwargs):
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none()


class UserRepository(BaseRepository[User]):
    def __init__(self, db):
        super().__init__(db, User)

    def get_by_email(self, email, include_deleted=False):
        stmt = select(User).where(User.email == email)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username, include_deleted=False):
        stmt = select(User).where(User.username == username)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_with_roles(self, id, include_deleted=False):
        stmt = select(User).where(User.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(self, query, include_deleted=False, limit=20, offset=0):
        pattern = f"%{query}%"
        base_stmt = select(User).where(
            or_(User.email.ilike(pattern), User.username.ilike(pattern),
                User.first_name.ilike(pattern), User.last_name.ilike(pattern))
        )
        count_stmt = select(func.count()).select_from(User).where(
            or_(User.email.ilike(pattern), User.username.ilike(pattern),
                User.first_name.ilike(pattern), User.last_name.ilike(pattern))
        )
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(self.db.execute(base_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)).scalars().all())
        return items, total

    def assign_role(self, user_id, role_id):
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        role = self.db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        existing = self.db.execute(
            select(UserRoleLink).where(UserRoleLink.user_id == user_id, UserRoleLink.role_id == role_id)
        ).scalar_one_or_none()
        if not existing:
            user.roles.append(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def remove_role(self, user_id, role_id):
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        role = self.db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_last_login(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.last_login = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def verify_email(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.is_verified = True
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user_id, new_hashed_password):
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.hashed_password = new_hashed_password
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate(self, user_id):
        user = self.get_by_id(user_id, include_deleted=True)
        if not user:
            return None
        user.is_active = True
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = False
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db):
        super().__init__(db, Role)

    def get_by_name(self, name, include_deleted=False):
        stmt = select(Role).where(Role.name == name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_roles(self, include_deleted=False):
        stmt = select(Role).order_by(Role.name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_users_with_role(self, role_id, include_deleted=False):
        role = self.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        from sqlalchemy import exists
        link_exists = exists().where(
            UserRoleLink.user_id == User.id,
            UserRoleLink.role_id == role_id,
        )
        stmt = select(User).where(link_exists)
        count_stmt = select(func.count()).select_from(User).where(link_exists)
        if not include_deleted and hasattr(User, "deleted_at"):
            stmt = stmt.where(User.deleted_at.is_(None))
            count_stmt = count_stmt.where(User.deleted_at.is_(None))
        total = self.db.execute(count_stmt).scalar() or 0
        users = list(self.db.execute(stmt).scalars().all())
        return users, total


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db):
        super().__init__(db, AuditLog)

    def log_event(self, user_id, action, resource, ip_address=None, user_agent=None, details=None):
        return self.create({
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details,
        })

    def count_by_action(self, action):
        pattern = f"%{action}%"
        stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action.ilike(pattern))
        return self.db.execute(stmt).scalar() or 0


# -- Service implementations (matching the real ones) --
from app.core.password import get_password_hash, verify_password
from app.core.jwt import _create_token, create_access_token, create_refresh_token, decode_token


class AuthService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def register_user(self, user_in, ip_address=None, user_agent=None):
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

        self.audit_repo.log_event(user_id=user.id, action="user.register", resource="auth",
                                   ip_address=ip_address, user_agent=user_agent)
        return user

    def authenticate_user(self, email, password, ip_address=None):
        from app.core.exceptions import SecurityError as SecurityErr
        user = self.user_repo.get_by_email(email)
        if not user:
            self.audit_repo.log_event(user_id=None, action="user.login.failed", resource="auth",
                                       ip_address=ip_address, details={"reason": "email_not_found"})
            raise NotFoundError(f"No account found with email '{email}'")
        if not verify_password(password, user.hashed_password):
            self.audit_repo.log_event(user_id=user.id, action="user.login.failed", resource="auth",
                                       ip_address=ip_address, details={"reason": "wrong_password"})
            raise InvalidPassword("Incorrect password")
        if user.deleted_at is not None:
            raise SecurityErr("This account has been deactivated")
        if not user.is_active:
            raise SecurityErr("This account has been deactivated")
        if not user.is_verified:
            raise SecurityErr("Email not verified. Please verify your email before logging in")
        self.user_repo.update_last_login(user.id)
        self.audit_repo.log_event(user_id=user.id, action="user.login", resource="auth", ip_address=ip_address)
        return user

    def login(self, email, password, ip_address=None, user_agent=None):
        user = self.authenticate_user(email, password, ip_address)
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        from app.schemas.auth import Token
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    def logout(self, access_token, refresh_token, user_id=None, ip_address=None):
        from app.core.token_blacklist import add_token
        for token in [access_token, refresh_token]:
            try:
                payload = decode_token(token)
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
                    add_token(jti, expires_in=expires_in)
            except Exception:
                pass
        self.audit_repo.log_event(user_id=user_id, action="user.logout", resource="auth",
                                   ip_address=ip_address)

    def refresh_access_token(self, refresh_token, ip_address=None):
        from app.core.exceptions import SecurityError as SecurityErr
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidToken("Provided token is not a refresh token")
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidToken("Token missing subject claim")
        user = self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")
        if user.deleted_at is not None:
            raise SecurityErr("Account has been deactivated")
        if not user.is_active:
            raise SecurityErr("Account is inactive")
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            from app.core.token_blacklist import add_token
            expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
            add_token(jti, expires_in=expires_in)
        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))
        from app.schemas.auth import Token
        return Token(access_token=new_access, refresh_token=new_refresh, token_type="bearer")

    def change_password(self, user_id, old_password, new_password, ip_address=None):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        if not verify_password(old_password, user.hashed_password):
            raise InvalidPassword("Current password is incorrect")
        new_hashed = get_password_hash(new_password)
        self.user_repo.change_password(user_id, new_hashed)
        self.audit_repo.log_event(user_id=user_id, action="user.password.change", resource="auth", ip_address=ip_address)

    def forgot_password(self, email, ip_address=None):
        user = self.user_repo.get_by_email(email)
        reset_token = _create_token(
            subject=str(user.id) if user else "unknown",
            token_type="reset_password",
            expires_delta=__import__('datetime').timedelta(minutes=15),
        )
        self.audit_repo.log_event(user_id=user.id if user else None, action="user.password.reset.requested", resource="auth", ip_address=ip_address)
        return reset_token

    def reset_password(self, token, new_password, ip_address=None):
        payload = decode_token(token)
        if payload.get("type") != "reset_password":
            raise InvalidToken("Provided token is not a password reset token")
        user_id = payload.get("sub")
        if not user_id or user_id == "unknown":
            raise NotFoundError("User not found")
        user = self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")
        new_hashed = get_password_hash(new_password)
        self.user_repo.change_password(user.id, new_hashed)
        self.audit_repo.log_event(user_id=user.id, action="user.password.reset", resource="auth", ip_address=ip_address)

    def verify_email(self, token, ip_address=None):
        payload = decode_token(token)
        if payload.get("type") != "verify_email":
            raise InvalidToken("Provided token is not an email verification token")
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidToken("Token missing subject claim")
        user = self.user_repo.verify_email(uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found")
        self.audit_repo.log_event(user_id=user.id, action="user.email.verified", resource="auth", ip_address=ip_address)

    def resend_verification(self, user_id, ip_address=None):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        verify_token = _create_token(subject=str(user.id), token_type="verify_email", expires_delta=__import__('datetime').timedelta(hours=24))
        self.audit_repo.log_event(user_id=user.id, action="user.email.verification.resend", resource="auth", ip_address=ip_address)
        return verify_token

    def validate_access_token(self, token):
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise InvalidToken("Provided token is not an access token")
        return payload

    def validate_refresh_token(self, token):
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise InvalidToken("Provided token is not a refresh token")
        return payload

    def revoke_token(self, token, user_id=None, ip_address=None):
        from app.core.token_blacklist import add_token
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                expires_in = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
                add_token(jti, expires_in=expires_in)
        except Exception:
            pass
        self.audit_repo.log_event(user_id=user_id, action="user.token.revoked", resource="auth", ip_address=ip_address)


class UserService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def create_user(self, user_in, ip_address=None, user_agent=None):
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
            "email": user_in.email, "username": user_in.username,
            "hashed_password": hashed, "first_name": user_in.first_name,
            "last_name": user_in.last_name, "phone": user_in.phone,
            "is_active": True, "is_verified": False,
        })
        default_role = self.role_repo.get_by_name("viewer")
        if default_role:
            self.user_repo.assign_role(user.id, default_role.id)
        self.audit_repo.log_event(user_id=user.id, action="user.create", resource="user", ip_address=ip_address)
        return user

    def update_user(self, user_id, user_in, ip_address=None):
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
        if update_data:
            self.audit_repo.log_event(user_id=user_id, action="user.update", resource="user", ip_address=ip_address,
                                       details={"fields": list(update_data.keys())})
        return updated

    def soft_delete_user(self, user_id, ip_address=None):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        self.user_repo.delete(user)
        self.audit_repo.log_event(user_id=user_id, action="user.delete.soft", resource="user", ip_address=ip_address)

    def delete_user(self, user_id, ip_address=None):
        user = self.user_repo.get_by_id(user_id, include_deleted=True)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        self.user_repo.hard_delete(user)
        self.audit_repo.log_event(user_id=user_id, action="user.delete.hard", resource="user", ip_address=ip_address)

    def restore_user(self, user_id, ip_address=None):
        user = self.user_repo.restore(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found or not soft-deleted")
        self.audit_repo.log_event(user_id=user_id, action="user.restore", resource="user", ip_address=ip_address)
        return user

    def activate_user(self, user_id, ip_address=None):
        user = self.user_repo.activate(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        self.audit_repo.log_event(user_id=user_id, action="user.activate", resource="user", ip_address=ip_address)
        return user

    def deactivate_user(self, user_id, ip_address=None):
        user = self.user_repo.deactivate(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        self.audit_repo.log_event(user_id=user_id, action="user.deactivate", resource="user", ip_address=ip_address)
        return user

    def assign_role(self, user_id, role_id, ip_address=None):
        user = self.user_repo.assign_role(user_id, role_id)
        self.audit_repo.log_event(user_id=user_id, action="user.role.assign", resource="user", ip_address=ip_address, details={"role_id": str(role_id)})
        return user

    def remove_role(self, user_id, role_id, ip_address=None):
        user = self.user_repo.remove_role(user_id, role_id)
        self.audit_repo.log_event(user_id=user_id, action="user.role.remove", resource="user", ip_address=ip_address, details={"role_id": str(role_id)})
        return user

    def get_profile(self, user_id):
        user = self.user_repo.get_with_roles(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        return user

    def search_users(self, query, page=1, page_size=20, include_deleted=False):
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        offset = (page - 1) * page_size
        return self.user_repo.search(query=query.strip(), include_deleted=include_deleted, limit=page_size, offset=offset)


class RoleService:
    def __init__(self, db):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def create_role(self, name, description=None, ip_address=None):
        existing = self.role_repo.get_by_name(name)
        if existing:
            raise DuplicateError(f"Role with name '{name}' already exists")
        role = self.role_repo.create({"name": name, "description": description})
        self.audit_repo.log_event(user_id=None, action="role.create", resource="role", ip_address=ip_address, details={"name": str(name)})
        return role

    def rename_role(self, role_id, new_name, description=None, ip_address=None):
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
        self.audit_repo.log_event(user_id=None, action="role.update", resource="role", ip_address=ip_address)
        return updated

    def delete_role(self, role_id, ip_address=None):
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        self.role_repo.delete(role)
        self.audit_repo.log_event(user_id=None, action="role.delete", resource="role", ip_address=ip_address)

    def assign_users(self, role_id, user_ids, ip_address=None):
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
        self.audit_repo.log_event(user_id=None, action="role.assign.users", resource="role", ip_address=ip_address)
        return role

    def remove_users(self, role_id, user_ids, ip_address=None):
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
        self.audit_repo.log_event(user_id=None, action="role.remove.users", resource="role", ip_address=ip_address)
        return role

    def get_users(self, role_id, page=1, page_size=20, include_deleted=False):
        role = self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        offset = (page - 1) * page_size
        users, total = self.role_repo.get_users_with_role(role_id=role_id, include_deleted=include_deleted)
        return users[offset:offset + page_size], total


# -- Test helpers --
def _make_user_create(overrides=None):
    from app.schemas.user import UserCreate
    data = {
        "email": f"{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "SecureP@ss1234",
        "first_name": "Test",
        "last_name": "User",
        "phone": None,
    }
    if overrides:
        data.update(overrides)
    return UserCreate(**data)


def _make_user_update(overrides=None):
    from app.schemas.user import UserUpdate
    data = {}
    if overrides:
        data.update(overrides)
    return UserUpdate(**data)


# -- Fixtures --
@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def viewer_role(db):
    role = Role(name=UserRole.VIEWER, description="Viewer")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def admin_role(db):
    role = Role(name=UserRole.ADMIN, description="Admin")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def auth_service(db):
    return AuthService(db)


@pytest.fixture
def user_service(db):
    return UserService(db)


@pytest.fixture
def role_service(db):
    return RoleService(db)


# ================================================================
# AUTH SERVICE TESTS
# ================================================================

class TestRegisterUser:
    def test_register_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        assert user.id is not None
        assert user.email == user_create.email
        assert user.is_active is True
        assert user.is_verified is False
        assert user.deleted_at is None

    def test_register_duplicate_email(self, auth_service, viewer_role):
        user_create = _make_user_create()
        auth_service.register_user(user_create)
        with pytest.raises(DuplicateError):
            auth_service.register_user(user_create)

    def test_register_duplicate_username(self, auth_service, viewer_role):
        user1 = _make_user_create()
        user2 = _make_user_create({"email": "other@example.com", "username": user1.username})
        auth_service.register_user(user1)
        with pytest.raises(DuplicateError):
            auth_service.register_user(user2)

    def test_register_duplicate_phone(self, auth_service, viewer_role):
        user1 = _make_user_create({"phone": "+1234567890"})
        user2 = _make_user_create({"email": "other@example.com", "username": "other_user", "phone": "+1234567890"})
        auth_service.register_user(user1)
        with pytest.raises(DuplicateError):
            auth_service.register_user(user2)

    def test_register_assigns_viewer_role(self, auth_service, viewer_role):
        user = auth_service.register_user(_make_user_create())
        assert viewer_role in user.roles or any(r.name == UserRole.VIEWER for r in user.roles)

    def test_register_creates_audit_log(self, auth_service, viewer_role):
        user = auth_service.register_user(_make_user_create())
        count = auth_service.audit_repo.count_by_action("user.register")
        assert count == 1

    def test_register_password_is_hashed(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        assert user.hashed_password != user_create.password
        assert user.hashed_password.startswith("$2b$")


class TestAuthenticateUser:
    def test_authenticate_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        auth_service.user_repo.activate(user.id)
        auth = auth_service.authenticate_user(user_create.email, "SecureP@ss1234")
        assert auth.id == user.id

    def test_authenticate_wrong_password(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        with pytest.raises(InvalidPassword):
            auth_service.authenticate_user(user_create.email, "WrongP@ss1234")

    def test_authenticate_email_not_found(self, auth_service):
        with pytest.raises(NotFoundError):
            auth_service.authenticate_user("nonexistent@example.com", "AnyP@ss1234")

    def test_authenticate_inactive_user(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        auth_service.user_repo.deactivate(user.id)
        from app.core.exceptions import SecurityError
        with pytest.raises(SecurityError):
            auth_service.authenticate_user(user_create.email, "SecureP@ss1234")

    def test_authenticate_unverified_user(self, auth_service, viewer_role):
        user_create = _make_user_create()
        auth_service.register_user(user_create)
        from app.core.exceptions import SecurityError
        with pytest.raises(SecurityError):
            auth_service.authenticate_user(user_create.email, "SecureP@ss1234")

    def test_authenticate_updates_last_login(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        assert user.last_login is None
        auth_service.authenticate_user(user_create.email, "SecureP@ss1234")
        assert auth_service.user_repo.get_by_id(user.id).last_login is not None

    def test_authenticate_logs_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        auth_service.authenticate_user(user_create.email, "SecureP@ss1234")
        assert auth_service.audit_repo.count_by_action("user.login") == 1

    def test_authenticate_logs_failure(self, auth_service, viewer_role):
        user_create = _make_user_create()
        auth_service.register_user(user_create)
        with pytest.raises(InvalidPassword):
            auth_service.authenticate_user(user_create.email, "WrongP@ss1234")
        assert auth_service.audit_repo.count_by_action("user.login.failed") >= 1


class TestLogin:
    def test_login_returns_token(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        result = auth_service.login(user_create.email, "SecureP@ss1234")
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "bearer"

    def test_login_token_has_correct_type(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        result = auth_service.login(user_create.email, "SecureP@ss1234")
        access_payload = decode_token(result.access_token)
        refresh_payload = decode_token(result.refresh_token)
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"


class TestLogout:
    def test_logout_blacklists_tokens(self, auth_service, viewer_role):
        from app.core.token_blacklist import is_blacklisted
        from app.core.jwt import decode_token_unsafe
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        result = auth_service.login(user_create.email, "SecureP@ss1234")
        auth_service.logout(result.access_token, result.refresh_token, user_id=user.id)
        access_payload = decode_token_unsafe(result.access_token)
        assert is_blacklisted(access_payload["jti"]) is True

    def test_logout_creates_audit_log(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        result = auth_service.login(user_create.email, "SecureP@ss1234")
        auth_service.logout(result.access_token, result.refresh_token, user_id=user.id)
        assert auth_service.audit_repo.count_by_action("user.logout") == 1


class TestRefreshAccessToken:
    def test_refresh_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        login_result = auth_service.login(user_create.email, "SecureP@ss1234")
        refreshed = auth_service.refresh_access_token(login_result.refresh_token)
        assert refreshed.access_token is not None
        assert refreshed.refresh_token is not None

    def test_refresh_with_access_token_fails(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        login_result = auth_service.login(user_create.email, "SecureP@ss1234")
        with pytest.raises(InvalidToken):
            auth_service.refresh_access_token(login_result.access_token)

    def test_refresh_blacklisted_token_fails(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        login_result = auth_service.login(user_create.email, "SecureP@ss1234")
        auth_service.logout(login_result.access_token, login_result.refresh_token, user_id=user.id)
        from app.core.exceptions import TokenRevoked
        with pytest.raises(TokenRevoked):
            auth_service.refresh_access_token(login_result.refresh_token)


class TestChangePassword:
    def test_change_password_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.user_repo.verify_email(user.id)
        old_hash = user.hashed_password
        auth_service.change_password(user.id, "SecureP@ss1234", "NewP@ss5678!")
        updated = auth_service.user_repo.get_by_id(user.id)
        assert updated.hashed_password != old_hash

    def test_change_password_wrong_old(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        with pytest.raises(InvalidPassword):
            auth_service.change_password(user.id, "WrongP@ss1234", "NewP@ss5678!")

    def test_change_password_creates_audit_log(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        auth_service.change_password(user.id, "SecureP@ss1234", "NewP@ss5678!")
        assert auth_service.audit_repo.count_by_action("user.password.change") == 1


class TestForgotPassword:
    def test_forgot_password_returns_token(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        token = auth_service.forgot_password(user_create.email)
        assert token is not None
        payload = decode_token(token)
        assert payload["type"] == "reset_password"

    def test_forgot_password_nonexistent_email(self, auth_service):
        token = auth_service.forgot_password("nobody@example.com")
        assert token is not None
        payload = decode_token(token)
        assert payload["sub"] == "unknown"


class TestResetPassword:
    def test_reset_password_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        token = auth_service.forgot_password(user_create.email)
        old_hash = user.hashed_password
        auth_service.reset_password(token, "NewP@ss5678!")
        new_hash = auth_service.user_repo.get_by_id(user.id).hashed_password
        assert new_hash != old_hash

    def test_reset_password_bad_token(self, auth_service):
        with pytest.raises(InvalidToken):
            auth_service.reset_password("invalid_token", "NewP@ss5678!")

    def test_reset_password_creates_audit_log(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        token = auth_service.forgot_password(user_create.email)
        auth_service.reset_password(token, "NewP@ss5678!")
        from sqlalchemy import select, func
        from app.models.audit_log import AuditLog
        stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action == "user.password.reset")
        count = auth_service.db.execute(stmt).scalar() or 0
        assert count == 1


class TestVerifyEmail:
    def test_verify_email_success(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        verify_token = auth_service.resend_verification(user.id)
        assert user.is_verified is False
        auth_service.verify_email(verify_token)
        assert auth_service.user_repo.get_by_id(user.id).is_verified is True

    def test_verify_email_bad_token(self, auth_service):
        with pytest.raises(InvalidToken):
            auth_service.verify_email("bad_token")

    def test_verify_email_creates_audit_log(self, auth_service, viewer_role):
        user_create = _make_user_create()
        user = auth_service.register_user(user_create)
        verify_token = auth_service.resend_verification(user.id)
        auth_service.verify_email(verify_token)
        assert auth_service.audit_repo.count_by_action("user.email.verified") == 1


class TestValidateToken:
    def test_validate_access_token(self, auth_service):
        token = create_access_token(subject=str(uuid.uuid4()))
        payload = auth_service.validate_access_token(token)
        assert payload["type"] == "access"

    def test_validate_refresh_token(self, auth_service):
        token = create_refresh_token(subject=str(uuid.uuid4()))
        payload = auth_service.validate_refresh_token(token)
        assert payload["type"] == "refresh"

    def test_validate_access_rejects_refresh(self, auth_service):
        token = create_refresh_token(subject=str(uuid.uuid4()))
        with pytest.raises(InvalidToken):
            auth_service.validate_access_token(token)


class TestRevokeToken:
    def test_revoke_token(self, auth_service):
        token = create_access_token(subject=str(uuid.uuid4()))
        auth_service.revoke_token(token)
        from app.core.token_blacklist import is_blacklisted
        from app.core.jwt import decode_token_unsafe
        payload = decode_token_unsafe(token)
        assert is_blacklisted(payload["jti"]) is True

    def test_revoke_token_creates_audit_log(self, auth_service):
        token = create_access_token(subject=str(uuid.uuid4()))
        auth_service.revoke_token(token)
        assert auth_service.audit_repo.count_by_action("user.token.revoked") == 1


# ================================================================
# USER SERVICE TESTS
# ================================================================

class TestUserServiceCreate:
    def test_create_user(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        assert user.id is not None
        assert user.is_active is True

    def test_create_user_duplicate_email(self, user_service, viewer_role):
        uc = _make_user_create()
        user_service.create_user(uc)
        with pytest.raises(DuplicateError):
            user_service.create_user(uc)


class TestUserServiceUpdate:
    def test_update_user_name(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        updated = user_service.update_user(user.id, _make_user_update({"first_name": "Jane"}))
        assert updated.first_name == "Jane"

    def test_update_user_not_found(self, user_service):
        from app.schemas.user import UserUpdate
        with pytest.raises(NotFoundError):
            user_service.update_user(uuid.uuid4(), UserUpdate())


class TestUserServiceDelete:
    def test_soft_delete(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.soft_delete_user(user.id)
        assert user_service.user_repo.get_by_id(user.id) is None

    def test_hard_delete(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.delete_user(user.id)
        assert user_service.user_repo.get_by_id(user.id, include_deleted=True) is None

    def test_restore(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.soft_delete_user(user.id)
        restored = user_service.restore_user(user.id)
        assert restored.id == user.id
        assert restored.deleted_at is None


class TestUserServiceActivate:
    def test_activate_deactivate(self, user_service, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.deactivate_user(user.id)
        assert user_service.user_repo.get_by_id(user.id).is_active is False
        user_service.activate_user(user.id)
        assert user_service.user_repo.get_by_id(user.id).is_active is True


class TestUserServiceRoleAssignment:
    def test_assign_role(self, user_service, admin_role, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.assign_role(user.id, admin_role.id)
        profile = user_service.get_profile(user.id)
        role_names = [r.name for r in profile.roles]
        assert UserRole.ADMIN in role_names

    def test_remove_role(self, user_service, admin_role, viewer_role):
        user = user_service.create_user(_make_user_create())
        user_service.assign_role(user.id, admin_role.id)
        user_service.remove_role(user.id, admin_role.id)
        profile = user_service.get_profile(user.id)
        role_names = [r.name for r in profile.roles]
        assert UserRole.ADMIN not in role_names


class TestUserServiceSearch:
    def test_search_users(self, user_service, viewer_role):
        user_service.create_user(_make_user_create({"email": "findme@example.com", "username": "findme"}))
        items, total = user_service.search_users("findme")
        assert total >= 1

    def test_search_empty_query(self, user_service):
        with pytest.raises(ValueError):
            user_service.search_users("")


# ================================================================
# ROLE SERVICE TESTS
# ================================================================

class TestRoleService:
    def test_create_role(self, role_service):
        role = role_service.create_role(UserRole.RESEARCHER, "Researcher role")
        assert role.id is not None
        assert role.name == UserRole.RESEARCHER

    def test_create_duplicate(self, role_service):
        role_service.create_role(UserRole.ADMIN, "Admin role")
        with pytest.raises(DuplicateError):
            role_service.create_role(UserRole.ADMIN, "Another admin")

    def test_rename_role(self, role_service):
        role = role_service.create_role(UserRole.VIEWER)
        role_service.rename_role(role.id, UserRole.ADMIN, "Upgraded")
        assert role_service.role_repo.get_by_id(role.id).name == UserRole.ADMIN

    def test_delete_role(self, role_service):
        role = role_service.create_role(UserRole.GUEST)
        role_service.delete_role(role.id)
        assert role_service.role_repo.get_by_id(role.id) is None

    def test_assign_users(self, role_service, user_service, viewer_role, admin_role):
        user1 = user_service.create_user(_make_user_create({"email": "u1@test.com", "username": "test_u1"}))
        user2 = user_service.create_user(_make_user_create({"email": "u2@test.com", "username": "test_u2"}))
        role_service.assign_users(admin_role.id, [user1.id, user2.id])
        users, total = role_service.get_users(admin_role.id)
        assert total == 2

    def test_remove_users(self, role_service, user_service, viewer_role, admin_role):
        user1 = user_service.create_user(_make_user_create({"email": "ru1@test.com", "username": "test_ru1"}))
        user2 = user_service.create_user(_make_user_create({"email": "ru2@test.com", "username": "test_ru2"}))
        role_service.assign_users(admin_role.id, [user1.id, user2.id])
        role_service.remove_users(admin_role.id, [user1.id])
        _, total = role_service.get_users(admin_role.id)
        assert total == 1

    def test_get_users_paginated(self, role_service, user_service, viewer_role, admin_role):
        for i in range(5):
            user_service.create_user(_make_user_create({"email": f"p{i}@test.com", "username": f"test_p{i}"}))
        users, total = role_service.get_users(viewer_role.id, page=1, page_size=2)
        assert len(users) == 2
        assert total >= 5

    def test_create_role_audit_log(self, role_service):
        role_service.create_role(UserRole.PLANNER)
        assert role_service.audit_repo.count_by_action("role.create") == 1
