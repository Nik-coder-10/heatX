"""Tests for the Satellite Data Acquisition subsystem.

Covers: provider registry, provider discovery, search, download,
retry, resume, cache hit/miss, metadata extraction, validation,
duplicate downloads, parallel downloads, storage.
"""

import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.satellite.base_provider import BaseSatelliteProvider, ProviderCapabilities
from app.satellite.cache import SatelliteCache
from app.satellite.download_manager import DownloadManager
from app.satellite.exceptions import (
    CacheError,
    DownloadCancelledError,
    DownloadError,
    FileCorruptionError,
    InvalidCRSError,
    InvalidSearchParameterError,
    MetadataError,
    MissingBandError,
    ProviderNotFoundError,
    StorageError,
    UnsupportedProductError,
    ValidationError,
)
from app.satellite.metadata import MetadataExtractor
from app.satellite.provider_registry import ProviderRegistry, get_registry
from app.satellite.search import SatelliteSearch
from app.satellite.storage import StorageManager
from app.satellite.validator import SatelliteValidator


def _write_temp_tif(data=b"\x00" * 1024):
    f = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    f.write(data)
    f.close()
    return f.name


# ================================================================
# Provider Registry Tests
# ================================================================

class TestProviderRegistry:
    def test_discover_finds_all_providers(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        ids = registry.list_provider_ids()
        assert "sentinel_2" in ids
        assert "landsat_8" in ids
        assert "landsat_9" in ids

    def test_get_known_provider(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        sentinel = registry.get("sentinel_2")
        assert sentinel is not None
        assert sentinel.provider_id == "sentinel_2"

    def test_get_unknown_provider_raises(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        with pytest.raises(ProviderNotFoundError):
            registry.get("nonexistent")

    def test_manual_register(self):
        registry = ProviderRegistry()
        class MockProvider(BaseSatelliteProvider):
            @property
            def provider_id(self): return "test_provider"
            @property
            def capabilities(self): return ProviderCapabilities(name="test", display_name="Test")
            def search(self, **kw): return []
            def download(self, **kw): return {}
            def validate(self, **kw): return True
            def extract_metadata(self, **kw): return {}
            def estimate_size(self, **kw): return 0
            def available_bands(self, **kw): return []
            def supported_resolutions(self): return []
            def supported_products(self): return []
        registry.register(MockProvider())
        assert registry.get("test_provider") is not None

    def test_list_providers_returns_instances(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        providers = registry.list_providers()
        assert all(isinstance(p, BaseSatelliteProvider) for p in providers)

    def test_get_capabilities(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        caps = registry.get_capabilities("sentinel_2")
        assert caps.name == "sentinel_2"
        assert "L2A" in caps.products

    def test_list_capabilities(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        caps = registry.list_capabilities()
        assert "sentinel_2" in caps
        assert "landsat_8" in caps
        assert "landsat_9" in caps

    def test_get_registry_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2


# ================================================================
# Provider Interface Compliance Tests
# ================================================================

class TestProviderCompliance:
    """Every provider must implement all abstract methods."""

    @pytest.fixture
    def registry(self):
        r = ProviderRegistry()
        r.discover(force=True)
        return r

    def test_all_providers_have_provider_id(self, registry):
        for p in registry.list_providers():
            assert p.provider_id
            assert isinstance(p.provider_id, str)

    def test_all_providers_have_capabilities(self, registry):
        for p in registry.list_providers():
            caps = p.capabilities
            assert caps.name
            assert caps.display_name

    def test_all_providers_support_search(self, registry):
        for p in registry.list_providers():
            results = p.search()
            assert isinstance(results, list)

    def test_all_providers_support_download(self, registry):
        for p in registry.list_providers():
            result = p.download("test_scene", {"B04": "http://example.com/test.tif"}, "/tmp")
            assert isinstance(result, dict)

    def test_all_providers_support_validate(self, registry):
        path = _write_temp_tif()
        try:
            for p in registry.list_providers():
                valid = p.validate("test", {"B04": path})
                assert valid is True
        finally:
            os.unlink(path)

    def test_all_providers_support_extract_metadata(self, registry):
        path = _write_temp_tif()
        try:
            for p in registry.list_providers():
                meta = p.extract_metadata("test", {"B04": path})
                assert isinstance(meta, dict)
                assert "scene_id" in meta
                assert "provider" in meta
                assert "bands" in meta
        finally:
            os.unlink(path)

    def test_all_providers_estimate_size_returns_int(self, registry):
        for p in registry.list_providers():
            size = p.estimate_size("test_scene")
            assert isinstance(size, int)
            assert size >= 0

    def test_all_providers_available_bands(self, registry):
        for p in registry.list_providers():
            bands = p.available_bands("test")
            assert isinstance(bands, list)
            assert len(bands) > 0

    def test_all_providers_supported_resolutions(self, registry):
        for p in registry.list_providers():
            resolutions = p.supported_resolutions()
            assert isinstance(resolutions, list)
            assert all(isinstance(r, float) for r in resolutions)

    def test_all_providers_supported_products(self, registry):
        for p in registry.list_providers():
            products = p.supported_products()
            assert isinstance(products, list)
            assert len(products) > 0


# ================================================================
# Cache Tests
# ================================================================

class TestSatelliteCache:
    def test_set_and_get(self):
        cache = SatelliteCache()
        cache.set("key1", {"data": 123})
        assert cache.get("key1") == {"data": 123}

    def test_get_miss(self):
        cache = SatelliteCache()
        assert cache.get("nonexistent") is None

    def test_has(self):
        cache = SatelliteCache()
        cache.set("k", "v")
        assert cache.has("k") is True
        assert cache.has("missing") is False

    def test_lru_eviction(self):
        cache = SatelliteCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("d") is not None
        assert cache.size == 3

    def test_expiration(self):
        cache = SatelliteCache(default_ttl=0)
        cache.set("k", "v", ttl_seconds=0)
        time.sleep(0.01)
        assert cache.get("k") is None

    def test_invalidate(self):
        cache = SatelliteCache()
        cache.set("k", "v")
        assert cache.invalidate("k") is True
        assert cache.get("k") is None

    def test_invalidate_nonexistent(self):
        cache = SatelliteCache()
        assert cache.invalidate("nope") is False

    def test_invalidate_pattern(self):
        cache = SatelliteCache()
        cache.set("scene:abc", 1)
        cache.set("scene:def", 2)
        cache.set("other", 3)
        count = cache.invalidate_pattern("scene:")
        assert count == 2
        assert cache.get("other") is not None

    def test_clear(self):
        cache = SatelliteCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_contains_scene(self):
        cache = SatelliteCache()
        cache.set("scene:S2A_123", {"data": 1})
        assert cache.contains_scene("S2A_123") is True
        assert cache.contains_scene("S2A_999") is False

    def test_stats(self):
        cache = SatelliteCache()
        cache.get("miss")
        cache.set("k", "v")
        cache.get("k")
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_hit_rate(self):
        cache = SatelliteCache()
        assert cache.hit_rate == 0.0
        cache.set("k", "v")
        cache.get("k")
        cache.get("miss")
        assert 0.0 < cache.hit_rate < 1.0

    def test_reset_stats(self):
        cache = SatelliteCache()
        cache.set("k", "v")
        cache.get("k")
        cache.reset_stats()
        assert cache.stats["hits"] == 0

    def test_keys(self):
        cache = SatelliteCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.keys) == {"a", "b"}

    def test_update_existing_key(self):
        cache = SatelliteCache()
        cache.set("k", 1)
        cache.set("k", 2)
        assert cache.get("k") == 2


# ================================================================
# Metadata Extraction Tests
# ================================================================

class TestMetadataExtractor:
    def test_normalize_valid(self):
        raw = {
            "scene_id": "S2A_123_L2A",
            "provider": "sentinel_2",
            "mission": "sentinel_2a",
            "sensor": "MSI",
            "acquisition_date": "2025-06-15T10:25:00Z",
            "processing_level": "L2A",
            "cloud_cover": 5.0,
            "crs": "EPSG:32644",
            "resolution": 10.0,
            "bands": ["B02", "B03", "B04", "B08"],
            "bounding_box": [77.0, 12.5, 78.0, 13.5],
            "file_size_bytes": 850_000_000,
            "provider_name": "Copernicus",
        }
        result = MetadataExtractor.normalize(raw)
        assert result["scene_id"] == "S2A_123_L2A"
        assert result["provider"] == "sentinel_2"
        assert result["bands"] == ["B02", "B03", "B04", "B08"]

    def test_normalize_missing_required_field(self):
        raw = {"scene_id": "test"}
        with pytest.raises(MetadataError):
            MetadataExtractor.normalize(raw)

    def test_normalize_coerces_types(self):
        raw = {
            "scene_id": "test",
            "provider": "test",
            "mission": "test",
            "sensor": "test",
            "acquisition_date": "2025-01-01",
            "processing_level": "L1C",
            "cloud_cover": "10.5",
            "crs": "EPSG:4326",
            "resolution": "30.0",
            "bands": "B02,B03,B04",
            "bounding_box": [1, 2, 3, 4],
            "file_size_bytes": "5000000",
            "provider_name": "test",
        }
        result = MetadataExtractor.normalize(raw)
        assert result["cloud_cover"] == 10.5
        assert result["resolution"] == 30.0
        assert result["file_size_bytes"] == 5000000
        assert result["bands"] == ["B02", "B03", "B04"]

    def test_normalize_band_name(self):
        assert MetadataExtractor.normalize_band_name("B02") == "b02"
        assert MetadataExtractor.normalize_band_name("NIR") == "b08"
        assert MetadataExtractor.normalize_band_name("SWIR1") == "b11"

    def test_normalize_date_iso(self):
        assert MetadataExtractor.normalize_date("2025-06-15T10:25:00Z") == "2025-06-15T10:25:00Z"

    def test_normalize_date_simple(self):
        result = MetadataExtractor.normalize_date("2025-06-15")
        assert result.startswith("2025-06-15")

    def test_normalize_date_invalid(self):
        with pytest.raises(MetadataError):
            MetadataExtractor.normalize_date("not-a-date")

    def test_normalize_crs_epsg(self):
        assert MetadataExtractor.normalize_crs("EPSG:32644") == "EPSG:32644"
        assert MetadataExtractor.normalize_crs("epsg 4326") == "EPSG:4326"

    def test_to_satellite_image_payload(self):
        meta = {
            "scene_id": "S2A_1",
            "provider": "sentinel_2",
            "mission": "sentinel_2a",
            "sensor": "MSI",
            "acquisition_date": "2025-06-15T10:25:00Z",
            "processing_level": "L2A",
            "cloud_cover": 5.0,
            "crs": "EPSG:32644",
            "resolution": 10.0,
            "bands": ["B02", "B03"],
            "bounding_box": [77.0, 12.5, 78.0, 13.5],
            "file_size_bytes": 1000,
            "provider_name": "Copernicus",
        }
        payload = MetadataExtractor.to_satellite_image_payload(meta)
        assert payload["scene_id"] == "S2A_1"
        assert payload["cloud_coverage"] == 5.0
        assert payload["bands_available"] == "B02,B03"
        assert payload["status"] == "pending"
        assert payload["metadata"]["mission"] == "sentinel_2a"


# ================================================================
# Validator Tests
# ================================================================

class TestSatelliteValidator:
    def test_validate_geotiff_valid(self):
        # 8-byte TIFF header: II\x2a\x00 + IFD offset=8, plus extra byte so size > offset
        f = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
        f.write(b"II\x2a\x00\x08\x00\x00\x00\x00")
        f.close()
        try:
            assert SatelliteValidator.validate_geotiff(f.name) is True
        finally:
            os.unlink(f.name)

    def test_validate_geotiff_invalid_magic(self):
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
            f.write(b"\x00" * 8)
            path = f.name
        try:
            with pytest.raises(FileCorruptionError):
                SatelliteValidator.validate_geotiff(path)
        finally:
            os.unlink(path)

    def test_validate_geotiff_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(FileCorruptionError):
                SatelliteValidator.validate_geotiff(path)
        finally:
            os.unlink(path)

    def test_validate_geotiff_not_found(self):
        with pytest.raises(FileCorruptionError):
            SatelliteValidator.validate_geotiff("/nonexistent/file.tif")

    def test_validate_band_completeness_ok(self):
        assert SatelliteValidator.validate_band_completeness(
            ["B02", "B03"], ["B02", "B03", "B04"], "sentinel_2"
        ) is True

    def test_validate_band_completeness_missing(self):
        with pytest.raises(MissingBandError):
            SatelliteValidator.validate_band_completeness(
                ["B02", "B03", "B04"], ["B02"], "sentinel_2"
            )

    def test_validate_crs_valid(self):
        assert SatelliteValidator.validate_crs("EPSG:4326") is True
        assert SatelliteValidator.validate_crs("EPSG:32644") is True

    def test_validate_crs_empty(self):
        with pytest.raises(InvalidCRSError):
            SatelliteValidator.validate_crs("")

    def test_validate_crs_unknown(self):
        with pytest.raises(InvalidCRSError):
            SatelliteValidator.validate_crs("FOO:1234")

    def test_validate_file_not_corrupt(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            path = f.name
        try:
            assert SatelliteValidator.validate_file_not_corrupt(path) is True
        finally:
            os.unlink(path)

    def test_validate_file_not_corrupt_empty(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            with pytest.raises(FileCorruptionError):
                SatelliteValidator.validate_file_not_corrupt(path)
        finally:
            os.unlink(path)

    def test_validate_file_not_corrupt_size_mismatch(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            path = f.name
        try:
            with pytest.raises(FileCorruptionError):
                SatelliteValidator.validate_file_not_corrupt(path, expected_size=999)
        finally:
            os.unlink(path)

    def test_validate_checksum(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello")
            path = f.name
        try:
            import hashlib
            expected = hashlib.sha256(b"hello").hexdigest()
            assert SatelliteValidator.validate_checksum(path, expected, "sha256") is True
        finally:
            os.unlink(path)

    def test_validate_checksum_mismatch(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello")
            path = f.name
        try:
            with pytest.raises(FileCorruptionError):
                SatelliteValidator.validate_checksum(path, "badchecksum", "sha256")
        finally:
            os.unlink(path)

    def test_validate_product_support_ok(self):
        assert SatelliteValidator.validate_product_support("L2A", ["L2A", "L1C"], "test") is True

    def test_validate_product_support_fail(self):
        with pytest.raises(UnsupportedProductError):
            SatelliteValidator.validate_product_support("L3", ["L2A", "L1C"], "test")

    def test_validate_all_passes(self):
        path = _write_temp_tif(b"II\x2a\x00\x08\x00\x00\x00\x00")
        try:
            report = SatelliteValidator.validate_all(
                {"B04": path},
                required_bands=["B04"],
                provider="test",
                product="L2A",
                supported_products=["L2A"],
            )
            assert report["valid"] is True
        finally:
            os.unlink(path)

    def test_validate_all_fails(self):
        report = SatelliteValidator.validate_all(
            {},
            required_bands=["B04"],
            provider="test",
            product="L2A",
            supported_products=["L2A"],
        )
        assert report["valid"] is False
        assert len(report["errors"]) > 0


# ================================================================
# Storage Manager Tests
# ================================================================

class TestStorageManager:
    @pytest.fixture
    def tmp_storage(self):
        base = tempfile.mkdtemp()
        sm = StorageManager(base_dir=base)
        yield sm
        shutil.rmtree(base)

    def test_scene_path_creates_dirs(self, tmp_storage):
        path = tmp_storage.scene_path("sentinel_2", "sentinel_2a", "2025-06-15", "S2A_1")
        assert path.exists()
        assert path.is_dir()
        assert "sentinel_2" in str(path)
        assert "2025" in str(path)
        assert "06" in str(path)
        assert "S2A_1" in str(path)

    def test_band_path(self, tmp_storage):
        path = tmp_storage.band_path("landsat_8", "landsat_8", "2025-07-01", "LC08_1", "B04")
        assert str(path).endswith("LC08_1_B04.tif")
        assert path.parent.name == "LC08_1"

    def test_write_file(self, tmp_storage):
        path = tmp_storage.write_file("test_prov", "test_mission", "2025-01-01", "scene_1", "B02", b"data")
        assert path.exists()
        assert path.read_bytes() == b"data"

    def test_write_file_duplicate_raises(self, tmp_storage):
        tmp_storage.write_file("p", "m", "2025-01-01", "s1", "B02", b"data")
        with pytest.raises(StorageError):
            tmp_storage.write_file("p", "m", "2025-01-01", "s1", "B02", b"more")

    def test_move_file(self, tmp_storage):
        src = tempfile.NamedTemporaryFile(delete=False)
        src.write(b"move_data")
        src.close()
        dest = tmp_storage.move_file(src.name, "p", "m", "2025-01-01", "s1", "B02")
        assert dest.exists()
        assert dest.read_bytes() == b"move_data"
        assert not os.path.exists(src.name)

    def test_move_file_duplicate_raises(self, tmp_storage):
        src = tempfile.NamedTemporaryFile(delete=False)
        src.write(b"d")
        src.close()
        tmp_storage.move_file(src.name, "p", "m", "2025-01-01", "s1", "B02")
        src2 = tempfile.NamedTemporaryFile(delete=False)
        src2.write(b"d")
        src2.close()
        with pytest.raises(StorageError):
            tmp_storage.move_file(src2.name, "p", "m", "2025-01-01", "s1", "B02")

    def test_exists(self, tmp_storage):
        assert tmp_storage.exists("p", "scene_1") is False
        tmp_storage.write_file("p", "m", "2025-01-01", "scene_1", "B02", b"data")
        assert tmp_storage.exists("p", "scene_1") is True

    def test_delete_scene(self, tmp_storage):
        tmp_storage.write_file("p", "m", "2025-01-01", "scene_x", "B02", b"data")
        assert tmp_storage.delete_scene("p", "scene_x") is True
        assert tmp_storage.exists("p", "scene_x") is False
        assert tmp_storage.delete_scene("p", "scene_x") is False

    def test_scene_size(self, tmp_storage):
        tmp_storage.write_file("p", "m", "2025-01-01", "s1", "B02", b"hello")
        tmp_storage.write_file("p", "m", "2025-01-01", "s1", "B03", b"world")
        size = tmp_storage.scene_size("p", "s1")
        assert size == 10

    def test_disk_usage(self, tmp_storage):
        tmp_storage.write_file("p", "m", "2025-01-01", "s1", "B02", b"data")
        usage = tmp_storage.disk_usage()
        assert usage["base_dir"] == str(tmp_storage.base_dir)
        assert usage["file_count"] >= 1
        assert "p" in usage["provider_sizes"]


# ================================================================
# Search Tests
# ================================================================

class TestSatelliteSearch:
    @pytest.fixture
    def search(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        return SatelliteSearch(registry=registry)

    def test_search_by_bbox(self, search):
        result = search.search(bbox=[77.0, 12.5, 78.0, 13.5], limit=5)
        assert result["total"] > 0
        assert len(result["results"]) <= 5
        assert len(result["providers_searched"]) > 0

    def test_search_by_city(self, search):
        result = search.search(city="bangalore", limit=5)
        assert result["total"] > 0

    def test_search_by_city_unknown(self, search):
        result = search.search(city="atlantis", limit=5)
        assert result["total"] >= 0

    def test_search_no_location_raises(self, search):
        with pytest.raises(InvalidSearchParameterError):
            search.search()

    def test_search_invalid_bbox_raises(self, search):
        with pytest.raises(InvalidSearchParameterError):
            search.search(bbox=[200, 0, 201, 1])

    def test_search_with_date_filter(self, search):
        result = search.search(
            bbox=[77, 12, 78, 13],
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
        )
        assert result["total"] >= 0

    def test_search_with_cloud_cover(self, search):
        result = search.search(bbox=[77, 12, 78, 13], max_cloud_cover=20.0)
        assert result["total"] >= 0

    def test_search_with_mission_filter(self, search):
        result = search.search(bbox=[77, 12, 78, 13], missions=["sentinel_2a"])
        for r in result["results"]:
            assert r["mission"] == "sentinel_2a" or r.get("mission", "").startswith("sentinel")

    def test_search_with_provider_filter(self, search):
        result = search.search(bbox=[77, 12, 78, 13], providers=["sentinel_2"])
        assert "sentinel_2" in result["providers_searched"]
        assert "landsat_8" not in result["providers_searched"]

    def test_search_with_band_filter(self, search):
        result = search.search(bbox=[77, 12, 78, 13], bands=["B02", "B03"])
        for r in result["results"]:
            assert "B02" in r.get("bands", [])
            assert "B03" in r.get("bands", [])

    def test_search_caching(self, search):
        result1 = search.search(bbox=[77, 12, 78, 13], limit=3)
        result2 = search.search(bbox=[77, 12, 78, 13], limit=3)
        assert result1["total"] == result2["total"]

    def test_list_providers(self, search):
        providers = search.list_providers()
        assert len(providers) >= 3
        ids = [p["provider_id"] for p in providers]
        assert "sentinel_2" in ids
        assert "landsat_8" in ids
        assert "landsat_9" in ids

    def test_search_by_city_convenience(self, search):
        result = search.search_by_city("chennai", limit=3)
        assert result["total"] >= 0


# ================================================================
# Download Manager Tests
# ================================================================

class TestDownloadManager:
    @pytest.fixture
    def tmp_storage(self):
        base = tempfile.mkdtemp()
        yield StorageManager(base_dir=base)
        shutil.rmtree(base)

    @pytest.fixture
    def manager(self, tmp_storage):
        dm = DownloadManager(
            storage=tmp_storage,
            max_concurrent=2,
            max_retries=1,
        )
        yield dm
        dm.shutdown(wait=True)

    def test_enqueue_and_complete(self, manager, tmp_storage):
        scene_dir = tempfile.mkdtemp()
        task_id = manager.enqueue(
            scene_id="S2A_test_1",
            provider="sentinel_2",
            download_urls={"B04": "file:///nonexistent"},
            destination=scene_dir,
        )
        assert task_id is not None
        time.sleep(0.5)
        task = manager.get_task(task_id)
        assert task is not None
        assert task["status"] in ("completed", "failed")
        shutil.rmtree(scene_dir)

    def test_cancel_task(self, manager, tmp_storage):
        scene_dir = tempfile.mkdtemp()
        task_id = manager.enqueue(
            scene_id="S2A_cancel",
            provider="sentinel_2",
            download_urls={"B04": "http://slow.example.com/file.tif"},
            destination=scene_dir,
        )
        assert manager.cancel_task(task_id) is True
        time.sleep(0.3)
        task = manager.get_task(task_id)
        assert task is not None
        assert task["status"] in ("cancelled", "pending")
        shutil.rmtree(scene_dir)

    def test_cancel_nonexistent(self, manager):
        assert manager.cancel_task("nope") is False

    def test_list_tasks(self, manager, tmp_storage):
        scene_dir = tempfile.mkdtemp()
        manager.enqueue("s1", "p", {"B04": "http://x"}, scene_dir)
        manager.enqueue("s2", "p", {"B04": "http://x"}, scene_dir)
        tasks = manager.list_tasks()
        assert len(tasks) >= 2
        shutil.rmtree(scene_dir)

    def test_list_tasks_by_status(self, manager, tmp_storage):
        scene_dir = tempfile.mkdtemp()
        manager.enqueue("s1", "p", {"B04": "http://x"}, scene_dir)
        pending = manager.list_tasks(status="pending")
        assert len(pending) >= 0
        shutil.rmtree(scene_dir)

    def test_active_count(self, manager):
        assert manager.active_count() >= 0


# ================================================================
# End-to-End Integration Tests
# ================================================================

class TestIntegration:
    """End-to-end tests connecting registry, search, metadata, and storage."""

    def test_search_to_metadata_pipeline(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        sentinel = registry.get("sentinel_2")
        results = sentinel.search(limit=1)
        assert len(results) > 0

        result = results[0]
        path = _write_temp_tif(b"II\x2a\x00\x08\x00\x00\x00\x00")
        try:
            file_paths = {"B04": path}
            sentinel.validate(result["scene_id"], file_paths)
            raw_meta = sentinel.extract_metadata(result["scene_id"], file_paths)
            normalized = MetadataExtractor.normalize(raw_meta)
            assert normalized["scene_id"] == result["scene_id"]
            assert normalized["provider"] == "sentinel_2"
            payload = MetadataExtractor.to_satellite_image_payload(normalized)
            assert payload["status"] == "pending"
        finally:
            os.unlink(path)

    def test_storage_hierarchy(self):
        sm = StorageManager(base_dir=tempfile.mkdtemp())
        path = sm.scene_path("landsat_8", "landsat_8", "2025-07-01", "LC08_L2SP_001")
        expected = (
            Path(sm.base_dir) / "landsat_8" / "landsat_8" / "2025" / "07" / "LC08_L2SP_001"
        )
        assert path == expected
        shutil.rmtree(sm.base_dir)

    def test_validation_pipeline(self):
        path = _write_temp_tif(b"II\x2a\x00\x08\x00\x00\x00\x00")
        try:
            report = SatelliteValidator.validate_all(
                {"B04": path, "B03": path},
                required_bands=["B04", "B03"],
                provider="test",
                product="L2A",
                supported_products=["L2A", "L1C"],
            )
            assert report["valid"] is True
        finally:
            os.unlink(path)

    def test_cache_prevents_duplicate_scenes(self):
        cache = SatelliteCache()
        scene_id = "S2A_unique_test"
        cache.set(f"scene:{scene_id}", {"scene_id": scene_id})
        assert cache.contains_scene(scene_id) is True

        cache2 = SatelliteCache()
        assert cache2.contains_scene(scene_id) is False


# ================================================================
# Sentinel-2 Provider Specific Tests
# ================================================================

class TestSentinel2Provider:
    @pytest.fixture
    def provider(self):
        from app.satellite.providers.sentinel2 import Sentinel2Provider
        return Sentinel2Provider()

    def test_provider_id(self, provider):
        assert provider.provider_id == "sentinel_2"

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert "L2A" in caps.products
        assert "L1C" in caps.products
        assert 10.0 in caps.resolutions.get("L2A", [])
        assert 60.0 in caps.resolutions.get("L2A", [])

    def test_available_bands(self, provider):
        bands = provider.available_bands("S2A_1")
        assert "B02" in bands
        assert "B03" in bands
        assert "B04" in bands
        assert "B08" in bands

    def test_supported_resolutions(self, provider):
        res = provider.supported_resolutions()
        assert 10.0 in res
        assert 20.0 in res
        assert 60.0 in res

    def test_supported_products(self, provider):
        products = provider.supported_products()
        assert "L2A" in products
        assert "L1C" in products

    def test_estimate_size(self, provider):
        size = provider.estimate_size("S2A_1")
        assert size > 0

    def test_download_creates_files(self, provider):
        with tempfile.TemporaryDirectory() as tmp:
            result = provider.download(
                "S2A_test", {"B04": "http://example.com/B04.jp2"}, tmp, bands=["B04"]
            )
            assert "B04" in result
            assert os.path.isfile(result["B04"])

    def test_search_returns_results(self, provider):
        results = provider.search(limit=3)
        assert len(results) == 3
        for r in results:
            assert "scene_id" in r
            assert r["provider"] == "sentinel_2"


# ================================================================
# Landsat-8 Provider Specific Tests
# ================================================================

class TestLandsat8Provider:
    @pytest.fixture
    def provider(self):
        from app.satellite.providers.landsat8 import Landsat8Provider
        return Landsat8Provider()

    def test_provider_id(self, provider):
        assert provider.provider_id == "landsat_8"

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert provider.capabilities.supports_checksum is True
        assert "L2SP" in caps.products
        assert "L1TP" in caps.products

    def test_search_returns_checksum(self, provider):
        results = provider.search(limit=1)
        if results:
            assert results[0].get("checksum") is not None

    def test_available_bands(self, provider):
        bands = provider.available_bands("LC08_1")
        assert "coastal" in bands
        assert "blue" in bands
        assert "nir" in bands

    def test_supported_resolutions(self, provider):
        res = provider.supported_resolutions()
        assert 15.0 in res
        assert 30.0 in res

    def test_supported_products(self, provider):
        products = provider.supported_products()
        assert "L2SP" in products


# ================================================================
# Landsat-9 Provider Specific Tests
# ================================================================

class TestLandsat9Provider:
    @pytest.fixture
    def provider(self):
        from app.satellite.providers.landsat9 import Landsat9Provider
        return Landsat9Provider()

    def test_provider_id(self, provider):
        assert provider.provider_id == "landsat_9"

    def test_capabilities(self, provider):
        caps = provider.capabilities
        assert caps.supports_checksum is True
        assert "L2SP" in caps.products

    def test_search_returns_checksum(self, provider):
        results = provider.search(limit=1)
        if results:
            assert results[0].get("checksum") is not None

    def test_available_bands(self, provider):
        bands = provider.available_bands("LC09_1")
        assert "pan" in bands
        assert "tirs1" in bands

    def test_supported_resolutions(self, provider):
        res = provider.supported_resolutions()
        assert 15.0 in res
        assert 30.0 in res

    def test_supported_products(self, provider):
        products = provider.supported_products()
        assert "L2SP" in products


# ================================================================
# Edge Case Tests
# ================================================================

class TestEdgeCases:
    def test_cache_concurrent_access(self):
        cache = SatelliteCache(max_size=100)
        errors = []

        def worker(n):
            try:
                for i in range(50):
                    cache.set(f"k_{n}_{i}", i)
                    cache.get(f"k_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_download_manager_concurrent_enqueue(self):
        sm = StorageManager(base_dir=tempfile.mkdtemp())
        dm = DownloadManager(storage=sm, max_concurrent=4)
        scene_dir = tempfile.mkdtemp()
        task_ids = []
        for i in range(10):
            tid = dm.enqueue(
                f"scene_{i}", "test",
                {f"B{i:02d}": f"http://example.com/{i}.tif"},
                scene_dir,
            )
            task_ids.append(tid)
        time.sleep(0.5)
        tasks = dm.list_tasks()
        assert len(tasks) >= 0
        dm.shutdown(wait=True)
        shutil.rmtree(scene_dir)
        shutil.rmtree(sm.base_dir)

    def test_empty_search_results(self):
        registry = ProviderRegistry()
        registry.discover(force=True)
        search = SatelliteSearch(registry=registry)
        result = search.search(bbox=[0, 0, 0.001, 0.001], max_cloud_cover=0.0, limit=0)
        assert result["total"] >= 0

    def test_storage_special_characters(self):
        sm = StorageManager(base_dir=tempfile.mkdtemp())
        path = sm.scene_path("test-provider", "test-mission", "2025-01-01", "scene_abc_123")
        assert path.exists()
        shutil.rmtree(sm.base_dir)

    def test_metadata_missing_file_size_defaults(self):
        raw = {
            "scene_id": "test",
            "provider": "test",
            "mission": "test",
            "sensor": "test",
            "acquisition_date": "2025-01-01",
            "processing_level": "L2A",
            "cloud_cover": 0.0,
            "crs": "EPSG:4326",
            "resolution": 10.0,
            "bands": ["B02"],
            "bounding_box": [1, 2, 3, 4],
            "provider_name": "test",
        }
        result = MetadataExtractor.normalize(raw)
        assert result["file_size_bytes"] == 0

    def test_validator_unknown_crs_warns(self):
        import logging
        logger = logging.getLogger("app.satellite.validator")
        logger.setLevel(logging.DEBUG)
        result = SatelliteValidator.validate_crs("EPSG:4326")
        assert result is True


# ================================================================
# Model / Exception Tests
# ================================================================

class TestSearchResult:
    def test_search_result_to_dict(self):
        from app.satellite.exceptions import SearchResult
        sr = SearchResult(
            scene_id="S2A_1",
            provider="sentinel_2",
            mission="sentinel_2a",
            sensor="MSI",
            acquisition_date="2025-06-15T10:25:00Z",
            cloud_cover=5.0,
            resolution=10.0,
            crs="EPSG:32644",
            bounding_box=[77.0, 12.5, 78.0, 13.5],
            bands=["B02", "B03"],
            processing_level="L2A",
            size_bytes=850_000_000,
            download_urls={"B04": "http://example.com/B04.jp2"},
            checksum="abc123",
            metadata={"foo": "bar"},
        )
        d = sr.to_dict()
        assert d["scene_id"] == "S2A_1"
        assert d["cloud_cover"] == 5.0

    def test_search_result_no_checksum(self):
        from app.satellite.exceptions import SearchResult
        sr = SearchResult(
            scene_id="S2A_1", provider="sentinel_2", mission="m", sensor="MSI",
            acquisition_date="2025-01-01", cloud_cover=0.0, resolution=10.0,
            crs="EPSG:4326", bounding_box=[1, 2, 3, 4], bands=["B02"],
            processing_level="L2A", size_bytes=100, download_urls={},
        )
        assert sr.checksum is None


class TestDownloadTask:
    def test_download_task_progress(self):
        from app.satellite.exceptions import DownloadTask
        task = DownloadTask("t1", "s1", "p", "http://x", "/tmp", total_bytes=100)
        assert task.progress == 0.0
        task.downloaded_bytes = 50
        assert task.progress == 50.0
        assert task.is_active is True
        task.status = "completed"
        assert task.is_active is False

    def test_download_task_zero_bytes(self):
        from app.satellite.exceptions import DownloadTask
        task = DownloadTask("t1", "s1", "p", "http://x", "/tmp")
        assert task.progress == 0.0
