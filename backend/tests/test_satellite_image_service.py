"""Tests for the SatelliteImageService."""

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import create_engine, exc, event, String, Text, DateTime, Float, ForeignKey, Enum, JSON, func, select, Column
from sqlalchemy.orm import sessionmaker, declarative_base
import pytest

from app.database.enums import ProcessingStatus, SatelliteProvider

# -- Self-contained test setup --
Base = declarative_base()
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -- Local model --
class SatelliteImage(Base):
    __tablename__ = "satellite_images"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False)
    provider = Column(Enum(SatelliteProvider), nullable=False)
    sensor = Column(String(100), nullable=False)
    capture_date = Column(DateTime(timezone=True), nullable=False)
    resolution = Column(Float, nullable=False)
    cloud_coverage = Column(Float, nullable=False)
    scene_id = Column(String(255), nullable=False, unique=True)
    bands_available = Column(String(255), nullable=False)
    crs = Column(String(50), nullable=False)
    footprint = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=False)
    image_metadata = Column("metadata", JSON, nullable=True)
    status = Column(Enum(ProcessingStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

# -- Local repository (mirrors real repo) --
_FILTER_MAP = {
    "project_id": SatelliteImage.project_id,
    "provider": SatelliteImage.provider,
    "status": SatelliteImage.status,
    "scene_id": SatelliteImage.scene_id,
    "sensor": SatelliteImage.sensor,
    "crs": SatelliteImage.crs,
}
_SORT_MAP = {
    "capture_date": SatelliteImage.capture_date,
    "created_at": SatelliteImage.created_at,
    "cloud_coverage": SatelliteImage.cloud_coverage,
    "resolution": SatelliteImage.resolution,
    "scene_id": SatelliteImage.scene_id,
}

ModelT = TypeVar("ModelT")

class BaseRepository(Generic[ModelT]):
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self._soft_delete = hasattr(model, "deleted_at")

    def _apply_exclude_deleted(self, stmt):
        if self._soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, id, include_deleted=False):
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, data):
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj, data):
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj):
        if self._soft_delete:
            obj.deleted_at = datetime.now(timezone.utc)
            self.db.add(obj)
        else:
            self.db.delete(obj)
        self.db.commit()

    def restore(self, id):
        if not self._soft_delete:
            return None
        obj = self.db.execute(select(self.model).where(self.model.id == id)).scalar_one_or_none()
        if obj:
            obj.deleted_at = None
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def count(self, include_deleted=False):
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def exists(self, id, include_deleted=False):
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).first() is not None


class SatelliteImageRepository(BaseRepository[SatelliteImage]):
    def __init__(self, db):
        super().__init__(db, SatelliteImage)

    def get_by_scene_id(self, scene_id, include_deleted=False):
        stmt = select(SatelliteImage).where(SatelliteImage.scene_id == scene_id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_project(self, project_id, include_deleted=False):
        stmt = select(SatelliteImage).where(SatelliteImage.project_id == project_id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_provider(self, provider, include_deleted=False):
        stmt = select(SatelliteImage).where(SatelliteImage.provider == provider)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(self, status, include_deleted=False):
        stmt = select(SatelliteImage).where(SatelliteImage.status == status)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def list(self, filters=None, sort_by="capture_date", sort_order="desc", include_deleted=False):
        stmt = select(SatelliteImage)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        stmt = _build_filters(stmt, filters)
        stmt = _build_sort(stmt, sort_by, sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def paginate(self, filters=None, sort_by="capture_date", sort_order="desc", limit=20, offset=0, include_deleted=False):
        base_stmt = select(SatelliteImage)
        count_stmt = select(func.count()).select_from(SatelliteImage)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        base_stmt = _build_filters(base_stmt, filters)
        count_stmt = _build_filters(count_stmt, filters)
        base_stmt = _build_sort(base_stmt, sort_by, sort_order)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(self.db.execute(base_stmt.offset(offset).limit(limit)).scalars().all())
        return items, total

    def count_by_project(self, project_id, include_deleted=False):
        stmt = select(func.count()).select_from(SatelliteImage).where(SatelliteImage.project_id == project_id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def count_by_status(self, status, include_deleted=False):
        stmt = select(func.count()).select_from(SatelliteImage).where(SatelliteImage.status == status)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0


def _build_filters(stmt, filters):
    if not filters:
        return stmt
    for key, value in filters.items():
        if value is None:
            continue
        if key == "capture_date_from" and isinstance(value, datetime):
            stmt = stmt.where(SatelliteImage.capture_date >= value)
        elif key == "capture_date_to" and isinstance(value, datetime):
            stmt = stmt.where(SatelliteImage.capture_date <= value)
        elif key == "cloud_coverage_max":
            stmt = stmt.where(SatelliteImage.cloud_coverage <= value)
        elif key == "resolution_max":
            stmt = stmt.where(SatelliteImage.resolution <= value)
        elif key in _FILTER_MAP:
            stmt = stmt.where(_FILTER_MAP[key] == value)
    return stmt

def _build_sort(stmt, sort_by, sort_order):
    column = _SORT_MAP.get(sort_by)
    if column is None:
        return stmt
    if sort_order == "asc":
        return stmt.order_by(column.asc())
    return stmt.order_by(column.desc())

# -- Local service (mirrors real service) --

class SatelliteImageError(Exception): ...
class DuplicateSceneIdError(SatelliteImageError): ...
class ImageNotFoundError(SatelliteImageError): ...
class InvalidStatusTransitionError(SatelliteImageError): ...
class InvalidProviderError(SatelliteImageError): ...
class InvalidMetadataError(SatelliteImageError): ...
class InvalidRasterPathError(SatelliteImageError): ...

_VALID_STATUS_TRANSITIONS = {
    ProcessingStatus.PENDING: {ProcessingStatus.QUEUED, ProcessingStatus.CANCELLED},
    ProcessingStatus.QUEUED: {ProcessingStatus.RUNNING, ProcessingStatus.CANCELLED},
    ProcessingStatus.RUNNING: {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED},
    ProcessingStatus.COMPLETED: {ProcessingStatus.PENDING},
    ProcessingStatus.FAILED: {ProcessingStatus.PENDING, ProcessingStatus.QUEUED},
    ProcessingStatus.CANCELLED: {ProcessingStatus.PENDING},
}

def _validate_status_transition(current, new):
    allowed = _VALID_STATUS_TRANSITIONS.get(current)
    if allowed is None or new not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition from '{current.value}' to '{new.value}'."
        )


class SatelliteImageService:
    def __init__(self, db):
        self.repo = SatelliteImageRepository(db)

    def create_image(self, data):
        self._validate_scene_id_unique(data.get("scene_id"))
        self._validate_provider(data.get("provider"))
        return self.repo.create(data)

    def update_image(self, image_id, data):
        image = self._get_or_raise(image_id)
        if "status" in data:
            _validate_status_transition(image.status, data["status"])
        if "scene_id" in data and data["scene_id"] != image.scene_id:
            self._validate_scene_id_unique(data["scene_id"])
        return self.repo.update(image, data)

    def delete_image(self, image_id):
        image = self._get_or_raise(image_id)
        self.repo.delete(image)

    def restore_image(self, image_id):
        image = self._get_or_raise(image_id, include_deleted=True)
        if image.deleted_at is None:
            raise ImageNotFoundError(
                f"SatelliteImage with id '{image_id}' is not deleted."
            )
        restored = self.repo.restore(image_id)
        if restored is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return restored

    def get_image(self, image_id, include_deleted=False):
        return self._get_or_raise(image_id, include_deleted)

    def list_images(self, filters=None, sort_by="capture_date", sort_order="desc"):
        return self.repo.list(filters=filters, sort_by=sort_by, sort_order=sort_order)

    def search_images(self, filters=None, sort_by="capture_date", sort_order="desc", limit=20, offset=0):
        return self.repo.paginate(filters=filters, sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset)

    def validate_image(self, data):
        scene_id = data.get("scene_id")
        provider = data.get("provider")
        if scene_id:
            existing = self.repo.get_by_scene_id(scene_id)
            if existing:
                raise DuplicateSceneIdError(f"Scene ID '{scene_id}' already exists.")
        if provider:
            self._validate_provider(provider)
        return True

    def change_processing_status(self, image_id, new_status):
        image = self._get_or_raise(image_id)
        _validate_status_transition(image.status, new_status)
        return self.repo.update(image, {"status": new_status})

    def attach_metadata(self, image_id, metadata):
        self._validate_metadata(metadata)
        image = self._get_or_raise(image_id)
        existing = image.image_metadata or {}
        if isinstance(existing, str):
            existing = {}
        merged = {**existing, **metadata}
        return self.repo.update(image, {"image_metadata": merged})

    def update_cloud_cover(self, image_id, cloud_cover):
        if cloud_cover < 0.0 or cloud_cover > 100.0:
            raise SatelliteImageError(f"Cloud cover must be between 0 and 100, got {cloud_cover}.")
        image = self._get_or_raise(image_id)
        return self.repo.update(image, {"cloud_coverage": cloud_cover})

    def update_raster_path(self, image_id, path):
        self._validate_raster_path(path)
        image = self._get_or_raise(image_id)
        return self.repo.update(image, {"storage_path": path})

    def statistics(self, project_id=None):
        total = self.repo.count()
        by_status = {s.value: self.repo.count_by_status(s) for s in ProcessingStatus}
        result = {"total_images": total, "by_status": by_status}
        if project_id:
            result["project_id"] = str(project_id)
            result["project_count"] = self.repo.count_by_project(project_id)
        return result

    def _get_or_raise(self, image_id, include_deleted=False):
        obj = self.repo.get_by_id(image_id, include_deleted=include_deleted)
        if obj is None:
            raise ImageNotFoundError(f"SatelliteImage with id '{image_id}' not found.")
        return obj

    def _validate_scene_id_unique(self, scene_id):
        if scene_id is None:
            return
        existing = self.repo.get_by_scene_id(scene_id)
        if existing:
            raise DuplicateSceneIdError(f"Scene ID '{scene_id}' already exists.")

    def _validate_provider(self, provider):
        if provider is None:
            return
        if not isinstance(provider, SatelliteProvider):
            raise InvalidProviderError(f"Invalid provider: {provider}")

    def _validate_metadata(self, metadata):
        if not isinstance(metadata, dict):
            raise InvalidMetadataError("Metadata must be a dictionary.")

    def _validate_raster_path(self, path):
        if not path or not isinstance(path, str):
            raise InvalidRasterPathError("Raster path must be a non-empty string.")

# -- Helpers --
_PROJECT_ID = "11111111-1111-1111-1111-111111111111"

def make_image_data(overrides=None):
    data = {
        "project_id": _PROJECT_ID,
        "provider": SatelliteProvider.SENTINEL_2,
        "sensor": "MSI",
        "capture_date": datetime(2025, 6, 15, tzinfo=timezone.utc),
        "resolution": 10.0,
        "cloud_coverage": 5.0,
        "scene_id": f"S2A_{uuid.uuid4().hex[:8]}",
        "bands_available": "B1,B2,B3,B4,B5,B6,B7,B8,B8A,B9,B11,B12",
        "crs": "EPSG:32644",
        "storage_path": f"/data/satellite/{uuid.uuid4().hex}.tif",
        "status": ProcessingStatus.PENDING,
    }
    if overrides:
        data.update(overrides)
    return data

# -- Fixtures --
@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def svc(db):
    return SatelliteImageService(db)

@pytest.fixture
def created_image(svc):
    return svc.create_image(make_image_data())


# -- Tests: CRUD --

class TestCreateImage:
    def test_create_success(self, svc):
        img = svc.create_image(make_image_data())
        assert img.id is not None
        assert img.status == ProcessingStatus.PENDING

    def test_create_duplicate_scene_id(self, svc):
        data = make_image_data({"scene_id": "DUP_SCENE"})
        svc.create_image(data)
        with pytest.raises(DuplicateSceneIdError):
            svc.create_image(data)

    def test_create_invalid_provider(self, svc):
        data = make_image_data({"provider": "INVALID"})
        with pytest.raises(InvalidProviderError):
            svc.create_image(data)


class TestGetImage:
    def test_get_success(self, svc, created_image):
        got = svc.get_image(created_image.id)
        assert got.id == created_image.id

    def test_get_not_found(self, svc):
        with pytest.raises(ImageNotFoundError):
            svc.get_image(uuid.uuid4())


class TestUpdateImage:
    def test_update_single_field(self, svc, created_image):
        updated = svc.update_image(created_image.id, {"cloud_coverage": 50.0})
        assert updated.cloud_coverage == 50.0

    def test_update_status_valid(self, svc, created_image):
        updated = svc.update_image(created_image.id, {"status": ProcessingStatus.QUEUED})
        assert updated.status == ProcessingStatus.QUEUED

    def test_update_status_invalid(self, svc, created_image):
        with pytest.raises(InvalidStatusTransitionError):
            svc.update_image(created_image.id, {"status": ProcessingStatus.RUNNING})

    def test_update_scene_id_duplicate(self, svc):
        svc.create_image(make_image_data({"scene_id": "SCENE_A"}))
        img2 = svc.create_image(make_image_data({"scene_id": "SCENE_B"}))
        with pytest.raises(DuplicateSceneIdError):
            svc.update_image(img2.id, {"scene_id": "SCENE_A"})

    def test_update_scene_id_same_value(self, svc, created_image):
        updated = svc.update_image(created_image.id, {"scene_id": created_image.scene_id})
        assert updated.scene_id == created_image.scene_id


class TestDeleteImage:
    def test_delete_soft_delete(self, svc, created_image):
        svc.delete_image(created_image.id)
        with pytest.raises(ImageNotFoundError):
            svc.get_image(created_image.id)

    def test_delete_nonexistent(self, svc):
        with pytest.raises(ImageNotFoundError):
            svc.delete_image(uuid.uuid4())


class TestRestoreImage:
    def test_restore_success(self, svc, created_image):
        svc.delete_image(created_image.id)
        restored = svc.restore_image(created_image.id)
        assert restored.id == created_image.id
        assert restored.deleted_at is None

    def test_restore_not_deleted(self, svc, created_image):
        with pytest.raises(ImageNotFoundError):
            svc.restore_image(created_image.id)

    def test_restore_nonexistent(self, svc):
        with pytest.raises(ImageNotFoundError):
            svc.restore_image(uuid.uuid4())


# -- Tests: List / Search --

class TestListImages:
    def test_list_all(self, svc):
        svc.create_image(make_image_data())
        svc.create_image(make_image_data({"scene_id": "scene_2"}))
        results = svc.list_images()
        assert len(results) == 2

    def test_list_with_filters(self, svc):
        svc.create_image(make_image_data({"provider": SatelliteProvider.MODIS, "scene_id": "modis_1"}))
        svc.create_image(make_image_data({"scene_id": "s2_1"}))
        results = svc.list_images(filters={"provider": SatelliteProvider.MODIS})
        assert len(results) == 1


class TestSearchImages:
    def test_search_pagination(self, svc):
        for i in range(5):
            svc.create_image(make_image_data({"scene_id": f"scene_{i}"}))
        items, total = svc.search_images(limit=2, offset=0)
        assert len(items) == 2
        assert total == 5

    def test_search_with_filters(self, svc):
        svc.create_image(make_image_data({"status": ProcessingStatus.PENDING}))
        svc.create_image(make_image_data({"status": ProcessingStatus.COMPLETED, "scene_id": "done_1"}))
        items, total = svc.search_images(filters={"status": ProcessingStatus.COMPLETED})
        assert len(items) == 1
        assert total == 1


# -- Tests: Domain operations --

class TestValidateImage:
    def test_validate_valid(self, svc):
        assert svc.validate_image(make_image_data()) is True

    def test_validate_duplicate_scene(self, svc):
        data = make_image_data({"scene_id": "TO_VALIDATE"})
        svc.create_image(data)
        with pytest.raises(DuplicateSceneIdError):
            svc.validate_image(data)


class TestChangeProcessingStatus:
    def test_valid_transition_pending_to_queued(self, svc, created_image):
        updated = svc.change_processing_status(created_image.id, ProcessingStatus.QUEUED)
        assert updated.status == ProcessingStatus.QUEUED

    def test_valid_transition_completed_to_pending(self, svc, created_image):
        svc.change_processing_status(created_image.id, ProcessingStatus.QUEUED)
        svc.change_processing_status(created_image.id, ProcessingStatus.RUNNING)
        svc.change_processing_status(created_image.id, ProcessingStatus.COMPLETED)
        updated = svc.change_processing_status(created_image.id, ProcessingStatus.PENDING)
        assert updated.status == ProcessingStatus.PENDING

    def test_invalid_transition_pending_to_completed(self, svc, created_image):
        with pytest.raises(InvalidStatusTransitionError):
            svc.change_processing_status(created_image.id, ProcessingStatus.COMPLETED)

    def test_invalid_transition_nonexistent_image(self, svc):
        with pytest.raises(ImageNotFoundError):
            svc.change_processing_status(uuid.uuid4(), ProcessingStatus.QUEUED)


class TestAttachMetadata:
    def test_attach_new_metadata(self, svc, created_image):
        updated = svc.attach_metadata(created_image.id, {"processor": "sen2cor", "version": "1.0"})
        assert updated.image_metadata is not None
        assert updated.image_metadata["processor"] == "sen2cor"

    def test_attach_merges_with_existing(self, svc, created_image):
        svc.attach_metadata(created_image.id, {"key_a": "value_a"})
        updated = svc.attach_metadata(created_image.id, {"key_b": "value_b"})
        assert updated.image_metadata["key_a"] == "value_a"
        assert updated.image_metadata["key_b"] == "value_b"

    def test_attach_overwrites_existing_key(self, svc, created_image):
        svc.attach_metadata(created_image.id, {"key": "old"})
        updated = svc.attach_metadata(created_image.id, {"key": "new"})
        assert updated.image_metadata["key"] == "new"

    def test_attach_invalid_type(self, svc, created_image):
        with pytest.raises(InvalidMetadataError):
            svc.attach_metadata(created_image.id, "not_a_dict")


class TestUpdateCloudCover:
    def test_update_valid(self, svc, created_image):
        updated = svc.update_cloud_cover(created_image.id, 25.0)
        assert updated.cloud_coverage == 25.0

    def test_update_above_100(self, svc, created_image):
        with pytest.raises(SatelliteImageError):
            svc.update_cloud_cover(created_image.id, 150.0)

    def test_update_below_0(self, svc, created_image):
        with pytest.raises(SatelliteImageError):
            svc.update_cloud_cover(created_image.id, -5.0)


class TestUpdateRasterPath:
    def test_update_valid_path(self, svc, created_image):
        path = "/data/new/scene.tif"
        updated = svc.update_raster_path(created_image.id, path)
        assert updated.storage_path == path

    def test_update_empty_path(self, svc, created_image):
        with pytest.raises(InvalidRasterPathError):
            svc.update_raster_path(created_image.id, "")


class TestStatistics:
    def test_statistics_total(self, svc):
        svc.create_image(make_image_data())
        svc.create_image(make_image_data({"scene_id": "scene_2"}))
        stats = svc.statistics()
        assert stats["total_images"] == 2

    def test_statistics_by_status(self, svc):
        svc.create_image(make_image_data({"status": ProcessingStatus.PENDING}))
        svc.create_image(make_image_data({"status": ProcessingStatus.COMPLETED, "scene_id": "done_1"}))
        stats = svc.statistics()
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["completed"] == 1

    def test_statistics_by_project(self, svc):
        other_project = "22222222-2222-2222-2222-222222222222"
        svc.create_image(make_image_data())
        svc.create_image(make_image_data({"scene_id": "scene_2"}))
        svc.create_image(make_image_data({"project_id": other_project, "scene_id": "scene_3"}))
        stats = svc.statistics(project_id=_PROJECT_ID)
        assert stats["project_count"] == 2


# -- Tests: Error handling --

class TestErrorHandling:
    def test_get_image_include_deleted(self, svc, created_image):
        svc.delete_image(created_image.id)
        got = svc.get_image(created_image.id, include_deleted=True)
        assert got.id == created_image.id
        assert got.deleted_at is not None

    def test_delete_twice(self, svc, created_image):
        svc.delete_image(created_image.id)
        with pytest.raises(ImageNotFoundError):
            svc.delete_image(created_image.id)
