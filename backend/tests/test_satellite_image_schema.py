"""Tests for the SatelliteImage Pydantic schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.database.enums import ProcessingStatus, SatelliteProvider
from app.schemas.satellite_image import (
    SatelliteImageBase,
    SatelliteImageCreate,
    SatelliteImageUpdate,
    SatelliteImageResponse,
    SatelliteImageListResponse,
    SatelliteImageFilter,
    SatelliteImageSummary,
)

_VALID_DATA = {
    "project_id": uuid.uuid4(),
    "provider": SatelliteProvider.SENTINEL_2,
    "sensor": "MSI",
    "capture_date": datetime(2025, 6, 15, tzinfo=timezone.utc),
    "resolution": 10.0,
    "cloud_coverage": 5.0,
    "scene_id": "S2A_20250615_T44QPR",
    "bands_available": "B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12",
    "crs": "EPSG:32644",
    "storage_path": "/data/satellite/sentinel2/2025/06/15/S2A_20250615_T44QPR.tif",
    "status": ProcessingStatus.PENDING,
}


class TestSatelliteImageBase:
    def test_valid_base(self):
        schema = SatelliteImageBase(**_VALID_DATA)
        assert schema.provider == SatelliteProvider.SENTINEL_2
        assert schema.cloud_coverage == 5.0
        assert schema.metadata is None

    def test_metadata_optional(self):
        data = {**_VALID_DATA, "metadata": {"key": "value"}}
        schema = SatelliteImageBase(**data)
        assert schema.metadata == {"key": "value"}


class TestSatelliteImageCreate:
    def test_valid_create(self):
        schema = SatelliteImageCreate(**_VALID_DATA)
        assert schema.scene_id == "S2A_20250615_T44QPR"
        assert isinstance(schema.project_id, uuid.UUID)

    def test_cloud_coverage_above_100(self):
        data = {**_VALID_DATA, "cloud_coverage": 150.0}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)

    def test_cloud_coverage_below_0(self):
        data = {**_VALID_DATA, "cloud_coverage": -5.0}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)

    def test_cloud_coverage_at_boundaries(self):
        data = {**_VALID_DATA, "cloud_coverage": 0.0}
        assert SatelliteImageCreate(**data).cloud_coverage == 0.0
        data["cloud_coverage"] = 100.0
        assert SatelliteImageCreate(**data).cloud_coverage == 100.0

    def test_resolution_zero(self):
        data = {**_VALID_DATA, "resolution": 0.0}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)

    def test_resolution_negative(self):
        data = {**_VALID_DATA, "resolution": -1.0}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)

    def test_resolution_positive(self):
        data = {**_VALID_DATA, "resolution": 0.5}
        schema = SatelliteImageCreate(**data)
        assert schema.resolution == 0.5

    def test_empty_scene_id(self):
        data = {**_VALID_DATA, "scene_id": ""}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)

    def test_missing_required_field(self):
        data = {k: v for k, v in _VALID_DATA.items() if k != "project_id"}
        with pytest.raises(ValidationError):
            SatelliteImageCreate(**data)


class TestSatelliteImageUpdate:
    def test_empty_update(self):
        schema = SatelliteImageUpdate()
        assert schema.model_dump(exclude_unset=True) == {}

    def test_partial_update(self):
        schema = SatelliteImageUpdate(status=ProcessingStatus.COMPLETED)
        assert schema.status == ProcessingStatus.COMPLETED
        assert schema.provider is None

    def test_invalid_cloud_coverage(self):
        with pytest.raises(ValidationError):
            SatelliteImageUpdate(cloud_coverage=200.0)

    def test_invalid_resolution(self):
        with pytest.raises(ValidationError):
            SatelliteImageUpdate(resolution=0.0)

    def test_empty_scene_id_rejected(self):
        with pytest.raises(ValidationError):
            SatelliteImageUpdate(scene_id="")

    def test_valid_update_all_fields(self):
        schema = SatelliteImageUpdate(
            provider=SatelliteProvider.LANDSAT_8,
            sensor="OLI",
            resolution=15.0,
        )
        assert schema.provider == SatelliteProvider.LANDSAT_8
        assert schema.sensor == "OLI"
        assert schema.resolution == 15.0


class TestSatelliteImageResponse:
    def test_from_attributes(self):
        obj = _make_orm_object()
        schema = SatelliteImageResponse.model_validate(obj)
        assert schema.id == obj.id
        assert schema.provider == SatelliteProvider.SENTINEL_2
        assert schema.scene_id == obj.scene_id
        assert schema.created_at == obj.created_at
        assert schema.updated_at == obj.updated_at

    def test_invalid_data_rejected(self):
        with pytest.raises(ValidationError):
            SatelliteImageResponse.model_validate(dict())


class TestSatelliteImageSummary:
    def test_from_attributes(self):
        obj = _make_orm_object()
        schema = SatelliteImageSummary.model_validate(obj)
        assert schema.id == obj.id
        assert schema.provider == SatelliteProvider.SENTINEL_2
        assert schema.scene_id == obj.scene_id
        assert "storage_path" not in SatelliteImageSummary.model_fields

    def test_summary_has_limited_fields(self):
        fields = set(SatelliteImageSummary.model_fields.keys())
        assert fields == {
            "id", "project_id", "provider", "scene_id",
            "capture_date", "cloud_coverage", "status", "created_at",
        }


class TestSatelliteImageListResponse:
    def test_valid_list_response(self):
        obj = _make_orm_object()
        item = SatelliteImageResponse.model_validate(obj)
        schema = SatelliteImageListResponse(
            items=[item],
            total=1,
            page=1,
            page_size=20,
        )
        assert len(schema.items) == 1
        assert schema.total == 1

    def test_invalid_page(self):
        with pytest.raises(ValidationError):
            SatelliteImageListResponse(items=[], total=0, page=0, page_size=20)

    def test_invalid_page_size(self):
        with pytest.raises(ValidationError):
            SatelliteImageListResponse(items=[], total=0, page=1, page_size=200)


class TestSatelliteImageFilter:
    def test_empty_filter(self):
        schema = SatelliteImageFilter()
        assert schema.project_id is None
        assert schema.provider is None
        assert schema.status is None

    def test_cloud_coverage_max_invalid(self):
        with pytest.raises(ValidationError):
            SatelliteImageFilter(cloud_coverage_max=150.0)

    def test_resolution_max_invalid(self):
        with pytest.raises(ValidationError):
            SatelliteImageFilter(resolution_max=0.0)

    def test_filter_with_values(self):
        schema = SatelliteImageFilter(
            provider=SatelliteProvider.MODIS,
            status=ProcessingStatus.RUNNING,
            cloud_coverage_max=50.0,
        )
        assert schema.provider == SatelliteProvider.MODIS
        assert schema.status == ProcessingStatus.RUNNING


class TestEnumSerialization:
    def test_provider_enum_to_str(self):
        schema = SatelliteImageCreate(**_VALID_DATA)
        d = schema.model_dump()
        assert d["provider"] == SatelliteProvider.SENTINEL_2

    def test_status_enum_to_str(self):
        schema = SatelliteImageCreate(**_VALID_DATA)
        d = schema.model_dump()
        assert d["status"] == ProcessingStatus.PENDING


# -- helpers

def _make_orm_object():
    class FakeORMObject:
        id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        project_id = uuid.UUID("87654321-4321-8765-4321-876543218765")
        provider = SatelliteProvider.SENTINEL_2
        sensor = "MSI"
        capture_date = datetime(2025, 6, 15, tzinfo=timezone.utc)
        resolution = 10.0
        cloud_coverage = 5.0
        scene_id = "S2A_20250615_T44QPR"
        bands_available = "B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12"
        crs = "EPSG:32644"
        footprint = None
        storage_path = "/data/satellite/sentinel2/S2A_20250615_T44QPR.tif"
        metadata = None
        status = ProcessingStatus.PENDING
        created_at = datetime(2025, 6, 16, tzinfo=timezone.utc)
        updated_at = datetime(2025, 6, 16, tzinfo=timezone.utc)
        deleted_at = None

    return FakeORMObject()
