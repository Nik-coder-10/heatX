"""Pydantic schemas for satellite data acquisition operations."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SatelliteSearchRequest(BaseModel):
    bbox: Optional[list[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    city: Optional[str] = Field(None, description="City name for bounding box resolution")
    date_from: Optional[str] = Field(None, description="Start date (ISO-8601)")
    date_to: Optional[str] = Field(None, description="End date (ISO-8601)")
    max_cloud_cover: Optional[float] = Field(None, ge=0, le=100)
    resolution: Optional[float] = Field(None, gt=0)
    missions: Optional[list[str]] = Field(None, description="Filter by mission names")
    bands: Optional[list[str]] = Field(None, description="Required spectral bands")
    providers: Optional[list[str]] = Field(None, description="Provider IDs to search")
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


class SatelliteSearchResponse(BaseModel):
    results: list[dict]
    total: int
    providers_searched: list[str]


class SatelliteDownloadRequest(BaseModel):
    scene_id: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    mission: str = Field(..., min_length=1, max_length=100)
    acquisition_date: str = Field(..., description="ISO-8601 acquisition date")
    project_id: uuid.UUID
    bands: Optional[list[str]] = None
    download_urls: Optional[dict[str, str]] = None
    checksum: Optional[str] = None


class SatelliteDownloadTaskResponse(BaseModel):
    task_id: str
    scene_id: str
    provider: str
    status: str
    progress: float
    band_progress: Optional[dict[str, float]] = None
    downloaded_bytes: Optional[dict[str, int]] = None
    total_bytes: Optional[dict[str, int]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SatelliteProviderResponse(BaseModel):
    provider_id: str
    name: str
    missions: list[str]
    bands: dict[str, list[str]]
    resolutions: list[float]
    products: list[str]
    supports_polygon: bool
    supports_checksum: bool
    requires_api_key: bool


class SatelliteStorageStatsResponse(BaseModel):
    base_dir: str
    total_bytes: int
    file_count: int
    provider_sizes: dict[str, int]
    disk_total: int
    disk_used: int
    disk_free: int
    usage_percent: float


class SatelliteCacheStatsResponse(BaseModel):
    hits: int
    misses: int
    evictions: int
    expirations: int
    invalidations: int
    size: int
    hit_rate: float


class SatelliteImportResult(BaseModel):
    image_id: uuid.UUID
    scene_id: str
    provider: str
    status: str
    storage_path: str
    bands_available: str
    capture_date: datetime
