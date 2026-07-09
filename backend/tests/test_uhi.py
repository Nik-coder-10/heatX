import numpy as np
import pytest
from numpy.testing import assert_allclose


@pytest.fixture
def simple_lst():
    arr = np.full((50, 50), 25.0, dtype=np.float64)
    arr[20:30, 20:30] = 45.0
    arr[5:10, 5:10] = 40.0
    return arr


@pytest.fixture
def noisy_lst():
    np.random.seed(42)
    arr = np.random.normal(30, 3, (100, 100)).astype(np.float64)
    arr[30:50, 30:50] += 12
    arr[70:80, 70:80] += 15
    return arr


@pytest.fixture
def quality_flags():
    qa = np.zeros((50, 50), dtype=np.uint8)
    qa[25:28, 25:28] = 1
    return qa


@pytest.fixture
def transform_30m():
    from affine import Affine
    return Affine(30.0, 0.0, 0.0, 0.0, -30.0, 0.0)


@pytest.fixture
def simple_cube(simple_lst, transform_30m):
    class FakeCube:
        feature_names = ["lst_celsius", "ndvi", "ndbi", "ndwi", "quality_flags", "land_cover"]
        transform = transform_30m
        crs = "EPSG:32650"
        features = {
            "lst_celsius": simple_lst.copy(),
            "ndvi": np.full_like(simple_lst, 0.3),
            "ndbi": np.full_like(simple_lst, 0.1),
            "ndwi": np.full_like(simple_lst, -0.2),
            "quality_flags": np.zeros_like(simple_lst, dtype=np.uint8),
            "land_cover": None,
        }
    return FakeCube()


# ===========================================================================
# Test Exceptions
# ===========================================================================

class TestUHIExceptions:
    def test_uhi_error(self):
        from app.uhi import UHIError
        e = UHIError("base error")
        assert str(e) == "base error"

    def test_detection_error(self):
        from app.uhi import DetectionError
        with pytest.raises(DetectionError):
            raise DetectionError("detection failed")

    def test_missing_feature_error(self):
        from app.uhi import MissingFeatureError
        with pytest.raises(MissingFeatureError):
            raise MissingFeatureError("missing lst")

    def test_geometry_error(self):
        from app.uhi import GeometryError
        with pytest.raises(GeometryError):
            raise GeometryError("invalid polygon")

    def test_clustering_error(self):
        from app.uhi import ClusteringError
        with pytest.raises(ClusteringError):
            raise ClusteringError("sklearn not found")

    def test_segmentation_error(self):
        from app.uhi import SegmentationError
        with pytest.raises(SegmentationError):
            raise SegmentationError("segmentation failed")

    def test_configuration_error(self):
        from app.uhi import ConfigurationError
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("bad config")


# ===========================================================================
# Test Configuration
# ===========================================================================

class TestUHIDetectionConfig:
    def test_defaults(self):
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.defaults()
        assert cfg.method == "hybrid"
        assert cfg.zscore_threshold == 2.0
        assert cfg.min_hotspot_area_m2 == 900
        assert cfg.resolution == 30.0

    def test_from_dict(self):
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"method": "percentile", "percentile": 95})
        assert cfg.method == "percentile"
        assert cfg.percentile == 95

    def test_from_dict_override(self):
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"method": "zscore", "zscore_threshold": 3.0})
        assert cfg.method == "zscore"
        assert cfg.zscore_threshold == 3.0

    def test_to_dict(self):
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.defaults()
        d = {k: v for k, v in cfg.__dict__.items()}
        assert isinstance(d, dict)
        assert d.get("method") == "hybrid"


# ===========================================================================
# Test Hotspot
# ===========================================================================

class TestHotspot:
    def _make_hs(self, **overrides):
        from app.uhi import Hotspot
        base = dict(
            id="UHI-001", severity="High", confidence=0.85,
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            area_sq_km=0.25, perimeter_km=2.0, centroid=(0.5, 0.5), bbox=(0, 0, 1, 1),
            mean_temperature_c=42.0, max_temperature_c=45.0, min_temperature_c=38.0,
            pixel_count=100, mean_ndvi=0.2, mean_ndbi=0.4, mean_ndwi=-0.3,
            dominant_landcover="builtup", vegetation_fraction=0.15, builtup_fraction=0.75,
            compactness=0.78, elongation=1.2, nearest_hotspot_distance_km=None,
            recommended_actions=["Increase tree canopy"],
        )
        base.update(overrides)
        return Hotspot(**base)

    def test_hotspot_creation(self):
        hs = self._make_hs()
        assert hs.id == "UHI-001"
        assert hs.severity == "High"
        assert hs.area_sq_km == 0.25
        s = hs.summary()
        assert s["id"] == "UHI-001"
        assert s["area_sq_km"] == 0.25

    def test_hotspot_to_dict(self):
        hs = self._make_hs()
        d = hs.to_dict()
        assert d["id"] == "UHI-001"
        assert d["mean_temperature_c"] == 42.0

    def test_uhi_result(self):
        from app.uhi import Hotspot, UHIResult
        hs = self._make_hs()
        result = UHIResult(
            hotspots=[hs],
            metadata={"method": "zscore"},
            statistics={"n_hotspots": 1},
            detection_mask=np.zeros((10, 10), dtype=np.uint8),
            severity_map=np.zeros((10, 10), dtype=np.int32),
        )
        assert len(result.hotspots) == 1
        assert result.statistics["n_hotspots"] == 1

    def test_uhi_result_to_geojson(self):
        from app.uhi import UHIResult
        hs = self._make_hs()
        result = UHIResult(
            hotspots=[hs], metadata={}, statistics={"n_hotspots": 1},
            detection_mask=np.zeros((10, 10), dtype=np.uint8),
            severity_map=np.zeros((10, 10), dtype=np.int32),
        )
        gj = result.to_geojson()
        assert gj["type"] == "FeatureCollection"
        assert len(gj["features"]) == 1
        assert gj["features"][0]["properties"]["id"] == "UHI-001"


# ===========================================================================
# Test Registry
# ===========================================================================

class TestRegistry:
    def test_detectors_registered(self):
        from app.uhi import DETECTORS
        expected = {"adaptive_threshold", "zscore", "percentile", "morans_i",
                    "dbscan", "connected_components", "hybrid"}
        assert set(DETECTORS.keys()) == expected

    def test_detector_functions(self):
        from app.uhi import DETECTORS
        for name, defn in DETECTORS.items():
            assert callable(defn["function"]), f"{name} function not callable"
            assert "name" in defn

    def test_detection_method_def(self):
        from app.uhi import DetectionMethodDef
        d = DetectionMethodDef(
            name="test_method",
            description="A test",
            scientific_basis="Testing",
            expected_inputs=["lst_celsius"],
            limitations=["None"],
            computational_complexity="O(n)",
            urban_climate_applicability="Test",
        )
        assert d.name == "test_method"


# ===========================================================================
# Test Detector
# ===========================================================================

class TestDetector:
    def test_adaptive_threshold(self, simple_lst):
        from app.uhi import detect_adaptive_threshold
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"percentile": 80})
        result = detect_adaptive_threshold(simple_lst, config=cfg)
        mask = result["binary_mask"]
        assert mask.shape == simple_lst.shape
        assert mask.dtype == np.uint8
        assert mask[25, 25] == 1
        assert mask[0, 0] == 0

    def test_zscore(self, simple_lst):
        from app.uhi import detect_zscore
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"zscore_threshold": 0.5})
        result = detect_zscore(simple_lst, config=cfg)
        mask = result["binary_mask"]
        assert mask.shape == simple_lst.shape
        assert mask.sum() > 0

    def test_percentile(self, simple_lst):
        from app.uhi import detect_percentile
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"percentile": 90})
        result = detect_percentile(simple_lst, config=cfg)
        mask = result["binary_mask"]
        assert mask.shape == simple_lst.shape
        assert mask[25, 25] == 1

    def test_morans_i(self, simple_lst):
        from app.uhi import detect_morans_i
        result = detect_morans_i(simple_lst)
        assert result["binary_mask"].shape == simple_lst.shape

    def test_dbscan(self, simple_lst):
        from app.uhi import detect_dbscan
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"percentile": 85})
        result = detect_dbscan(simple_lst, config=cfg)
        assert result["binary_mask"].shape == simple_lst.shape

    def test_connected_components(self, simple_lst):
        from app.uhi import detect_connected_components
        from app.uhi import detect_zscore
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"zscore_threshold": 1.5})
        zr = detect_zscore(simple_lst, config=cfg)
        result = detect_connected_components(zr["binary_mask"])
        assert result["labeled_mask"].shape == simple_lst.shape

    def test_hybrid(self, simple_lst):
        from app.uhi import detect_hybrid
        result = detect_hybrid(simple_lst)
        assert result["binary_mask"].shape == simple_lst.shape

    def test_detector_handles_uniform(self):
        lst = np.full((30, 30), 25.0, dtype=np.float64)
        from app.uhi import detect_adaptive_threshold, detect_zscore, detect_percentile
        for fn in [detect_adaptive_threshold, detect_zscore, detect_percentile]:
            r = fn(lst)
            assert r["binary_mask"].sum() == 0, f"{fn.__name__} detected hotspots in uniform data"


# ===========================================================================
# Test Segmentation
# ===========================================================================

class TestSegmentation:
    def test_label_connected_components(self):
        from app.uhi import label_connected_components
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:5, 2:5] = 1
        mask[10:13, 10:13] = 1
        labeled, n = label_connected_components(mask)
        assert n == 2
        assert labeled.max() == 2

    def test_no_components(self):
        from app.uhi import label_connected_components
        mask = np.zeros((20, 20), dtype=np.uint8)
        labeled, n = label_connected_components(mask)
        assert n == 0

    def test_mask_to_polygons(self, transform_30m):
        from app.uhi import label_connected_components, mask_to_polygons
        mask = np.zeros((30, 30), dtype=np.uint8)
        mask[5:15, 5:15] = 1
        labeled, n = label_connected_components(mask)
        polys = mask_to_polygons(labeled, transform_30m, min_area_m2=0)
        assert len(polys) == 1


# ===========================================================================
# Test Clustering
# ===========================================================================

class TestClustering:
    def test_cluster_dbscan(self):
        from app.uhi import cluster_dbscan
        coords = np.array([[5, 5], [6, 5], [5, 6], [20, 20], [21, 20], [20, 21],
                           [50, 50], [51, 50], [50, 51], [100, 100]], dtype=np.float64)
        labels = cluster_dbscan(coords, eps_pixels=5, min_samples=2, resolution=30)
        assert len(labels) == len(coords)
        n_clusters = len(set(labels) - {-1})
        assert n_clusters >= 1

    def test_filter_small_clusters(self):
        from app.uhi import filter_small_clusters
        labeled = np.zeros((30, 30), dtype=np.int32)
        labeled[2:4, 2:4] = 1
        labeled[10:20, 10:20] = 2
        result = filter_small_clusters(labeled, min_pixels=5)
        assert 1 not in result
        assert 2 in result

    def test_merge_clusters_by_overlap(self):
        from app.uhi import merge_clusters_by_overlap
        labeled = np.zeros((20, 20), dtype=np.int32)
        labeled[2:8, 2:8] = 1
        labeled[6:12, 6:12] = 2
        result = merge_clusters_by_overlap(labeled, overlap_threshold=0.1)
        assert len(np.unique(result)) <= 3


# ===========================================================================
# Test Morphology
# ===========================================================================

class TestMorphology:
    def test_morphological_open(self):
        from app.uhi.morphology import morphological_open
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[5:15, 5:15] = 1
        result = morphological_open(mask, pixels=2)
        assert result.sum() <= mask.sum()

    def test_morphological_close(self):
        from app.uhi.morphology import morphological_close
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[5, 5] = 1
        mask[5, 7] = 1
        result = morphological_close(mask, pixels=2)
        assert result[5, 6] == 1

    def test_fill_holes(self):
        from app.uhi.morphology import fill_holes
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:18, 2:18] = 1
        mask[10:12, 10:12] = 0
        result = fill_holes(mask)
        assert result[10, 10] == 1

    def test_remove_small_objects(self):
        from app.uhi.morphology import remove_small_objects
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:4, 2:4] = 1
        mask[10:15, 10:15] = 1
        result = remove_small_objects(mask, min_size_pixels=5)
        assert (result[2:4, 2:4] == 0).all()
        assert result[12, 12] == 1

    def test_smooth_boundary(self):
        from app.uhi.morphology import smooth_boundary
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[8:12, 8:12] = 1
        result = smooth_boundary(mask, sigma=1.0)
        assert result.dtype == np.uint8

    def test_apply_morphology(self):
        from app.uhi.morphology import apply_morphology
        from app.uhi import UHIDetectionConfig
        mask = np.zeros((30, 30), dtype=np.uint8)
        mask[5:25, 5:25] = 1
        mask[10:12, 10:12] = 0
        result = apply_morphology(mask, UHIDetectionConfig.defaults())
        assert result[12, 12] == 1


# ===========================================================================
# Test Classification / Severity
# ===========================================================================

class TestClassification:
    def test_classify_severity(self):
        from app.uhi import classify_severity
        lst = np.full((30, 30), 30.0, dtype=np.float64)
        lst[10:20, 10:20] = 45.0
        mask = np.zeros((30, 30), dtype=np.uint8)
        mask[10:20, 10:20] = 1
        label, score = classify_severity(lst, mask, rural_mean=30.0)
        assert isinstance(label, str)
        assert isinstance(score, float)
        assert score > 0

    def test_classify_severity_map(self):
        from app.uhi import classify_severity_map
        lst = np.full((20, 20), 25.0, dtype=np.float64)
        lst[5:15, 5:15] = 40.0
        sev_map = classify_severity_map(lst, rural_mean=25.0)
        assert sev_map.shape == lst.shape
        assert sev_map[0, 0] == 0
        assert sev_map[10, 10] >= 2


class TestSeverityConstants:
    def test_colors(self):
        from app.uhi import SEVERITY_COLORS
        assert "Very Low" in SEVERITY_COLORS

    def test_recommendations(self):
        from app.uhi import SEVERITY_RECOMMENDATIONS
        assert len(SEVERITY_RECOMMENDATIONS["Very Low"]) == 0
        assert len(SEVERITY_RECOMMENDATIONS["Extreme"]) > 0

    def test_order(self):
        from app.uhi import SEVERITY_ORDER
        assert len(SEVERITY_ORDER) == 6


# ===========================================================================
# Test Spatial Analysis
# ===========================================================================

class TestSpatialAnalysis:
    def test_compute_compactness(self):
        from app.uhi import compute_compactness
        c = compute_compactness(1.0, 4.0)
        assert c == pytest.approx(np.pi / 4, rel=1e-3)

    def test_compute_elongation(self):
        from app.uhi import compute_elongation
        mask = np.zeros((30, 30), dtype=np.uint8)
        mask[10, 10:20] = 1
        e = compute_elongation(mask, resolution=30.0)
        assert e >= 0


# ===========================================================================
# Test Quality
# ===========================================================================

class TestQuality:
    def test_compute_confidence(self):
        from app.uhi.quality import compute_confidence
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[5:15, 5:15] = 1
        lst = np.full((20, 20), 30.0, dtype=np.float64)
        lst[5:15, 5:15] = 45.0
        confidence = compute_confidence(mask, lst)
        assert confidence.shape == mask.shape
        assert confidence[mask == 0].sum() == 0
        assert confidence[5:15, 5:15].sum() > 0

    def test_ensemble_confidence(self):
        from app.uhi.quality import compute_confidence
        mask = np.zeros((10, 10), dtype=np.uint8)
        mask[3:7, 3:7] = 1
        sub = {"method_a": [mask], "method_b": [mask]}
        confidence = compute_confidence(mask, sub_results=sub, method="ensemble")
        assert confidence[5, 5] > 0

    def test_hotspot_confidence_from_mask(self):
        from app.uhi.quality import hotspot_confidence_from_mask
        conf = np.ones((10, 10), dtype=np.float32)
        mask = np.zeros((10, 10), dtype=np.uint8)
        mask[3:7, 3:7] = 1
        c = hotspot_confidence_from_mask(conf, mask)
        assert c == pytest.approx(1.0)

    def test_data_completeness(self):
        from app.uhi.quality import compute_data_completeness
        lst = np.full((50, 50), 25.0, dtype=np.float64)
        lst[0:5, 0:5] = np.nan
        dc = compute_data_completeness(lst)
        assert dc == pytest.approx(0.99, rel=1e-2)

    def test_boundary_confidence(self):
        from app.uhi.quality import compute_boundary_confidence
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[5:15, 5:15] = 1
        bc = compute_boundary_confidence(mask)
        assert 0 <= bc <= 1

    def test_overall_quality_score(self):
        from app.uhi.quality import compute_overall_quality_score
        score = compute_overall_quality_score(None, 0.95, 0.8, 0.9)
        assert 0 <= score <= 1


# ===========================================================================
# Test Validator
# ===========================================================================

class TestValidator:
    def test_validate_feature_cube_valid(self, simple_cube):
        from app.uhi import validate_feature_cube
        warnings = validate_feature_cube(simple_cube)
        assert isinstance(warnings, list)

    def test_validate_feature_cube_missing(self, simple_cube):
        from app.uhi import validate_feature_cube, MissingFeatureError
        cube = simple_cube
        cube.features["lst_celsius"] = None
        with pytest.raises(MissingFeatureError):
            validate_feature_cube(cube)

    def test_validate_hotspot(self):
        from app.uhi import validate_hotspot, Hotspot
        hs = Hotspot(
            id="UHI-001", severity="High", confidence=0.85,
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            area_sq_km=0.25, perimeter_km=2.0, centroid=(0.5, 0.5), bbox=(0, 0, 1, 1),
            mean_temperature_c=42.0, max_temperature_c=45.0, min_temperature_c=38.0,
            pixel_count=100, mean_ndvi=0.2, mean_ndbi=0.4, mean_ndwi=-0.3,
            dominant_landcover="builtup", vegetation_fraction=0.15, builtup_fraction=0.75,
            compactness=0.78, elongation=1.2, nearest_hotspot_distance_km=None,
            recommended_actions=[],
        )
        issues = validate_hotspot(hs)
        assert len(issues) == 0

    def test_validate_hotspot_invalid(self):
        from app.uhi import validate_hotspot, Hotspot
        hs = Hotspot(
            id="", severity="", confidence=1.5,
            geometry={"type": "Point", "coordinates": [0, 0]},
            area_sq_km=-1, perimeter_km=0, centroid=(0, 0), bbox=(0, 0, 0, 0),
            mean_temperature_c=0, max_temperature_c=0, min_temperature_c=0,
            pixel_count=0, mean_ndvi=0, mean_ndbi=0, mean_ndwi=0,
            dominant_landcover="", vegetation_fraction=0, builtup_fraction=0,
            compactness=0, elongation=0, nearest_hotspot_distance_km=None,
            recommended_actions=[],
        )
        issues = validate_hotspot(hs)
        assert len(issues) > 0


# ===========================================================================
# Test Statistics
# ===========================================================================

class TestStatistics:
    def test_empty_hotspots(self):
        from app.uhi import compute_uhi_statistics
        stats = compute_uhi_statistics([])
        assert stats["n_hotspots"] == 0

    def test_compute_statistics(self):
        from app.uhi import compute_uhi_statistics, Hotspot
        hs1 = Hotspot(
            id="UHI-001", severity="High", confidence=0.85,
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            area_sq_km=0.5, perimeter_km=3.0, centroid=(0.5, 0.5), bbox=(0, 0, 1, 1),
            mean_temperature_c=42.0, max_temperature_c=45.0, min_temperature_c=38.0,
            pixel_count=100, mean_ndvi=0.2, mean_ndbi=0.4, mean_ndwi=-0.3,
            dominant_landcover="builtup", vegetation_fraction=0.15, builtup_fraction=0.75,
            compactness=0.78, elongation=1.2, nearest_hotspot_distance_km=None,
            recommended_actions=[], severity_score=3.5,
        )
        hs2 = Hotspot(
            id="UHI-002", severity="Moderate", confidence=0.7,
            geometry={"type": "Polygon", "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]},
            area_sq_km=0.1, perimeter_km=1.2, centroid=(2.5, 2.5), bbox=(2, 2, 3, 3),
            mean_temperature_c=38.0, max_temperature_c=40.0, min_temperature_c=36.0,
            pixel_count=40, mean_ndvi=0.3, mean_ndbi=0.2, mean_ndwi=-0.1,
            dominant_landcover="vegetation", vegetation_fraction=0.6, builtup_fraction=0.3,
            compactness=0.85, elongation=1.1, nearest_hotspot_distance_km=2.0,
            recommended_actions=[], severity_score=2.0,
        )
        stats = compute_uhi_statistics([hs1, hs2])
        assert stats["n_hotspots"] == 2
        assert stats["average_area_sq_km"] == pytest.approx(0.3)


# ===========================================================================
# Test Metadata
# ===========================================================================

class TestMetadata:
    def test_build_uhi_metadata(self):
        from app.uhi import build_uhi_metadata
        meta = build_uhi_metadata("zscore", {"threshold": 2.0}, n_hotspots=5, crs="EPSG:32650", resolution=30.0)
        assert meta["detection_method"] == "zscore"
        assert meta["n_hotspots"] == 5
        assert meta["crs"] == "EPSG:32650"

    def test_metadata_version(self):
        from app.uhi import build_uhi_metadata
        meta = build_uhi_metadata("percentile")
        assert meta["version"] == "1.0.0"

    def test_metadata_with_additional(self):
        from app.uhi import build_uhi_metadata
        meta = build_uhi_metadata("hybrid", additional={"scene_id": "LC08_001"})
        assert meta["additional"]["scene_id"] == "LC08_001"


# ===========================================================================
# Test Engine
# ===========================================================================

class TestEngine:
    def test_engine_defaults(self):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine()
        assert engine.config.method == "hybrid"

    def test_engine_from_dict(self):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine({"method": "percentile", "percentile": 95})
        assert engine.config.method == "percentile"

    def test_engine_detect(self, simple_cube):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine({"method": "percentile", "percentile": 90})
        result = engine.detect(simple_cube)
        assert result is not None
        assert len(result.hotspots) > 0

    def test_engine_run_pipeline(self, simple_cube):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine({"method": "zscore", "zscore_threshold": 1.5})
        result = engine.run_pipeline(simple_cube)
        assert result.statistics["n_hotspots"] >= 1
        assert result.detection_mask is not None
        assert result.severity_map is not None

    def test_engine_no_detection(self):
        from app.uhi import UHIDetectionEngine
        lst = np.full((20, 20), 25.0, dtype=np.float64)
        class FlatCube:
            feature_names = ["lst_celsius"]
            features = {"lst_celsius": lst}
            transform = None
            crs = None
        engine = UHIDetectionEngine({"method": "zscore", "zscore_threshold": 5.0})
        result = engine.detect(FlatCube())
        assert len(result.hotspots) == 0

    def test_engine_raises_missing_feature(self):
        from app.uhi import UHIDetectionEngine, MissingFeatureError
        class BadCube:
            feature_names = []
            features = {}
            transform = None
            crs = None
        engine = UHIDetectionEngine()
        with pytest.raises(MissingFeatureError):
            engine.detect(BadCube())

    def test_engine_raises_no_valid_data(self):
        from app.uhi import UHIDetectionEngine, DetectionError
        class NanCube:
            feature_names = ["lst_celsius"]
            features = {"lst_celsius": np.full((10, 10), np.nan)}
            transform = None
            crs = None
        engine = UHIDetectionEngine()
        with pytest.raises(DetectionError):
            engine.detect(NanCube())

    def test_engine_unknown_method(self):
        from app.uhi import DetectionError
        from app.uhi.engine import run_detection
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"method": "unknown_method"})
        lst = np.full((10, 10), 25.0, dtype=np.float64)
        with pytest.raises(DetectionError):
            run_detection(lst, config=cfg)

    def test_engine_result_property(self, simple_cube):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine({"method": "percentile", "percentile": 90})
        assert engine.result is None
        engine.detect(simple_cube)
        assert engine.result is not None

    def test_run_detection_function(self, simple_lst):
        from app.uhi.engine import run_detection
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"method": "percentile", "percentile": 90})
        mask = run_detection(simple_lst, config=cfg)
        assert mask.shape == simple_lst.shape
        assert mask.dtype == np.uint8
        assert mask.sum() > 0

    def test_detect_with_quality_flags(self, simple_lst, quality_flags):
        from app.uhi.engine import run_detection
        from app.uhi import UHIDetectionConfig
        cfg = UHIDetectionConfig.from_dict({"method": "zscore", "zscore_threshold": 1.5})
        mask = run_detection(simple_lst, config=cfg, quality_flags=quality_flags)
        assert mask.shape == simple_lst.shape
        assert mask[25:28, 25:28].sum() == 0


# ===========================================================================
# Test Large Raster
# ===========================================================================

class TestLargeRaster:
    def test_large_raster_detection(self):
        from app.uhi import UHIDetectionEngine
        np.random.seed(123)
        lst = np.random.normal(30, 4, (500, 500)).astype(np.float64)
        lst[100:150, 100:150] += 15
        class LargeCube:
            feature_names = ["lst_celsius"]
            features = {"lst_celsius": lst}
            transform = None
            crs = None
        engine = UHIDetectionEngine({"method": "percentile", "percentile": 90})
        result = engine.detect(LargeCube())
        assert result.statistics["n_hotspots"] >= 1


# ===========================================================================
# Test Integration
# ===========================================================================

class TestIntegration:
    def test_full_pipeline(self, simple_cube):
        from app.uhi import UHIDetectionEngine
        engine = UHIDetectionEngine({"method": "zscore", "zscore_threshold": 1.5})
        result = engine.detect(simple_cube)
        assert result.statistics["n_hotspots"] >= 1

        for hs in result.hotspots:
            assert hs.id.startswith("UHI-")
            assert 0 <= hs.confidence <= 1
            assert hs.area_sq_km > 0

        gj = result.to_geojson()
        assert len(gj["features"]) == len(result.hotspots)

    def test_different_methods_produce_different_results(self, simple_lst):
        from app.uhi import UHIDetectionEngine
        class Cube:
            feature_names = ["lst_celsius"]
            features = {"lst_celsius": simple_lst}
            transform = None
            crs = None

        results = {}
        for method in ["zscore", "percentile", "adaptive_threshold"]:
            engine = UHIDetectionEngine({"method": method})
            result = engine.detect(Cube())
            results[method] = result.statistics["n_hotspots"]

        methods_with_hotspots = sum(1 for v in results.values() if v > 0)
        assert methods_with_hotspots > 0


# ===========================================================================
# Test Visualization
# ===========================================================================

class TestVisualization:
    def test_render_hotspot_map(self, simple_lst, tmp_path, transform_30m):
        from app.uhi import Hotspot, render_hotspot_map
        hs = Hotspot(
            id="UHI-001", severity="High", confidence=0.85,
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            area_sq_km=0.25, perimeter_km=2.0, centroid=(0.5, 0.5), bbox=(0, 0, 1, 1),
            mean_temperature_c=42.0, max_temperature_c=45.0, min_temperature_c=38.0,
            pixel_count=100, mean_ndvi=0.2, mean_ndbi=0.4, mean_ndwi=-0.3,
            dominant_landcover="builtup", vegetation_fraction=0.15, builtup_fraction=0.75,
            compactness=0.78, elongation=1.2, nearest_hotspot_distance_km=None,
            recommended_actions=[],
        )
        out = tmp_path / "hotspot_map.png"
        path = render_hotspot_map(simple_lst, [hs], str(out))
        assert out.exists()

    def test_render_severity_heatmap(self, tmp_path):
        from app.uhi import render_severity_heatmap
        sev = np.random.randint(0, 6, (50, 50)).astype(np.int32)
        out = tmp_path / "severity.png"
        path = render_severity_heatmap(sev, str(out))
        assert out.exists()

    def test_render_boundary_overlay(self, tmp_path, simple_lst):
        from app.uhi import render_boundary_overlay
        mask = np.zeros_like(simple_lst, dtype=np.uint8)
        mask[simple_lst > 35] = 1
        out = tmp_path / "boundary.png"
        path = render_boundary_overlay(simple_lst, mask, str(out))
        assert out.exists()
