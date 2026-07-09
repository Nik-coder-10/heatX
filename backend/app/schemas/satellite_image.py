"""Pydantic schemas for the SatelliteImage model."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.database.enums import ProcessingStatus, SatelliteProvider


class SatelliteImageBase(BaseModel):
    """Shared base fields for SatelliteImage schemas.

    Attributes:
        project_id: UUID of the owning project
        provider: Satellite imagery provider
        sensor: Sensor name used for capture
        capture_date: Date/time when the image was captured
        resolution: Ground sample distance in meters
        cloud_coverage: Cloud cover percentage (0-100)
        scene_id: Provider scene identifier
        bands_available: Comma-separated list of available spectral bands
        crs: Coordinate Reference System (e.g. EPSG:4326)
        storage_path: Path to the raster file in storage
        metadata: Arbitrary JSON metadata
        status: Processing status
    """

    project_id: uuid.UUID
    provider: SatelliteProvider
    sensor: str = Field(..., max_length=100)
    capture_date: datetime
    resolution: float = Field(..., gt=0, description="Ground sample distance in meters")
    cloud_coverage: float = Field(
        ..., ge=0, le=100, description="Cloud cover percentage (0-100)"
    )
    scene_id: str = Field(..., min_length=1, max_length=255)
    bands_available: str = Field(..., max_length=255)
    crs: str = Field(..., max_length=50)
    storage_path: str = Field(..., max_length=500)
    metadata: Optional[Any] = Field(None, description="Arbitrary JSON metadata")
    status: ProcessingStatus


class SatelliteImageCreate(SatelliteImageBase):
    """Schema for creating a new satellite image record.

    Inherits all fields from SatelliteImageBase as required inputs.
    """


class SatelliteImageUpdate(BaseModel):
    """Schema for updating an existing satellite image. All fields are optional."""

    provider: Optional[SatelliteProvider] = None
    sensor: Optional[str] = Field(None, max_length=100)
    capture_date: Optional[datetime] = None
    resolution: Optional[float] = Field(None, gt=0)
    cloud_coverage: Optional[float] = Field(None, ge=0, le=100)
    scene_id: Optional[str] = Field(None, min_length=1, max_length=255)
    bands_available: Optional[str] = Field(None, max_length=255)
    crs: Optional[str] = Field(None, max_length=50)
    footprint: Optional[str] = None
    storage_path: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Any] = None
    status: Optional[ProcessingStatus] = None


class SatelliteImageResponse(SatelliteImageBase):
    """Full satellite image response including system-managed fields.

    Attributes:
        id: UUID primary key
        footprint: Optional image footprint geometry (WKT/GeoJSON)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    id: uuid.UUID
    footprint: Optional[Any] = None
    metadata: Optional[Any] = Field(
        None, validation_alias="image_metadata", description="Arbitrary JSON metadata"
    )
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SatelliteImageListResponse(BaseModel):
    """Paginated list response for satellite images."""

    items: list[SatelliteImageResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SatelliteImageFilter(BaseModel):
    """Query filters for listing satellite images."""

    project_id: Optional[uuid.UUID] = None
    provider: Optional[SatelliteProvider] = None
    status: Optional[ProcessingStatus] = None
    scene_id: Optional[str] = Field(None, max_length=255)
    capture_date_from: Optional[datetime] = None
    capture_date_to: Optional[datetime] = None
    cloud_coverage_max: Optional[float] = Field(None, ge=0, le=100)
    resolution_max: Optional[float] = Field(None, gt=0)


class SatelliteImageSummary(BaseModel):
    """Lightweight satellite image summary for list displays."""

    id: uuid.UUID
    project_id: uuid.UUID
    provider: SatelliteProvider
    scene_id: str
    capture_date: datetime
    cloud_coverage: float
    status: ProcessingStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
