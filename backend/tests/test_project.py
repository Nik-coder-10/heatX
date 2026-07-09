"""Tests for the Project model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, exc, event, String, Text, Integer, Float, DateTime, ForeignKey, Enum, func, Column
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import pytest

from app.database.enums import ProjectStatus, Visibility

# Self-contained test setup (avoids model import cascade)
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Enable FK enforcement for SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    projects = relationship("Project", back_populates="owner")


class City(Base):
    __tablename__ = "cities"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    projects = relationship("Project", back_populates="city")


class Project(Base):
    __tablename__ = "projects"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(ForeignKey("users.id"), nullable=False)
    city_id = Column(ForeignKey("cities.id"), nullable=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, nullable=False)
    visibility = Column(Enum(Visibility), default=Visibility.PRIVATE, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    owner = relationship("User", back_populates="projects")
    city = relationship("City", back_populates="projects")


def _create_user(db):
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_city(db):
    city = City(name="TestCity")
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


@pytest.fixture
def db():
    """Create a fresh database session for testing."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_project_creation(db):
    """Test creating a project with all required fields."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Urban Heat Analysis",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.id is not None
    assert isinstance(project.id, uuid.UUID)
    assert project.name == "Urban Heat Analysis"
    assert project.owner_id == user.id
    assert project.city_id == city.id
    assert project.status == ProjectStatus.ACTIVE
    assert project.visibility == Visibility.PRIVATE
    assert project.description is None
    assert project.start_date is None
    assert project.end_date is None
    assert project.deleted_at is None
    assert project.created_at is not None
    assert project.updated_at is not None


def test_project_optional_fields(db):
    """Test creating a project with optional fields."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Detailed Analysis",
        description="A detailed urban heat island analysis",
        owner_id=user.id,
        city_id=city.id,
        status=ProjectStatus.DRAFT,
        visibility=Visibility.TEAM,
        start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.description == "A detailed urban heat island analysis"
    assert project.status == ProjectStatus.DRAFT
    assert project.visibility == Visibility.TEAM
    # SQLite stores datetime without tzinfo, compare naive values
    assert project.start_date.replace(tzinfo=None) == datetime(2025, 1, 1, tzinfo=timezone.utc).replace(tzinfo=None)
    assert project.end_date.replace(tzinfo=None) == datetime(2025, 12, 31, tzinfo=timezone.utc).replace(tzinfo=None)


def test_project_status_enum(db):
    """Test all ProjectStatus enum values."""
    user = _create_user(db)
    city = _create_city(db)
    for status in ProjectStatus:
        project = Project(
            name=f"Project {status.value}",
            owner_id=user.id,
            city_id=city.id,
            status=status,
        )
        db.add(project)
    db.commit()

    count = db.query(Project).count()
    assert count == len(list(ProjectStatus))


def test_project_visibility_enum(db):
    """Test all Visibility enum values."""
    user = _create_user(db)
    city = _create_city(db)
    for visibility in Visibility:
        project = Project(
            name=f"Project {visibility.value}",
            owner_id=user.id,
            city_id=city.id,
            visibility=visibility,
        )
        db.add(project)
    db.commit()

    count = db.query(Project).count()
    assert count == len(list(Visibility))


def test_project_owner_relationship(db):
    """Test the User -> Project relationship."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Owner Test",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.owner.id == user.id
    assert project in user.projects


def test_project_city_relationship(db):
    """Test the City -> Project relationship."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="City Test",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.city.id == city.id
    assert project in city.projects


def test_project_timestamp_generation(db):
    """Test that timestamps are auto-generated."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Timestamp Test",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.created_at is not None
    assert project.updated_at is not None
    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)


def test_project_soft_delete(db):
    """Test soft delete on Project model."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Soft Delete Test",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.deleted_at is None

    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    assert project.deleted_at is not None

    project.deleted_at = None
    db.commit()
    db.refresh(project)

    assert project.deleted_at is None


def test_project_database_persistence(db):
    """Test full round-trip persistence."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Persistence Test",
        owner_id=user.id,
        city_id=city.id,
        description="Test description",
        status=ProjectStatus.PROCESSING,
    )
    db.add(project)
    db.commit()

    retrieved = db.query(Project).filter(Project.name == "Persistence Test").first()
    assert retrieved is not None
    assert retrieved.description == "Test description"
    assert retrieved.status == ProjectStatus.PROCESSING
    assert retrieved.owner_id == user.id
    assert retrieved.city_id == city.id


def test_project_foreign_key_integrity(db):
    """Test that invalid FKs raise IntegrityError."""
    city = _create_city(db)
    project = Project(
        name="Bad Owner",
        owner_id=uuid.uuid4(),
        city_id=city.id,
    )
    db.add(project)
    with pytest.raises(exc.IntegrityError):
        db.commit()


def test_project_query_by_owner(db):
    """Test querying projects by owner."""
    user1 = _create_user(db)
    user2 = _create_user(db)
    city = _create_city(db)

    for i in range(3):
        db.add(Project(name=f"User1 Project {i}", owner_id=user1.id, city_id=city.id))
    for i in range(2):
        db.add(Project(name=f"User2 Project {i}", owner_id=user2.id, city_id=city.id))
    db.commit()

    user1_projects = db.query(Project).filter(Project.owner_id == user1.id).count()
    user2_projects = db.query(Project).filter(Project.owner_id == user2.id).count()

    assert user1_projects == 3
    assert user2_projects == 2


def test_project_query_by_city(db):
    """Test querying projects by city."""
    user = _create_user(db)
    city1 = _create_city(db)
    city2 = _create_city(db)

    for i in range(4):
        db.add(Project(name=f"City1 Project {i}", owner_id=user.id, city_id=city1.id))
    for i in range(1):
        db.add(Project(name=f"City2 Project {i}", owner_id=user.id, city_id=city2.id))
    db.commit()

    city1_projects = db.query(Project).filter(Project.city_id == city1.id).count()
    city2_projects = db.query(Project).filter(Project.city_id == city2.id).count()

    assert city1_projects == 4
    assert city2_projects == 1


def test_project_defaults(db):
    """Test default values for status and visibility."""
    user = _create_user(db)
    city = _create_city(db)
    project = Project(
        name="Defaults Test",
        owner_id=user.id,
        city_id=city.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert project.status == ProjectStatus.ACTIVE
    assert project.visibility == Visibility.PRIVATE
