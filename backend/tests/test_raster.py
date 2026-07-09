"""Comprehensive tests for the Raster Management subsystem."""

import os
import sys
import tempfile
import uuid

import numpy as np
import pytest

from app.raster import (
    RasterManager,
    RasterError,
    RasterNotFoundError,
    CorruptedRasterError,
    UnsupportedFormatError,
    RasterValidationError,
    RasterTransformError,
    RasterTilingError,
    read_bands,
    read_window,
    read_bbox,
    read_aoi,
    get_raster_info,
    write_geotiff,
    write_cog,
    copy_with_compression,
    extract_metadata,
    validate_all,
    crop,
    clip,
    reproject,
    resample,
    extract_band,
    split,
    stack_bands,
    merge,
    compress,
    decompress,
    get_compression_info,
    compute_statistics,
    compute_all_statistics,
    compute_histogram,
    compute_percentiles,
    compute_nodata_percentage,
    create_png_preview,
    create_jpeg_preview,
    create_thumbnail,
    create_false_color_composite,
    create_tiles,
    create_tile_index,
    read_tile,
    stream_blocks,
)

TEST_DIR = tempfile.mkdtemp(prefix="raster_test_")
NP_RANDOM = np.random.RandomState(42)

# Shared test raster parameters
WIDTH, HEIGHT = 128, 96
CRS = "EPSG:4326"
TRANSFORM = (0.1, 0.0, 72.0, 0.0, -0.1, 19.0)
NODATA = -9999.0


@pytest.fixture(scope="module")
def single_band_path():
    """Create a single-band test GeoTIFF."""
    data = NP_RANDOM.rand(HEIGHT, WIDTH).astype(np.float32)
    path = os.path.join(TEST_DIR, f"single_{uuid.uuid4().hex}.tif")
    write_geotiff(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA, compression="lzw")
    return path


@pytest.fixture(scope="module")
def multi_band_path():
    """Create a 4-band test GeoTIFF (simulating RGBN)."""
    data = NP_RANDOM.rand(4, HEIGHT, WIDTH).astype(np.float32)
    path = os.path.join(TEST_DIR, f"multi_{uuid.uuid4().hex}.tif")
    write_geotiff(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA, compression="lzw")
    return path


@pytest.fixture(scope="module")
def small_band_path():
    """Create a very small test GeoTIFF."""
    data = NP_RANDOM.rand(16, 16).astype(np.float32)
    path = os.path.join(TEST_DIR, f"small_{uuid.uuid4().hex}.tif")
    write_geotiff(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA, compression=None)
    return path


@pytest.fixture(scope="module")
def int_band_path():
    """Create an integer-band test GeoTIFF."""
    data = NP_RANDOM.randint(0, 255, (HEIGHT, WIDTH)).astype(np.uint8)
    path = os.path.join(TEST_DIR, f"int_{uuid.uuid4().hex}.tif")
    write_geotiff(path, data, transform=TRANSFORM, crs=CRS, nodata=0, compression="deflate")
    return path


@pytest.fixture(scope="module")
def manager():
    return RasterManager(compression="lzw", tile_size=64)


# ============================================================
# EXCEPTIONS
# ============================================================

class TestExceptions:
    def test_base_exception(self):
        assert issubclass(RasterError, Exception)
        assert issubclass(RasterNotFoundError, RasterError)
        assert issubclass(CorruptedRasterError, RasterError)
        assert issubclass(UnsupportedFormatError, RasterError)
        assert issubclass(RasterTransformError, RasterError)

    def test_exception_message(self):
        try:
            raise RasterNotFoundError("file not found")
        except RasterError as e:
            assert "file not found" in str(e)


# ============================================================
# WRITING
# ============================================================

class TestWriter:
    def test_write_geotiff(self, single_band_path):
        assert os.path.isfile(single_band_path)
        info = get_raster_info(single_band_path)
        assert info["width"] == WIDTH
        assert info["height"] == HEIGHT
        assert info["count"] == 1
        assert info["crs"] == CRS

    def test_write_geotiff_multi_band(self, multi_band_path):
        assert os.path.isfile(multi_band_path)
        info = get_raster_info(multi_band_path)
        assert info["count"] == 4

    def test_write_geotiff_no_compression(self, small_band_path):
        assert os.path.isfile(small_band_path)
        info = get_raster_info(small_band_path)
        assert info["compression"] is None

    def test_write_cog(self):
        data = NP_RANDOM.rand(3, HEIGHT, WIDTH).astype(np.float32)
        path = os.path.join(TEST_DIR, f"cog_{uuid.uuid4().hex}.tif")
        write_cog(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA, compression="lzw")
        assert os.path.isfile(path)
        info = get_raster_info(path)
        assert info["tiled"] is True
        assert info["count"] == 3
        assert info["crs"] == CRS

    def test_write_cog_default_overviews(self):
        data = NP_RANDOM.rand(1, 512, 512).astype(np.float32)
        path = os.path.join(TEST_DIR, f"cog_ovr_{uuid.uuid4().hex}.tif")
        write_cog(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA, compression="deflate")
        assert os.path.isfile(path)

    def test_write_int_geotiff(self, int_band_path):
        assert os.path.isfile(int_band_path)
        info = get_raster_info(int_band_path)
        assert info["dtype"] == "uint8"
        assert info["count"] == 1

    def test_copy_with_compression(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"copy_{uuid.uuid4().hex}.tif")
        result = copy_with_compression(single_band_path, dst, compression="deflate")
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["compression"] == "DEFLATE"

    def test_copy_with_compression_change_compression(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"copy_zstd_{uuid.uuid4().hex}.tif")
        result = copy_with_compression(single_band_path, dst, compression="zstd")
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["compression"] == "ZSTD"

    def test_write_invalid_compression(self):
        data = NP_RANDOM.rand(HEIGHT, WIDTH).astype(np.float32)
        path = os.path.join(TEST_DIR, "bad_comp.tif")
        with pytest.raises(UnsupportedFormatError):
            write_geotiff(path, data, transform=TRANSFORM, crs=CRS, compression="invalid")


# ============================================================
# READING
# ============================================================

class TestReader:
    def test_read_bands_all(self, single_band_path):
        data, meta = read_bands(single_band_path)
        assert data.shape == (HEIGHT, WIDTH)
        assert meta["crs"] is not None
        assert meta["dtype"] == "float32"

    def test_read_bands_multi(self, multi_band_path):
        data, meta = read_bands(multi_band_path)
        assert data.shape == (4, HEIGHT, WIDTH)
        assert data.dtype == np.float32

    def test_read_bands_selected(self, multi_band_path):
        data, meta = read_bands(multi_band_path, bands=[2, 4])
        assert data.shape == (2, HEIGHT, WIDTH)

    def test_read_window(self, single_band_path):
        window = ((10, 30), (20, 50))
        data, meta = read_window(single_band_path, window)
        assert data.shape == (20, 30)

    def test_read_window_with_out_shape(self, single_band_path):
        window = ((0, HEIGHT), (0, WIDTH))
        data, meta = read_window(single_band_path, window, out_shape=(48, 64))
        assert data.shape == (48, 64)

    def test_read_bbox(self, multi_band_path):
        bbox = (72.5, 18.5, 73.5, 19.5)
        data, meta = read_bbox(multi_band_path, bbox)
        assert data.ndim == 3
        assert data.shape[0] == 4

    def test_read_bbox_no_overlap(self, single_band_path):
        bbox = (200.0, 50.0, 201.0, 51.0)
        with pytest.raises(RasterError):
            read_bbox(single_band_path, bbox)

    def test_read_aoi(self, multi_band_path):
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [72.0, 19.0],
                [73.0, 19.0],
                [73.0, 20.0],
                [72.0, 20.0],
                [72.0, 19.0],
            ]],
        }
        data, meta = read_aoi(multi_band_path, geom)
        assert data.ndim == 3

    def test_read_aoi_single_band(self, single_band_path):
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [72.0, 18.5],
                [72.5, 18.5],
                [72.5, 19.0],
                [72.0, 19.0],
                [72.0, 18.5],
            ]],
        }
        data, meta = read_aoi(single_band_path, geom)
        assert data.ndim == 2

    def test_get_raster_info(self, multi_band_path):
        info = get_raster_info(multi_band_path)
        assert info["width"] == WIDTH
        assert info["height"] == HEIGHT
        assert info["count"] == 4
        assert info["crs"] == CRS
        assert "bounds" in info

    def test_stream_blocks(self, single_band_path):
        blocks = list(stream_blocks(single_band_path, band=1, block_size=64))
        assert len(blocks) > 0
        for block_data, (row_off, col_off), meta in blocks:
            assert block_data.ndim == 2
            assert block_data.size > 0
            assert meta["crs"] is not None

    def test_stream_blocks_multi_band(self, multi_band_path):
        blocks = list(stream_blocks(multi_band_path, band=3, block_size=64))
        assert len(blocks) > 0

    def test_read_bands_masked(self, single_band_path):
        data, meta = read_bands(single_band_path, masked=True)
        assert isinstance(data, np.ma.MaskedArray)

    def test_read_bands_out_shape(self, single_band_path):
        data, meta = read_bands(single_band_path, out_shape=(48, 64))
        assert data.shape == (48, 64)


# ============================================================
# METADATA
# ============================================================

class TestMetadata:
    def test_extract_basic(self, multi_band_path):
        meta = extract_metadata(multi_band_path)
        assert meta["width"] == WIDTH
        assert meta["height"] == HEIGHT
        assert meta["count"] == 4
        assert meta["crs"] == CRS
        assert "bounds" in meta
        assert meta["driver"] == "GTiff"
        assert meta["dtype"] == "float32"
        assert meta["nodata"] == NODATA

    def test_extract_detailed(self, multi_band_path):
        meta = extract_metadata(multi_band_path, detailed=True)
        assert "bands" in meta
        assert len(meta["bands"]) == 4
        for band_info in meta["bands"]:
            assert "band" in band_info
            assert "dtype" in band_info
            assert "color_interp" in band_info

    def test_extract_file_not_found(self):
        with pytest.raises(RasterNotFoundError):
            extract_metadata("/nonexistent/path.tif")

    def test_extract_transform_info(self, single_band_path):
        meta = extract_metadata(single_band_path)
        assert meta["transform"] is not None
        assert len(meta["transform"]) >= 6
        assert meta["resolutions"] is not None

    def test_extract_color_interp(self, multi_band_path):
        meta = extract_metadata(multi_band_path)
        assert len(meta["color_interp"]) == 4


# ============================================================
# VALIDATION
# ============================================================

class TestValidator:
    def test_validate_healthy(self, single_band_path):
        report = validate_all(single_band_path)
        assert report["valid"] is True
        assert len(report["errors"]) == 0

    def test_validate_multi_band(self, multi_band_path):
        report = validate_all(multi_band_path, expected_bands=4)
        assert report["valid"] is True

    def test_validate_wrong_band_count(self, multi_band_path):
        report = validate_all(multi_band_path, expected_bands=99)
        assert report["valid"] is False
        assert any("band_count" in e for e in report["errors"])

    def test_validate_file_not_found(self):
        report = validate_all("/nonexistent/path.tif")
        assert report["valid"] is False

    def test_validate_corrupted_file(self):
        path = os.path.join(TEST_DIR, f"corrupt_{uuid.uuid4().hex}.tif")
        with open(path, "wb") as f:
            f.write(b"not a valid tiff file")
        report = validate_all(path)
        assert report["valid"] is False

    def test_validate_empty_file(self):
        path = os.path.join(TEST_DIR, f"empty_{uuid.uuid4().hex}.tif")
        with open(path, "wb") as f:
            f.write(b"")
        report = validate_all(path)
        assert report["valid"] is False

    def test_validate_int_raster(self, int_band_path):
        report = validate_all(int_band_path)
        assert report["valid"] is True

    def test_validate_expected_crs(self, single_band_path):
        report = validate_all(single_band_path, expected_crs=CRS)
        assert report["valid"] is True

    def test_validate_expected_crs_wrong(self, single_band_path):
        report = validate_all(single_band_path, expected_crs="EPSG:3857")
        assert report["valid"] is False


# ============================================================
# TRANSFORMATIONS
# ============================================================

class TestTransform:
    def test_crop(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"crop_{uuid.uuid4().hex}.tif")
        bbox = (72.5, 18.5, 73.5, 19.5)
        result = crop(multi_band_path, dst, bbox)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["count"] == 4
        assert info["crs"] == CRS

    def test_crop_single_band(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"crop_single_{uuid.uuid4().hex}.tif")
        result = crop(single_band_path, dst, (72.0, 18.0, 73.0, 20.0))
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["count"] == 1

    def test_crop_no_overlap(self, single_band_path):
        dst = os.path.join(TEST_DIR, "crop_none.tif")
        with pytest.raises(RasterTransformError):
            crop(single_band_path, dst, (200.0, 50.0, 201.0, 51.0))

    def test_reproject(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"reproj_{uuid.uuid4().hex}.tif")
        result = reproject(single_band_path, dst, "EPSG:3857")
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["crs"] == "EPSG:3857"

    def test_resample_scale_factor(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"resample_{uuid.uuid4().hex}.tif")
        result = resample(multi_band_path, dst, scale_factor=0.5)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["width"] == WIDTH // 2 or info["width"] == WIDTH // 2 + 1
        assert info["height"] == HEIGHT // 2 or info["height"] == HEIGHT // 2 + 1
        assert info["crs"] == CRS

    def test_resample_target_dimensions(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"resample_dim_{uuid.uuid4().hex}.tif")
        result = resample(single_band_path, dst, width=64, height=48)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["width"] == 64
        assert info["height"] == 48

    def test_extract_band(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"band3_{uuid.uuid4().hex}.tif")
        result = extract_band(multi_band_path, dst, band=3)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["count"] == 1
        assert info["crs"] == CRS

    def test_extract_band_invalid(self, multi_band_path):
        dst = os.path.join(TEST_DIR, "bad_band.tif")
        with pytest.raises(RasterTransformError):
            extract_band(multi_band_path, dst, band=99)

    def test_split(self, multi_band_path):
        dst_dir = os.path.join(TEST_DIR, f"split_{uuid.uuid4().hex}")
        paths = split(multi_band_path, dst_dir, prefix="test_band")
        assert len(paths) == 4
        for p in paths:
            assert os.path.isfile(p)
            info = get_raster_info(p)
            assert info["count"] == 1

    def test_stack_bands(self, multi_band_path):
        extracted = []
        for i in range(1, 4):
            p = os.path.join(TEST_DIR, f"extract_{i}_{uuid.uuid4().hex}.tif")
            extract_band(multi_band_path, p, band=i)
            extracted.append(p)
        dst = os.path.join(TEST_DIR, f"stacked_{uuid.uuid4().hex}.tif")
        result = stack_bands(extracted, dst)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["count"] == 3

    def test_merge(self):
        paths = []
        for i in range(3):
            data = NP_RANDOM.rand(HEIGHT, WIDTH).astype(np.float32)
            p = os.path.join(TEST_DIR, f"merge_src_{i}_{uuid.uuid4().hex}.tif")
            offset = 72.0 + i * 1.5
            t = (0.1, 0.0, offset, 0.0, -0.1, 19.0)
            write_geotiff(p, data, transform=t, crs=CRS, nodata=NODATA, compression="lzw")
            paths.append(p)
        dst = os.path.join(TEST_DIR, f"merged_{uuid.uuid4().hex}.tif")
        result = merge(paths, dst)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["crs"] == CRS

    def test_clip_polygon(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"clip_{uuid.uuid4().hex}.tif")
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [72.0, 18.5],
                [73.0, 18.5],
                [73.0, 19.5],
                [72.0, 19.5],
                [72.0, 18.5],
            ]],
        }
        result = clip(multi_band_path, dst, geom)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["crs"] == CRS

    def test_resample_no_params(self, single_band_path):
        dst = os.path.join(TEST_DIR, "resample_bad.tif")
        with pytest.raises(RasterTransformError):
            resample(single_band_path, dst)


# ============================================================
# COMPRESSION
# ============================================================

class TestCompression:
    def test_compress_lzw(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"comp_lzw_{uuid.uuid4().hex}.tif")
        result = compress(single_band_path, dst, algorithm="lzw")
        assert os.path.isfile(result)
        info = get_compression_info(result)
        assert info["algorithm"] == "LZW"

    def test_compress_deflate(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"comp_def_{uuid.uuid4().hex}.tif")
        result = compress(single_band_path, dst, algorithm="deflate", level=6)
        assert os.path.isfile(result)
        info = get_compression_info(result)
        assert info["algorithm"] == "DEFLATE"

    def test_compress_zstd(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"comp_zstd_{uuid.uuid4().hex}.tif")
        result = compress(single_band_path, dst, algorithm="zstd", level=3)
        assert os.path.isfile(result)
        info = get_compression_info(result)
        assert info["algorithm"] == "ZSTD"

    def test_decompress(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"decomp_{uuid.uuid4().hex}.tif")
        result = decompress(single_band_path, dst)
        assert os.path.isfile(result)
        info = get_raster_info(result)
        assert info["compression"] is None

    def test_compression_info(self, single_band_path):
        info = get_compression_info(single_band_path)
        assert info["algorithm"] in ("LZW", None)
        assert info["compressed_size_bytes"] > 0

    def test_compress_invalid_algo(self, single_band_path):
        dst = os.path.join(TEST_DIR, "bad_algo.tif")
        with pytest.raises(UnsupportedFormatError):
            compress(single_band_path, dst, algorithm="nonexistent")

    def test_estimate_ratio(self, single_band_path):
        from app.raster.compression import estimate_compression_ratio
        ratio = estimate_compression_ratio(single_band_path, algorithm="lzw")
        assert ratio > 0


# ============================================================
# TILING
# ============================================================

class TestTiling:
    def test_create_tiles(self, multi_band_path):
        out_dir = os.path.join(TEST_DIR, f"tiles_{uuid.uuid4().hex}")
        tiles = create_tiles(multi_band_path, out_dir, tile_size=64, prefix="t")
        assert len(tiles) > 0
        for t in tiles:
            assert os.path.isfile(t["path"])
            assert "bounds" in t
        assert len(os.listdir(out_dir)) == len(tiles)

    def test_create_tile_index(self, multi_band_path):
        index = create_tile_index(multi_band_path, tile_size=64)
        assert index["n_cols"] > 0
        assert index["n_rows"] > 0
        assert index["width"] == WIDTH
        assert index["height"] == HEIGHT
        assert len(index["tiles"]) == index["n_cols"] * index["n_rows"]

    def test_read_tile(self, multi_band_path):
        data, meta = read_tile(multi_band_path, 0, 0, tile_size=64)
        assert data is not None
        assert "transform" in meta
        assert "crs" in meta

    def test_read_tile_out_of_bounds(self, multi_band_path):
        with pytest.raises(RasterError):
            read_tile(multi_band_path, 999, 999, tile_size=64)

    def test_create_tiles_with_overlap(self, single_band_path):
        out_dir = os.path.join(TEST_DIR, f"tiles_overlap_{uuid.uuid4().hex}")
        tiles = create_tiles(single_band_path, out_dir, tile_size=64, overlap=8)
        assert len(tiles) > 0


# ============================================================
# STATISTICS
# ============================================================

class TestStatistics:
    def test_compute_statistics(self, single_band_path):
        stats = compute_statistics(single_band_path, band=1)
        assert stats["min"] is not None
        assert stats["max"] is not None
        assert stats["mean"] is not None
        assert stats["std"] is not None
        assert stats["band"] == 1
        assert 0 <= stats["min"] <= stats["max"] <= 1.0

    def test_compute_all_statistics(self, multi_band_path):
        all_stats = compute_all_statistics(multi_band_path)
        assert len(all_stats["bands"]) == 4
        for b in all_stats["bands"]:
            assert b["min"] is not None
        assert all_stats["total_stats"]["band_count"] == 4

    def test_compute_histogram(self, single_band_path):
        hist = compute_histogram(single_band_path, band=1, bins=64)
        assert len(hist["histogram"]) == 64
        assert hist["band"] == 1
        assert hist["bins"] == 64

    def test_compute_percentiles(self, single_band_path):
        percentiles = compute_percentiles(single_band_path, band=1)
        assert len(percentiles) == 7
        for p in ["2", "10", "25", "50", "75", "90", "98"]:
            assert p in percentiles
            assert percentiles[p] is not None
        assert percentiles["2"] <= percentiles["50"] <= percentiles["98"]

    def test_compute_percentiles_custom(self, single_band_path):
        percentiles = compute_percentiles(single_band_path, band=1, percentiles=[5, 95])
        assert "5" in percentiles
        assert "95" in percentiles

    def test_nodata_percentage(self, single_band_path):
        result = compute_nodata_percentage(single_band_path, band=1)
        assert result["band"] == 1
        assert 0 <= result["nodata_pct"] <= 100
        assert result["total_count"] > 0

    def test_compute_statistics_int_raster(self, int_band_path):
        stats = compute_statistics(int_band_path, band=1)
        assert stats["min"] is not None
        assert 0 <= stats["min"] <= stats["max"] <= 255

    def test_compute_statistics_invalid_band(self, single_band_path):
        with pytest.raises(RasterError):
            compute_statistics(single_band_path, band=99)


# ============================================================
# PREVIEW
# ============================================================

class TestPreview:
    def test_create_png_preview(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"preview_{uuid.uuid4().hex}.png")
        result = create_png_preview(multi_band_path, dst, band=2)
        assert os.path.isfile(result)
        assert result.endswith(".png")
        assert os.path.getsize(result) > 100

    def test_create_jpeg_preview(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"jpeg_{uuid.uuid4().hex}.jpg")
        result = create_jpeg_preview(multi_band_path, dst, band=1, quality=90)
        assert os.path.isfile(result)
        assert os.path.getsize(result) > 50

    def test_create_thumbnail(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"thumb_{uuid.uuid4().hex}.png")
        result = create_thumbnail(single_band_path, dst, size=(64, 64))
        assert os.path.isfile(result)
        from PIL import Image
        with Image.open(result) as img:
            assert img.size[0] <= 64
            assert img.size[1] <= 64

    def test_create_false_color(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"falsecolor_{uuid.uuid4().hex}.png")
        result = create_false_color_composite(
            multi_band_path, dst, red_band=3, green_band=2, blue_band=1
        )
        assert os.path.isfile(result)
        from PIL import Image
        with Image.open(result) as img:
            assert img.mode == "RGB"

    def test_create_png_preview_with_dimensions(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"preview_dim_{uuid.uuid4().hex}.png")
        result = create_png_preview(single_band_path, dst, width=100, height=80)
        assert os.path.isfile(result)
        from PIL import Image
        with Image.open(result) as img:
            assert img.size[0] == 100
            assert img.size[1] == 80

    def test_create_jpeg_preview_quality(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"jpeg_q_{uuid.uuid4().hex}.jpg")
        create_jpeg_preview(single_band_path, dst, band=1, quality=10)
        assert os.path.isfile(dst)
        create_jpeg_preview(single_band_path, dst.replace(".jpg", "_hq.jpg"), band=1, quality=100)
        assert os.path.isfile(dst.replace(".jpg", "_hq.jpg"))


# ============================================================
# MANAGER
# ============================================================

class TestManager:
    def test_manager_info(self, manager, multi_band_path):
        info = manager.info(multi_band_path)
        assert info["width"] == WIDTH
        assert info["count"] == 4

    def test_manager_metadata(self, manager, multi_band_path):
        meta = manager.metadata(multi_band_path)
        assert meta["crs"] == CRS
        assert meta["count"] == 4

    def test_manager_validate(self, manager, single_band_path):
        report = manager.validate(single_band_path)
        assert report["valid"] is True

    def test_manager_read(self, manager, multi_band_path):
        data, meta = manager.read(multi_band_path)
        assert data.shape[0] == 4

    def test_manager_read_bbox(self, manager, multi_band_path):
        data, meta = manager.read_bbox(multi_band_path, (72.5, 18.5, 73.0, 19.0))
        assert data.ndim == 3

    def test_manager_write_and_read(self, manager):
        data = NP_RANDOM.rand(HEIGHT, WIDTH).astype(np.float32)
        path = os.path.join(TEST_DIR, f"mgr_write_{uuid.uuid4().hex}.tif")
        manager.write(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA)
        read_data, meta = manager.read(path)
        assert read_data.shape == (HEIGHT, WIDTH)
        assert np.allclose(data, read_data, atol=1e-6)

    def test_manager_write_cog(self, manager):
        data = NP_RANDOM.rand(3, HEIGHT, WIDTH).astype(np.float32)
        path = os.path.join(TEST_DIR, f"mgr_cog_{uuid.uuid4().hex}.tif")
        manager.write_cog(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA)
        info = manager.info(path)
        assert info["tiled"] is True

    def test_manager_crop(self, manager, multi_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_crop_{uuid.uuid4().hex}.tif")
        manager.crop(multi_band_path, dst, (72.5, 18.5, 73.0, 19.0))
        assert os.path.isfile(dst)

    def test_manager_reproject(self, manager, single_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_reproj_{uuid.uuid4().hex}.tif")
        manager.reproject(single_band_path, dst, "EPSG:3857")
        info = manager.info(dst)
        assert info["crs"] == "EPSG:3857"

    def test_manager_statistics(self, manager, multi_band_path):
        stats = manager.statistics(multi_band_path, band=1)
        assert stats["min"] is not None

    def test_manager_all_statistics(self, manager, multi_band_path):
        all_stats = manager.all_statistics(multi_band_path)
        assert len(all_stats["bands"]) == 4

    def test_manager_preview(self, manager, single_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_preview_{uuid.uuid4().hex}.png")
        manager.create_png_preview(single_band_path, dst)
        assert os.path.isfile(dst)

    def test_manager_tiles(self, manager, single_band_path):
        out_dir = os.path.join(TEST_DIR, f"mgr_tiles_{uuid.uuid4().hex}")
        tiles = manager.create_tiles(single_band_path, out_dir, tile_size=64)
        assert len(tiles) > 0

    def test_manager_compress(self, manager, single_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_comp_{uuid.uuid4().hex}.tif")
        manager.compress(single_band_path, dst, algorithm="zstd")
        assert os.path.isfile(dst)

    def test_manager_extract_band(self, manager, multi_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_extract_{uuid.uuid4().hex}.tif")
        manager.extract_band(multi_band_path, dst, band=2)
        info = manager.info(dst)
        assert info["count"] == 1

    def test_manager_health_report(self, manager):
        report = manager.health_report()
        assert "readiness_score" in report
        assert "status" in report
        assert "capabilities" in report
        assert "dependencies" in report
        assert report["dependencies"]["rasterio"] is True
        assert report["dependencies"]["numpy"] is True

    def test_manager_thumbnail(self, manager, single_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_thumb_{uuid.uuid4().hex}.png")
        manager.create_thumbnail(single_band_path, dst, size=(32, 32))
        assert os.path.isfile(dst)

    def test_manager_false_color(self, manager, multi_band_path):
        dst = os.path.join(TEST_DIR, f"mgr_fc_{uuid.uuid4().hex}.png")
        manager.create_false_color(multi_band_path, dst)
        assert os.path.isfile(dst)

    def test_manager_histogram(self, manager, single_band_path):
        hist = manager.histogram(single_band_path, band=1, bins=128)
        assert len(hist["histogram"]) == 128

    def test_manager_percentiles(self, manager, single_band_path):
        pcts = manager.percentiles(single_band_path, band=1)
        assert len(pcts) == 7

    def test_manager_nodata_pct(self, manager, single_band_path):
        result = manager.nodata_percentage(single_band_path, band=1)
        assert 0 <= result["nodata_pct"] <= 100


# ============================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================

class TestEdgeCases:
    def test_file_not_found(self):
        with pytest.raises(RasterNotFoundError):
            read_bands("/nonexistent.tif")

    def test_corrupted_file_error(self):
        path = os.path.join(TEST_DIR, f"bad_file_{uuid.uuid4().hex}.tif")
        with open(path, "w") as f:
            f.write("not a binary tiff")
        with pytest.raises(RasterError):
            read_bands(path)

    def test_extract_band_invalid_index(self, single_band_path):
        with pytest.raises(RasterError):
            read_bands(single_band_path, bands=[99])

    def test_zero_size_raster(self):
        path = os.path.join(TEST_DIR, f"zero_{uuid.uuid4().hex}.tif")
        with open(path, "wb") as f:
            f.write(b"")
        with pytest.raises(RasterError):
            extract_metadata(path)

    def test_invalid_compression_algorithm(self, single_band_path):
        from app.raster.writer import _validate_compression
        with pytest.raises(UnsupportedFormatError):
            _validate_compression("rar")

    def test_transform_no_src(self):
        with pytest.raises(RasterNotFoundError):
            crop("/nonexistent.tif", "/tmp/out.tif", (0, 0, 1, 1))


# ============================================================
# CRS PRESERVATION
# ============================================================

class TestCRSPreservation:
    def test_write_preserves_crs(self, single_band_path):
        assert get_raster_info(single_band_path)["crs"] == CRS

    def test_crop_preserves_crs(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"crs_crop_{uuid.uuid4().hex}.tif")
        crop(single_band_path, dst, (72.0, 18.5, 72.5, 19.5))
        assert get_raster_info(dst)["crs"] == CRS

    def test_resample_preserves_crs(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"crs_resamp_{uuid.uuid4().hex}.tif")
        resample(single_band_path, dst, scale_factor=0.5)
        assert get_raster_info(dst)["crs"] == CRS

    def test_extract_band_preserves_crs(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"crs_extract_{uuid.uuid4().hex}.tif")
        extract_band(multi_band_path, dst, band=1)
        assert get_raster_info(dst)["crs"] == CRS

    def test_merge_preserves_crs(self):
        paths = []
        for i in range(2):
            data = NP_RANDOM.rand(32, 32).astype(np.float32)
            p = os.path.join(TEST_DIR, f"merge_crs_{i}_{uuid.uuid4().hex}.tif")
            offset = 72.0 + i * 0.5
            t = (0.1, 0.0, offset, 0.0, -0.1, 19.0)
            write_geotiff(p, data, transform=t, crs=CRS, nodata=NODATA)
            paths.append(p)
        dst = os.path.join(TEST_DIR, f"merge_crs_out_{uuid.uuid4().hex}.tif")
        merge(paths, dst)
        assert get_raster_info(dst)["crs"] == CRS

    def test_stack_preserves_crs(self, single_band_path):
        paths = [single_band_path, single_band_path]
        dst = os.path.join(TEST_DIR, f"stack_crs_{uuid.uuid4().hex}.tif")
        stack_bands(paths, dst)
        assert get_raster_info(dst)["crs"] == CRS

    def test_compress_preserves_crs(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"crs_comp_{uuid.uuid4().hex}.tif")
        compress(single_band_path, dst, algorithm="lzw")
        assert get_raster_info(dst)["crs"] == CRS

    def test_tiling_preserves_crs(self, single_band_path):
        out_dir = os.path.join(TEST_DIR, f"crs_tiles_{uuid.uuid4().hex}")
        tiles = create_tiles(single_band_path, out_dir, tile_size=64)
        if tiles:
            assert get_raster_info(tiles[0]["path"])["crs"] == CRS


# ============================================================
# NODATA HANDLING
# ============================================================

class TestNoDataHandling:
    def test_nodata_preserved_write(self, single_band_path):
        assert get_raster_info(single_band_path)["nodata"] == NODATA

    def test_nodata_in_read_masked(self, single_band_path):
        data, _ = read_bands(single_band_path, masked=True)
        assert isinstance(data, np.ma.MaskedArray)

    def test_nodata_preserved_crop(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"nd_crop_{uuid.uuid4().hex}.tif")
        crop(single_band_path, dst, (72.0, 18.5, 72.5, 19.5))
        info = get_raster_info(dst)
        assert info["nodata"] == NODATA

    def test_nodata_preserved_resample(self, single_band_path):
        dst = os.path.join(TEST_DIR, f"nd_resamp_{uuid.uuid4().hex}.tif")
        resample(single_band_path, dst, scale_factor=0.5)
        info = get_raster_info(dst)
        assert info["nodata"] == NODATA

    def test_nodata_preserved_extract(self, multi_band_path):
        dst = os.path.join(TEST_DIR, f"nd_extract_{uuid.uuid4().hex}.tif")
        extract_band(multi_band_path, dst, band=1)
        info = get_raster_info(dst)
        assert info["nodata"] == NODATA

    def test_nodata_all_valid(self):
        data = NP_RANDOM.rand(HEIGHT, WIDTH).astype(np.float32)
        path = os.path.join(TEST_DIR, f"no_nodata_{uuid.uuid4().hex}.tif")
        write_geotiff(path, data, transform=TRANSFORM, crs=CRS)
        info = get_raster_info(path)
        assert info["nodata"] is None

    def test_nodata_percentage_all_valid(self):
        data = np.ones((64, 64), dtype=np.float32)
        path = os.path.join(TEST_DIR, f"all_valid_{uuid.uuid4().hex}.tif")
        write_geotiff(path, data, transform=TRANSFORM, crs=CRS, nodata=NODATA)
        result = compute_nodata_percentage(path, band=1)
        assert result["nodata_pct"] == 0.0


# ============================================================
# CLEANUP
# ============================================================

def teardown_module():
    import shutil
    if os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
