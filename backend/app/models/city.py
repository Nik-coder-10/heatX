"""City model for the UrbanHeatAI platform."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class City(Base):
    """City model representing geographic cities in the system.

    Attributes:
        id: UUID primary key
        name: City name
        state: State or region (optional)
        country: Country name
        latitude: City latitude coordinate
        longitude: City longitude coordinate
        bounding_box: Polygon geometry boundary using PostGIS (optional)
        timezone: IANA timezone string (e.g. \"America/New_York\") (optional)
        population: City population (optional)
        area_sq_km: City area in square kilometers (optional)
        climate_zone: Climate zone classification (optional)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        deleted_at: Soft delete timestamp
        projects: List of projects associated with this city
    """

    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_cities_name_country"),
        Index("ix_cities_latitude_longitude", "latitude", "longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    # Bounding box as a Polygon (or MultiPolygon) using PostGIS
    bounding_box: Mapped[Optional[Geometry]] = mapped_column(
        Geometry("POLYGON", srid=4326), nullable=True
    )
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sq_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    climate_zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    projects: Mapped[List["Project"]] = relationship(back_populates="city")

    def __repr__(self) -> str:
        return (
            f"<City(id={self.id}, name='{self.name}', "
            f"state='{self.state}', country='{self.country}')>"
        )