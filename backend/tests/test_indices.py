import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from app.indices.exceptions import (
    IndexNotFoundError,
    MissingBandError,
    DimensionMismatchError,
    CRSMismatchError,
    ComputationError,
    ClassificationError,
    InvalidRangeError,
)
from app.indices.registry import (
    get_index,
    list_indices,
    list_index_names,
    IndexDefinition,
)
from app.indices.calculator import (
    ndvi, savi, evi, msavi, ndbi, ibi, ui,
    ndwi, mndwi, ndmi, bsi, ndisi, gndvi,
    compute_index,
)
from app.indices.validator import (
    check_bands_exist, check_band_paths,
    check_dimensions, check_crs_consistency,
    check_nodata, check_range,
)
from app.indices.statistics import (
    compute_statistics, compute_histogram, compute_percentiles,
)
from app.indices.classification import (
    classify, write_classification, classification_report, get_scheme,
)
from app.indices.visualization import (
    apply_colormap, get_colormap, write_png, write_geotiff,
)
from app.indices.metadata import generate_metadata
from app.indices.engine import (
    SpectralIndicesEngine,
    resolve_band_key,
    resolve_band_path,
    build_band_map,
    BAND_ALIASES,
    health_report,
)

WIDTH, HEIGHT = 64, 48
CRS_EPSG = "EPSG:4326"
TEST_DIR = None


def setup_module():
    global TEST_DIR
    TEST_DIR = tempfile.mkdtemp(prefix="indices_test_")


def teardown_module():
    if TEST_DIR and os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def _create_band(path, data=None, width=WIDTH, height=HEIGHT, dtype=np.float32,
                 crs=CRS_EPSG, nodata=None):
    if data is None:
        data = np.random.RandomState(42).rand(height, width).astype(dtype)
    elif data.ndim == 2:
        pass
    transform = from_bounds(-1.0, -1.0, 1.0, 1.0, width, height)
    profile = {
        "driver": "GTiff", "width": width, "height": height, "count": 1,
        "dtype": dtype, "crs": crs, "transform": transform,
        "compress": "lzw", "tiled": True, "blockxsize": 64, "blockysize": 64,
    }
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        if data.ndim == 2:
            dst.write(data[np.newaxis, ...])
        else:
            dst.write(data)
    return str(path)


def _make_bands(band_names, values=None, nodata=None):
    paths = {}
    for i, name in enumerate(band_names):
        p = os.path.join(TEST_DIR, f"band_{name}_{uuid.uuid4().hex}.tif")
        if values and name in values:
            _create_band(p, data=values[name], nodata=nodata)
        else:
            _create_band(p, nodata=nodata)
        paths[name] = p
    return paths


def _constant_band(value, h=HEIGHT, w=WIDTH):
    return np.full((h, w), value, dtype=np.float64)


# ================================================================
# Registry Tests
# ================================================================

class TestRegistry:
    def test_get_index_exists(self):
        idx = get_index("NDVI")
        assert idx.name == "NDVI"
        assert "nir" in idx.required_bands
        assert "red" in idx.required_bands

    def test_get_index_case_insensitive(self):
        idx = get_index("ndvi")
        assert idx.name == "NDVI"

    def test_get_index_not_found(self):
        with pytest.raises(IndexNotFoundError):
            get_index("NONEXISTENT_INDEX")

    def test_list_indices_all(self):
        indices = list_indices()
        assert len(indices) >= 13

    def test_list_indices_by_tag(self):
        veg = list_indices("vegetation")
        assert any(i.name == "NDVI" for i in veg)
        urban = list_indices("urban")
        assert any(i.name == "NDBI" for i in urban)

    def test_list_index_names(self):
        names = list_index_names()
        assert "NDVI" in names
        assert "NDBI" in names
        assert "NDWI" in names

    def test_index_definition_all_fields(self):
        idx = get_index("EVI")
        assert idx.formula
        assert idx.description
        assert idx.interpretation
        assert idx.urban_heat_relevance
        assert idx.limitations
        assert idx.common_misuse
        assert len(idx.required_bands) >= 3

    def test_all_indices_have_required_fields(self):
        for idx in list_indices():
            assert idx.name, f"Missing name in {idx}"
            assert idx.formula, f"Missing formula in {idx.name}"
            assert idx.description, f"Missing description in {idx.name}"
            assert idx.required_bands, f"Missing required_bands in {idx.name}"
            assert idx.value_range, f"Missing value_range in {idx.name}"
            assert idx.tags, f"Missing tags in {idx.name}"

    def test_index_value_ranges_valid(self):
        for idx in list_indices():
            lo, hi = idx.value_range
            assert lo < hi, f"Invalid range for {idx.name}: ({lo}, {hi})"


# ================================================================
# Calculator Tests
# ================================================================

class TestCalculator:
    def test_ndvi(self):
        nir = _constant_band(0.8)
        red = _constant_band(0.2)
        result = ndvi(nir, red)
        assert np.allclose(result, 0.6, atol=1e-10)
        assert result.dtype == np.float64

    def test_ndvi_negative(self):
        nir = _constant_band(0.1)
        red = _constant_band(0.5)
        result = ndvi(nir, red)
        assert result[0, 0] < 0

    def test_ndvi_zero_divisor(self):
        nir = np.zeros((10, 10), dtype=np.float64)
        red = np.zeros((10, 10), dtype=np.float64)
        result = ndvi(nir, red)
        assert result[0, 0] == 0.0

    def test_ndvi_clipped(self):
        nir = _constant_band(1000.0)
        red = _constant_band(-1000.0)
        result = ndvi(nir, red)
        assert -1.0 <= result.min() <= result.max() <= 1.0

    def test_savi_default_L(self):
        nir = _constant_band(0.8)
        red = _constant_band(0.2)
        result = savi(nir, red)
        expected = (0.8 - 0.2) / (0.8 + 0.2 + 0.5) * 1.5
        assert np.allclose(result, expected, atol=1e-10)

    def test_savi_custom_L(self):
        nir = _constant_band(0.8)
        red = _constant_band(0.2)
        result = savi(nir, red, L=1.0)
        expected = (0.8 - 0.2) / (0.8 + 0.2 + 1.0) * 2.0
        assert np.allclose(result, expected, atol=1e-10)

    def test_evi(self):
        nir = _constant_band(0.8)
        red = _constant_band(0.2)
        blue = _constant_band(0.1)
        result = evi(nir, red, blue)
        expected = 2.5 * (0.8 - 0.2) / (0.8 + 6*0.2 - 7.5*0.1 + 1)
        assert np.allclose(result, expected, atol=1e-10)

    def test_msavi(self):
        nir = _constant_band(0.8)
        red = _constant_band(0.2)
        result = msavi(nir, red)
        assert -1.0 <= result[0, 0] <= 1.0

    def test_msavi_high_vegetation(self):
        nir = _constant_band(0.9)
        red = _constant_band(0.1)
        result = msavi(nir, red)
        assert result[0, 0] > 0

    def test_ndbi(self):
        swir1 = _constant_band(0.6)
        nir = _constant_band(0.3)
        result = ndbi(swir1, nir)
        assert np.allclose(result, (0.6-0.3)/(0.6+0.3), atol=1e-10)

    def test_ibi(self):
        nir = _constant_band(0.3)
        red = _constant_band(0.2)
        swir1 = _constant_band(0.6)
        green = _constant_band(0.4)
        result = ibi(nir, red, swir1, green)
        assert -1.0 <= result[0, 0] <= 1.0

    def test_ui(self):
        swir2 = _constant_band(0.5)
        nir = _constant_band(0.3)
        result = ui(swir2, nir)
        assert abs(result[0, 0] - 0.25) < 1e-10

    def test_ndwi(self):
        green = _constant_band(0.4)
        nir = _constant_band(0.1)
        result = ndwi(green, nir)
        assert np.allclose(result, (0.4-0.1)/(0.4+0.1), atol=1e-10)

    def test_mndwi(self):
        green = _constant_band(0.4)
        swir1 = _constant_band(0.1)
        result = mndwi(green, swir1)
        assert np.allclose(result, (0.4-0.1)/(0.4+0.1), atol=1e-10)

    def test_ndmi(self):
        nir = _constant_band(0.7)
        swir1 = _constant_band(0.3)
        result = ndmi(nir, swir1)
        assert np.allclose(result, (0.7-0.3)/(0.7+0.3), atol=1e-10)

    def test_bsi(self):
        swir1 = _constant_band(0.6)
        red = _constant_band(0.4)
        nir = _constant_band(0.2)
        blue = _constant_band(0.1)
        result = bsi(swir1, red, nir, blue)
        expected = ((0.6+0.4) - (0.2+0.1)) / ((0.6+0.4) + (0.2+0.1))
        assert np.allclose(result, expected, atol=1e-10)

    def test_ndisi(self):
        tir = _constant_band(300.0)
        nir = _constant_band(0.3)
        swir1 = _constant_band(0.4)
        swir2 = _constant_band(0.2)
        result = ndisi(tir, nir, swir1, swir2)
        assert -1.0 <= result[0, 0] <= 1.0

    def test_gndvi(self):
        nir = _constant_band(0.8)
        green = _constant_band(0.3)
        result = gndvi(nir, green)
        assert np.allclose(result, (0.8-0.3)/(0.8+0.3), atol=1e-10)

    def test_compute_index_by_name(self):
        arrays = {"nir": _constant_band(0.8), "red": _constant_band(0.2)}
        result = compute_index("ndvi", arrays)
        assert np.allclose(result, 0.6, atol=1e-10)

    def test_compute_index_missing_band(self):
        with pytest.raises(ComputationError):
            compute_index("ndvi", {"nir": np.ones((10, 10))})

    def test_compute_index_unknown(self):
        with pytest.raises(ComputationError):
            compute_index("unknown_idx", {})

    def test_compute_index_savi_with_L(self):
        arrays = {"nir": _constant_band(0.8), "red": _constant_band(0.2)}
        result = compute_index("savi", arrays, L=1.0)
        assert result[0, 0] > 0


# ================================================================
# Band Aliasing Tests
# ================================================================

class TestBandMapping:
    def test_resolve_band_key_sentinel2(self):
        assert resolve_band_key("B8", "sentinel2") == "nir"
        assert resolve_band_key("B4", "sentinel2") == "red"
        assert resolve_band_key("B3", "sentinel2") == "green"
        assert resolve_band_key("B11", "sentinel2") == "swir1"
        assert resolve_band_key("B12", "sentinel2") == "swir2"

    def test_resolve_band_key_landsat(self):
        assert resolve_band_key("Band5", "landsat8") == "nir"
        assert resolve_band_key("Band4", "landsat8") == "red"
        assert resolve_band_key("Band6", "landsat8") == "swir1"

    def test_resolve_band_key_common_names(self):
        assert resolve_band_key("near_infrared") == "nir"
        assert resolve_band_key("NearInfrared") == "nir"
        assert resolve_band_key("swir1") == "swir1"
        assert resolve_band_key("thermal") == "tir"

    def test_resolve_band_path_direct(self):
        paths = {"nir": "/path/to/nir.tif"}
        assert resolve_band_path("nir", paths) == "/path/to/nir.tif"

    def test_resolve_band_path_provider(self):
        paths = {"B8": "/path/to/b8.tif"}
        assert resolve_band_path("nir", paths, "sentinel2") == "/path/to/b8.tif"

    def test_resolve_band_path_alias(self):
        paths = {"near_infrared": "/path/to/nir.tif"}
        assert resolve_band_path("nir", paths) == "/path/to/nir.tif"

    def test_resolve_band_path_not_found(self):
        assert resolve_band_path("nir", {"red": "/r.tif"}) is None

    def test_build_band_map(self):
        paths = {"B8": "/b8.tif", "B4": "/b4.tif"}
        result = build_band_map(paths, ["nir", "red"], "sentinel2")
        assert "nir" in result
        assert "red" in result
        assert result["nir"] == "/b8.tif"

    def test_build_band_map_missing(self):
        with pytest.raises(MissingBandError):
            build_band_map({"B8": "/b8.tif"}, ["nir", "red", "blue"], "sentinel2")


# ================================================================
# Validator Tests
# ================================================================

class TestValidator:
    def test_check_bands_exist_ok(self):
        paths = _make_bands(["nir", "red"])
        check_bands_exist(paths, ["nir", "red"])

    def test_check_bands_exist_missing(self):
        with pytest.raises(MissingBandError):
            check_bands_exist({"nir": "/n.tif"}, ["nir", "red"])

    def test_check_dimensions_ok(self):
        paths = _make_bands(["nir", "red"])
        infos = check_band_paths(paths)
        check_dimensions(infos)

    def test_check_dimensions_mismatch(self):
        p1 = os.path.join(TEST_DIR, f"dim_b1_{uuid.uuid4().hex}.tif")
        p2 = os.path.join(TEST_DIR, f"dim_b2_{uuid.uuid4().hex}.tif")
        _create_band(p1, width=64, height=48)
        _create_band(p2, width=32, height=24)
        infos = check_band_paths({"b1": p1, "b2": p2})
        with pytest.raises(DimensionMismatchError):
            check_dimensions(infos)

    def test_check_crs_consistency_ok(self):
        paths = _make_bands(["nir", "red"])
        infos = check_band_paths(paths)
        check_crs_consistency(infos)

    def test_check_crs_consistency_mismatch(self):
        p1 = os.path.join(TEST_DIR, f"crs_b1_{uuid.uuid4().hex}.tif")
        p2 = os.path.join(TEST_DIR, f"crs_b2_{uuid.uuid4().hex}.tif")
        _create_band(p1, crs="EPSG:4326")
        _create_band(p2, crs="EPSG:3857")
        infos = check_band_paths({"b1": p1, "b2": p2})
        with pytest.raises(CRSMismatchError):
            check_crs_consistency(infos)

    def test_check_nodata_all_valid(self):
        data = np.ones((48, 64), dtype=np.float64)
        result = check_nodata(data, None)
        assert result["invalid_pct"] == 0.0

    def test_check_nodata_with_nans(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[0, 0] = np.nan
        result = check_nodata(data, None)
        assert result["invalid_pixels"] == 1

    def test_check_range_in_range(self):
        data = np.array([[0.3], [0.5]], dtype=np.float64)
        result = check_range(data, (-1.0, 1.0))
        assert result["in_range"] is True

    def test_check_range_out_of_range(self):
        data = np.array([[100.0]], dtype=np.float64)
        with pytest.raises(InvalidRangeError):
            check_range(data, (-1.0, 1.0))


# ================================================================
# Statistics Tests
# ================================================================

class TestStatistics:
    def test_compute_statistics_basic(self):
        data = np.linspace(0, 1, 100).reshape(10, 10)
        stats = compute_statistics(data)
        assert abs(stats["min"]) < 1e-10
        assert abs(stats["max"] - 1.0) < 1e-10
        assert abs(stats["mean"] - 0.5) < 0.1
        assert stats["valid_pct"] == 100.0

    def test_compute_statistics_with_nodata(self):
        data = np.ones((10, 10), dtype=np.float64)
        data[0, 0] = -9999.0
        stats = compute_statistics(data, nodata=-9999.0)
        assert stats["invalid_pixel_count"] == 1
        assert stats["valid_pixel_count"] == 99

    def test_compute_histogram(self):
        data = np.random.RandomState(42).rand(100, 100)
        hist = compute_histogram(data, bins=10)
        assert hist["bins"] == 10
        assert len(hist["counts"]) == 10

    def test_compute_percentiles(self):
        data = np.linspace(0, 1, 1000).reshape(50, 20)
        p = compute_percentiles(data, [50])
        assert 0.45 < p[50] < 0.55


# ================================================================
# Classification Tests
# ================================================================

class TestClassification:
    def test_classify_ndvi(self):
        data = np.array([[0.1, 0.4], [0.6, -0.1]], dtype=np.float64)
        scheme = get_scheme("ndvi")
        result = classify(data, scheme)
        assert result[0, 0] == 2
        assert result[0, 1] == 4
        assert result[1, 0] == 5
        assert result[1, 1] == 1

    def test_classify_ndbi(self):
        data = np.array([[-0.1, 0.2], [0.4, -0.3]], dtype=np.float64)
        scheme = get_scheme("ndbi")
        result = classify(data, scheme)
        assert result[0, 0] == 1
        assert result[0, 1] == 3

    def test_classify_unknown_scheme(self):
        with pytest.raises(ClassificationError):
            get_scheme("unknown_index")

    def test_classification_report(self):
        data = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        scheme = get_scheme("ndvi")
        report = classification_report(data, scheme)
        assert "total_pixels" in report
        assert "classes" in report

    def test_write_classification_creates_file(self):
        data = np.ones((10, 10), dtype=np.uint8)
        path = os.path.join(TEST_DIR, "class_test.tif")
        profile = {"driver": "GTiff", "width": 10, "height": 10, "count": 1,
                   "dtype": "float32", "crs": CRS_EPSG,
                   "transform": from_bounds(-1, -1, 1, 1, 10, 10)}
        scheme = get_scheme("ndvi")
        result = write_classification(data, path, profile, scheme)
        assert os.path.isfile(result)


# ================================================================
# Visualization Tests
# ================================================================

class TestVisualization:
    def test_get_colormap(self):
        cmap = get_colormap("ndvi")
        assert len(cmap) >= 5

    def test_get_colormap_fallback(self):
        cmap = get_colormap("unknown")
        assert len(cmap) == 3

    def test_apply_colormap(self):
        data = np.array([[0.0, 0.5], [-0.5, 1.0]], dtype=np.float64)
        cmap = get_colormap("ndvi")
        rgb = apply_colormap(data, cmap)
        assert rgb.shape == (3, 2, 2)
        assert rgb.dtype == np.uint8

    def test_apply_colormap_with_nodata(self):
        data = np.array([[0.5, np.nan]], dtype=np.float64)
        cmap = get_colormap("ndvi")
        rgb = apply_colormap(data, cmap, nodata=-9999.0)
        assert rgb.shape == (3, 1, 2)

    def test_write_png_creates_file(self):
        rgb = np.zeros((3, 10, 10), dtype=np.uint8)
        rgb[0] = 255
        path = os.path.join(TEST_DIR, "test.png")
        result = write_png(rgb, path)
        assert os.path.isfile(result)

    def test_write_geotiff(self):
        data = np.random.rand(10, 10).astype(np.float32)
        path = os.path.join(TEST_DIR, "viz_geotiff.tif")
        profile = {"driver": "GTiff", "width": 10, "height": 10, "count": 1,
                   "dtype": "float32", "crs": CRS_EPSG,
                   "transform": from_bounds(-1, -1, 1, 1, 10, 10)}
        result = write_geotiff(data, path, profile, "TEST")
        assert os.path.isfile(result)
        with rasterio.open(result) as src:
            assert src.tags().get("algorithm") == "TEST"


# ================================================================
# Metadata Tests
# ================================================================

class TestMetadata:
    def test_generate_metadata(self):
        paths = _make_bands(["nir", "red"])
        meta = generate_metadata("NDVI", paths)
        assert meta["algorithm"] == "NDVI"
        assert "(NIR - Red)" in meta["formula"]
        assert meta["source_band_count"] == 2
        assert meta["crs"] == "EPSG:4326"
        assert meta["width"] == WIDTH
        assert meta["height"] == HEIGHT
        assert meta["provider_independent"] is True

    def test_generate_metadata_with_band_map(self):
        paths = _make_bands(["nir", "red"])
        meta = generate_metadata("NDVI", paths, band_map={"nir": paths["nir"]})
        assert "band_mapping" in meta

    def test_generate_metadata_with_output_path(self):
        paths = _make_bands(["nir", "red"])
        meta = generate_metadata("NDVI", paths, output_path="/out/ndvi.tif")
        assert meta["output_path"] == str(Path("/out/ndvi.tif").absolute())


# ================================================================
# Engine Tests
# ================================================================

class TestEngine:
    def test_compute_ndvi_from_files(self):
        paths = _make_bands(["nir", "red"])
        with rasterio.open(paths["nir"]) as src:
            nir_data = src.read(1)
        with rasterio.open(paths["red"]) as src:
            red_data = src.read(1)
        nir_data[:] = 0.8
        red_data[:] = 0.2
        with rasterio.open(paths["nir"], "r+") as src:
            src.write(nir_data, 1)
        with rasterio.open(paths["red"], "r+") as src:
            src.write(red_data, 1)

        engine = SpectralIndicesEngine(window_size=32)
        out_path = os.path.join(TEST_DIR, "engine_ndvi.tif")
        result = engine.compute("NDVI", paths, out_path)
        assert "output_path" in result
        assert os.path.isfile(result["output_path"])
        assert "quality" in result
        assert result["quality"]["quality_score"] >= 50

    def test_compute_with_quality(self):
        paths = _make_bands(["nir", "red", "blue"])
        engine = SpectralIndicesEngine(window_size=32)
        result = engine.compute("EVI", paths)
        assert "quality" in result
        assert "quality_score" in result["quality"]
        assert "confidence_score" in result["quality"]
        assert "statistics" in result["quality"]

    def test_compute_batch(self):
        paths = _make_bands(["nir", "red", "green", "swir1"])
        engine = SpectralIndicesEngine(window_size=32)
        out_dir = os.path.join(TEST_DIR, "batch_out")
        results = engine.compute_batch(["NDVI", "NDWI"], paths, out_dir)
        assert "NDVI" in results
        assert "NDWI" in results

    def test_compute_with_classification(self):
        paths = _make_bands(["nir", "red"])
        nir_path = paths["nir"]
        red_path = paths["red"]
        with rasterio.open(nir_path, "r+") as src:
            src.write(np.full((1, HEIGHT, WIDTH), 0.8, dtype=np.float32))
        with rasterio.open(red_path, "r+") as src:
            src.write(np.full((1, HEIGHT, WIDTH), 0.2, dtype=np.float32))

        engine = SpectralIndicesEngine(window_size=32)
        out_path = os.path.join(TEST_DIR, "engine_classify.tif")
        result = engine.compute("NDVI", paths, out_path, classification=True)
        assert "classification" in result

    def test_compute_with_colorized(self):
        paths = _make_bands(["nir", "red"])
        engine = SpectralIndicesEngine(window_size=32)
        out_path = os.path.join(TEST_DIR, "engine_colorized.tif")
        result = engine.compute("NDVI", paths, out_path, colorized=True)
        assert "colorized" in result

    def test_compute_with_provider_mapping(self):
        paths = {"B8": os.path.join(TEST_DIR, f"nir_{uuid.uuid4().hex}.tif"),
                 "B4": os.path.join(TEST_DIR, f"red_{uuid.uuid4().hex}.tif")}
        _create_band(paths["B8"])
        _create_band(paths["B4"])
        engine = SpectralIndicesEngine()
        out_path = os.path.join(TEST_DIR, "engine_provider.tif")
        result = engine.compute("NDVI", paths, out_path, provider="sentinel2")
        assert os.path.isfile(result["output_path"])

    def test_compute_all_indices(self):
        band_sets = {
            "NDVI": ["nir", "red"],
            "SAVI": ["nir", "red"],
            "EVI": ["nir", "red", "blue"],
            "MSAVI": ["nir", "red"],
            "NDBI": ["swir1", "nir"],
            "NDWI": ["green", "nir"],
            "MNDWI": ["green", "swir1"],
            "NDMI": ["nir", "swir1"],
            "GNDVI": ["nir", "green"],
            "UI": ["swir2", "nir"],
        }
        engine = SpectralIndicesEngine(window_size=32)
        for idx_name, req_bands in band_sets.items():
            paths = _make_bands(req_bands)
            try:
                result = engine.compute(idx_name, paths)
                assert "quality" in result
            except Exception as e:
                pytest.fail(f"{idx_name} failed: {e}")

    def test_metadata_written_to_output(self):
        paths = _make_bands(["nir", "red"])
        engine = SpectralIndicesEngine(window_size=32)
        out_path = os.path.join(TEST_DIR, "engine_meta.tif")
        result = engine.compute("NDVI", paths, out_path)
        with rasterio.open(result["output_path"]) as src:
            tags = src.tags()
            assert "algorithm" in tags

    def test_empty_output_dir_created(self):
        paths = _make_bands(["nir", "red"])
        engine = SpectralIndicesEngine(window_size=32)
        out_path = os.path.join(TEST_DIR, "new_dir", "ndvi.tif")
        result = engine.compute("NDVI", paths, out_path)
        assert os.path.isfile(result["output_path"])


# ================================================================
# Edge Case Tests
# ================================================================

class TestEdgeCases:
    def test_missing_band_paths(self):
        with pytest.raises(MissingBandError):
            build_band_map({"b8": "/b8.tif"}, ["nir", "red"], "sentinel2")

    def test_index_not_found(self):
        engine = SpectralIndicesEngine()
        with pytest.raises(IndexNotFoundError):
            engine.compute("NONEXISTENT", {"nir": "/n.tif", "red": "/r.tif"})

    def test_statistics_all_nodata(self):
        data = np.full((10, 10), -9999.0, dtype=np.float64)
        stats = compute_statistics(data, nodata=-9999.0)
        assert stats["valid_pixel_count"] == 0
        assert stats["invalid_pct"] == 100.0

    def test_histogram_empty(self):
        data = np.full((10, 10), np.nan, dtype=np.float64)
        hist = compute_histogram(data)
        assert hist["bins"] == 256

    def test_percentiles_all_nodata(self):
        data = np.full((10, 10), -9999.0, dtype=np.float64)
        p = compute_percentiles(data, [50], nodata=-9999.0)
        assert p[50] == 0.0

    def test_classify_nodata_pixels(self):
        data = np.full((10, 10), np.nan, dtype=np.float64)
        scheme = get_scheme("ndvi")
        result = classify(data, scheme)
        assert result.sum() == 0


# ================================================================
# Health Report Tests
# ================================================================

class TestHealthReport:
    def test_health_report_structure(self):
        report = health_report()
        assert report["subsystem"] == "Spectral Indices Engine"
        assert report["status"] == "healthy"
        assert report["n_indices"] >= 13
        assert report["readiness_score"] >= 70

    def test_health_report_coverage(self):
        report = health_report()
        coverage = report["coverage"]
        assert coverage["vegetation"] is True
        assert coverage["built_up"] is True
        assert coverage["water"] is True
        assert coverage["moisture"] is True

    def test_health_report_providers(self):
        report = health_report()
        assert "sentinel2" in report["supported_providers"]
        assert "landsat8" in report["supported_providers"]

    def test_health_report_band_aliases(self):
        report = health_report()
        assert report["band_aliases"]["nir"] >= 8
