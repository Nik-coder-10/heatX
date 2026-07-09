"""
Unit tests for the database mixins.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

from app.database.mixins import (
    AuditMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    BaseModel,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def test_uuid_primary_key_mixin():
    class TestUUIDModel(UUIDPrimaryKeyMixin, Base):
        __tablename__ = "test_uuid"
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestUUIDModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert isinstance(instance.id, uuid.UUID)
        assert instance.id.version == 4
        assert instance.id is not None


def test_timestamp_mixin():
    class TestTimestampModel(TimestampMixin, Base):
        __tablename__ = "test_timestamp"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestTimestampModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert instance.created_at is not None
        assert instance.updated_at is not None

        old_updated_at = instance.updated_at
        import time
        time.sleep(1.1)
        instance.name = "updated"
        session.commit()
        session.refresh(instance)
        assert instance.updated_at >= old_updated_at


def test_timestamp_to_dict():
    class TestTimestampModel(TimestampMixin, Base):
        __tablename__ = "test_timestamp_dict"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestTimestampModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        result = instance.to_dict()
        assert "created_at" in result
        assert "updated_at" in result


def test_soft_delete_mixin():
    class TestSoftDeleteModel(SoftDeleteMixin, Base):
        __tablename__ = "test_soft_delete"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestSoftDeleteModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert instance.deleted_at is None
        assert not instance.is_deleted()
        assert instance.is_active_record()

        instance.soft_delete()
        session.commit()
        session.refresh(instance)
        assert instance.deleted_at is not None
        assert instance.is_deleted()
        assert not instance.is_active_record()

        instance.restore()
        session.commit()
        session.refresh(instance)
        assert instance.deleted_at is None
        assert not instance.is_deleted()
        assert instance.is_active_record()


def test_soft_delete_alias_methods():
    class TestSoftDeleteAliasModel(SoftDeleteMixin, Base):
        __tablename__ = "test_soft_delete_alias"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestSoftDeleteAliasModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert instance.deleted_at is None
        instance.mark_deleted()
        assert instance.deleted_at is not None
        assert instance.is_deleted()

        instance.restore_record()
        assert instance.deleted_at is None
        assert not instance.is_deleted()


def test_soft_delete_tz_aware():
    instance_type = type("TestModel", (SoftDeleteMixin,), {"__abstract__": True})
    instance = instance_type()
    instance.soft_delete()
    assert instance.deleted_at is not None
    assert instance.deleted_at.tzinfo is not None
    assert instance.deleted_at.tzinfo == timezone.utc


def test_audit_mixin():
    class TestAuditModel(AuditMixin, Base):
        __tablename__ = "test_audit"
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestAuditModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert instance.created_by is None
        assert instance.updated_by is None

        user_id = uuid.uuid4()
        instance.created_by = user_id
        instance.updated_by = user_id
        session.commit()
        session.refresh(instance)

        assert instance.created_by == user_id
        assert instance.updated_by == user_id


def test_base_model():
    class TestBaseModel(BaseModel, Base):
        __tablename__ = "test_base"
        name = Column(String(50))

    Base.metadata.create_all(engine)
    with TestingSessionLocal() as session:
        instance = TestBaseModel(name="test")
        session.add(instance)
        session.commit()
        session.refresh(instance)

        assert isinstance(instance.id, uuid.UUID)
        assert instance.id.version == 4

        assert instance.created_at is not None
        assert instance.updated_at is not None

        assert instance.deleted_at is None
        assert not instance.is_deleted()
        assert instance.is_active_record()

        instance.soft_delete()
        session.commit()
        session.refresh(instance)
        assert instance.deleted_at is not None
        assert instance.is_deleted()
        assert not instance.is_active_record()


if __name__ == "__main__":
    test_uuid_primary_key_mixin()
    print("UUIDPrimaryKeyMixin test passed")
    test_timestamp_mixin()
    print("TimestampMixin test passed")
    test_timestamp_to_dict()
    print("TimestampMixin to_dict test passed")
    test_soft_delete_mixin()
    print("SoftDeleteMixin test passed")
    test_soft_delete_alias_methods()
    print("SoftDeleteMixin alias methods test passed")
    test_soft_delete_tz_aware()
    print("SoftDeleteMixin timezone test passed")
    test_audit_mixin()
    print("AuditMixin test passed")
    test_base_model()
    print("BaseModel test passed")
    print("All tests passed!")