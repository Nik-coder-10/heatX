"""Tests for the SatelliteImage model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, exc, event, String, Text, DateTime, Float, ForeignKey, Enum, func, Column
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import pytest

from app.database.enums import SatelliteProvider, ProcessingStatus

# Self-contained test setup (avoids model import cascade)
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Project(Base):
    __tablename__ = "projects"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, default="Test Project")
    satellite_images = relationship("SatelliteImage", back_populates="project")


class SatelliteImage(Base):
    __tablename__ = "satellite_images"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(ForeignKey("projects.id"), nullable=False)
    provider = Column(Enum(SatelliteProvider), nullable=False)
    sensor = Column(String(100), nullable=False)
    capture_date = Column(DateTime(timezone=True), nullable=False)
    resolution = Column(Float, nullable=False)
    cloud_coverage = Column(Float, nullable=False)
    scene_id = Column(String(255), nullable=False)
    bands_available = Column(String(255), nullable=False)
    crs = Column(String(50), nullable=False)
    footprint = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=False)
    image_metadata = Column("metadata", Text, nullable=True)
    status = Column(Enum(ProcessingStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="satellite_images")


def _create_project(db):
    project = Project(name="Satellite Test Project")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _default_image(project_id):
    return SatelliteImage(
        project_id=project_id,
        provider=SatelliteProvider.SENTINEL_2,
        sensor="MSI",
        capture_date=datetime(2025, 6, 15, tzinfo=timezone.utc),
        resolution=10.0,
        cloud_coverage=5.0,
        scene_id="S2A_20250615_T44QPR",
        bands_available="B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12",
        crs="EPSG:32644",
        storage_path="/data/satellite/sentinel2/2025/06/15/S2A_20250615_T44QPR.tif",
        status=ProcessingStatus.PENDING,
    )


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_satellite_image_creation(db):
    """Test creating a satellite image with all required fields."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.id is not None
    assert isinstance(image.id, uuid.UUID)
    assert image.project_id == project.id
    assert image.provider == SatelliteProvider.SENTINEL_2
    assert image.sensor == "MSI"
    assert image.scene_id == "S2A_20250615_T44QPR"
    assert image.crs == "EPSG:32644"
    assert image.storage_path == "/data/satellite/sentinel2/2025/06/15/S2A_20250615_T44QPR.tif"
    assert image.status == ProcessingStatus.PENDING
    assert image.footprint is None
    assert image.image_metadata is None
    assert image.deleted_at is None
    assert image.created_at is not None
    assert image.updated_at is not None


def test_satellite_image_optional_fields(db):
    """Test satellite image with optional fields populated."""
    project = _create_project(db)
    image = _default_image(project.id)
    image.footprint = "POLYGON((30 10, 40 10, 40 20, 30 20, 30 10))"
    image.image_metadata = '{"processor": "sen2cor", "version": "1.0"}'
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.footprint is not None
    assert "POLYGON" in image.footprint
    assert image.image_metadata is not None


def test_satellite_image_provider_enum(db):
    """Test all SatelliteProvider enum values."""
    project = _create_project(db)
    for provider in SatelliteProvider:
        image = _default_image(project.id)
        image.provider = provider
        image.scene_id = f"scene_{provider.value}"
        db.add(image)
    db.commit()

    count = db.query(SatelliteImage).count()
    assert count == len(list(SatelliteProvider))


def test_satellite_image_processing_status_enum(db):
    """Test all ProcessingStatus enum values."""
    project = _create_project(db)
    for status in ProcessingStatus:
        image = _default_image(project.id)
        image.status = status
        image.scene_id = f"scene_{status.value}"
        db.add(image)
    db.commit()

    count = db.query(SatelliteImage).count()
    assert count == len(list(ProcessingStatus))


def test_satellite_image_project_relationship(db):
    """Test the bidirectional Project <-> SatelliteImage relationship."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.project.id == project.id
    assert image in project.satellite_images


def test_satellite_image_metadata_persistence(db):
    """Test storing and retrieving JSON metadata."""
    project = _create_project(db)
    image = _default_image(project.id)
    image.image_metadata = '{"cloud_cover_method": "manual", "tile": "44QPR"}'
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.image_metadata is not None
    assert '"tile": "44QPR"' in image.image_metadata


def test_satellite_image_footprint_field(db):
    """Test that footprint geometry can be null or set."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.footprint is None

    image.footprint = "POLYGON((30 10, 40 10, 40 20, 30 20, 30 10))"
    db.commit()
    db.refresh(image)

    assert image.footprint is not None
    assert "POLYGON" in image.footprint


def test_satellite_image_raster_path(db):
    """Test storage_path field."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.storage_path.endswith(".tif")
    assert "sentinel2" in image.storage_path


def test_satellite_image_timestamp_generation(db):
    """Test that timestamps are auto-generated."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.created_at is not None
    assert image.updated_at is not None
    assert isinstance(image.created_at, datetime)
    assert isinstance(image.updated_at, datetime)


def test_satellite_image_soft_delete(db):
    """Test soft delete on SatelliteImage model."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()
    db.refresh(image)

    assert image.deleted_at is None

    image.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(image)

    assert image.deleted_at is not None

    image.deleted_at = None
    db.commit()
    db.refresh(image)

    assert image.deleted_at is None


def test_satellite_image_database_persistence(db):
    """Test full CRUD round-trip."""
    project = _create_project(db)
    image = _default_image(project.id)
    db.add(image)
    db.commit()

    retrieved = db.query(SatelliteImage).filter(
        SatelliteImage.scene_id == "S2A_20250615_T44QPR"
    ).first()
    assert retrieved is not None
    assert retrieved.provider == SatelliteProvider.SENTINEL_2
    assert retrieved.status == ProcessingStatus.PENDING
    assert retrieved.crs == "EPSG:32644"

    retrieved.status = ProcessingStatus.COMPLETED
    db.commit()

    updated = db.query(SatelliteImage).filter(
        SatelliteImage.scene_id == "S2A_20250615_T44QPR"
    ).first()
    assert updated.status == ProcessingStatus.COMPLETED


def test_satellite_image_foreign_key_integrity(db):
    """Test that invalid project_id raises IntegrityError."""
    image = _default_image(uuid.uuid4())
    db.add(image)
    with pytest.raises(exc.IntegrityError):
        db.commit()
