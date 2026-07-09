"""SatelliteImage model for the UrbanHeatAI platform."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, Float, ForeignKey, JSON, Enum, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.core.database import Base
from app.models.project import Project
from app.database.enums import SatelliteProvider, ProcessingStatus


class SatelliteImage(Base):
    """SatelliteImage model representing satellite imagery data.

    Attributes:
        id: UUID primary key
        project_id: Foreign key to the associated project
        provider: Satellite imagery provider (from SatelliteProvider enum)
        sensor: Sensor name used for capture
        capture_date: Date/time when the image was captured
        resolution: Ground sample distance in meters
        cloud_coverage: Cloud cover percentage (0-100)
        scene_id: Provider scene identifier
        bands_available: Comma-separated list of available spectral bands
        crs: Coordinate Reference System (e.g. EPSG:4326)
        footprint: Polygon geometry of the image footprint (PostGIS)
        storage_path: Path to the raster file in storage
        metadata: Arbitrary JSON metadata
        status: Processing status (from ProcessingStatus enum)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        deleted_at: Soft delete timestamp
        project: Related Project that owns this image
        processed_images: List of processed image derivatives
    """

    __tablename__ = "satellite_images"
    __table_args__ = (
        Index("ix_satellite_images_project_id", "project_id"),
        Index("ix_satellite_images_provider_capture", "provider", "capture_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    provider: Mapped[SatelliteProvider] = mapped_column(Enum(SatelliteProvider), nullable=False)
    sensor: Mapped[str] = mapped_column(String(100), nullable=False)
    capture_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution: Mapped[float] = mapped_column(nullable=False)
    cloud_coverage: Mapped[float] = mapped_column(nullable=False)
    scene_id: Mapped[str] = mapped_column(String(255), nullable=False)
    bands_available: Mapped[str] = mapped_column(String(255), nullable=False)
    crs: Mapped[str] = mapped_column(String(50), nullable=False)
    footprint: Mapped[Optional[Geometry]] = mapped_column(
        Geometry("POLYGON", srid=4326), nullable=True
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    status: Mapped[ProcessingStatus] = mapped_column(Enum(ProcessingStatus), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped[Project] = relationship(back_populates="satellite_images")
    # FIXME: Uncomment when ProcessedImage model is created (Feature 2.6)
    # processed_images: Mapped[List["ProcessedImage"]] = relationship(back_populates="satellite_image")

    def __repr__(self) -> str:
        return (
            f"<SatelliteImage(id={self.id}, scene_id='{self.scene_id}', "
            f"provider='{self.provider}', status='{self.status}')>"
        )