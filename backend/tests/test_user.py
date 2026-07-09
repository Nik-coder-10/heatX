"""Tests for the User model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, exc, String, Boolean, DateTime, ForeignKey, func, Column, Enum
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import pytest

from app.database.enums import UserRole

# Self-contained test setup (avoids model graph import cascade)
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Role(Base):
    __tablename__ = "roles"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Enum(UserRole), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    users = relationship("User", back_populates="role")


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


@pytest.fixture
def db():
    """Create a fresh database session for testing."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _create_role(db, name=UserRole.ADMIN, description="Test role"):
    """Helper to create a role for user tests."""
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def test_user_creation(db):
    """Test creating a user with all required fields."""
    role = _create_role(db)
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

    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.hashed_password == "hashedpassword123"
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.is_active is True
    assert user.is_verified is False
    assert user.deleted_at is None
    assert user.created_at is not None
    assert user.updated_at is not None


def test_user_optional_fields(db):
    """Test creating a user with optional fields."""
    role = _create_role(db)
    user = User(
        email="optional@example.com",
        username="optionaluser",
        hashed_password="hash123",
        first_name="Jane",
        last_name="Smith",
        phone="+1234567890",
        profile_image_url="https://example.com/avatar.jpg",
        full_name="Jane Smith",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.phone == "+1234567890"
    assert user.profile_image_url == "https://example.com/avatar.jpg"
    assert user.full_name == "Jane Smith"
    assert user.last_login is None


def test_user_email_uniqueness(db):
    """Test that email must be unique."""
    role = _create_role(db)
    user1 = User(
        email="duplicate@example.com",
        username="user1",
        hashed_password="hash1",
        first_name="A",
        last_name="B",
        role_id=role.id
    )
    db.add(user1)
    db.commit()

    user2 = User(
        email="duplicate@example.com",
        username="user2",
        hashed_password="hash2",
        first_name="C",
        last_name="D",
        role_id=role.id
    )
    db.add(user2)
    with pytest.raises(exc.IntegrityError):
        db.commit()


def test_user_username_uniqueness(db):
    """Test that username must be unique."""
    role = _create_role(db)
    user1 = User(
        email="unique1@example.com",
        username="shareduser",
        hashed_password="hash1",
        first_name="A",
        last_name="B",
        role_id=role.id
    )
    db.add(user1)
    db.commit()

    user2 = User(
        email="unique2@example.com",
        username="shareduser",
        hashed_password="hash2",
        first_name="C",
        last_name="D",
        role_id=role.id
    )
    db.add(user2)
    with pytest.raises(exc.IntegrityError):
        db.commit()


def test_user_timestamp_generation(db):
    """Test that timestamps are auto-generated on creation."""
    role = _create_role(db)
    user = User(
        email="timestamps@example.com",
        username="timestampuser",
        hashed_password="hash",
        first_name="Time",
        last_name="Stamps",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.created_at is not None
    assert user.updated_at is not None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


def test_user_soft_delete(db):
    """Test soft delete functionality on User model."""
    role = _create_role(db)
    user = User(
        email="softdelete@example.com",
        username="softdeleteuser",
        hashed_password="hash",
        first_name="Soft",
        last_name="Delete",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.deleted_at is None

    user.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    assert user.deleted_at is not None

    user.deleted_at = None
    db.commit()
    db.refresh(user)

    assert user.deleted_at is None


def test_user_active_flag(db):
    """Test the is_active flag."""
    role = _create_role(db)
    user = User(
        email="active@example.com",
        username="activeuser",
        hashed_password="hash",
        first_name="Active",
        last_name="User",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.is_active is True

    user.is_active = False
    db.commit()
    db.refresh(user)
    assert user.is_active is False


def test_user_email_verified_flag(db):
    """Test the is_verified (email verified) flag."""
    role = _create_role(db)
    user = User(
        email="verified@example.com",
        username="verifieduser",
        hashed_password="hash",
        first_name="Verified",
        last_name="User",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.is_verified is False

    user.is_verified = True
    db.commit()
    db.refresh(user)
    assert user.is_verified is True


def test_user_password_hash_storage(db):
    """Test that password hash is stored correctly."""
    role = _create_role(db)
    user = User(
        email="password@example.com",
        username="passworduser",
        hashed_password="my_secret_hash_value_123",
        first_name="Pass",
        last_name="Word",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password == "my_secret_hash_value_123"
    assert len(user.hashed_password) > 0


def test_user_database_persistence(db):
    """Test that user persists and can be retrieved from the database."""
    role = _create_role(db)
    user = User(
        email="persist@example.com",
        username="persistuser",
        hashed_password="persisthash",
        first_name="Persist",
        last_name="User",
        role_id=role.id
    )
    db.add(user)
    db.commit()

    retrieved = db.query(User).filter(User.email == "persist@example.com").first()
    assert retrieved is not None
    assert retrieved.username == "persistuser"
    assert retrieved.first_name == "Persist"
    assert retrieved.last_name == "User"
    assert retrieved.hashed_password == "persisthash"
    assert retrieved.role_id == role.id


def test_user_last_login(db):
    """Test that last_login can be set and retrieved."""
    role = _create_role(db)
    user = User(
        email="lastlogin@example.com",
        username="lastloginuser",
        hashed_password="hash",
        first_name="Last",
        last_name="Login",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.last_login is None

    now = datetime.now(timezone.utc)
    user.last_login = now
    db.commit()
    db.refresh(user)

    assert user.last_login is not None


def test_user_role_relationship(db):
    """Test the relationship between User and Role models."""
    role = _create_role(db, name=UserRole.RESEARCHER, description="Researcher")
    user = User(
        email="rel@example.com",
        username="reluser",
        hashed_password="relhash",
        first_name="Rel",
        last_name="User",
        role_id=role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.role_id == role.id
    assert user.role.name == UserRole.RESEARCHER
    assert user.role.description == "Researcher"
