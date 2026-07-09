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

from app.preprocessing.exceptions import (
    CloudMaskError,
    NoDataError,
    ResamplingError,
    AlignmentError,
    NormalizationError,
    BandMathError,
    ConfigurationError,
    PipelineExecutionError,
)
from app.preprocessing.cloud_mask import (
    parse_sentinel2_qa60,
    parse_landsat_qa_pixel,
    compute_cloud_coverage,
    write_mask,
)
from app.preprocessing.nodata import (
    detect_nodata_pixels,
    fill_constant,
    fill_nearest_valid,
    fill_linear,
    fill_cubic,
    apply_nodata_handling,
)
from app.preprocessing.normalization import (
    min_max_normalize,
    zscore_normalize,
    percentile_clip_normalize,
    reflectance_scale,
    denormalize,
)
from app.preprocessing.resampling import (
    resample_to_resolution,
    resample_to_dimensions,
    get_resampling_method,
)
from app.preprocessing.alignment import align_bands, check_alignment
from app.preprocessing.band_math import (
    ndvi,
    ndbi,
    ndwi,
    savi,
    evi,
    compute_indices,
    resolve_band,
)
from app.preprocessing.quality import (
    compute_cloud_pct,
    compute_nodata_pct,
    compute_band_consistency,
    compute_spatial_consistency,
    compute_radiometric_statistics,
    compute_quality_score,
)
from app.preprocessing.mosaic import mosaic_scenes
from app.preprocessing.pipeline import PreprocessingPipeline, PipelineContext, health_report
from app.preprocessing.configuration import (
    PipelineConfig,
    CloudMaskConfig,
    NoDataConfig,
    ResamplingConfig,
    AlignmentConfig,
    NormalizationConfig,
    MosaicConfig,
    QualityConfig,
)

WIDTH, HEIGHT = 64, 48
CRS_EPSG = "EPSG:4326"
TEST_DIR = None


def setup_module():
    global TEST_DIR
    TEST_DIR = tempfile.mkdtemp(prefix="preprocessing_test_")


def teardown_module():
    if TEST_DIR and os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def _create_test_raster(
    path,
    width=WIDTH,
    height=HEIGHT,
    dtype=np.float32,
    n_bands=1,
    crs=CRS_EPSG,
    nodata=None,
    transform=None,
    data_fn=None,
):
    if transform is None:
        transform = from_bounds(-1.0, -1.0, 1.0, 1.0, width, height)
    if data_fn is None:
        data = np.random.RandomState(42).rand(n_bands, height, width).astype(dtype)
    else:
        data = data_fn(n_bands, height, width)

    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": n_bands,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 64,
        "blockysize": 64,
    }
    if nodata is not None:
        profile["nodata"] = nodata

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
    return str(path)


# ================================================================
# Configuration Tests
# ================================================================

class TestPipelineConfig:
    def test_default_config(self):
        config = PipelineConfig()
        assert config.cloud_mask.enabled is True
        assert config.nodata.enabled is True
        assert config.resampling.enabled is True
        assert config.alignment.enabled is True
        assert config.normalization.enabled is True
        assert config.mosaic.enabled is True
        assert config.quality.enabled is True

    def test_from_dict(self):
        data = {"cloud_mask": {"enabled": False}, "normalization": {"method": "zscore"}}
        config = PipelineConfig.from_dict(data)
        assert config.cloud_mask.enabled is False
        assert config.normalization.method == "zscore"
        assert config.nodata.enabled is True

    def test_from_json(self):
        data = {"resampling": {"method": "cubic", "enabled": False}}
        path = os.path.join(TEST_DIR, "config.json")
        with open(path, "w") as f:
            json.dump(data, f)
        config = PipelineConfig.from_json(path)
        assert config.resampling.method == "cubic"
        assert config.resampling.enabled is False

    def test_roundtrip_dict(self):
        config = PipelineConfig()
        d = config.to_dict()
        restored = PipelineConfig.from_dict(d)
        assert restored.cloud_mask.cloud_confidence_threshold == config.cloud_mask.cloud_confidence_threshold
        assert restored.nodata.fill_strategy == config.nodata.fill_strategy
        assert restored.normalization.method == config.normalization.method

    def test_config_from_dict_invalid_key_ignored(self):
        config = PipelineConfig.from_dict({"nonexistent": {"foo": 1}})
        assert config.cloud_mask.enabled is True

    def test_config_error_on_missing_file(self):
        with pytest.raises(ConfigurationError):
            PipelineConfig.from_json("/nonexistent/config.json")


# ================================================================
# Cloud Mask Tests
# ================================================================

class TestCloudMask:
    def test_parse_sentinel2_qa60_no_cloud(self):
        qa = np.zeros((48, 64), dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["cloud"].sum() == 0
        assert masks["combined"].sum() == 0
        assert masks["cirrus"].sum() == 0

    def test_parse_sentinel2_qa60_full_cloud(self):
        qa = np.full((48, 64), 0b00001100, dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["cloud"].all()
        assert masks["combined"].all()
        assert masks["cirrus"].sum() == 0

    def test_parse_sentinel2_qa60_cirrus(self):
        qa = np.full((48, 64), 0b00110000, dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["cirrus"].all()
        assert masks["combined"].all()
        assert masks["cloud"].sum() == 0

    def test_parse_sentinel2_qa60_snow(self):
        qa = np.full((48, 64), 0b11000000, dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["snow"].all()

    def test_parse_sentinel2_qa60_nodata(self):
        qa = np.full((48, 64), 0b00000001, dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["nodata"].all()

    def test_parse_sentinel2_qa60_3d_input(self):
        qa = np.ones((1, 48, 64), dtype=np.uint16) * 0b00001100
        masks = parse_sentinel2_qa60(qa)
        assert masks["cloud"].all()

    def test_parse_sentinel2_qa60_cloud_threshold_medium(self):
        qa = np.full((48, 64), 0b00001000, dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa, cloud_threshold=3)
        assert masks["cloud"].sum() == 0
        masks2 = parse_sentinel2_qa60(qa, cloud_threshold=2)
        assert masks2["cloud"].all()

    def test_parse_landsat_qa_pixel_cloud(self):
        qa = np.full((48, 64), 0b00001000, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["cloud"].all()
        assert masks["shadow"].sum() == 0

    def test_parse_landsat_qa_pixel_shadow(self):
        qa = np.full((48, 64), 0b00010000, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["shadow"].all()

    def test_parse_landsat_qa_pixel_cirrus(self):
        qa = np.full((48, 64), 0b00000100, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["cirrus"].all()

    def test_parse_landsat_qa_pixel_snow(self):
        qa = np.full((48, 64), 0b00100000, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["snow"].all()

    def test_parse_landsat_qa_pixel_fill(self):
        qa = np.full((48, 64), 0b00000001, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["fill"].all()
        assert masks["combined"].all()

    def test_parse_landsat_qa_pixel_clear(self):
        qa = np.full((48, 64), 0b01000000, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["clear"].all()

    def test_parse_landsat_qa_pixel_dilated_cloud(self):
        qa = np.full((48, 64), 0b00000010, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa)
        assert masks["cloud"].all()

    def test_parse_landsat_qa_pixel_cloud_conf(self):
        qa = np.full((48, 64), 0b00000010_00000000, dtype=np.uint16)
        masks = parse_landsat_qa_pixel(qa, cloud_threshold=2)
        assert masks["cloud"].all()

    def test_parse_landsat_qa_pixel_3d(self):
        qa = np.ones((1, 48, 64), dtype=np.uint16) * 0b00001000
        masks = parse_landsat_qa_pixel(qa)
        assert masks["cloud"].all()

    def test_compute_cloud_coverage_all_cloud(self):
        mask = np.ones((100, 100), dtype=bool)
        assert compute_cloud_coverage(mask) == 100.0

    def test_compute_cloud_coverage_half(self):
        mask = np.zeros((100, 100), dtype=bool)
        mask[:50] = True
        assert abs(compute_cloud_coverage(mask) - 50.0) < 0.01

    def test_compute_cloud_coverage_zero(self):
        mask = np.zeros((100, 100), dtype=bool)
        assert compute_cloud_coverage(mask) == 0.0

    def test_compute_cloud_coverage_empty(self):
        assert compute_cloud_coverage(np.zeros((0, 0), dtype=bool)) == 0.0

    def test_write_mask_creates_file(self):
        mask = np.zeros((48, 64), dtype=bool)
        mask[10:20, 10:20] = True
        path = os.path.join(TEST_DIR, "test_write_mask.tif")
        profile = {"driver": "GTiff", "width": 64, "height": 48, "count": 1,
                   "dtype": "float32", "crs": CRS_EPSG,
                   "transform": from_bounds(-1, -1, 1, 1, 64, 48)}
        result = write_mask(mask, path, profile)
        assert os.path.isfile(result)
        with rasterio.open(result) as src:
            assert src.count == 1
            assert src.dtypes[0] == "uint8"
            data = src.read(1)
            assert data.dtype == np.uint8
            assert data[12, 12] > 0

    def test_cloud_mask_stage_error_no_qa(self):
        from app.preprocessing.cloud_mask import CloudMaskStage
        stage = CloudMaskStage()
        with pytest.raises(CloudMaskError):
            stage.execute({"B04": "/nonexistent.tif"}, TEST_DIR)


# ================================================================
# NoData Handling Tests
# ================================================================

class TestNoData:
    def test_detect_nodata_constant_value(self):
        data = np.ones((3, 48, 64))
        data[0, 10:15, 10:15] = -9999.0
        mask = detect_nodata_pixels(data, -9999.0)
        assert mask[12, 12]
        assert not mask[0, 0]

    def test_detect_nodata_nan(self):
        data = np.ones((3, 48, 64))
        data[0, 20:25, 20:25] = np.nan
        mask = detect_nodata_pixels(data, None)
        assert mask[22, 22]
        assert not mask[0, 0]

    def test_detect_nodata_inf(self):
        data = np.ones((3, 48, 64))
        data[0, 30:35, 30:35] = np.inf
        mask = detect_nodata_pixels(data, None)
        assert mask[32, 32]

    def test_detect_nodata_2d(self):
        data = np.ones((48, 64))
        data[5:10, 5:10] = -9999.0
        mask = detect_nodata_pixels(data, -9999.0)
        assert mask[7, 7]

    def test_detect_nodata_custom_tolerance(self):
        data = np.ones((3, 48, 64))
        data[0, 0, 0] = -9999.0001
        mask = detect_nodata_pixels(data, -9999.0)
        assert not mask[0, 0]

    def test_fill_constant(self):
        data = np.ones((3, 48, 64), dtype=np.float64)
        data[0, 10:15, 10:15] = np.nan
        mask = np.isnan(data[0])
        filled = fill_constant(data, mask, 0.0)
        assert filled[0, 12, 12] == 0.0
        assert filled[0, 0, 0] == 1.0

    def test_fill_nearest_valid(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[10:15, 10:15] = np.nan
        mask = np.isnan(data)
        filled = fill_nearest_valid(data, mask)
        assert not np.isnan(filled).any()
        assert filled[12, 12] > 0

    def test_fill_linear(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[20:25, 20:25] = np.nan
        mask = np.isnan(data)
        filled = fill_linear(data, mask)
        assert not np.isnan(filled).any()

    def test_fill_cubic(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[30:35, 30:35] = np.nan
        mask = np.isnan(data)
        filled = fill_cubic(data, mask)
        assert not np.isnan(filled).any()

    def test_apply_nodata_handling_constant(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[0, 0] = np.nan
        mask = np.isnan(data)
        result = apply_nodata_handling(data, mask, "constant", fill_value=42.0)
        assert result[0, 0] == 42.0

    def test_apply_nodata_handling_interpolate_nearest(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[0, 0] = np.nan
        mask = np.isnan(data)
        result = apply_nodata_handling(data, mask, "interpolate", "nearest")
        assert not np.isnan(result).any()

    def test_apply_nodata_handling_interpolate_linear(self):
        data = np.ones((48, 64), dtype=np.float64)
        data[15:20, 15:20] = np.nan
        mask = np.isnan(data)
        result = apply_nodata_handling(data, mask, "interpolate", "linear")
        assert not np.isnan(result).any()

    def test_apply_nodata_handling_invalid_strategy(self):
        with pytest.raises(NoDataError):
            apply_nodata_handling(np.ones((10, 10)), np.zeros((10, 10), dtype=bool), "invalid")

    def test_apply_nodata_handling_invalid_method(self):
        with pytest.raises(NoDataError):
            apply_nodata_handling(np.ones((10, 10)), np.zeros((10, 10), dtype=bool), "interpolate", "invalid")


# ================================================================
# Resampling Tests
# ================================================================

class TestResampling:
    def test_resample_to_resolution(self):
        src = os.path.join(TEST_DIR, f"resample_src_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src)
        resample_to_resolution(src, dst, (0.05, 0.05), method="bilinear")
        with rasterio.open(dst) as src_ds:
            assert src_ds.width > 0
            assert src_ds.height > 0
            assert src_ds.crs.to_string() == CRS_EPSG

    def test_resample_to_dimensions(self):
        src = os.path.join(TEST_DIR, f"resample_dim_src_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_dim_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src)
        resample_to_dimensions(src, dst, 32, 24, method="nearest")
        with rasterio.open(dst) as src_ds:
            assert src_ds.width == 32
            assert src_ds.height == 24

    def test_resample_to_dimensions_lanczos(self):
        src = os.path.join(TEST_DIR, f"resample_lanczos_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_lanczos_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src)
        resample_to_dimensions(src, dst, 128, 96, method="lanczos")
        with rasterio.open(dst) as src_ds:
            assert src_ds.width == 128

    def test_resample_to_dimensions_average(self):
        src = os.path.join(TEST_DIR, f"resample_avg_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_avg_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src)
        resample_to_dimensions(src, dst, 16, 12, method="average")
        with rasterio.open(dst) as src_ds:
            assert src_ds.width == 16

    def test_resample_invalid_method(self):
        with pytest.raises(ResamplingError):
            get_resampling_method("invalid_method_name")

    def test_resample_valid_methods(self):
        for name in ("nearest", "bilinear", "cubic", "lanczos", "average"):
            method = get_resampling_method(name)
            assert method is not None

    def test_resample_negative_resolution_error(self):
        src = os.path.join(TEST_DIR, f"resample_neg_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_neg_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src)
        with pytest.raises(ResamplingError):
            resample_to_resolution(src, dst, (-0.05, 0.05))

    def test_resample_preserves_nodata(self):
        src = os.path.join(TEST_DIR, f"resample_nd_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"resample_nd_dst_{uuid.uuid4().hex}.tif")
        _create_test_raster(src, nodata=-9999.0)
        resample_to_resolution(src, dst, (0.05, 0.05), method="nearest")
        with rasterio.open(dst) as ds:
            assert ds.nodata == -9999.0


# ================================================================
# Alignment Tests
# ================================================================

class TestAlignment:
    def test_align_bands(self):
        b1 = os.path.join(TEST_DIR, f"align_b1_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"align_b2_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1)
        _create_test_raster(b2, crs="EPSG:3857")
        out_dir = os.path.join(TEST_DIR, f"align_out_{uuid.uuid4().hex}")
        result = align_bands({"B04": b1, "B03": b2}, out_dir, target_crs=CRS_EPSG)
        for name, path in result.items():
            with rasterio.open(path) as src:
                assert src.crs.to_string() == CRS_EPSG

    def test_align_bands_same_crs(self):
        b1 = os.path.join(TEST_DIR, f"align_same1_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"align_same2_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1, width=64, height=48)
        _create_test_raster(b2, width=128, height=96)
        out_dir = os.path.join(TEST_DIR, f"align_same_out_{uuid.uuid4().hex}")
        result = align_bands({"B04": b1, "B03": b2}, out_dir, target_crs=CRS_EPSG,
                             target_resolution=(0.05, 0.05))
        for name, path in result.items():
            with rasterio.open(path) as src:
                assert src.crs.to_string() == CRS_EPSG

    def test_align_bands_target_extent(self):
        b1 = os.path.join(TEST_DIR, f"align_ext_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1)
        out_dir = os.path.join(TEST_DIR, f"align_ext_out_{uuid.uuid4().hex}")
        result = align_bands({"B04": b1}, out_dir, target_extent=(-0.5, -0.5, 0.5, 0.5))
        assert os.path.isfile(result["B04"])

    def test_align_bands_empty_input(self):
        with pytest.raises(AlignmentError):
            align_bands({}, TEST_DIR)

    def test_check_alignment_aligned(self):
        b1 = os.path.join(TEST_DIR, f"check_aligned_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"check_aligned2_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1, width=64, height=48)
        _create_test_raster(b2, width=64, height=48)
        report = check_alignment({"B04": b1, "B03": b2})
        assert report["aligned"] is True

    def test_check_alignment_misaligned(self):
        b1 = os.path.join(TEST_DIR, f"check_mis_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"check_mis2_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1, width=64, height=48)
        _create_test_raster(b2, width=128, height=96)
        report = check_alignment({"B04": b1, "B03": b2})
        assert report["aligned"] is False

    def test_align_preserves_nodata(self):
        b1 = os.path.join(TEST_DIR, f"align_nd1_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"align_nd2_{uuid.uuid4().hex}.tif")
        _create_test_raster(b1, nodata=-9999.0)
        _create_test_raster(b2, nodata=-9999.0)
        out_dir = os.path.join(TEST_DIR, f"align_nd_out_{uuid.uuid4().hex}")
        result = align_bands({"B04": b1, "B03": b2}, out_dir, target_crs=CRS_EPSG)
        for path in result.values():
            with rasterio.open(path) as src:
                assert src.nodata == -9999.0


# ================================================================
# Normalization Tests
# ================================================================

class TestNormalization:
    def test_min_max_normalize_2d(self):
        data = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        result, params = min_max_normalize(data, per_band=False)
        assert abs(result[0, 0]) < 1e-10
        assert abs(result[1, 1] - 1.0) < 1e-10

    def test_min_max_normalize_3d_per_band(self):
        data = np.zeros((2, 48, 64), dtype=np.float64)
        data[0] = np.linspace(0, 10, 48 * 64).reshape(48, 64)
        data[1] = np.linspace(0, 100, 48 * 64).reshape(48, 64)
        result, params = min_max_normalize(data, per_band=True)
        assert abs(result[0].max() - 1.0) < 1e-10
        assert abs(result[1].max() - 1.0) < 1e-10

    def test_min_max_constant_band(self):
        data = np.ones((3, 48, 64), dtype=np.float64)
        result, params = min_max_normalize(data, per_band=True)
        assert result[0].sum() == 0.0

    def test_zscore_normalize(self):
        data = np.random.RandomState(42).randn(48, 64).astype(np.float64)
        result, params = zscore_normalize(data, per_band=False)
        assert abs(result.mean()) < 0.5
        assert abs(result.std() - 1.0) < 0.2

    def test_zscore_constant_band(self):
        data = np.ones((3, 48, 64), dtype=np.float64)
        result, params = zscore_normalize(data, per_band=True)
        assert result[0].sum() == 0.0

    def test_percentile_clip_normalize(self):
        data = np.random.RandomState(42).rand(48, 64).astype(np.float64)
        data[0, 0] = 100.0
        data[1, 1] = -100.0
        result, params = percentile_clip_normalize(data, 2.0, 98.0, per_band=False)
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_reflectance_scale(self):
        data = np.array([[10000, 20000], [30000, 40000]], dtype=np.float64)
        result, params = reflectance_scale(data, 0.0001)
        assert abs(result[0, 0] - 1.0) < 1e-10
        assert abs(result[1, 1] - 4.0) < 1e-10

    def test_reflectance_scale_with_offset(self):
        data = np.array([[10000, 20000]], dtype=np.float64)
        result, params = reflectance_scale(data, 0.0001, -0.1)
        assert abs(result[0, 0] - 0.9) < 1e-10

    def test_denormalize_min_max_2d(self):
        data = np.random.RandomState(42).rand(48, 64).astype(np.float64)
        normalized, params = min_max_normalize(data, per_band=False)
        restored = denormalize(normalized, params, "min_max")
        assert np.allclose(data, restored, atol=1e-10)

    def test_denormalize_min_max_3d(self):
        data = np.random.RandomState(42).rand(3, 48, 64).astype(np.float64)
        data[0] *= 10
        normalized, params = min_max_normalize(data, per_band=True)
        restored = denormalize(normalized, params, "min_max")
        assert np.allclose(data, restored, atol=1e-10)

    def test_denormalize_zscore_2d(self):
        data = np.random.RandomState(42).randn(48, 64).astype(np.float64)
        normalized, params = zscore_normalize(data, per_band=False)
        restored = denormalize(normalized, params, "zscore")
        assert np.allclose(data, restored, atol=1e-10)

    def test_denormalize_unsupported(self):
        with pytest.raises(NormalizationError):
            denormalize(np.ones((10, 10)), {}, "invalid_method")


# ================================================================
# Band Math Tests
# ================================================================

class TestBandMath:
    def test_ndvi(self):
        bands = {
            "nir": np.full((48, 64), 0.8, dtype=np.float64),
            "red": np.full((48, 64), 0.2, dtype=np.float64),
        }
        result = ndvi(bands)
        assert np.allclose(result, 0.6, atol=1e-10)

    def test_ndvi_water(self):
        bands = {
            "nir": np.full((48, 64), 0.05, dtype=np.float64),
            "red": np.full((48, 64), 0.02, dtype=np.float64),
        }
        result = ndvi(bands)
        assert result[0, 0] < 0.5

    def test_ndvi_zero_divisor(self):
        bands = {
            "nir": np.zeros((48, 64), dtype=np.float64),
            "red": np.zeros((48, 64), dtype=np.float64),
        }
        result = ndvi(bands)
        assert result[0, 0] == 0.0

    def test_ndvi_clipped(self):
        bands = {
            "nir": np.full((48, 64), 100.0, dtype=np.float64),
            "red": np.full((48, 64), -100.0, dtype=np.float64),
        }
        result = ndvi(bands)
        assert -1.0 <= result.min() <= result.max() <= 1.0

    def test_ndbi(self):
        bands = {
            "swir1": np.full((48, 64), 0.6, dtype=np.float64),
            "nir": np.full((48, 64), 0.3, dtype=np.float64),
        }
        result = ndbi(bands)
        assert result[0, 0] > 0

    def test_ndwi(self):
        bands = {
            "green": np.full((48, 64), 0.4, dtype=np.float64),
            "nir": np.full((48, 64), 0.1, dtype=np.float64),
        }
        result = ndwi(bands)
        assert result[0, 0] > 0

    def test_savi(self):
        bands = {
            "nir": np.full((48, 64), 0.8, dtype=np.float64),
            "red": np.full((48, 64), 0.2, dtype=np.float64),
        }
        result = savi(bands, L=0.5)
        assert 0 < result[0, 0] < 1.0

    def test_evi(self):
        bands = {
            "nir": np.full((48, 64), 0.8, dtype=np.float64),
            "red": np.full((48, 64), 0.2, dtype=np.float64),
            "blue": np.full((48, 64), 0.1, dtype=np.float64),
        }
        result = evi(bands)
        assert 0 < result[0, 0] < 2.0

    def test_compute_indices(self):
        bands = {
            "nir": np.full((48, 64), 0.8, dtype=np.float64),
            "red": np.full((48, 64), 0.2, dtype=np.float64),
            "green": np.full((48, 64), 0.4, dtype=np.float64),
            "blue": np.full((48, 64), 0.1, dtype=np.float64),
            "swir1": np.full((48, 64), 0.6, dtype=np.float64),
        }
        results = compute_indices(bands, ["ndvi", "ndbi", "ndwi", "savi", "evi"])
        assert "ndvi" in results
        assert "ndbi" in results
        assert "ndwi" in results
        assert "savi" in results
        assert "evi" in results

    def test_compute_indices_unknown(self):
        bands = {"nir": np.ones((10, 10)), "red": np.ones((10, 10))}
        results = compute_indices(bands, ["unknown_index"])
        assert results == {}

    def test_resolve_band_missing(self):
        with pytest.raises(BandMathError):
            resolve_band({"nir": np.ones((10, 10))}, "red")

    def test_resolve_band_alias(self):
        result = resolve_band(
            {"nir08": np.ones((10, 10))},
            "nir",
            alias_map={"nir": "nir08"},
        )
        assert result is not None


# ================================================================
# Quality Assessment Tests
# ================================================================

class TestQuality:
    def test_quality_score_no_issues(self):
        score = compute_quality_score(0, 0, True, True)
        assert score >= 95.0

    def test_quality_score_all_cloud(self):
        score = compute_quality_score(100, 0, True, True)
        assert score < 100.0

    def test_quality_score_band_inconsistent(self):
        score = compute_quality_score(0, 0, False, True)
        assert score < 100.0

    def test_compute_quality_score_custom_weights(self):
        score = compute_quality_score(
            50, 10, True, True, None,
            {"cloud": 0.5, "nodata": 0.5, "band_consistency": 0.0,
             "spatial_consistency": 0.0, "radiometric": 0.0},
        )
        expected = 0.5 * 50.0 + 0.5 * 90.0
        assert abs(score - expected) < 0.01


# ================================================================
# Mosaic Tests
# ================================================================

class TestMosaic:
    def test_mosaic_two_scenes(self):
        s1 = os.path.join(TEST_DIR, f"mos1_{uuid.uuid4().hex}.tif")
        s2 = os.path.join(TEST_DIR, f"mos2_{uuid.uuid4().hex}.tif")
        _create_test_raster(s1, width=32, height=32,
                            transform=from_bounds(-1.0, -1.0, 0.0, 1.0, 32, 32))
        _create_test_raster(s2, width=32, height=32,
                            transform=from_bounds(0.0, -1.0, 1.0, 1.0, 32, 32))
        out = os.path.join(TEST_DIR, f"mosaic_out_{uuid.uuid4().hex}.tif")
        result = mosaic_scenes(
            [s1, s2], out, strategy="newest", resampling_method="bilinear",
        )
        assert os.path.isfile(result["output_path"])
        assert result["width"] > 32

    def test_mosaic_less_than_two_scenes(self):
        out = os.path.join(TEST_DIR, f"mosaic_err_{uuid.uuid4().hex}.tif")
        with pytest.raises(Exception):
            mosaic_scenes([out], out)


# ================================================================
# Pipeline Tests
# ================================================================

class TestPipeline:
    def test_pipeline_default_execution(self):
        b04 = os.path.join(TEST_DIR, f"pipe_b04_{uuid.uuid4().hex}.tif")
        qa = os.path.join(TEST_DIR, f"pipe_qa_{uuid.uuid4().hex}.tif")
        _create_test_raster(b04)
        qa_data = np.zeros((48, 64), dtype=np.uint16)
        qa_profile = {
            "driver": "GTiff", "width": 64, "height": 48, "count": 1,
            "dtype": "uint16", "crs": CRS_EPSG,
            "transform": from_bounds(-1, -1, 1, 1, 64, 48),
        }
        with rasterio.open(qa, "w", **qa_profile) as dst:
            dst.write(qa_data, 1)

        config = PipelineConfig(
            cloud_mask=CloudMaskConfig(enabled=True, output_snow_mask=False),
            nodata=NoDataConfig(enabled=True, fill_strategy="constant", constant_fill_value=0.0),
            resampling=ResamplingConfig(enabled=False),
            alignment=AlignmentConfig(enabled=False),
            normalization=NormalizationConfig(enabled=False),
            mosaic=MosaicConfig(enabled=False),
            quality=QualityConfig(enabled=True),
            work_dir=os.path.join(TEST_DIR, f"pipe_work_{uuid.uuid4().hex}"),
            preserve_intermediate=True,
        )
        pipeline = PreprocessingPipeline(config)
        ctx = pipeline.execute({"B04": b04}, qa_path=qa)
        assert ctx.cloud_mask_path is not None
        assert os.path.isfile(ctx.cloud_mask_path)
        assert "cloud_mask" in ctx.stage_results
        assert "nodata" in ctx.stage_results
        assert "quality" in ctx.stage_results
        assert "quality_score" in ctx.quality_report
        assert ctx.quality_report["quality_score"] >= 0

    def test_pipeline_stage_independent_execution(self):
        b04 = os.path.join(TEST_DIR, f"pipe_indep_{uuid.uuid4().hex}.tif")
        _create_test_raster(b04)
        config = PipelineConfig(
            normalization=NormalizationConfig(enabled=True, method="min_max"),
        )
        for s in ["cloud_mask", "nodata", "resampling", "alignment", "mosaic", "quality"]:
            getattr(config, s).enabled = False

        pipeline = PreprocessingPipeline(config)
        ctx = pipeline.execute({"B04": b04},
                               output_dir=os.path.join(TEST_DIR, f"pipe_indep_out_{uuid.uuid4().hex}"))
        assert "normalization" in ctx.stage_results

    def test_pipeline_all_stages_disabled(self):
        b04 = os.path.join(TEST_DIR, f"pipe_disabled_{uuid.uuid4().hex}.tif")
        _create_test_raster(b04)
        config = PipelineConfig()
        for s in ["cloud_mask", "nodata", "resampling", "alignment", "normalization", "mosaic", "quality"]:
            getattr(config, s).enabled = False

        pipeline = PreprocessingPipeline(config)
        ctx = pipeline.execute({"B04": b04},
                               output_dir=os.path.join(TEST_DIR, f"pipe_disabled_out_{uuid.uuid4().hex}"))
        stage_keys = [k for k in ctx.stage_results if not k.startswith("_")]
        assert len(stage_keys) == 0

    def test_pipeline_from_dict_config(self):
        config_dict = {
            "cloud_mask": {"enabled": False},
            "nodata": {"enabled": False},
            "normalization": {"method": "zscore"},
        }
        pipeline = PreprocessingPipeline(config_dict)
        assert pipeline.config.normalization.method == "zscore"
        assert pipeline.config.cloud_mask.enabled is False

    def test_pipeline_config_object(self):
        config = PipelineConfig()
        pipeline = PreprocessingPipeline(config)
        assert pipeline.config is config

    def test_pipeline_invalid_config_type(self):
        with pytest.raises(PipelineExecutionError):
            PreprocessingPipeline(42)

    def test_pipeline_context_cleanup(self):
        b04 = os.path.join(TEST_DIR, f"pipe_clean_{uuid.uuid4().hex}.tif")
        _create_test_raster(b04)
        import tempfile as tf
        config = PipelineConfig(
            cloud_mask=CloudMaskConfig(enabled=False),
            nodata=NoDataConfig(enabled=False),
            resampling=ResamplingConfig(enabled=False),
            alignment=AlignmentConfig(enabled=False),
            normalization=NormalizationConfig(enabled=False),
            mosaic=MosaicConfig(enabled=False),
            quality=QualityConfig(enabled=True),
            preserve_intermediate=False,
        )
        pipeline = PreprocessingPipeline(config)
        qa_path = os.path.join(TEST_DIR, f"pipe_clean_qa_{uuid.uuid4().hex}.tif")
        qa_profile = {
            "driver": "GTiff", "width": 64, "height": 48, "count": 1,
            "dtype": "uint16", "crs": CRS_EPSG,
            "transform": from_bounds(-1, -1, 1, 1, 64, 48),
        }
        with rasterio.open(qa_path, "w", **qa_profile) as dst:
            dst.write(np.zeros((48, 64), dtype=np.uint16), 1)
        ctx = pipeline.execute({"B04": b04}, qa_path=qa_path)
        assert ctx is not None


# ================================================================
# Health Report Tests
# ================================================================

class TestHealthReport:
    def test_health_report_structure(self):
        report = health_report()
        assert report["subsystem"] == "Raster Preprocessing Pipeline"
        assert report["status"] == "healthy"
        assert "implemented_stages" in report
        assert len(report["implemented_stages"]) >= 7
        assert report["readiness_score"] >= 70
        assert report["readiness_label"] in ("PRODUCTION", "BETA", "DEVELOPMENT")
        assert report["extensibility_score"] >= 80

    def test_health_report_includes_validation_notes(self):
        report = health_report()
        assert len(report["scientific_validation_notes"]) > 0
        assert any("CRS" in note for note in report["scientific_validation_notes"])

    def test_health_report_includes_performance_notes(self):
        report = health_report()
        assert len(report["performance_notes"]) > 0


# ================================================================
# Edge Case Tests
# ================================================================

class TestEdgeCases:
    def test_cloud_mask_empty_qa(self):
        qa = np.zeros((0, 0), dtype=np.uint16)
        masks = parse_sentinel2_qa60(qa)
        assert masks["cloud"].size == 0

    def test_nodata_all_valid(self):
        data = np.ones((3, 48, 64))
        mask = detect_nodata_pixels(data, -9999.0)
        assert mask.sum() == 0

    def test_nodata_empty_array(self):
        data = np.ones((0, 0))
        mask = detect_nodata_pixels(data, None)
        assert mask.size == 0

    def test_resample_file_not_found(self):
        with pytest.raises(Exception):
            resample_to_resolution("/nonexistent.tif", "/out.tif", (0.05, 0.05))

    def test_align_no_inputs(self):
        with pytest.raises(AlignmentError):
            align_bands({}, TEST_DIR)

    def test_normalize_empty_data(self):
        data = np.zeros((0, 0), dtype=np.float64)
        with pytest.raises(ValueError):
            min_max_normalize(data, per_band=False)

    def test_band_math_empty_arrays(self):
        bands = {"nir": np.zeros((0, 0)), "red": np.zeros((0, 0))}
        result = ndvi(bands)
        assert result.size == 0

    def test_quality_score_extreme_values(self):
        score = compute_quality_score(100, 100, False, False, None)
        assert score >= 0

    def test_pixel_alignment_correct(self):
        height, width = 4, 4
        b1 = os.path.join(TEST_DIR, f"pixalign_b1_{uuid.uuid4().hex}.tif")
        b2 = os.path.join(TEST_DIR, f"pixalign_b2_{uuid.uuid4().hex}.tif")
        transform = from_bounds(0.0, 0.0, 1.0, 1.0, width, height)
        data1 = np.arange(height * width, dtype=np.float32).reshape(1, height, width)
        data2 = np.flipud(data1.copy())
        with rasterio.open(b1, "w", driver="GTiff", width=width, height=height,
                           count=1, dtype="float32", crs=CRS_EPSG, transform=transform) as dst:
            dst.write(data1)
        with rasterio.open(b2, "w", driver="GTiff", width=width, height=height,
                           count=1, dtype="float32", crs=CRS_EPSG, transform=transform) as dst:
            dst.write(data2)

        out_dir = os.path.join(TEST_DIR, f"pixalign_out_{uuid.uuid4().hex}")
        result = align_bands({"B04": b1, "B03": b2}, out_dir, target_crs=CRS_EPSG,
                             target_resolution=(0.25, 0.25), align_pixels=True)
        for path in result.values():
            with rasterio.open(path) as src:
                assert src.width > 0
                assert src.height > 0

    def test_crs_preserved_through_resample(self):
        src = os.path.join(TEST_DIR, f"crs_resample_{uuid.uuid4().hex}.tif")
        dst = os.path.join(TEST_DIR, f"crs_resample_out_{uuid.uuid4().hex}.tif")
        _create_test_raster(src, crs="EPSG:32644")
        resample_to_dimensions(src, dst, 32, 24, method="bilinear")
        with rasterio.open(dst) as ds:
            assert ds.crs.to_string() == "EPSG:32644"

    def test_nodata_propagated_through_fill(self):
        data = np.ones((3, 48, 64), dtype=np.float64)
        data[0, 10:15, 10:15] = np.nan
        mask = detect_nodata_pixels(data, None)
        filled = fill_nearest_valid(data, mask)
        assert not np.isnan(filled).any()

    def test_large_raster_simulation(self):
        src = os.path.join(TEST_DIR, f"large_{uuid.uuid4().hex}.tif")
        _create_test_raster(src, width=512, height=512)
        dst = os.path.join(TEST_DIR, f"large_out_{uuid.uuid4().hex}.tif")
        resample_to_dimensions(src, dst, 256, 256, method="bilinear")
        with rasterio.open(dst) as ds:
            assert ds.width == 256
            assert ds.height == 256

    def test_config_disable_single_stage(self):
        config = PipelineConfig.from_dict({"cloud_mask": {"enabled": False}})
        assert config.cloud_mask.enabled is False
        assert config.nodata.enabled is True

    def test_pipeline_with_qa_path(self):
        b04 = os.path.join(TEST_DIR, f"pipe_qa_path_{uuid.uuid4().hex}.tif")
        _create_test_raster(b04)
        config = PipelineConfig(
            cloud_mask=CloudMaskConfig(enabled=True, output_snow_mask=False),
            nodata=NoDataConfig(enabled=False),
            resampling=ResamplingConfig(enabled=False),
            alignment=AlignmentConfig(enabled=False),
            normalization=NormalizationConfig(enabled=False),
            mosaic=MosaicConfig(enabled=False),
            quality=QualityConfig(enabled=False),
            preserve_intermediate=True,
        )
        qa_path = os.path.join(TEST_DIR, f"pipe_qa_file_{uuid.uuid4().hex}.tif")
        qa_profile = {
            "driver": "GTiff", "width": 64, "height": 48, "count": 1,
            "dtype": "uint16", "crs": CRS_EPSG,
            "transform": from_bounds(-1, -1, 1, 1, 64, 48),
        }
        with rasterio.open(qa_path, "w", **qa_profile) as dst:
            dst.write(np.zeros((48, 64), dtype=np.uint16), 1)

        pipeline = PreprocessingPipeline(config)
        ctx = pipeline.execute({"B04": b04}, qa_path=qa_path)
        assert ctx.cloud_mask_path is not None
