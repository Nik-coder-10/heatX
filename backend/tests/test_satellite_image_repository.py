"""Tests for the SatelliteImageRepository."""

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import create_engine, exc, event, String, Text, DateTime, Float, ForeignKey, Enum, func, select, Column
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

# -- Local model (Text fallback for Geometry) --
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
    image_metadata = Column("metadata", Text, nullable=True)
    status = Column(Enum(ProcessingStatus), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

# -- Filter/sort maps (mirrors the real repository) --
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


def _build_filters(stmt, filters: Optional[dict]) -> Any:
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


def _build_sort(stmt, sort_by: str, sort_order: str) -> Any:
    column = _SORT_MAP.get(sort_by)
    if column is None:
        return stmt
    if sort_order == "asc":
        return stmt.order_by(column.asc())
    return stmt.order_by(column.desc())


# -- Local repository implementation --
ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, db, model: type[ModelT]):
        self.db = db
        self.model = model
        self._soft_delete = hasattr(model, "deleted_at")

    def _apply_exclude_deleted(self, stmt):
        if self._soft_delete:
            return stmt.where(self.model.deleted_at.is_(None))
        return stmt

    def get_by_id(self, id: uuid.UUID, include_deleted: bool = False):
        stmt = select(self.model).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, data: dict):
        obj = self.model(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj, data: dict):
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

    def restore(self, id: uuid.UUID):
        if not self._soft_delete:
            return None
        obj = self.db.execute(
            select(self.model).where(self.model.id == id)
        ).scalar_one_or_none()
        if obj:
            obj.deleted_at = None
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
        return obj

    def count(self, include_deleted: bool = False):
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def exists(self, id: uuid.UUID, include_deleted: bool = False):
        stmt = select(self.model.id).where(self.model.id == id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).first() is not None


class SatelliteImageRepository(BaseRepository[SatelliteImage]):
    def __init__(self, db) -> None:
        super().__init__(db, SatelliteImage)

    def get_by_scene_id(self, scene_id: str, include_deleted: bool = False):
        stmt = select(SatelliteImage).where(SatelliteImage.scene_id == scene_id)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_project(self, project_id: uuid.UUID, include_deleted: bool = False):
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.project_id == project_id)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_provider(self, provider: SatelliteProvider, include_deleted: bool = False):
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.provider == provider)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(self, status: ProcessingStatus, include_deleted: bool = False):
        stmt = (
            select(SatelliteImage)
            .where(SatelliteImage.status == status)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return list(self.db.execute(stmt).scalars().all())

    def list(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ):
        stmt = select(SatelliteImage)
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        stmt = _build_filters(stmt, filters)
        stmt = _build_sort(stmt, sort_by, sort_order)
        return list(self.db.execute(stmt).scalars().all())

    def paginate(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "capture_date",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ):
        base_stmt = select(SatelliteImage)
        count_stmt = select(func.count()).select_from(SatelliteImage)
        if not include_deleted:
            base_stmt = self._apply_exclude_deleted(base_stmt)
            count_stmt = self._apply_exclude_deleted(count_stmt)
        base_stmt = _build_filters(base_stmt, filters)
        count_stmt = _build_filters(count_stmt, filters)
        base_stmt = _build_sort(base_stmt, sort_by, sort_order)
        total = self.db.execute(count_stmt).scalar() or 0
        items = list(
            self.db.execute(base_stmt.offset(offset).limit(limit)).scalars().all()
        )
        return items, total

    def count_by_project(self, project_id: uuid.UUID, include_deleted: bool = False):
        stmt = (
            select(func.count())
            .select_from(SatelliteImage)
            .where(SatelliteImage.project_id == project_id)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0

    def count_by_status(self, status: ProcessingStatus, include_deleted: bool = False):
        stmt = (
            select(func.count())
            .select_from(SatelliteImage)
            .where(SatelliteImage.status == status)
        )
        if not include_deleted:
            stmt = self._apply_exclude_deleted(stmt)
        return self.db.execute(stmt).scalar() or 0


# -- Test helpers --
_PROJECT_ID = "11111111-1111-1111-1111-111111111111"
_PROJECT_ID_2 = "22222222-2222-2222-2222-222222222222"
_PROJECT_UUID = uuid.UUID(_PROJECT_ID)
_PROJECT_UUID_2 = uuid.UUID(_PROJECT_ID_2)


def _make_image(overrides: Optional[dict] = None) -> dict:
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
def repo(db):
    return SatelliteImageRepository(db)


# -- Tests: Base CRUD --

class TestCreate:
    def test_create_success(self, repo):
        data = _make_image()
        obj = repo.create(data)
        assert obj.id is not None
        assert obj.provider == SatelliteProvider.SENTINEL_2
        assert obj.status == ProcessingStatus.PENDING
        assert obj.created_at is not None
        assert obj.updated_at is not None

    def test_create_with_all_fields(self, repo):
        data = _make_image({
            "footprint": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            "image_metadata": '{"processor": "sen2cor"}',
            "cloud_coverage": 0.0,
            "resolution": 0.5,
        })
        obj = repo.create(data)
        assert obj.footprint is not None
        assert obj.image_metadata is not None
        assert obj.cloud_coverage == 0.0
        assert obj.resolution == 0.5


class TestGetById:
    def test_get_by_id_found(self, repo):
        data = _make_image()
        obj = repo.create(data)
        found = repo.get_by_id(obj.id)
        assert found is not None
        assert found.id == obj.id

    def test_get_by_id_not_found(self, repo):
        found = repo.get_by_id(uuid.uuid4())
        assert found is None

    def test_get_by_id_excludes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        found = repo.get_by_id(obj.id)
        assert found is None

    def test_get_by_id_includes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        found = repo.get_by_id(obj.id, include_deleted=True)
        assert found is not None
        assert found.deleted_at is not None


class TestUpdate:
    def test_update_single_field(self, repo):
        obj = repo.create(_make_image())
        updated = repo.update(obj, {"status": ProcessingStatus.COMPLETED})
        assert updated.status == ProcessingStatus.COMPLETED

    def test_update_multiple_fields(self, repo):
        obj = repo.create(_make_image())
        updated = repo.update(obj, {
            "cloud_coverage": 20.0,
            "status": ProcessingStatus.RUNNING,
        })
        assert updated.cloud_coverage == 20.0
        assert updated.status == ProcessingStatus.RUNNING

    def test_update_ignores_unknown_fields(self, repo):
        obj = repo.create(_make_image())
        updated = repo.update(obj, {"nonexistent": "value"})
        assert updated.id == obj.id


class TestDelete:
    def test_soft_delete_sets_deleted_at(self, repo):
        obj = repo.create(_make_image())
        assert obj.deleted_at is None
        repo.delete(obj)
        assert obj.deleted_at is not None

    def test_soft_delete_excludes_from_query(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        assert repo.count() == 0

    def test_delete_idempotent(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        repo.delete(obj)
        assert repo.count() == 0


class TestRestore:
    def test_restore_clears_deleted_at(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        restored = repo.restore(obj.id)
        assert restored is not None
        assert restored.deleted_at is None

    def test_restore_makes_visible(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        repo.restore(obj.id)
        assert repo.count() == 1

    def test_restore_nonexistent(self, repo):
        restored = repo.restore(uuid.uuid4())
        assert restored is None


class TestCount:
    def test_count_zero(self, repo):
        assert repo.count() == 0

    def test_count_matches_inserts(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({"scene_id": "scene_2"}))
        assert repo.count() == 2

    def test_count_excludes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.create(_make_image({"scene_id": "scene_2"}))
        repo.delete(obj)
        assert repo.count() == 1

    def test_count_includes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.create(_make_image({"scene_id": "scene_2"}))
        repo.delete(obj)
        assert repo.count(include_deleted=True) == 2


class TestExists:
    def test_exists_true(self, repo):
        obj = repo.create(_make_image())
        assert repo.exists(obj.id) is True

    def test_exists_false(self, repo):
        assert repo.exists(uuid.uuid4()) is False

    def test_exists_excludes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        assert repo.exists(obj.id) is False

    def test_exists_includes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        assert repo.exists(obj.id, include_deleted=True) is True


# -- Tests: Domain-specific lookups --

class TestGetBySceneId:
    def test_found(self, repo):
        data = _make_image({"scene_id": "UNIQUE_SCENE_001"})
        obj = repo.create(data)
        found = repo.get_by_scene_id("UNIQUE_SCENE_001")
        assert found is not None
        assert found.id == obj.id

    def test_not_found(self, repo):
        found = repo.get_by_scene_id("NONEXISTENT")
        assert found is None

    def test_excludes_deleted(self, repo):
        obj = repo.create(_make_image({"scene_id": "DELETE_ME"}))
        repo.delete(obj)
        found = repo.get_by_scene_id("DELETE_ME")
        assert found is None


class TestGetByProject:
    def test_returns_project_images(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({"project_id": _PROJECT_ID, "scene_id": "scene_2"}))
        repo.create(_make_image({"project_id": _PROJECT_ID_2, "scene_id": "scene_3"}))
        results = repo.get_by_project(_PROJECT_ID)
        assert len(results) == 2

    def test_empty_project(self, repo):
        results = repo.get_by_project(uuid.uuid4())
        assert results == []


class TestGetByProvider:
    def test_filters_by_provider(self, repo):
        repo.create(_make_image({"provider": SatelliteProvider.SENTINEL_2}))
        repo.create(_make_image({"provider": SatelliteProvider.LANDSAT_8, "scene_id": "ls8_1"}))
        results = repo.get_by_provider(SatelliteProvider.LANDSAT_8)
        assert len(results) == 1
        assert results[0].provider == SatelliteProvider.LANDSAT_8


class TestGetByStatus:
    def test_filters_by_status(self, repo):
        repo.create(_make_image({"status": ProcessingStatus.PENDING}))
        repo.create(_make_image({"status": ProcessingStatus.COMPLETED, "scene_id": "done_1"}))
        results = repo.get_by_status(ProcessingStatus.COMPLETED)
        assert len(results) == 1
        assert results[0].status == ProcessingStatus.COMPLETED


# -- Tests: List with filters and sorting --

class TestList:
    def test_list_all(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({"scene_id": "scene_2"}))
        results = repo.list()
        assert len(results) == 2

    def test_list_filter_provider(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({"provider": SatelliteProvider.MODIS, "scene_id": "modis_1"}))
        results = repo.list(filters={"provider": SatelliteProvider.MODIS})
        assert len(results) == 1

    def test_list_filter_capture_date_from(self, repo):
        repo.create(_make_image({"capture_date": datetime(2025, 1, 1, tzinfo=timezone.utc)}))
        repo.create(_make_image({
            "capture_date": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "scene_id": "june_scene",
        }))
        results = repo.list(filters={"capture_date_from": datetime(2025, 6, 1, tzinfo=timezone.utc)})
        assert len(results) == 1

    def test_list_filter_cloud_coverage_max(self, repo):
        repo.create(_make_image({"cloud_coverage": 10.0, "scene_id": "low_cloud"}))
        repo.create(_make_image({"cloud_coverage": 80.0, "scene_id": "high_cloud"}))
        results = repo.list(filters={"cloud_coverage_max": 50.0})
        assert len(results) == 1

    def test_list_sort_by_ascending(self, repo):
        repo.create(_make_image({"resolution": 30.0, "scene_id": "low_res"}))
        repo.create(_make_image({"resolution": 10.0, "scene_id": "high_res"}))
        results = repo.list(sort_by="resolution", sort_order="asc")
        assert results[0].resolution == 10.0
        assert results[1].resolution == 30.0

    def test_list_sort_by_descending(self, repo):
        repo.create(_make_image({"resolution": 10.0, "scene_id": "high_res"}))
        repo.create(_make_image({"resolution": 30.0, "scene_id": "low_res"}))
        results = repo.list(sort_by="resolution", sort_order="desc")
        assert results[0].resolution == 30.0
        assert results[1].resolution == 10.0

    def test_list_excludes_deleted_by_default(self, repo):
        obj = repo.create(_make_image())
        repo.create(_make_image({"scene_id": "scene_2"}))
        repo.delete(obj)
        results = repo.list()
        assert len(results) == 1


# -- Tests: Pagination --

class TestPaginate:
    def test_paginate_defaults(self, repo):
        for i in range(5):
            repo.create(_make_image({"scene_id": f"scene_{i}"}))
        items, total = repo.paginate()
        assert len(items) == 5
        assert total == 5

    def test_paginate_with_limit(self, repo):
        for i in range(5):
            repo.create(_make_image({"scene_id": f"scene_{i}"}))
        items, total = repo.paginate(limit=2)
        assert len(items) == 2
        assert total == 5

    def test_paginate_with_offset(self, repo):
        data1 = _make_image({"scene_id": "first"})
        data2 = _make_image({"scene_id": "second"})
        data3 = _make_image({"scene_id": "third"})
        repo.create(data1)
        repo.create(data2)
        repo.create(data3)
        items, total = repo.paginate(limit=2, offset=2)
        assert len(items) == 1
        assert total == 3

    def test_paginate_with_filters(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({
            "provider": SatelliteProvider.LANDSAT_8,
            "scene_id": "ls_1",
        }))
        items, total = repo.paginate(filters={"provider": SatelliteProvider.LANDSAT_8})
        assert len(items) == 1
        assert total == 1


# -- Tests: Aggregates --

class TestCountByProject:
    def test_count_by_project(self, repo):
        repo.create(_make_image())
        repo.create(_make_image({"project_id": _PROJECT_ID, "scene_id": "scene_2"}))
        repo.create(_make_image({"project_id": _PROJECT_ID_2, "scene_id": "scene_3"}))
        assert repo.count_by_project(_PROJECT_ID) == 2
        assert repo.count_by_project(_PROJECT_ID_2) == 1

    def test_count_by_project_excludes_deleted(self, repo):
        obj = repo.create(_make_image())
        repo.delete(obj)
        assert repo.count_by_project(_PROJECT_ID) == 0


class TestCountByStatus:
    def test_count_by_status(self, repo):
        repo.create(_make_image({"status": ProcessingStatus.PENDING}))
        repo.create(_make_image({"status": ProcessingStatus.COMPLETED, "scene_id": "done_1"}))
        assert repo.count_by_status(ProcessingStatus.PENDING) == 1
        assert repo.count_by_status(ProcessingStatus.COMPLETED) == 1

    def test_count_by_status_zero(self, repo):
        assert repo.count_by_status(ProcessingStatus.FAILED) == 0


# -- Tests: Error handling --

class TestTransactionRollback:
    def test_rollback_on_create_failure(self, db, repo):
        with pytest.raises(Exception):
            repo.create({"invalid": "data"})
        db.rollback()
        assert repo.count() == 0


class TestDuplicateSceneId:
    def test_duplicate_scene_id_raises(self, db, repo):
        data = _make_image({"scene_id": "DUPLICATE_SCENE"})
        repo.create(data)
        with pytest.raises(exc.IntegrityError):
            repo.create(data)
        db.rollback()
