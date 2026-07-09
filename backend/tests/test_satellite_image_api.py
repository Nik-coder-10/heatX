"""Tests for SatelliteImage API endpoints using local model + dependency overrides."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import (
    Column, DateTime, Enum, Float, JSON, String, Text, create_engine, func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from fastapi import FastAPI
# Import Report to resolve real User model's "reports" mapper.
import app.models.report  # noqa: F401
from app.api.v1.endpoints.satellite_image import router as satellite_router
from app.database.enums import ProcessingStatus, SatelliteProvider
from app.services.satellite_image import (
    DuplicateSceneIdError,
    ImageNotFoundError,
    InvalidMetadataError,
    InvalidProviderError,
    InvalidRasterPathError,
    InvalidStatusTransitionError,
    SatelliteImageService,
)

app = FastAPI()
app.include_router(satellite_router, prefix="/api/v1/satellite", tags=["satellite"])

# -- Local model (same approach as test_satellite_image_service.py) --

LocalBase = declarative_base()


class SatelliteImageModel(LocalBase):
    __tablename__ = "satellite_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False)
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
    image_metadata = Column("metadata", JSON, nullable=True)
    status = Column(Enum(ProcessingStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SatelliteImageModel(id={self.id}, scene_id='{self.scene_id}', "
            f"provider='{self.provider}', status='{self.status}')>"
        )


# -- Local repository --

_FILTER_MAP: dict[str, Any] = {
    "project_id": SatelliteImageModel.project_id,
    "provider": SatelliteImageModel.provider,
    "status": SatelliteImageModel.status,
    "scene_id": SatelliteImageModel.scene_id,
    "sensor": SatelliteImageModel.sensor,
    "crs": SatelliteImageModel.crs,
}

_SORT_MAP: dict[str, Any] = {
    "capture_date": SatelliteImageModel.capture_date,
    "created_at": SatelliteImageModel.created_at,
    "cloud_coverage": SatelliteImageModel.cloud_coverage,
    "resolution": SatelliteImageModel.resolution,
    "scene_id": SatelliteImageModel.scene_id,
}


class LocalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, image_id, include_deleted: bool = False) -> Optional[SatelliteImageModel]:
        q = self.db.query(SatelliteImageModel).filter(SatelliteImageModel.id == str(image_id))
        if not include_deleted:
            q = q.filter(SatelliteImageModel.deleted_at.is_(None))
        return q.first()

    def get_by_scene_id(self, scene_id: str) -> Optional[SatelliteImageModel]:
        return self.db.query(SatelliteImageModel).filter(
            SatelliteImageModel.scene_id == scene_id,
            SatelliteImageModel.deleted_at.is_(None),
        ).first()

    def _serialize(self, data: dict) -> dict:
        return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in data.items()}

    def create(self, data: dict) -> SatelliteImageModel:
        obj = SatelliteImageModel(**self._serialize(data))
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: SatelliteImageModel, data: dict) -> SatelliteImageModel:
        for field, value in self._serialize(data).items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: SatelliteImageModel) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        self.db.add(obj)
        self.db.commit()

    def restore(self, image_id) -> Optional[SatelliteImageModel]:
        obj = self.db.query(SatelliteImageModel).filter(
            SatelliteImageModel.id == str(image_id)
        ).first()
        if obj:
            obj.deleted_at = None
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def list(self, filters: Optional[dict] = None, sort_by: str = "capture_date",
             sort_order: str = "desc", include_deleted: bool = False) -> list[SatelliteImageModel]:
        q = self.db.query(SatelliteImageModel)
        if not include_deleted:
            q = q.filter(SatelliteImageModel.deleted_at.is_(None))
        q = self._apply_filters(q, filters)
        q = self._apply_sort(q, sort_by, sort_order)
        return q.all()

    def paginate(self, filters: Optional[dict] = None, sort_by: str = "capture_date",
                 sort_order: str = "desc", limit: int = 20, offset: int = 0,
                 include_deleted: bool = False) -> tuple[list[SatelliteImageModel], int]:
        base_q = self.db.query(SatelliteImageModel)
        count_q = self.db.query(SatelliteImageModel)
        if not include_deleted:
            base_q = base_q.filter(SatelliteImageModel.deleted_at.is_(None))
            count_q = count_q.filter(SatelliteImageModel.deleted_at.is_(None))
        base_q = self._apply_filters(base_q, filters)
        count_q = self._apply_filters(count_q, filters)
        base_q = self._apply_sort(base_q, sort_by, sort_order)
        total = count_q.count()
        items = base_q.offset(offset).limit(limit).all()
        return items, total

    def count(self, include_deleted: bool = False) -> int:
        q = self.db.query(SatelliteImageModel)
        if not include_deleted:
            q = q.filter(SatelliteImageModel.deleted_at.is_(None))
        return q.count()

    def count_by_status(self, status: ProcessingStatus, include_deleted: bool = False) -> int:
        q = self.db.query(SatelliteImageModel).filter(SatelliteImageModel.status == status)
        if not include_deleted:
            q = q.filter(SatelliteImageModel.deleted_at.is_(None))
        return q.count()

    def count_by_project(self, project_id, include_deleted: bool = False) -> int:
        q = self.db.query(SatelliteImageModel).filter(SatelliteImageModel.project_id == str(project_id))
        if not include_deleted:
            q = q.filter(SatelliteImageModel.deleted_at.is_(None))
        return q.count()

    def _apply_filters(self, q, filters: Optional[dict]):
        if not filters:
            return q
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, uuid.UUID):
                value = str(value)
            if key == "capture_date_from" and isinstance(value, datetime):
                q = q.filter(SatelliteImageModel.capture_date >= value)
            elif key == "capture_date_to" and isinstance(value, datetime):
                q = q.filter(SatelliteImageModel.capture_date <= value)
            elif key == "cloud_coverage_max":
                q = q.filter(SatelliteImageModel.cloud_coverage <= value)
            elif key == "resolution_max":
                q = q.filter(SatelliteImageModel.resolution <= value)
            elif key in _FILTER_MAP:
                col = _FILTER_MAP[key]
                q = q.filter(col == value)
        return q

    def _apply_sort(self, q, sort_by: str, sort_order: str):
        col = _SORT_MAP.get(sort_by)
        if col is None:
            return q
        if sort_order == "asc":
            return q.order_by(col.asc())
        return q.order_by(col.desc())


# -- Local service (mirrors real SatelliteImageService logic) --

_VALID_STATUS_TRANSITIONS: dict[ProcessingStatus, set[ProcessingStatus]] = {
    ProcessingStatus.PENDING: {ProcessingStatus.QUEUED, ProcessingStatus.CANCELLED},
    ProcessingStatus.QUEUED: {ProcessingStatus.RUNNING, ProcessingStatus.CANCELLED},
    ProcessingStatus.RUNNING: {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED},
    ProcessingStatus.COMPLETED: {ProcessingStatus.PENDING},
    ProcessingStatus.FAILED: {ProcessingStatus.PENDING, ProcessingStatus.QUEUED},
    ProcessingStatus.CANCELLED: {ProcessingStatus.PENDING},
}


class LocalService:
    def __init__(self, db: Session):
        self.repo = LocalRepository(db)

    def create_image(self, data: dict) -> SatelliteImageModel:
        self._validate_scene_id_unique(data.get("scene_id"))
        self._validate_provider(data.get("provider"))
        return self.repo.create(data)

    def get_image(self, image_id: str, include_deleted: bool = False) -> SatelliteImageModel:
        return self._get_or_raise(image_id, include_deleted)

    def update_image(self, image_id: str, data: dict) -> SatelliteImageModel:
        image = self._get_or_raise(image_id)
        if "status" in data:
            self._validate_status_transition(image.status, data["status"])
        if "scene_id" in data and data["scene_id"] != image.scene_id:
            self._validate_scene_id_unique(data["scene_id"])
        return self.repo.update(image, data)

    def delete_image(self, image_id: str) -> None:
        image = self._get_or_raise(image_id)
        self.repo.delete(image)

    def restore_image(self, image_id: str) -> SatelliteImageModel:
        image = self._get_or_raise(image_id, include_deleted=True)
        if image.deleted_at is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' is not deleted.")
        restored = self.repo.restore(image_id)
        if restored is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return restored

    def list_images(self, filters: Optional[dict] = None, sort_by: str = "capture_date",
                    sort_order: str = "desc") -> list[SatelliteImageModel]:
        return self.repo.list(filters=filters, sort_by=sort_by, sort_order=sort_order)

    def search_images(self, filters: Optional[dict] = None, sort_by: str = "capture_date",
                      sort_order: str = "desc", limit: int = 20,
                      offset: int = 0) -> tuple[list[SatelliteImageModel], int]:
        return self.repo.paginate(
            filters=filters, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset,
        )

    def statistics(self, project_id: Optional[str] = None) -> dict:
        total = self.repo.count()
        by_status = {s.value: self.repo.count_by_status(s) for s in ProcessingStatus}
        result: dict[str, Any] = {"total_images": total, "by_status": by_status}
        if project_id:
            result["project_id"] = project_id
            result["project_count"] = self.repo.count_by_project(project_id)
        return result

    def _get_or_raise(self, image_id: str, include_deleted: bool = False) -> SatelliteImageModel:
        obj = self.repo.get_by_id(image_id, include_deleted=include_deleted)
        if obj is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return obj

    def _validate_scene_id_unique(self, scene_id: Optional[str]) -> None:
        if scene_id is None:
            return
        existing = self.repo.get_by_scene_id(scene_id)
        if existing:
            raise DuplicateSceneIdError(f"Scene ID '{scene_id}' already exists.")

    def _validate_provider(self, provider: Any) -> None:
        if provider is None:
            return
        if not isinstance(provider, SatelliteProvider):
            raise InvalidProviderError(f"Invalid provider: {provider}")

    def _validate_status_transition(self, current: ProcessingStatus, new: ProcessingStatus) -> None:
        allowed = _VALID_STATUS_TRANSITIONS.get(current)
        if allowed is None or new not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot transition from '{current.value}' to '{new.value}'."
            )


# -- Fixtures and dependency overrides --

from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSessionLocal = sessionmaker(bind=engine)

# Create tables once at module level
LocalBase.metadata.create_all(bind=engine)

async def override_get_service():
    db = TestSessionLocal()
    try:
        yield LocalService(db)
    finally:
        db.close()

from app.api.v1.endpoints.satellite_image import get_service as real_get_service
from app.api.v1.endpoints.auth import get_current_user as real_get_current_user

app.dependency_overrides[real_get_service] = override_get_service

def _override_get_current_user():
    return MagicMock(id=uuid.uuid4(), email="test@example.com")

app.dependency_overrides[real_get_current_user] = _override_get_current_user

client = TestClient(app)


# -- Helper functions --

def _make_image_data(overrides: Optional[dict] = None) -> dict:
    data = {
        "project_id": str(uuid.uuid4()),
        "provider": "sentinel_2",
        "sensor": "MSI",
        "capture_date": "2024-06-15T10:30:00Z",
        "resolution": 10.0,
        "cloud_coverage": 15.0,
        "scene_id": f"scene-{uuid.uuid4().hex[:8]}",
        "bands_available": "B01,B02,B03,B04",
        "crs": "EPSG:32633",
        "storage_path": "/data/satellite/2024/06/15/sample.tif",
        "status": "pending",
    }
    if overrides:
        data.update(overrides)
    return data


# -- Database cleanup --

def _clear_table():
    with TestSessionLocal() as db:
        db.query(SatelliteImageModel).delete()
        db.commit()
        db.close()


# -- Tests --

class TestCreateEndpoint:
    def setup_method(self):
        _clear_table()
    def test_create_success(self):
        data = _make_image_data()
        resp = client.post("/api/v1/satellite/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["scene_id"] == data["scene_id"]
        assert body["provider"] == "sentinel_2"
        assert body["status"] == "pending"
        assert "id" in body
        assert "created_at" in body

    def test_create_duplicate_scene_id(self):
        data = _make_image_data()
        client.post("/api/v1/satellite/", json=data)
        resp = client.post("/api/v1/satellite/", json=data)
        assert resp.status_code == 409

    def test_create_invalid_provider(self):
        data = _make_image_data({"provider": "INVALID_PROVIDER"})
        resp = client.post("/api/v1/satellite/", json=data)
        assert resp.status_code == 422

    def test_create_missing_required_field(self):
        data = _make_image_data({"provider": None, "scene_id": None})
        # Remove required fields
        resp = client.post("/api/v1/satellite/", json={})
        assert resp.status_code == 422


class TestGetEndpoint:
    def setup_method(self):
        _clear_table()

    def _create_image(self) -> dict:
        data = _make_image_data()
        resp = client.post("/api/v1/satellite/", json=data)
        assert resp.status_code == 201
        return resp.json()

    def test_get_success(self):
        created = self._create_image()
        resp = client.get(f"/api/v1/satellite/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_not_found(self):
        resp = client.get(f"/api/v1/satellite/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateEndpoint:
    def setup_method(self):
        _clear_table()

    def _create_image(self) -> dict:
        data = _make_image_data()
        resp = client.post("/api/v1/satellite/", json=data)
        return resp.json()

    def test_update_single_field(self):
        created = self._create_image()
        resp = client.patch(f"/api/v1/satellite/{created['id']}", json={"sensor": "UpdatedSensor"})
        assert resp.status_code == 200
        assert resp.json()["sensor"] == "UpdatedSensor"

    def test_update_not_found(self):
        resp = client.patch(f"/api/v1/satellite/{uuid.uuid4()}", json={"sensor": "Test"})
        assert resp.status_code == 404

    def test_update_duplicate_scene_id(self):
        img1 = self._create_image()
        img2 = self._create_image()
        resp = client.patch(f"/api/v1/satellite/{img2['id']}", json={"scene_id": img1["scene_id"]})
        assert resp.status_code == 409

    def test_update_invalid_status_transition(self):
        created = self._create_image()
        # PENDING -> completed is invalid
        resp = client.patch(f"/api/v1/satellite/{created['id']}", json={"status": "completed"})
        assert resp.status_code == 400


class TestDeleteEndpoint:
    def setup_method(self):
        _clear_table()

    def _create_image(self) -> dict:
        data = _make_image_data()
        resp = client.post("/api/v1/satellite/", json=data)
        return resp.json()

    def test_delete_success(self):
        created = self._create_image()
        resp = client.delete(f"/api/v1/satellite/{created['id']}")
        assert resp.status_code == 204
        # Verify it's gone
        get_resp = client.get(f"/api/v1/satellite/{created['id']}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self):
        resp = client.delete(f"/api/v1/satellite/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestRestoreEndpoint:
    def setup_method(self):
        _clear_table()

    def _create_image(self) -> dict:
        data = _make_image_data()
        resp = client.post("/api/v1/satellite/", json=data)
        return resp.json()

    def test_restore_success(self):
        created = self._create_image()
        client.delete(f"/api/v1/satellite/{created['id']}")
        resp = client.post(f"/api/v1/satellite/{created['id']}/restore")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_restore_not_deleted(self):
        created = self._create_image()
        resp = client.post(f"/api/v1/satellite/{created['id']}/restore")
        assert resp.status_code == 404

    def test_restore_not_found(self):
        resp = client.post(f"/api/v1/satellite/{uuid.uuid4()}/restore")
        assert resp.status_code == 404


class TestListEndpoint:
    def setup_method(self):
        _clear_table()
    def test_list_all(self):
        for _ in range(3):
            data = _make_image_data()
            client.post("/api/v1/satellite/", json=data)
        resp = client.get("/api/v1/satellite/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_list_with_filters(self):
        proj_id = str(uuid.uuid4())
        data1 = _make_image_data({"project_id": proj_id, "cloud_coverage": 10.0})
        data2 = _make_image_data({"project_id": proj_id, "cloud_coverage": 50.0})
        client.post("/api/v1/satellite/", json=data1)
        client.post("/api/v1/satellite/", json=data2)
        resp = client.get(f"/api/v1/satellite/?project_id={proj_id}&cloud_coverage_max=30")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_pagination(self):
        for i in range(5):
            client.post("/api/v1/satellite/", json=_make_image_data({"scene_id": f"scene-{i}"}))
        resp = client.get("/api/v1/satellite/?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["page"] == 1
        assert body["page_size"] == 2


class TestSearchEndpoint:
    def setup_method(self):
        _clear_table()
    def test_search_pagination(self):
        for i in range(3):
            client.post("/api/v1/satellite/", json=_make_image_data({"scene_id": f"scene-{i}"}))
        resp = client.get("/api/v1/satellite/search?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3


class TestByProjectEndpoint:
    def setup_method(self):
        _clear_table()
    def test_get_by_project(self):
        proj_id = str(uuid.uuid4())
        client.post("/api/v1/satellite/", json=_make_image_data({"project_id": proj_id}))
        client.post("/api/v1/satellite/", json=_make_image_data({"project_id": proj_id}))
        resp = client.get(f"/api/v1/satellite/project/{proj_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestByProviderEndpoint:
    def setup_method(self):
        _clear_table()
    def test_get_by_provider(self):
        client.post("/api/v1/satellite/", json=_make_image_data({"provider": "sentinel_2"}))
        resp = client.get("/api/v1/satellite/provider/sentinel_2")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestByStatusEndpoint:
    def setup_method(self):
        _clear_table()
    def test_get_by_status(self):
        client.post("/api/v1/satellite/", json=_make_image_data({"status": "pending"}))
        resp = client.get("/api/v1/satellite/status/pending")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestStatisticsEndpoint:
    def setup_method(self):
        _clear_table()
    def test_statistics(self):
        for _ in range(2):
            client.post("/api/v1/satellite/", json=_make_image_data())
        resp = client.get("/api/v1/satellite/statistics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_images"] == 2
        assert "by_status" in body
        assert body["by_status"]["pending"] >= 2

    def test_statistics_with_project(self):
        proj_id = str(uuid.uuid4())
        client.post("/api/v1/satellite/", json=_make_image_data({"project_id": proj_id}))
        resp = client.get(f"/api/v1/satellite/statistics?project_id={proj_id}")
        assert resp.status_code == 200
        assert resp.json()["project_id"] == proj_id
        assert resp.json()["project_count"] == 1
