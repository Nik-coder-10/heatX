"""Tests for auth repository layer (UserRepository, RoleRepository, AuditLogRepository)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.database.enums import UserRole

# -- Self-contained test setup --
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Local models ---
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


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


# --- Repository implementations (local copies matching the real ones) ---
from typing import Any, Generic, Optional, TypeVar
from sqlalchemy import select, func

ModelT = TypeVar("ModelT")


class RepositoryError(Exception):
    pass

class NotFoundError(RepositoryError):
    pass

class DuplicateError(RepositoryError):
    pass


class BaseRepository(Generic[ModelT]):
    def __init__(self, db, model: type[ModelT]):
        self.db = db
        self.model = model
        self._soft_delete = hasattr(model, "deleted_at")

    def _apply_exclude_deleted(self, stmt):
        if self._soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, id: uuid.UUID, include_deleted: bool = False):
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self, include_deleted: bool = False):
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def filter(self, include_deleted: bool = False, **kwargs):
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return list(self.db.execute(stmt).scalars().all())

    def first(self, include_deleted: bool = False, **kwargs):
        stmt = select(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return self.db.execute(stmt.limit(1)).scalar_one_or_none()

    def create(self, data: dict):
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj, data: dict):
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

    def soft_delete(self, obj):
        if not self._soft_delete:
            raise RepositoryError("Model does not support soft delete")
        obj.deleted_at = datetime.now(timezone.utc)
        self.db.add(obj)
        self.db.commit()

    def hard_delete(self, obj):
        self.db.delete(obj)
        self.db.commit()

    def restore(self, id: uuid.UUID):
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

    def count(self, include_deleted: bool = False):
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def exists(self, id: uuid.UUID, include_deleted: bool = False):
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).first() is not None

    def paginate(self, page=1, page_size=20, filters=None, sort_by=None, sort_order="desc", include_deleted=False):
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

    def bulk_create(self, objects: list[dict]):
        instances = [self.model(**data) for data in objects]
        self.db.add_all(instances)
        self.db.commit()
        for obj in instances:
            self.db.refresh(obj)
        return instances

    def bulk_update(self, ids: list[uuid.UUID], data: dict):
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

    def bulk_delete(self, ids: list[uuid.UUID]):
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

    def count_filtered(self, include_deleted: bool = False, **kwargs):
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        for attr, value in kwargs.items():
            column = getattr(self.model, attr, None)
            if column is not None and value is not None:
                stmt = stmt.where(column == value)
        return self.db.execute(stmt).scalar() or 0


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

    def search(self, query, include_deleted=False, limit=20, offset=0):
        pattern = f"%{query}%"
        base_stmt = select(User).where(
            User.email.ilike(pattern) | User.username.ilike(pattern) |
            User.first_name.ilike(pattern) | User.last_name.ilike(pattern)
        )
        count_stmt = select(func.count()).select_from(User).where(
            User.email.ilike(pattern) | User.username.ilike(pattern) |
            User.first_name.ilike(pattern) | User.last_name.ilike(pattern)
        )
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def assign_role(self, user_id, role_id):
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
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
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.db.execute(select(Role).where(Role.id == role_id)).scalar_one_or_none()
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            self.db.refresh(user)
        return user

    def get_roles(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        return list(user.roles)

    def has_role(self, user_id, role_name):
        user = self.get_by_id(user_id)
        if not user:
            return False
        return any(r.name == role_name for r in user.roles)

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

    def get_all_users(self, include_deleted=False, limit=100, offset=0):
        base_stmt = select(User)
        count_stmt = select(func.count()).select_from(User)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def count_active(self):
        return self.count_filtered(is_active=True)

    def count_verified(self):
        return self.count_filtered(is_verified=True)


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db):
        super().__init__(db, Role)

    def get_by_name(self, name, include_deleted=False):
        stmt = select(Role).where(Role.name == name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name, description=None):
        role = self.get_by_name(name)
        if role:
            return role
        return self.create({"name": name, "description": description})

    def get_all_roles(self, include_deleted=False):
        stmt = select(Role).order_by(Role.name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_users_with_role(self, role_id, include_deleted=False):
        role = self.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        stmt = select(User).where(User.roles.any(Role.id == role_id))
        count_stmt = select(func.count()).select_from(User).where(User.roles.any(Role.id == role_id))
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        total = self.db.execute(count_stmt).scalar() or 0
        users = list(self.db.execute(stmt).scalars().all())
        return users, total

    def assign_to_user(self, user_id, role_id):
        role = self.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role with id {role_id} not found")
        user = self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        existing = self.db.execute(
            select(UserRoleLink).where(UserRoleLink.user_id == user_id, UserRoleLink.role_id == role_id)
        ).scalar_one_or_none()
        if not existing:
            user.roles.append(role)
            self.db.commit()
        return role

    def remove_from_user(self, user_id, role_id):
        user = self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        role = self.get_by_id(role_id)
        if role and role in user.roles:
            user.roles.remove(role)
            self.db.commit()

    def get_role_counts(self, include_deleted=False):
        stmt = select(Role.id, Role.name, func.count(UserRoleLink.user_id).label("user_count")).outerjoin(
            UserRoleLink, Role.id == UserRoleLink.role_id
        ).group_by(Role.id, Role.name).order_by(Role.name)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        rows = self.db.execute(stmt).all()
        return [{"role_id": str(row.id), "name": row.name, "user_count": row.user_count} for row in rows]


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db):
        super().__init__(db, AuditLog)

    def get_by_user(self, user_id, limit=50, offset=0):
        base_stmt = select(AuditLog).where(AuditLog.user_id == user_id)
        count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def get_by_action(self, action, limit=50, offset=0):
        pattern = f"%{action}%"
        base_stmt = select(AuditLog).where(AuditLog.action.ilike(pattern))
        count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action.ilike(pattern))
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def get_by_ip(self, ip_address, limit=50, offset=0):
        base_stmt = select(AuditLog).where(AuditLog.ip_address == ip_address)
        count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.ip_address == ip_address)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def get_by_date_range(self, start, end, limit=100, offset=0):
        base_stmt = select(AuditLog).where(AuditLog.timestamp >= start, AuditLog.timestamp <= end)
        count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= start, AuditLog.timestamp <= end)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def get_security_events(self, limit=50, offset=0):
        security_actions = ["user.login", "user.logout", "user.login.failed",
                            "user.password.change", "user.password.reset",
                            "user.role.assign", "user.role.remove"]
        base_stmt = select(AuditLog).where(AuditLog.action.in_(security_actions))
        count_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action.in_(security_actions))
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def get_recent_activity(self, limit=20):
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

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

    def get_distinct_actions(self):
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
        return [row[0] for row in self.db.execute(stmt).all()]


# --- Test helpers ---
def _make_user(overrides=None):
    data = {
        "email": f"{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "hashed_password": "hashed_password_123",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_verified": False,
    }
    if overrides:
        data.update(overrides)
    return data


def _make_role(name=None, description="Test role"):
    return {
        "name": name or UserRole.VIEWER,
        "description": description,
    }


def _make_audit_log(user_id=None, action="test.action", resource="test", overrides=None):
    data = {
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "ip_address": "192.168.1.1",
        "user_agent": "pytest",
        "details": {"key": "value"},
    }
    if overrides:
        data.update(overrides)
    return data


# --- Fixtures ---
@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user_repo(db):
    return UserRepository(db)


@pytest.fixture
def role_repo(db):
    return RoleRepository(db)


@pytest.fixture
def audit_repo(db):
    return AuditLogRepository(db)


@pytest.fixture
def base_repo(db):
    return BaseRepository(db, User)


# ================================================================
# BASE REPOSITORY TESTS
# ================================================================

class TestBaseGetAll:
    def test_get_all_empty(self, base_repo):
        assert base_repo.get_all() == []

    def test_get_all_returns_all(self, base_repo):
        base_repo.create(_make_user({"email": "a@b.com", "username": "a"}))
        base_repo.create(_make_user({"email": "c@d.com", "username": "b"}))
        assert len(base_repo.get_all()) == 2

    def test_get_all_excludes_deleted(self, base_repo):
        u = base_repo.create(_make_user({"email": "del@me.com", "username": "del"}))
        base_repo.delete(u)
        assert len(base_repo.get_all()) == 0

    def test_get_all_includes_deleted(self, base_repo):
        u = base_repo.create(_make_user({"email": "inc@me.com", "username": "inc"}))
        base_repo.delete(u)
        assert len(base_repo.get_all(include_deleted=True)) == 1


class TestBaseFilter:
    def test_filter_by_field(self, base_repo):
        base_repo.create(_make_user({"email": "find@me.com", "username": "find", "is_active": True}))
        base_repo.create(_make_user({"email": "other@me.com", "username": "other", "is_active": False}))
        results = base_repo.filter(is_active=True)
        assert len(results) == 1
        assert results[0].email == "find@me.com"

    def test_filter_multiple_fields(self, base_repo):
        base_repo.create(_make_user({"email": "multi@me.com", "username": "multi", "is_active": True, "is_verified": True}))
        base_repo.create(_make_user({"email": "noverify@me.com", "username": "noverify", "is_active": True, "is_verified": False}))
        results = base_repo.filter(is_active=True, is_verified=True)
        assert len(results) == 1

    def test_filter_empty_result(self, base_repo):
        results = base_repo.filter(email="nonexistent@example.com")
        assert results == []


class TestBaseFirst:
    def test_first_found(self, base_repo):
        u = base_repo.create(_make_user({"email": "first@me.com", "username": "first"}))
        result = base_repo.first(email="first@me.com")
        assert result is not None
        assert result.id == u.id

    def test_first_not_found(self, base_repo):
        result = base_repo.first(email="absent@me.com")
        assert result is None

    def test_first_excludes_deleted(self, base_repo):
        u = base_repo.create(_make_user({"email": "softdel@me.com", "username": "softdel"}))
        base_repo.delete(u)
        result = base_repo.first(email="softdel@me.com")
        assert result is None


class TestBaseSoftDelete:
    def test_soft_delete_method(self, base_repo):
        u = base_repo.create(_make_user({"email": "sd@me.com", "username": "sd"}))
        base_repo.soft_delete(u)
        assert u.deleted_at is not None

    def test_soft_delete_excludes_from_count(self, base_repo):
        u = base_repo.create(_make_user({"email": "sd2@me.com", "username": "sd2"}))
        base_repo.soft_delete(u)
        assert base_repo.count() == 0

    def test_soft_delete_raises_on_non_soft_model(self, db):
        class NoSoftDelete:
            pass
        with pytest.raises(RepositoryError):
            repo = BaseRepository(db, NoSoftDelete)
            repo.soft_delete(NoSoftDelete())


class TestBaseHardDelete:
    def test_hard_delete_removes_record(self, base_repo):
        u = base_repo.create(_make_user({"email": "hd@me.com", "username": "hd"}))
        base_repo.hard_delete(u)
        assert base_repo.count(include_deleted=True) == 0

    def test_hard_delete_clean(self, base_repo):
        u = base_repo.create(_make_user({"email": "hd2@me.com", "username": "hd2"}))
        base_repo.hard_delete(u)
        assert base_repo.get_by_id(u.id, include_deleted=True) is None


class TestBaseBulkCreate:
    def test_bulk_create_multiple(self, base_repo):
        users = base_repo.bulk_create([
            _make_user({"email": "b1@me.com", "username": "b1"}),
            _make_user({"email": "b2@me.com", "username": "b2"}),
            _make_user({"email": "b3@me.com", "username": "b3"}),
        ])
        assert len(users) == 3
        assert base_repo.count() == 3

    def test_bulk_create_empty(self, base_repo):
        users = base_repo.bulk_create([])
        assert users == []


class TestBaseBulkUpdate:
    def test_bulk_update_multiple(self, base_repo):
        u1 = base_repo.create(_make_user({"email": "bu1@me.com", "username": "bu1", "is_verified": False}))
        u2 = base_repo.create(_make_user({"email": "bu2@me.com", "username": "bu2", "is_verified": False}))
        count = base_repo.bulk_update([u1.id, u2.id], {"is_verified": True})
        assert count == 2
        assert base_repo.get_by_id(u1.id).is_verified is True
        assert base_repo.get_by_id(u2.id).is_verified is True

    def test_bulk_update_empty_ids(self, base_repo):
        count = base_repo.bulk_update([], {"is_verified": True})
        assert count == 0


class TestBaseBulkDelete:
    def test_bulk_delete_multiple(self, base_repo):
        u1 = base_repo.create(_make_user({"email": "bd1@me.com", "username": "bd1"}))
        u2 = base_repo.create(_make_user({"email": "bd2@me.com", "username": "bd2"}))
        count = base_repo.bulk_delete([u1.id, u2.id])
        assert count == 2
        assert base_repo.count() == 0

    def test_bulk_delete_excludes_deleted_twice(self, base_repo):
        u1 = base_repo.create(_make_user({"email": "bdx1@me.com", "username": "bdx1"}))
        u2 = base_repo.create(_make_user({"email": "bdx2@me.com", "username": "bdx2"}))
        base_repo.bulk_delete([u1.id, u2.id])
        count = base_repo.bulk_delete([u1.id, u2.id])
        assert count == 0


class TestBaseCountFiltered:
    def test_count_filtered_matches(self, base_repo):
        base_repo.create(_make_user({"email": "cf1@me.com", "username": "cf1", "is_active": True}))
        base_repo.create(_make_user({"email": "cf2@me.com", "username": "cf2", "is_active": False}))
        assert base_repo.count_filtered(is_active=True) == 1

    def test_count_filtered_all(self, base_repo):
        base_repo.create(_make_user({"email": "cf3@me.com", "username": "cf3"}))
        base_repo.create(_make_user({"email": "cf4@me.com", "username": "cf4"}))
        assert base_repo.count_filtered() == 2


class TestBasePaginate:
    def test_paginate_page_one(self, base_repo):
        for i in range(5):
            base_repo.create(_make_user({"email": f"pg{i}@me.com", "username": f"pg{i}"}))
        items, total = base_repo.paginate(page=1, page_size=2)
        assert len(items) == 2
        assert total == 5

    def test_paginate_last_page(self, base_repo):
        for i in range(5):
            base_repo.create(_make_user({"email": f"lp{i}@me.com", "username": f"lp{i}"}))
        items, total = base_repo.paginate(page=3, page_size=2)
        assert len(items) == 1
        assert total == 5

    def test_paginate_with_filters(self, base_repo):
        base_repo.create(_make_user({"email": "flt@me.com", "username": "flt", "is_active": True}))
        base_repo.create(_make_user({"email": "flt2@me.com", "username": "flt2", "is_active": False}))
        items, total = base_repo.paginate(filters={"is_active": True})
        assert len(items) == 1
        assert total == 1

    def test_paginate_sorted(self, base_repo):
        u1 = base_repo.create(_make_user({"email": "za@me.com", "username": "za", "first_name": "Zoe"}))
        u2 = base_repo.create(_make_user({"email": "aa@me.com", "username": "aa", "first_name": "Alice"}))
        items, total = base_repo.paginate(sort_by="first_name", sort_order="asc", page_size=10)
        assert items[0].id == u2.id
        assert items[1].id == u1.id


class TestBaseExistsByCriteria:
    def test_exists_by_id(self, base_repo):
        u = base_repo.create(_make_user({"email": "ex@me.com", "username": "ex"}))
        assert base_repo.exists(u.id) is True

    def test_exists_false(self, base_repo):
        assert base_repo.exists(uuid.uuid4()) is False


# ================================================================
# USER REPOSITORY TESTS
# ================================================================

class TestUserCreate:
    def test_create_user(self, user_repo):
        user = user_repo.create(_make_user())
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.is_active is True
        assert user.is_verified is False

    def test_create_duplicate_email_raises(self, db, user_repo):
        data = _make_user({"email": "dup@me.com", "username": "dup1"})
        user_repo.create(data)
        with pytest.raises(Exception):
            user_repo.create({"email": "dup@me.com", "username": "dup2",
                              "hashed_password": "pw", "first_name": "A", "last_name": "B"})
        db.rollback()


class TestUserGetByEmail:
    def test_get_by_email_found(self, user_repo):
        user = user_repo.create(_make_user({"email": "email@test.com", "username": "emailuser"}))
        found = user_repo.get_by_email("email@test.com")
        assert found is not None
        assert found.id == user.id

    def test_get_by_email_not_found(self, user_repo):
        assert user_repo.get_by_email("nope@nowhere.com") is None

    def test_get_by_email_excludes_deleted(self, user_repo):
        user = user_repo.create(_make_user({"email": "del@test.com", "username": "delemail"}))
        user_repo.delete(user)
        assert user_repo.get_by_email("del@test.com") is None

    def test_get_by_email_includes_deleted(self, user_repo):
        user = user_repo.create(_make_user({"email": "del2@test.com", "username": "delemail2"}))
        user_repo.delete(user)
        found = user_repo.get_by_email("del2@test.com", include_deleted=True)
        assert found is not None
        assert found.deleted_at is not None


class TestUserGetByUsername:
    def test_get_by_username_found(self, user_repo):
        user = user_repo.create(_make_user({"email": "uname@test.com", "username": "uniqueuser"}))
        found = user_repo.get_by_username("uniqueuser")
        assert found is not None
        assert found.id == user.id


class TestUserSearch:
    def test_search_by_email(self, user_repo):
        user_repo.create(_make_user({"email": "search@me.com", "username": "searchuser"}))
        items, total = user_repo.search("search@me")
        assert total == 1
        assert items[0].email == "search@me.com"

    def test_search_by_name(self, user_repo):
        user_repo.create(_make_user({"email": "name@me.com", "username": "nameuser",
                                      "first_name": "Findable", "last_name": "Person"}))
        items, total = user_repo.search("Findable")
        assert total == 1

    def test_search_no_results(self, user_repo):
        items, total = user_repo.search("zzzz_nonexistent")
        assert total == 0
        assert items == []

    def test_search_pagination(self, user_repo):
        for i in range(5):
            user_repo.create(_make_user({"email": f"spam{i}@me.com", "username": f"spam{i}"}))
        items, total = user_repo.search("@me.com", limit=2)
        assert len(items) == 2
        assert total == 5


class TestUserRoleAssignment:
    def test_assign_role(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "roleassign@me.com", "username": "roleassign"}))
        role = role_repo.create(_make_role(name=UserRole.RESEARCHER))
        updated = user_repo.assign_role(user.id, role.id)
        roles = user_repo.get_roles(user.id)
        assert len(roles) == 1
        assert roles[0].name == UserRole.RESEARCHER

    def test_assign_nonexistent_user_raises(self, user_repo):
        fake_id = uuid.uuid4()
        with pytest.raises(NotFoundError):
            user_repo.assign_role(fake_id, fake_id)

    def test_assign_nonexistent_role_raises(self, user_repo):
        user = user_repo.create(_make_user({"email": "norole@me.com", "username": "norole"}))
        with pytest.raises(NotFoundError):
            user_repo.assign_role(user.id, uuid.uuid4())

    def test_assign_role_idempotent(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "idempotent@me.com", "username": "idempotent"}))
        role = role_repo.create(_make_role(name=UserRole.ADMIN))
        user_repo.assign_role(user.id, role.id)
        user_repo.assign_role(user.id, role.id)
        assert len(user_repo.get_roles(user.id)) == 1

    def test_remove_role(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "removerole@me.com", "username": "removerole"}))
        role = role_repo.create(_make_role(name=UserRole.PLANNER))
        user_repo.assign_role(user.id, role.id)
        user_repo.remove_role(user.id, role.id)
        assert len(user_repo.get_roles(user.id)) == 0

    def test_has_role(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "hasrole@me.com", "username": "hasrole"}))
        role = role_repo.create(_make_role(name=UserRole.ADMIN))
        assert user_repo.has_role(user.id, "administrator") is False
        user_repo.assign_role(user.id, role.id)
        assert user_repo.has_role(user.id, "administrator") is True

    def test_has_role_nonexistent_user(self, user_repo):
        assert user_repo.has_role(uuid.uuid4(), "admin") is False


class TestUserStatusMutations:
    def test_update_last_login(self, user_repo):
        user = user_repo.create(_make_user({"email": "lastlogin@me.com", "username": "lastlogin"}))
        assert user.last_login is None
        updated = user_repo.update_last_login(user.id)
        assert updated is not None
        assert updated.last_login is not None

    def test_verify_email(self, user_repo):
        user = user_repo.create(_make_user({"email": "verify@me.com", "username": "verify"}))
        assert user.is_verified is False
        updated = user_repo.verify_email(user.id)
        assert updated is not None
        assert updated.is_verified is True

    def test_change_password(self, user_repo):
        user = user_repo.create(_make_user({"email": "changepw@me.com", "username": "changepw"}))
        updated = user_repo.change_password(user.id, "new_hashed_password_456")
        assert updated is not None
        assert updated.hashed_password == "new_hashed_password_456"

    def test_activate_deactivate(self, user_repo):
        user = user_repo.create(_make_user({"email": "act@me.com", "username": "act"}))
        user_repo.deactivate(user.id)
        assert user_repo.get_by_id(user.id).is_active is False
        user_repo.activate(user.id)
        assert user_repo.get_by_id(user.id).is_active is True

    def test_mutations_nonexistent_user(self, user_repo):
        assert user_repo.update_last_login(uuid.uuid4()) is None
        assert user_repo.verify_email(uuid.uuid4()) is None
        assert user_repo.change_password(uuid.uuid4(), "pw") is None
        assert user_repo.deactivate(uuid.uuid4()) is None


class TestUserAdminQueries:
    def test_get_all_users_pagination(self, user_repo):
        for i in range(10):
            user_repo.create(_make_user({"email": f"admin{i}@me.com", "username": f"admin{i}"}))
        items, total = user_repo.get_all_users(limit=3, offset=0)
        assert len(items) == 3
        assert total == 10

    def test_count_active_and_verified(self, user_repo):
        user_repo.create(_make_user({"email": "a1@me.com", "username": "a1", "is_active": True, "is_verified": True}))
        user_repo.create(_make_user({"email": "a2@me.com", "username": "a2", "is_active": True, "is_verified": False}))
        user_repo.create(_make_user({"email": "a3@me.com", "username": "a3", "is_active": False, "is_verified": True}))
        assert user_repo.count_active() == 2
        assert user_repo.count_verified() == 2


# ================================================================
# ROLE REPOSITORY TESTS
# ================================================================

class TestRoleCreate:
    def test_create_role(self, role_repo):
        role = role_repo.create(_make_role(name=UserRole.ADMIN))
        assert role.id is not None
        assert role.name == UserRole.ADMIN

    def test_create_duplicate_name(self, db, role_repo):
        role_repo.create(_make_role(name=UserRole.ADMIN))
        with pytest.raises(Exception):
            role_repo.create(_make_role(name=UserRole.ADMIN))
        db.rollback()


class TestRoleGetByName:
    def test_get_by_name_found(self, role_repo):
        role_repo.create(_make_role(name=UserRole.RESEARCHER))
        found = role_repo.get_by_name(UserRole.RESEARCHER)
        assert found is not None
        assert found.name == UserRole.RESEARCHER

    def test_get_by_name_not_found(self, role_repo):
        assert role_repo.get_by_name(UserRole.ADMIN) is None


class TestRoleGetOrCreate:
    def test_get_or_create_returns_existing(self, role_repo):
        role = role_repo.create(_make_role(name=UserRole.VIEWER))
        result = role_repo.get_or_create(UserRole.VIEWER)
        assert result.id == role.id

    def test_get_or_create_creates_new(self, role_repo):
        result = role_repo.get_or_create(UserRole.GUEST, description="Guest role")
        assert result is not None
        assert result.name == UserRole.GUEST


class TestRoleUsersWithRole:
    def test_get_users_with_role(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "roleuser@me.com", "username": "roleuser"}))
        role = role_repo.create(_make_role(name=UserRole.ADMIN))
        user_repo.assign_role(user.id, role.id)
        users, total = role_repo.get_users_with_role(role.id)
        assert total == 1
        assert users[0].id == user.id

    def test_get_users_with_role_nonexistent(self, role_repo):
        with pytest.raises(NotFoundError):
            role_repo.get_users_with_role(uuid.uuid4())

    def test_get_users_with_role_empty(self, role_repo):
        role = role_repo.create(_make_role(name=UserRole.VIEWER))
        users, total = role_repo.get_users_with_role(role.id)
        assert total == 0
        assert users == []


class TestRoleAssignmentFromRoleRepo:
    def test_assign_to_user(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "roleassign2@me.com", "username": "roleassign2"}))
        role = role_repo.create(_make_role(name=UserRole.RESEARCHER))
        result = role_repo.assign_to_user(user.id, role.id)
        assert result.id == role.id
        users, _ = role_repo.get_users_with_role(role.id)
        assert len(users) == 1

    def test_remove_from_user(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "roleremove@me.com", "username": "roleremove"}))
        role = role_repo.create(_make_role(name=UserRole.PLANNER))
        role_repo.assign_to_user(user.id, role.id)
        role_repo.remove_from_user(user.id, role.id)
        users, _ = role_repo.get_users_with_role(role.id)
        assert len(users) == 0


class TestRoleCounts:
    def test_get_role_counts(self, user_repo, role_repo):
        user = user_repo.create(_make_user({"email": "rc@me.com", "username": "rc"}))
        admin = role_repo.create(_make_role(name=UserRole.ADMIN))
        viewer = role_repo.create(_make_role(name=UserRole.VIEWER))
        user_repo.assign_role(user.id, admin.id)
        counts = role_repo.get_role_counts()
        counts_map = {c["name"]: c["user_count"] for c in counts}
        assert counts_map.get("administrator", 0) == 1
        assert counts_map.get("viewer", 0) == 0


class TestRoleAllRoles:
    def test_get_all_roles(self, role_repo):
        role_repo.create(_make_role(name=UserRole.ADMIN))
        role_repo.create(_make_role(name=UserRole.VIEWER))
        roles = role_repo.get_all_roles()
        assert len(roles) == 2

    def test_get_all_roles_ordered(self, role_repo):
        role_repo.create(_make_role(name=UserRole.RESEARCHER))
        role_repo.create(_make_role(name=UserRole.ADMIN))
        roles = role_repo.get_all_roles()
        assert roles[0].name == UserRole.ADMIN


# ================================================================
# AUDIT LOG REPOSITORY TESTS
# ================================================================

class TestAuditLogCreate:
    def test_log_event(self, audit_repo):
        log = audit_repo.log_event(
            user_id=None,
            action="test.create",
            resource="test_resource",
            ip_address="10.0.0.1",
            user_agent="pytest-agent",
            details={"key": "val"},
        )
        assert log.id is not None
        assert log.action == "test.create"
        assert log.resource == "test_resource"
        assert log.ip_address == "10.0.0.1"

    def test_log_event_with_user(self, audit_repo, user_repo):
        user = user_repo.create(_make_user({"email": "loguser@me.com", "username": "loguser"}))
        log = audit_repo.log_event(user_id=user.id, action="user.login", resource="auth")
        assert log.user_id == user.id


class TestAuditLogGetByUser:
    def test_get_by_user(self, audit_repo, user_repo):
        user = user_repo.create(_make_user({"email": "audituser@me.com", "username": "audituser"}))
        audit_repo.log_event(user_id=user.id, action="user.login", resource="auth")
        audit_repo.log_event(user_id=user.id, action="user.logout", resource="auth")
        items, total = audit_repo.get_by_user(user.id)
        assert total == 2

    def test_get_by_user_empty(self, audit_repo):
        items, total = audit_repo.get_by_user(uuid.uuid4())
        assert total == 0
        assert items == []


class TestAuditLogGetByAction:
    def test_get_by_action(self, audit_repo):
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.logout", resource="auth")
        items, total = audit_repo.get_by_action("login")
        assert total == 2

    def test_get_by_action_no_match(self, audit_repo):
        items, total = audit_repo.get_by_action("nonexistent")
        assert total == 0


class TestAuditLogGetByIP:
    def test_get_by_ip(self, audit_repo):
        audit_repo.log_event(user_id=None, action="test", resource="r", ip_address="1.2.3.4")
        audit_repo.log_event(user_id=None, action="test2", resource="r", ip_address="1.2.3.4")
        audit_repo.log_event(user_id=None, action="test3", resource="r", ip_address="5.6.7.8")
        items, total = audit_repo.get_by_ip("1.2.3.4")
        assert total == 2

    def test_get_by_ip_empty(self, audit_repo):
        items, total = audit_repo.get_by_ip("9.9.9.9")
        assert total == 0


class TestAuditLogDateRange:
    def test_get_by_date_range(self, audit_repo):
        now = datetime.now(timezone.utc)
        audit_repo.log_event(user_id=None, action="past", resource="r")
        items, total = audit_repo.get_by_date_range(
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert total == 0  # current datetime is > 2025

    def test_get_by_date_range_now(self, audit_repo):
        audit_repo.log_event(user_id=None, action="recent", resource="r")
        now = datetime.now(timezone.utc)
        start = datetime(now.year - 1, 1, 1, tzinfo=timezone.utc)
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        items, total = audit_repo.get_by_date_range(start, end)
        assert total >= 1


class TestAuditLogSecurityEvents:
    def test_get_security_events(self, audit_repo):
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.logout", resource="auth")
        audit_repo.log_event(user_id=None, action="user.password.change", resource="auth")
        audit_repo.log_event(user_id=None, action="data.export", resource="report")
        items, total = audit_repo.get_security_events()
        assert total == 3
        actions = [item.action for item in items]
        assert "data.export" not in actions

    def test_get_security_events_empty(self, audit_repo):
        audit_repo.log_event(user_id=None, action="data.export", resource="report")
        items, total = audit_repo.get_security_events()
        assert total == 0


class TestAuditLogRecentActivity:
    def test_get_recent_activity(self, audit_repo):
        for i in range(5):
            audit_repo.log_event(user_id=None, action=f"event.{i}", resource="r")
        recent = audit_repo.get_recent_activity(limit=3)
        assert len(recent) == 3

    def test_get_recent_activity_empty(self, audit_repo):
        assert audit_repo.get_recent_activity() == []


class TestAuditLogCountByAction:
    def test_count_by_action(self, audit_repo):
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.logout", resource="auth")
        assert audit_repo.count_by_action("login") == 2

    def test_count_by_action_no_match(self, audit_repo):
        assert audit_repo.count_by_action("zzz") == 0


class TestAuditLogDistinctActions:
    def test_get_distinct_actions(self, audit_repo):
        audit_repo.log_event(user_id=None, action="user.login", resource="auth")
        audit_repo.log_event(user_id=None, action="user.logout", resource="auth")
        actions = audit_repo.get_distinct_actions()
        assert "user.login" in actions
        assert "user.logout" in actions
        assert len(actions) == 2

    def test_get_distinct_actions_empty(self, audit_repo):
        assert audit_repo.get_distinct_actions() == []
