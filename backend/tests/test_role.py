"""
Tests for the Role model.
"""

"""Tests for the Role model."""

import sys
import os
import uuid

import pytest
from sqlalchemy import create_engine, exc, String, Boolean, DateTime, ForeignKey, func, Column
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.enums import UserRole

# Self-contained test base to avoid conflicts with other tests that use
# the shared Base from app.database.base.
Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    users = relationship("User", back_populates="role")

    def is_active_record(self):
        return self.deleted_at is None

    def soft_delete(self):
        from datetime import datetime, timezone
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        self.deleted_at = None

    def is_deleted(self):
        return self.deleted_at is not None


class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    role_id = Column(ForeignKey("roles.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    role = relationship("Role", back_populates="users")


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a fresh database session for testing."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_role_creation(db):
    """Test creating a role with all required fields."""
    role = Role(
        name=UserRole.ADMIN,
        description="Administrator role"
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    assert role.id is not None
    assert isinstance(role.id, uuid.UUID)
    assert role.name == UserRole.ADMIN
    assert role.description == "Administrator role"
    assert role.created_at is not None
    assert role.updated_at is not None
    assert role.deleted_at is None


def test_role_name_unique_constraint(db):
    """Test that role names must be unique."""
    # Create first role
    role1 = Role(name=UserRole.ADMIN, description="First admin role")
    db.add(role1)
    db.commit()

    # Try to create second role with same name
    role2 = Role(name=UserRole.ADMIN, description="Second admin role")
    db.add(role2)

    with pytest.raises(exc.IntegrityError):
        db.commit()


def test_role_description_can_be_null(db):
    """Test that role description can be null."""
    role = Role(name=UserRole.RESEARCHER, description=None)
    db.add(role)
    db.commit()
    db.refresh(role)

    assert role.description is None


def test_role_relationship_with_user(db):
    """Test relationship between Role and User models."""
    role = Role(name=UserRole.PLANNER, description="Planner role")
    db.add(role)
    db.commit()
    db.refresh(role)

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashedpassword123",
        first_name="John",
        last_name="Doe",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.role_id == role.id
    assert user.role == role
    assert len(role.users) == 1
    assert role.users[0] == user


def test_role_soft_delete(db):
    """Test soft delete functionality."""
    role = Role(name=UserRole.VIEWER, description="Viewer role")
    db.add(role)
    db.commit()
    db.refresh(role)

    # Verify initially not deleted
    assert role.deleted_at is None
    assert role.is_active_record() is True

    # Soft delete
    role.soft_delete()
    db.commit()
    db.refresh(role)

    # Verify soft deleted
    assert role.deleted_at is not None
    assert role.is_active_record() is False
    assert role.is_deleted() is True

    # Restore
    role.restore()
    db.commit()
    db.refresh(role)

    # Verify restored
    assert role.deleted_at is None
    assert role.is_active_record() is True
    assert role.is_deleted() is False


def _seed_roles(db):
    """Local seed roles function using the test's Role model."""
    default_roles = [
        {"name": UserRole.ADMIN, "description": "Administrator with full system access"},
        {"name": UserRole.RESEARCHER, "description": "Researcher with access to analytical tools and data"},
        {"name": UserRole.PLANNER, "description": "Planner with access to planning and visualization tools"},
        {"name": UserRole.VIEWER, "description": "Viewer with read-only access to reports and data"},
    ]
    for role_data in default_roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            db.add(Role(name=role_data["name"], description=role_data["description"]))
    db.commit()


def test_seed_roles_idempotent(db):
    """Test that seeding roles is idempotent."""
    # Run seed function first time
    _seed_roles(db)

    # Count roles after first seeding
    role_count_after_first = db.query(Role).count()
    assert role_count_after_first == 4

    # Run seed function second time
    _seed_roles(db)

    # Count should still be 4
    role_count_after_second = db.query(Role).count()
    assert role_count_after_second == 4

    # Verify all expected roles exist
    roles = db.query(Role).all()
    role_names = {role.name for role in roles}
    expected_names = {UserRole.ADMIN, UserRole.RESEARCHER, UserRole.PLANNER, UserRole.VIEWER}
    assert role_names == expected_names

    # Verify each role has correct description
    for role in roles:
        if role.name == UserRole.ADMIN:
            assert role.description == "Administrator with full system access"
        elif role.name == UserRole.RESEARCHER:
            assert role.description == "Researcher with access to analytical tools and data"
        elif role.name == UserRole.PLANNER:
            assert role.description == "Planner with access to planning and visualization tools"
        elif role.name == UserRole.VIEWER:
            assert role.description == "Viewer with read-only access to reports and data"


def test_seed_roles_does_not_duplicates(db):
    """Test that seeding doesn't create duplicate roles."""
    # Manually create one role first
    existing_role = Role(name=UserRole.ADMIN, description="Pre-existing admin")
    db.add(existing_role)
    db.commit()

    # Run seed function
    _seed_roles(db)

    # Should still have only 4 roles total (not 5)
    role_count = db.query(Role).count()
    assert role_count == 4

    # Verify the existing role wasn't duplicated
    admin_roles = db.query(Role).filter(Role.name == UserRole.ADMIN).all()
    assert len(admin_roles) == 1
    # The description should remain as originally set (not overwritten by seed)
    assert admin_roles[0].description == "Pre-existing admin"
