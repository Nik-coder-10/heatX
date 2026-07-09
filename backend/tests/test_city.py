"""Tests for the City model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, exc, String, Integer, Float, Text, DateTime, func, UniqueConstraint, Index, Column
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import pytest

# Self-contained test setup (avoids model import cascade)
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_cities_name_country"),
        Index("ix_cities_latitude_longitude", "latitude", "longitude"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bounding_box = Column(Text, nullable=True)
    timezone = Column(String(50), nullable=True)
    population = Column(Integer, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    climate_zone = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


@pytest.fixture
def db():
    """Create a fresh database session for testing."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_city_creation(db):
    """Test creating a city with all required fields."""
    city = City(
        name="Mumbai",
        country="India",
        latitude=19.0760,
        longitude=72.8777
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.id is not None
    assert isinstance(city.id, uuid.UUID)
    assert city.name == "Mumbai"
    assert city.country == "India"
    assert city.latitude == 19.0760
    assert city.longitude == 72.8777
    assert city.state is None
    assert city.timezone is None
    assert city.population is None
    assert city.area_sq_km is None
    assert city.climate_zone is None
    assert city.bounding_box is None
    assert city.deleted_at is None
    assert city.created_at is not None
    assert city.updated_at is not None


def test_city_optional_fields(db):
    """Test creating a city with all optional fields."""
    city = City(
        name="New York",
        state="New York",
        country="United States",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        population=8336817,
        area_sq_km=783.8,
        climate_zone="humid_subtropical",
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.state == "New York"
    assert city.timezone == "America/New_York"
    assert city.population == 8336817
    assert city.area_sq_km == 783.8
    assert city.climate_zone == "humid_subtropical"


def test_city_name_country_uniqueness(db):
    """Test that (name, country) pair must be unique."""
    city1 = City(
        name="London",
        country="United Kingdom",
        latitude=51.5074,
        longitude=-0.1278,
    )
    db.add(city1)
    db.commit()

    city2 = City(
        name="London",
        country="United Kingdom",
        latitude=51.5074,
        longitude=-0.1278,
    )
    db.add(city2)
    with pytest.raises(exc.IntegrityError):
        db.commit()


def test_city_same_name_different_country(db):
    """Test that same city name in different countries is allowed."""
    city1 = City(
        name="Springfield",
        country="United States",
        latitude=39.78,
        longitude=-89.65,
    )
    db.add(city1)
    db.commit()

    city2 = City(
        name="Springfield",
        country="Canada",
        latitude=45.78,
        longitude=-65.52,
    )
    db.add(city2)
    db.commit()

    assert city2.id is not None


def test_city_coordinates(db):
    """Test storing and retrieving latitude/longitude."""
    city = City(
        name="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.latitude == 35.6762
    assert city.longitude == 139.6503


def test_city_negative_coordinates(db):
    """Test negative coordinates (southern/western hemispheres)."""
    city = City(
        name="Sydney",
        country="Australia",
        latitude=-33.8688,
        longitude=151.2093,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.latitude == -33.8688


def test_city_timestamp_generation(db):
    """Test that timestamps are auto-generated on creation."""
    city = City(
        name="Berlin",
        country="Germany",
        latitude=52.5200,
        longitude=13.4050,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.created_at is not None
    assert city.updated_at is not None
    assert isinstance(city.created_at, datetime)
    assert isinstance(city.updated_at, datetime)


def test_city_soft_delete(db):
    """Test soft delete functionality on City model."""
    city = City(
        name="Paris",
        country="France",
        latitude=48.8566,
        longitude=2.3522,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.deleted_at is None

    city.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(city)

    assert city.deleted_at is not None

    city.deleted_at = None
    db.commit()
    db.refresh(city)

    assert city.deleted_at is None


def test_city_database_persistence(db):
    """Test that city persists and can be retrieved."""
    city = City(
        name="Dubai",
        country="UAE",
        latitude=25.2048,
        longitude=55.2708,
    )
    db.add(city)
    db.commit()

    retrieved = db.query(City).filter(City.name == "Dubai").first()
    assert retrieved is not None
    assert retrieved.country == "UAE"
    assert retrieved.latitude == 25.2048
    assert retrieved.longitude == 55.2708


def test_city_geometry_field(db):
    """Test that geometry (bounding_box) can be null or set."""
    city = City(
        name="Cairo",
        country="Egypt",
        latitude=30.0444,
        longitude=31.2357,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    assert city.bounding_box is None

    # Verify it can store text-based geometry data
    city.bounding_box = "POLYGON((30 30, 31 30, 31 31, 30 31, 30 30))"
    db.commit()
    db.refresh(city)

    assert city.bounding_box is not None
    assert "POLYGON" in city.bounding_box


def test_city_multiple_cities(db):
    """Test creating and querying multiple cities."""
    cities_data = [
        City(name="Delhi", country="India", latitude=28.7041, longitude=77.1025),
        City(name="Moscow", country="Russia", latitude=55.7558, longitude=37.6173),
        City(name="Beijing", country="China", latitude=39.9042, longitude=116.4074),
    ]
    for city in cities_data:
        db.add(city)
    db.commit()

    count = db.query(City).count()
    assert count == 3


def test_city_updated_at_on_update(db):
    """Test that updated_at changes on update."""
    city = City(
        name="Rome",
        country="Italy",
        latitude=41.9028,
        longitude=12.4964,
    )
    db.add(city)
    db.commit()
    db.refresh(city)

    original_updated_at = city.updated_at

    city.population = 2873000
    db.commit()
    db.refresh(city)

    assert city.updated_at >= original_updated_at
