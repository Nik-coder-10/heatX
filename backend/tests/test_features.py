import json
import os
import shutil
import tempfile

import numpy as np
import pytest

from app.features.exceptions import (
    FeatureError, FeatureNotFoundError, ExtractionError,
    FeatureCubeError, ExportError, ValidationError,
    ConfigurationError, MissingDependencyError,
)
from app.features.registry import (
    get, list_features, list_feature_names, list_categories,
    get_dependent_features, FeatureDefinition, FEATURE_REGISTRY,
)
from app.features.configuration import FeaturePipelineConfig
from app.features.feature_cube import GeoFeatureCube
from app.features.extractor import (
    extract_all_features, extract_thermal_features,
    extract_vegetation_features, extract_builtup_features,
    extract_water_features, extract_baresoil_features,
)
from app.features.spatial_features import (
    extract_spatial_features, compute_latitude, compute_longitude, compute_pixel_area,
)
from app.features.terrain_features import extract_terrain_features, compute_slope, compute_aspect
from app.features.temporal_features import extract_temporal_features
from app.features.urban_features import compute_urban_morphology_features
from app.features.quality import compute_quality_features, dataset_quality_report
from app.features.validator import validate_feature_cube, validate_features_consistency
from app.features.statistics import (
    compute_feature_statistics, compute_correlation_matrix, detect_outliers,
)
from app.features.selection import (
    select_features, variance_threshold, correlation_filter,
)
from app.features.metadata import build_feature_metadata
from app.features.exporters import (
    export_cube, to_parquet, to_csv, to_numpy,
)
from app.features.engine import GeoFeatureEngine


WIDTH, HEIGHT = 32, 24
TEST_DIR = None


def setup_module():
    global TEST_DIR
    TEST_DIR = tempfile.mkdtemp(prefix="features_test_")


def teardown_module():
    if TEST_DIR and os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def _raster(seed=42, h=HEIGHT, w=WIDTH, low=0.0, high=1.0):
    rng = np.random.RandomState(seed)
    return rng.uniform(low, high, (h, w)).astype(np.float32)


def _transform():
    from rasterio.transform import from_bounds
    return from_bounds(-1, -1, 1, 1, WIDTH, HEIGHT)


def _default_raster_data(h=HEIGHT, w=WIDTH):
    rng = np.random.RandomState(42)
    return {
        "lst_kelvin": rng.uniform(290, 320, (h, w)).astype(np.float32),
        "brightness_temp": rng.uniform(285, 310, (h, w)).astype(np.float32),
        "emissivity": rng.uniform(0.95, 0.99, (h, w)).astype(np.float32),
        "red": rng.uniform(0.05, 0.3, (h, w)).astype(np.float32),
        "nir": rng.uniform(0.1, 0.5, (h, w)).astype(np.float32),
        "green": rng.uniform(0.05, 0.2, (h, w)).astype(np.float32),
        "blue": rng.uniform(0.02, 0.1, (h, w)).astype(np.float32),
        "swir1": rng.uniform(0.05, 0.4, (h, w)).astype(np.float32),
        "swir2": rng.uniform(0.03, 0.3, (h, w)).astype(np.float32),
    }

class TestExceptions:
    def test_all_subclass_feature_error(self):
        for cls in [FeatureNotFoundError, ExtractionError, FeatureCubeError,
                    ExportError, ValidationError, ConfigurationError,
                    MissingDependencyError]:
            assert issubclass(cls, FeatureError)

    def test_exception_raise(self):
        with pytest.raises(FeatureNotFoundError):
            raise FeatureNotFoundError("test")
        with pytest.raises(ExtractionError):
            raise ExtractionError("test")
        with pytest.raises(ValidationError):
            raise ValidationError("test")

class TestRegistry:
    def test_list_categories(self):
        cats = list_categories()
        assert "thermal" in cats
        assert "vegetation" in cats
        assert "builtup" in cats
        assert "water" in cats
        assert "baresoil" in cats
        assert "spatial" in cats
        assert "temporal" in cats
        assert "quality" in cats

    def test_list_feature_names(self):
        names = list_feature_names()
        assert len(names) == 47
        assert "lst_kelvin" in names
        assert "ndvi" in names
        assert "ndbi" in names

    def test_list_feature_names_by_category(self):
        thermal = list_feature_names("thermal")
        assert len(thermal) == 7
        assert "lst_kelvin" in thermal
        assert "thermal_gradient" in thermal

    def test_get_feature(self):
        fd = get("lst_kelvin")
        assert fd.name == "lst_kelvin"
        assert fd.category == "thermal"
        assert fd.units == "K"
        assert len(fd.dependencies) > 0
        assert fd.scientific_meaning
        assert fd.ml_importance_notes
        assert fd.urban_heat_relevance
        assert fd.limitations
        assert fd.interpretation

    def test_get_feature_not_found(self):
        with pytest.raises(FeatureNotFoundError):
            get("nonexistent_feature")

    def test_get_dependent_features(self):
        deps = get_dependent_features("lst_kelvin")
        assert len(deps) > 0

    def test_vegetation_features(self):
        veg = list_feature_names("vegetation")
        assert "ndvi" in veg
        assert "savi" in veg
        assert "evi" in veg
        assert "msavi" in veg
        assert "gndvi" in veg
        assert "vegetation_fraction" in veg

    def test_urban_features(self):
        urban = list_feature_names("builtup")
        assert "ndbi" in urban
        assert "ibi" in urban
        assert "impervious_surface_pct" in urban

    def test_feature_definition_dataclass(self):
        fd = get("ndvi")
        assert isinstance(fd, FeatureDefinition)
        assert isinstance(fd.expected_range, tuple)
        assert len(fd.expected_range) == 2

class TestConfiguration:
    def test_default_config(self):
        cfg = FeaturePipelineConfig.defaults()
        assert cfg.window_size == 2048
        assert cfg.compute_thermal
        assert cfg.export_format == "parquet"

    def test_from_dict(self):
        cfg = FeaturePipelineConfig.from_dict({"window_size": 512, "compute_vegetation": False})
        assert cfg.window_size == 512
        assert not cfg.compute_vegetation

    def test_from_dict_invalid_key(self):
        with pytest.raises(ConfigurationError):
            FeaturePipelineConfig.from_dict({"invalid_key": 42})

class TestThermalExtraction:
    def test_extract_thermal_features(self):
        lst = _raster(42, low=290, high=320)
        bt = _raster(43, low=285, high=310)
        emis = _raster(44, low=0.95, high=0.99)
        f = extract_thermal_features(lst, bt, emis)
        assert "lst_kelvin" in f
        assert "lst_celsius" in f
        assert "brightness_temperature" in f
        assert "emissivity" in f
        assert "thermal_gradient" in f
        assert "local_temp_variance" in f
        assert "hotspot_distance" in f

    def test_thermal_celsius_from_kelvin(self):
        lst = np.full((4, 4), 300.0, dtype=np.float32)
        f = extract_thermal_features(lst_kelvin=lst)
        np.testing.assert_allclose(f["lst_celsius"], 26.85, rtol=1e-3)

    def test_thermal_gradient_non_negative(self):
        lst = np.random.RandomState(42).uniform(290, 320, (16, 16)).astype(np.float32)
        f = extract_thermal_features(lst_kelvin=lst)
        assert np.all(f["thermal_gradient"] >= 0)

    def test_hotspot_distance_zeros_within_hotspot(self):
        lst = np.full((10, 10), 300.0, dtype=np.float32)
        lst[5, 5] = 350.0
        f = extract_thermal_features(lst_kelvin=lst)
        assert f["hotspot_distance"][5, 5] == 0.0

class TestVegetationExtraction:
    def test_extract_vegetation_features(self):
        rng = np.random.RandomState(42)
        red = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        nir = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        f = extract_vegetation_features(red=red, nir=nir)
        assert "ndvi" in f
        assert "savi" in f
        assert "msavi" in f
        assert "vegetation_fraction" in f

    def test_ndvi_range(self):
        red = np.array([[0.2, 0.3]])
        nir = np.array([[0.5, 0.1]])
        f = extract_vegetation_features(red=red, nir=nir)
        assert -1.0 <= f["ndvi"].min() <= 1.0
        assert -1.0 <= f["ndvi"].max() <= 1.0

    def test_evi_requires_blue(self):
        rng = np.random.RandomState(42)
        red = rng.rand(8, 8).astype(np.float32)
        nir = rng.rand(8, 8).astype(np.float32)
        f = extract_vegetation_features(red=red, nir=nir)
        assert "evi" not in f

    def test_fvc_range(self):
        rng = np.random.RandomState(42)
        red = rng.rand(8, 8).astype(np.float32)
        nir = rng.rand(8, 8).astype(np.float32)
        f = extract_vegetation_features(red=red, nir=nir)
        assert np.all(f["vegetation_fraction"] >= 0)
        assert np.all(f["vegetation_fraction"] <= 1)

class TestBuiltupExtraction:
    def test_extract_builtup_features(self):
        rng = np.random.RandomState(42)
        nir = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        swir1 = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        f = extract_builtup_features(nir=nir, swir1=swir1)
        assert "ndbi" in f
        assert "impervious_surface_pct" in f

    def test_ibi_requires_all_three(self):
        rng = np.random.RandomState(42)
        f = extract_builtup_features(nir=rng.rand(8,8).astype(np.float32),
                                     swir1=rng.rand(8,8).astype(np.float32))
        assert "ibi" not in f

class TestWaterExtraction:
    def test_extract_water_features(self):
        rng = np.random.RandomState(42)
        green = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        nir = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        swir1 = rng.rand(HEIGHT, WIDTH).astype(np.float32)
        f = extract_water_features(green=green, nir=nir, swir1=swir1)
        assert "ndwi" in f
        assert "moisture_index" in f

class TestBaresoilExtraction:
    def test_extract_baresoil_features(self):
        rng = np.random.RandomState(42)
        data = {b: rng.rand(HEIGHT, WIDTH).astype(np.float32) for b in ["red","nir","blue","swir1"]}
        f = extract_baresoil_features(**data)
        assert "bsi" in f
        assert "bare_soil_pct" in f

class TestSpatialFeatures:
    def test_extract_spatial_features(self):
        from rasterio.transform import from_bounds
        t = from_bounds(-1, -1, 1, 1, WIDTH, HEIGHT)
        f = extract_spatial_features(t, HEIGHT, WIDTH)
        assert "latitude" in f
        assert "longitude" in f
        assert "pixel_area" in f
        assert f["latitude"].shape == (HEIGHT, WIDTH)
        assert f["longitude"].shape == (HEIGHT, WIDTH)

class TestTerrainFeatures:
    def test_extract_terrain_features(self):
        elev = np.random.RandomState(42).rand(HEIGHT, WIDTH).astype(np.float32) * 500
        f = extract_terrain_features(elev)
        assert "elevation" in f
        assert "slope" in f
        assert "aspect" in f
        assert np.all(f["slope"] >= 0)
        assert np.all(f["slope"] <= 90)

class TestTemporalFeatures:
    def test_extract_temporal_features(self):
        f = extract_temporal_features(acquisition_date="2024-06-15")
        assert "day_of_year" in f
        assert "month" in f
        assert "season" in f
        assert f["day_of_year"][0] == 167
        assert f["month"][0] == 6
        assert f["season"][0] == 2

class TestUrbanFeatures:
    def test_compute_urban_morphology(self):
        ndbi = _raster(42, low=-0.1, high=0.4)
        ndvi = _raster(43, low=-0.2, high=0.8)
        lst = _raster(44, low=290, high=320)
        f = compute_urban_morphology_features(ndbi=ndbi, ndvi=ndvi, lst_kelvin=lst)
        assert "uhi_intensity" in f
        assert "urban_density_local" in f

class TestQuality:
    def test_compute_quality_features(self):
        qa = np.zeros((8, 8), dtype=np.uint8)
        qa[0:2, 0:2] = 1
        f = compute_quality_features(quality_mask=qa)
        assert "cloud_pct" in f
        assert "missing_pixel_pct" in f
        assert "quality_flags" in f

    def test_confidence_score(self):
        uncert = np.full((8, 8), 1.0, dtype=np.float32)
        f = compute_quality_features(uncertainty=uncert)
        assert "confidence_score" in f
        assert np.all(f["confidence_score"] > 0)

class TestFeatureCube:
    def test_create_cube(self):
        d = _default_raster_data(8, 8)
        cube = GeoFeatureCube(features=d, crs="EPSG:4326", shape=(8, 8))
        assert cube.n_pixels == 64
        assert len(cube.feature_names) == 9
        assert cube.crs == "EPSG:4326"

    def test_to_flat_array(self):
        d = {"a": np.array([[1, 2], [3, 4]], dtype=np.float32),
             "b": np.array([[5, 6], [7, 8]], dtype=np.float32)}
        cube = GeoFeatureCube(features=d)
        flat = cube.to_flat_array()
        assert flat.shape == (4, 2)

    def test_subset(self):
        d = {"a": np.zeros((4, 4)), "b": np.ones((4, 4)), "c": np.full((4, 4), 2)}
        cube = GeoFeatureCube(features=d)
        sub = cube.subset(["a", "c"])
        assert "a" in sub.features
        assert "c" in sub.features
        assert "b" not in sub.features

class TestValidator:
    def test_validate_features_consistency(self):
        d = {"a": np.zeros((4, 4)), "b": np.ones((4, 4))}
        validate_features_consistency(d)

    def test_validate_features_consistency_mismatch(self):
        with pytest.raises(ValidationError):
            validate_features_consistency({"a": np.zeros((4, 4)), "b": np.ones((3, 3))})

    def test_validate_features_consistency_empty(self):
        with pytest.raises(ValidationError):
            validate_features_consistency({})

class TestStatistics:
    def test_compute_feature_statistics(self):
        d = {"a": np.array([[1.0, 2.0], [3.0, 4.0]])}
        stats = compute_feature_statistics(d)
        assert stats["a"]["mean"] == 2.5
        assert stats["a"]["min"] == 1.0
        assert stats["a"]["max"] == 4.0

    def test_correlation_matrix(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0]).reshape(1, -1)
        y = x * 2
        d = {"a": x, "b": y}
        corr = compute_correlation_matrix(d, ["a", "b"])
        assert abs(corr["matrix"][0][1]) > 0.99

    def test_detect_outliers(self):
        rng = np.random.RandomState(42)
        arr = rng.randn(100) * 5 + 50
        arr[0] = 500.0
        d = {"a": arr.reshape(1, -1)}
        out = detect_outliers(d, n_std=2.5)
        assert out["a"] >= 1

class TestSelection:
    def test_variance_threshold(self):
        d = {"a": np.full(100, 5.0), "b": np.random.randn(100)}
        sel = variance_threshold(d, threshold=0.5)
        assert "b" in sel
        assert "a" not in sel

    def test_correlation_filter(self):
        x = np.arange(100).astype(np.float64)
        d = {"a": x, "b": x * 2 + 1, "c": np.random.randn(100)}
        sel = correlation_filter(d, threshold=0.9)
        assert "c" in sel

class TestExporters:
    def test_to_parquet(self):
        pytest.importorskip("pyarrow")
        d = {"a": np.array([[1.0, 2.0], [3.0, 4.0]])}
        cube = GeoFeatureCube(features=d)
        out = os.path.join(TEST_DIR, "test.parquet")
        result = to_parquet(cube, out)
        assert os.path.isfile(result)

    def test_to_csv(self):
        d = {"a": np.array([[1.0, 2.0], [3.0, 4.0]])}
        cube = GeoFeatureCube(features=d)
        out = os.path.join(TEST_DIR, "test.csv")
        result = to_csv(cube, out)
        assert os.path.isfile(result)

    def test_to_numpy(self):
        d = {"a": np.array([[1.0, 2.0], [3.0, 4.0]])}
        cube = GeoFeatureCube(features=d)
        arr = to_numpy(cube)
        assert arr.shape == (4, 1)

    def test_to_numpy_save(self):
        d = {"a": np.array([[1.0, 2.0], [3.0, 4.0]])}
        cube = GeoFeatureCube(features=d)
        out = os.path.join(TEST_DIR, "test.npy")
        to_numpy(cube, path=out)
        assert os.path.isfile(out)

class TestEngine:
    def test_engine_init(self):
        engine = GeoFeatureEngine()
        assert engine.config.window_size == 2048

    def test_engine_init_with_dict(self):
        engine = GeoFeatureEngine({"window_size": 512})
        assert engine.config.window_size == 512

    def test_extract_features_smoke(self):
        engine = GeoFeatureEngine()
        d = _default_raster_data(8, 8)
        f = engine.extract_features(**d)
        assert len(f) > 10

    def test_build_cube(self):
        engine = GeoFeatureEngine()
        d = _default_raster_data(8, 8)
        f = engine.extract_features(**d)
        cube = engine.build_cube(f)
        assert isinstance(cube, GeoFeatureCube)
        assert cube.n_pixels == 64

    def test_run_pipeline(self):
        engine = GeoFeatureEngine({"compute_statistics": True})
        d = _default_raster_data(8, 8)
        from rasterio.transform import from_bounds
        t = from_bounds(-1, -1, 1, 1, 8, 8)
        cube = engine.run_pipeline(**d, transform=t, crs="EPSG:4326")
        assert isinstance(cube, GeoFeatureCube)
        assert "analysis" in cube.metadata

    def test_run_pipeline_with_export(self):
        pytest.importorskip("pyarrow")
        engine = GeoFeatureEngine({"compute_statistics": True})
        d = _default_raster_data(8, 8)
        out = os.path.join(TEST_DIR, "pipeline.parquet")
        cube = engine.run_pipeline(**d, export_path=out, export_format="parquet")
        assert os.path.isfile(out)

    def test_compute_statistics(self):
        engine = GeoFeatureEngine()
        d = _default_raster_data(8, 8)
        f = engine.extract_features(**d)
        cube = engine.build_cube(f)
        stats = engine.compute_statistics(cube)
        assert "statistics" in stats
        assert "correlation" in stats
        assert "quality" in stats

class TestLargeRaster:
    def test_extract_large_raster(self):
        engine = GeoFeatureEngine({"window_size": 64})
        h, w = 128, 128
        d = _default_raster_data(h, w)
        f = engine.extract_features(**d)
        assert len(f) > 10
        for v in f.values():
            assert v.shape[:2] == (h, w)

    def test_cube_large_pixel_count(self):
        h, w = 64, 64
        d = {"a": np.random.randn(h, w).astype(np.float32),
             "b": np.random.randn(h, w).astype(np.float32)}
        cube = GeoFeatureCube(features=d)
        assert cube.n_pixels == h * w

class TestMetadata:
    def test_build_feature_metadata(self):
        meta = build_feature_metadata(47, 9, ["a", "b"], ["thermal", "vegetation"])
        assert meta["n_features"] == 47
        assert meta["n_categories"] == 9
        assert "version" in meta
        assert "processing_timestamp" in meta

class TestIntegration:
    def test_end_to_end(self):
        engine = GeoFeatureEngine({"compute_statistics": True, "run_selection": True})
        d = _default_raster_data(8, 8)
        from rasterio.transform import from_bounds
        t = from_bounds(-1, -1, 1, 1, 8, 8)
        cube = engine.run_pipeline(
            **d, transform=t, crs="EPSG:4326", acquisition_date="2024-06-15",
        )
        assert cube.crs == "EPSG:4326"
        assert "analysis" in cube.metadata
        assert cube.n_pixels == 64
        assert len(cube.feature_names) > 10
        flat = cube.to_flat_array()
        assert flat.shape[0] == 64
        pytest.importorskip("pyarrow")
        out = os.path.join(TEST_DIR, "integration.parquet")
        export_cube(cube, out, format="parquet")
        assert os.path.isfile(out)

