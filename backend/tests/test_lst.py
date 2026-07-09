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

from app.lst.exceptions import (
    LSTError,
    SatelliteNotSupportedError,
    MissingThermalBandError,
    MissingSupportBandError,
    RadianceConversionError,
    BrightnessTemperatureError,
    EmissivityError,
    AtmosphericError,
    AlgorithmNotAvailableError,
    UncertaintyError,
    ValidationError,
    ComputationError,
)
from app.lst.registry import (
    get_satellite,
    get_thermal_band,
    list_supported_satellites,
    SATELLITE_REGISTRY,
    SatelliteDefinition,
    ThermalBandInfo,
)
from app.lst.algorithms import (
    get_algorithm,
    list_algorithms,
    ALGORITHM_REGISTRY,
    AlgorithmDefinition,
)
from app.lst.brightness_temperature import (
    dn_to_radiance,
    radiance_to_brightness_temperature,
    brightness_temperature_celsius,
    calculate_brightness_temperature,
)
from app.lst.emissivity import (
    ndvi_threshold_emissivity,
    vegetation_fraction,
    emissivity_water,
    emissivity_bare_soil,
    emissivity_urban,
    DEFAULT_EMISSIVITY_WATER,
    DEFAULT_EMISSIVITY_SOIL,
    DEFAULT_EMISSIVITY_VEGETATION,
    DEFAULT_EMISSIVITY_URBAN,
)
from app.lst.atmospheric import (
    SingleChannelCorrection,
    SingleChannelRTECorrection,
    SplitWindowCorrection,
    create_atmospheric_correction,
    AtmosphericCorrection,
)
from app.lst.uncertainty import (
    sensor_uncertainty,
    emissivity_uncertainty,
    atmospheric_uncertainty,
    total_uncertainty,
    confidence_interval,
    quality_score_from_uncertainty,
)
from app.lst.quality import (
    create_quality_mask,
    interpret_flags,
    describe_qa_mask,
    CLOUD, WATER, SNOW, LOW_EMISSIVITY,
    MISSING_BAND, INTERPOLATED, HIGH_UNCERTAINTY, URBAN_HOTSPOT,
)
from app.lst.validator import (
    validate_thermal_data,
    validate_supporting_bands,
    validate_dimensions,
    validate_crs,
    validate_nodata,
    validate_value_range,
)
from app.lst.statistics import compute_lst_statistics
from app.lst.visualization import (
    render_temperature_map,
    render_histogram,
    render_hotspot_overlay,
)
from app.lst.metadata import build_lst_metadata
from app.lst.engine import LSTEngine

WIDTH, HEIGHT = 64, 48
CRS_EPSG = "EPSG:4326"
TEST_DIR = None


def setup_module():
    global TEST_DIR
    TEST_DIR = tempfile.mkdtemp(prefix="lst_test_")


def teardown_module():
    if TEST_DIR and os.path.isdir(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def _random_band(seed=42, width=WIDTH, height=HEIGHT):
    rng = np.random.RandomState(seed)
    return rng.rand(height, width).astype(np.float32)


def _thermal_data(seed=42, width=WIDTH, height=HEIGHT, with_nodata=False):
    rng = np.random.RandomState(seed)
    data = rng.uniform(10000, 18000, (height, width)).astype(np.float32)
    if with_nodata:
        data[0:5, 0:5] = -9999
    return data


def _ndvi_data(seed=99, width=WIDTH, height=HEIGHT):
    rng = np.random.RandomState(seed)
    return rng.uniform(-0.3, 0.9, (height, width)).astype(np.float32)


def _create_geotiff(path, data, crs=CRS_EPSG, width=WIDTH, height=HEIGHT):
    transform = from_bounds(-1.0, -1.0, 1.0, 1.0, width, height)
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": data.dtype.name,
        "crs": CRS.from_user_input(crs),
        "transform": transform,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return path


# --- Exceptions ---

class TestExceptions:
    def test_lst_error_base(self):
        assert issubclass(SatelliteNotSupportedError, LSTError)
        assert issubclass(MissingThermalBandError, LSTError)
        assert issubclass(MissingSupportBandError, LSTError)
        assert issubclass(RadianceConversionError, LSTError)
        assert issubclass(BrightnessTemperatureError, LSTError)
        assert issubclass(EmissivityError, LSTError)
        assert issubclass(AtmosphericError, LSTError)
        assert issubclass(AlgorithmNotAvailableError, LSTError)
        assert issubclass(UncertaintyError, LSTError)
        assert issubclass(ValidationError, LSTError)
        assert issubclass(ComputationError, LSTError)

    def test_exception_raises_and_message(self):
        for exc_cls in [
            SatelliteNotSupportedError, MissingThermalBandError,
            MissingSupportBandError, RadianceConversionError,
            BrightnessTemperatureError, EmissivityError,
            AtmosphericError, AlgorithmNotAvailableError,
            UncertaintyError, ValidationError, ComputationError,
        ]:
            with pytest.raises(exc_cls):
                raise exc_cls("test message")


# --- Registry ---

class TestRegistry:
    def test_list_supported_satellites(self):
        sats = list_supported_satellites()
        assert "landsat8" in sats
        assert "landsat9" in sats
        assert "ecostress" in sats
        assert "modis" in sats
        assert "aster" in sats

    def test_get_satellite_landsat8(self):
        sat = get_satellite("landsat8")
        assert sat.name == "landsat8"
        assert sat.full_name == "Landsat-8"
        assert "Band10" in sat.thermal_bands
        assert "Band11" in sat.thermal_bands

    def test_get_satellite_landsat9(self):
        sat = get_satellite("landsat9")
        assert sat.full_name == "Landsat-9"

    def test_get_satellite_case_insensitive(self):
        sat = get_satellite("Landsat8")
        assert sat.name == "landsat8"

    def test_get_satellite_full_name(self):
        sat = get_satellite("Landsat-8")
        assert sat.name == "landsat8"

    def test_get_satellite_not_found(self):
        with pytest.raises(SatelliteNotSupportedError):
            get_satellite("nonexistent")

    def test_get_thermal_band_band10(self):
        info = get_thermal_band("landsat8", "Band10")
        assert info.band_name == "Band10"
        assert info.effective_wavelength == 10.895
        assert info.k1 == 774.8853
        assert info.k2 == 1321.0789
        assert info.ml == 3.3420e-4
        assert info.al == 0.1
        assert info.resolution == 100.0

    def test_get_thermal_band_band11(self):
        info = get_thermal_band("landsat9", "Band11")
        assert info.k1 == 480.8883
        assert info.k2 == 1201.1442

    def test_get_thermal_band_not_found(self):
        with pytest.raises(SatelliteNotSupportedError):
            get_thermal_band("landsat8", "Band99")

    def test_satellite_definition_dataclass(self):
        sat = get_satellite("ecostress")
        assert sat.name == "ecostress"
        assert "thermal" in sat.thermal_bands

    def test_thermal_band_info_dataclass(self):
        info = get_thermal_band("modis", "Band31")
        assert info.effective_wavelength == 11.03
        assert info.resolution == 1000.0

    def test_register_persistence(self):
        assert "landsat8" in SATELLITE_REGISTRY
        assert "landsat-8" in SATELLITE_REGISTRY

    def test_ecostress_definition(self):
        sat = get_satellite("ecostress")
        assert sat.reference
        assert sat.notes

    def test_aster_bands(self):
        sat = get_satellite("aster")
        assert len(sat.thermal_bands) == 5

    def test_landsat8_band10_constants(self):
        info = get_thermal_band("landsat8", "Band10")
        np.testing.assert_almost_equal(info.k1, 774.8853)
        np.testing.assert_almost_equal(info.k2, 1321.0789)

    def test_landsat9_equals_landsat8(self):
        l8 = get_thermal_band("landsat8", "Band10")
        l9 = get_thermal_band("landsat9", "Band10")
        assert l8.k1 == l9.k1
        assert l8.k2 == l9.k2


# --- Algorithms ---

class TestAlgorithms:
    def test_list_algorithms(self):
        algs = list_algorithms()
        names = [a.name for a in algs]
        assert "SingleChannel" in names
        assert "SingleChannelRTE" in names
        assert "SplitWindow" in names
        assert "TES" in names

    def test_get_algorithm_single_channel(self):
        alg = get_algorithm("SingleChannel")
        assert alg.name == "SingleChannel"
        assert "Jim" in alg.description
        assert len(alg.assumptions) > 0
        assert len(alg.limitations) > 0
        assert alg.expected_accuracy
        assert alg.urban_heat_applicability

    def test_get_algorithm_case_insensitive(self):
        alg = get_algorithm("singlechannel")
        assert alg.name == "SingleChannel"

    def test_get_algorithm_not_found(self):
        with pytest.raises(AlgorithmNotAvailableError):
            get_algorithm("unknown")

    def test_algorithm_tags_single_channel(self):
        alg = get_algorithm("SingleChannel")
        assert "single_channel" in alg.tags

    def test_algorithm_tags_split_window(self):
        alg = get_algorithm("SplitWindow")
        assert "split_window" in alg.tags

    def test_algorithm_tags_thermal(self):
        alg = get_algorithm("TES")
        assert "thermal" in alg.tags

    def test_single_channel_equation(self):
        alg = get_algorithm("SingleChannel")
        assert "T_b" in alg.equation
        assert "ln" in alg.equation

    def test_split_window_equation(self):
        alg = get_algorithm("SplitWindow")
        assert "T_i" in alg.equation
        assert "T_j" in alg.equation

    def test_tes_equation(self):
        alg = get_algorithm("TES")
        assert "NEM" in alg.equation

    def test_algorithm_required_inputs(self):
        alg = get_algorithm("SingleChannelRTE")
        assert "thermal_radiance" in alg.required_inputs
        assert "transmissivity" in alg.required_inputs

    def test_rte_optional_inputs(self):
        alg = get_algorithm("SingleChannel")
        assert "water_vapor" in alg.optional_inputs

    def test_all_algorithms_have_reference(self):
        for alg in list_algorithms():
            assert alg.description
            assert len(alg.assumptions) >= 2
            assert len(alg.limitations) >= 1


# --- Brightness Temperature ---

class TestBrightnessTemperature:
    def test_dn_to_radiance(self):
        dn = np.array([[10000, 15000], [20000, 30000]], dtype=np.float32)
        rad = dn_to_radiance(dn, ml=3.3420e-4, al=0.1)
        expected = dn * 3.3420e-4 + 0.1
        np.testing.assert_allclose(rad, expected)

    def test_dn_to_radiance_zero_dn(self):
        dn = np.zeros((4, 4), dtype=np.float32)
        rad = dn_to_radiance(dn, ml=3.3420e-4, al=0.1)
        np.testing.assert_allclose(rad, 0.1)

    def test_radiance_to_brightness_temperature(self):
        radiance = np.array([[5.0, 8.0], [10.0, 12.0]], dtype=np.float64)
        bt = radiance_to_brightness_temperature(radiance, k1=774.8853, k2=1321.0789)
        assert np.all(bt > 200)
        assert np.all(bt < 400)

    def test_radiance_to_bt_known_value(self):
        radiance = np.array([[7.0]])
        bt = radiance_to_brightness_temperature(radiance, k1=774.8853, k2=1321.0789)
        expected = 1321.0789 / np.log(774.8853 / 7.0 + 1.0)
        np.testing.assert_allclose(bt[0, 0], expected, rtol=1e-5)

    def test_radiance_to_bt_non_positive(self):
        radiance = np.array([[0.0]], dtype=np.float64)
        with pytest.raises(BrightnessTemperatureError):
            radiance_to_brightness_temperature(radiance, k1=774.8853, k2=1321.0789)

    def test_radiance_to_bt_negative(self):
        radiance = np.array([[-1.0]], dtype=np.float64)
        with pytest.raises(BrightnessTemperatureError):
            radiance_to_brightness_temperature(radiance, k1=774.8853, k2=1321.0789)

    def test_brightness_temperature_celsius(self):
        bt_k = np.array([[300.0, 310.0]])
        bt_c = brightness_temperature_celsius(bt_k)
        np.testing.assert_allclose(bt_c, np.array([[26.85, 36.85]]))

    def test_calculate_bt_with_ml_al(self):
        data = _thermal_data(seed=42)
        result = calculate_brightness_temperature(data, k1=774.8853, k2=1321.0789, ml=3.3420e-4, al=0.1)
        assert "bt_kelvin" in result
        assert "bt_celsius" in result
        assert "radiance" in result
        assert np.all(np.isfinite(result["bt_kelvin"]))
        assert result["bt_kelvin"].shape == (HEIGHT, WIDTH)

    def test_calculate_bt_without_ml_al(self):
        radiance = np.random.RandomState(42).uniform(3.0, 15.0, (HEIGHT, WIDTH)).astype(np.float32)
        result = calculate_brightness_temperature(radiance, k1=774.8853, k2=1321.0789)
        assert result["bt_kelvin"].shape == (HEIGHT, WIDTH)

    def test_calculate_bt_3d_array(self):
        data = np.random.RandomState(42).uniform(10000, 20000, (1, HEIGHT, WIDTH)).astype(np.float32)
        result = calculate_brightness_temperature(data, k1=774.8853, k2=1321.0789, ml=3.3420e-4, al=0.1)
        assert result["bt_kelvin"].shape == (HEIGHT, WIDTH)

    def test_bt_celsius_delta_from_bt_kelvin(self):
        data = _thermal_data(seed=42)
        result = calculate_brightness_temperature(data, k1=774.8853, k2=1321.0789, ml=3.3420e-4, al=0.1)
        np.testing.assert_allclose(result["bt_celsius"], result["bt_kelvin"] - 273.15)


# --- Emissivity ---

class TestEmissivity:
    def test_ndvi_threshold_emissivity_water(self):
        ndvi = np.array([[-0.2, -0.1], [0.0, 0.1]], dtype=np.float32)
        emis = ndvi_threshold_emissivity(ndvi)
        assert np.all(emis[ndvi < 0] == DEFAULT_EMISSIVITY_WATER)

    def test_ndvi_threshold_emissivity_bare_soil(self):
        ndvi = np.array([[0.1, 0.15]], dtype=np.float32)
        emis = ndvi_threshold_emissivity(ndvi)
        assert np.all(emis > 0.9)
        assert np.all(emis < 1.0)

    def test_ndvi_threshold_emissivity_mixed(self):
        ndvi = np.array([[0.3, 0.4]], dtype=np.float32)
        emis = ndvi_threshold_emissivity(ndvi)
        assert np.all(emis > 0.95)
        assert np.all(emis < 1.0)

    def test_ndvi_threshold_emissivity_dense_veg(self):
        ndvi = np.array([[0.6, 0.8]], dtype=np.float32)
        emis = ndvi_threshold_emissivity(ndvi)
        assert np.all(emis > 0.98)
        assert np.all(emis <= 1.0)

    def test_ndvi_threshold_clip_range(self):
        ndvi = np.array([[2.0, -2.0]], dtype=np.float32)
        emis = ndvi_threshold_emissivity(ndvi)
        assert np.all(emis >= 0.9)
        assert np.all(emis <= 1.0)

    def test_vegetation_fraction(self):
        ndvi = np.array([[0.0, 0.2, 0.5, 0.8]], dtype=np.float32)
        fvc = vegetation_fraction(ndvi)
        assert fvc[0, 0] == 0.0
        assert fvc[0, 2] == 1.0
        assert np.all(fvc >= 0)
        assert np.all(fvc <= 1)

    def test_emissivity_water(self):
        emis = emissivity_water((4, 4))
        assert emis.shape == (4, 4)
        assert np.all(emis == DEFAULT_EMISSIVITY_WATER)

    def test_emissivity_bare_soil(self):
        emis = emissivity_bare_soil((3, 3))
        assert emis.shape == (3, 3)
        assert np.all(emis == DEFAULT_EMISSIVITY_SOIL)

    def test_emissivity_urban_with_ndvi(self):
        ndvi = _ndvi_data()
        emis = emissivity_urban(ndvi=ndvi)
        assert emis.shape == (HEIGHT, WIDTH)
        assert np.all(emis >= 0.9)
        assert np.all(emis <= 1.0)

    def test_emissivity_urban_with_impervious(self):
        imp = np.ones((10, 10), dtype=np.float32)
        emis = emissivity_urban(impervious_fraction=imp)
        assert np.all(emis == DEFAULT_EMISSIVITY_URBAN)

    def test_emissivity_urban_no_input(self):
        with pytest.raises(EmissivityError):
            emissivity_urban()


# --- Atmospheric Correction ---

class TestAtmospheric:
    def test_single_channel_correction_basic(self):
        bt_kelvin = np.array([[300.0, 305.0]], dtype=np.float64)
        radiance = np.array([[8.0, 9.0]], dtype=np.float64)
        emissivity = np.array([[0.98, 0.97]], dtype=np.float64)
        sc = SingleChannelCorrection()
        lst = sc.correct(radiance, bt_kelvin, emissivity, effective_wavelength=10.895)
        assert lst.shape == bt_kelvin.shape
        assert np.all(np.isfinite(lst))
        assert np.all(lst > 200)
        assert np.all(lst < 400)

    def test_single_channel_with_water_vapor(self):
        bt = np.full((4, 4), 300.0, dtype=np.float64)
        rad = np.full((4, 4), 8.0, dtype=np.float64)
        emis = np.full((4, 4), 0.98, dtype=np.float64)
        sc = SingleChannelCorrection(water_vapor=1.5)
        lst = sc.correct(rad, bt, emis)
        assert np.all(np.isfinite(lst))

    def test_single_channel_identity_emissivity(self):
        bt = np.array([[300.0]])
        rad = np.array([[8.0]])
        emis = np.array([[1.0]])
        sc = SingleChannelCorrection()
        lst = sc.correct(rad, bt, emis)
        np.testing.assert_allclose(lst, bt, rtol=1e-3)

    def test_single_channel_rte_requires_params(self):
        bt = np.full((2, 2), 300.0)
        rad = np.full((2, 2), 8.0)
        emis = np.full((2, 2), 0.98)
        rte = SingleChannelRTECorrection()
        with pytest.raises(AtmosphericError):
            rte.correct(rad, bt, emis)

    def test_single_channel_rte_with_params(self):
        bt = np.full((2, 2), 300.0, dtype=np.float64)
        rad = np.full((2, 2), 8.0, dtype=np.float64)
        emis = np.full((2, 2), 0.98, dtype=np.float64)
        rte = SingleChannelRTECorrection(
            transmissivity=0.8, upwelling_radiance=0.5, downwelling_radiance=1.0
        )
        lst = rte.correct(rad, bt, emis)
        assert np.all(np.isfinite(lst))

    def test_split_window_requires_two_bands(self):
        bt = np.full((2, 2), 300.0)
        rad = np.full((2, 2), 8.0)
        emis = np.full((2, 2), 0.98)
        sw = SplitWindowCorrection()
        with pytest.raises(AtmosphericError):
            sw.correct(rad, bt, emis)

    def test_split_window_with_two_bands(self):
        bt_i = np.full((2, 2), 300.0, dtype=np.float64)
        bt_j = np.full((2, 2), 298.0, dtype=np.float64)
        eps_j = np.full((2, 2), 0.97, dtype=np.float64)
        sw = SplitWindowCorrection()
        lst = sw.correct(bt_i, bt_i, eps_j, bt_band_i=bt_i, bt_band_j=bt_j, emissivity_j=eps_j)
        assert np.all(np.isfinite(lst))

    def test_create_atmospheric_correction(self):
        ac = create_atmospheric_correction("single_channel")
        assert isinstance(ac, SingleChannelCorrection)

    def test_create_atmospheric_correction_rte(self):
        ac = create_atmospheric_correction("single_channel_rte")
        assert isinstance(ac, SingleChannelRTECorrection)

    def test_create_atmospheric_correction_split(self):
        ac = create_atmospheric_correction("split_window")
        assert isinstance(ac, SplitWindowCorrection)

    def test_create_atmospheric_correction_unknown(self):
        with pytest.raises(AtmosphericError):
            create_atmospheric_correction("unknown")

    def test_atmospheric_correction_base_raises(self):
        ac = AtmosphericCorrection()
        with pytest.raises(NotImplementedError):
            ac.correct(np.ones((2, 2)), np.ones((2, 2)), np.ones((2, 2)))


# --- Uncertainty ---

class TestUncertainty:
    def test_sensor_uncertainty_landsat8(self):
        u = sensor_uncertainty("landsat8")
        assert u == 0.5

    def test_sensor_uncertainty_unknown(self):
        u = sensor_uncertainty("unknown")
        assert u == 1.0

    def test_emissivity_uncertainty_default(self):
        emis = np.full((4, 4), 0.98, dtype=np.float64)
        u = emissivity_uncertainty(emis)
        assert u.shape == (4, 4)
        assert np.all(u > 0)

    def test_emissivity_uncertainty_with_bt(self):
        emis = np.full((4, 4), 0.98, dtype=np.float64)
        bt = np.full((4, 4), 300.0, dtype=np.float64)
        u = emissivity_uncertainty(emis, brightness_temp=bt)
        assert u.shape == (4, 4)

    def test_atmospheric_uncertainty_default(self):
        u = atmospheric_uncertainty()
        assert u == 0.5

    def test_atmospheric_uncertainty_with_wv(self):
        u = atmospheric_uncertainty(water_vapor=2.0)
        assert u == 0.5 + 0.3 * 2.0

    def test_total_uncertainty_scalar(self):
        total = total_uncertainty(0.5, 0.3, 0.5)
        expected = np.sqrt(0.5**2 + 0.3**2 + 0.5**2)
        np.testing.assert_allclose(total, expected)

    def test_total_uncertainty_array(self):
        s = np.full((3, 3), 0.5, dtype=np.float64)
        e = np.full((3, 3), 0.3, dtype=np.float64)
        a = np.full((3, 3), 0.5, dtype=np.float64)
        total = total_uncertainty(s, e, a)
        assert total.shape == (3, 3)

    def test_confidence_interval_95(self):
        lst = np.full((4, 4), 310.0, dtype=np.float64)
        uncert = np.full((4, 4), 1.0, dtype=np.float64)
        lower, mid, upper = confidence_interval(lst, uncert, 0.95)
        assert np.allclose(mid, lst)
        assert np.allclose(upper - mid, 1.96)

    def test_confidence_interval_68(self):
        lst = np.full((4, 4), 310.0)
        uncert = np.full((4, 4), 1.0)
        lower, mid, upper = confidence_interval(lst, uncert, 0.68)
        assert np.allclose(upper - mid, 1.0)

    def test_quality_score_from_uncertainty(self):
        uncert = np.full((10, 10), 1.0)
        score = quality_score_from_uncertainty(uncert)
        assert 0 <= score <= 100


# --- Quality ---

class TestQuality:
    def test_create_quality_mask_shape(self):
        qa = create_quality_mask((10, 10))
        assert qa.shape == (10, 10)
        assert qa.dtype == np.uint8

    def test_create_quality_mask_cloud(self):
        cloud = np.ones((4, 4), dtype=np.uint8)
        qa = create_quality_mask((4, 4), cloud_mask=cloud)
        assert np.all(qa & CLOUD > 0)

    def test_create_quality_mask_water(self):
        ndvi = np.full((4, 4), -0.2, dtype=np.float32)
        qa = create_quality_mask((4, 4), ndvi=ndvi)
        assert np.all(qa & WATER > 0)

    def test_create_quality_mask_hotspot(self):
        lst = np.array([[300, 310], [350, 290]], dtype=np.float64)
        qa = create_quality_mask((2, 2), lst=lst)
        assert qa[1, 0] & URBAN_HOTSPOT > 0

    def test_interpret_flags(self):
        flags = interpret_flags(CLOUD | WATER)
        assert "cloud" in flags
        assert "water" in flags

    def test_interpret_flags_no_flags(self):
        flags = interpret_flags(0)
        assert flags == []

    def test_describe_qa_mask(self):
        qa = np.array([CLOUD, WATER, SNOW, 0], dtype=np.uint8)
        desc = describe_qa_mask(qa)
        assert "cloud" in desc
        assert "clean" in desc

    def test_qa_mask_missing_band(self):
        qa = create_quality_mask((3, 3))
        qa[1, 1] |= MISSING_BAND
        flags = interpret_flags(int(qa[1, 1]))
        assert "missing_band" in flags

    def test_qa_mask_high_uncertainty(self):
        uncert = np.full((4, 4), 5.0, dtype=np.float64)
        qa = create_quality_mask((4, 4), uncertainty=uncert, uncertainty_threshold=3.0)
        assert np.all(qa & HIGH_UNCERTAINTY > 0)


# --- Validator ---

class TestValidator:
    def test_validate_thermal_data_valid(self):
        data = np.random.rand(10, 10).astype(np.float32)
        validate_thermal_data(data)

    def test_validate_thermal_data_none(self):
        with pytest.raises(ValidationError):
            validate_thermal_data(None)

    def test_validate_thermal_data_empty(self):
        with pytest.raises(ValidationError):
            validate_thermal_data(np.array([], dtype=np.float32))

    def test_validate_thermal_data_all_non_positive(self):
        with pytest.raises(ValidationError):
            validate_thermal_data(np.array([[0, -1], [-2, 0]], dtype=np.float32))

    def test_validate_supporting_bands_valid(self):
        ndvi = np.random.rand(10, 10).astype(np.float32)
        validate_supporting_bands(ndvi=ndvi)

    def test_validate_supporting_bands_empty(self):
        with pytest.raises(ValidationError):
            validate_supporting_bands(ndvi=np.array([], dtype=np.float32))

    def test_validate_dimensions_match(self):
        a = np.random.rand(10, 10)
        b = np.random.rand(10, 10)
        validate_dimensions([(a, "a"), (b, "b")])

    def test_validate_dimensions_mismatch(self):
        a = np.random.rand(10, 10)
        b = np.random.rand(5, 5)
        with pytest.raises(ValidationError):
            validate_dimensions([(a, "a"), (b, "b")])

    def test_validate_crs_valid(self):
        validate_crs("EPSG:4326")

    def test_validate_crs_none(self):
        with pytest.raises(ValidationError):
            validate_crs(None)

    def test_validate_nodata_no_nodata(self):
        data = np.random.rand(10, 10)
        frac = validate_nodata(data)
        assert frac == 0.0

    def test_validate_nodata_with_nodata(self):
        data = np.full((10, 10), -9999.0)
        data[5:, 5:] = 1.0
        frac = validate_nodata(data, nodata=-9999.0)
        assert frac > 0.0

    def test_validate_value_range_in_range(self):
        data = np.array([1.0, 2.0, 3.0])
        validate_value_range(data)

    def test_validate_value_range_out_of_range(self):
        data = np.array([-9999.0, 100000.0])
        validate_value_range(data)


# --- Statistics ---

class TestStatistics:
    def test_compute_lst_statistics_basic(self):
        lst = np.array([[300.0, 305.0], [310.0, 315.0]], dtype=np.float64)
        stats = compute_lst_statistics(lst)
        assert stats["mean"] == 307.5
        assert stats["valid_pixels"] == 4
        assert stats["percent_valid"] == 100.0

    def test_compute_lst_statistics_with_nodata(self):
        lst = np.array([[300.0, -9999], [310.0, 315.0]], dtype=np.float64)
        stats = compute_lst_statistics(lst, nodata_value=-9999.0)
        assert stats["valid_pixels"] == 3

    def test_compute_lst_statistics_all_invalid(self):
        lst = np.full((4, 4), np.nan)
        stats = compute_lst_statistics(lst)
        assert stats["valid_pixels"] == 0

    def test_compute_lst_statistics_histogram(self):
        lst = np.random.RandomState(42).uniform(290, 320, (10, 10))
        stats = compute_lst_statistics(lst)
        assert "histogram" in stats
        assert len(stats["histogram"]["counts"]) == 20

    def test_compute_lst_statistics_percentiles(self):
        lst = np.random.RandomState(42).uniform(290, 320, (100,))
        stats = compute_lst_statistics(lst)
        assert stats["p5"] <= stats["p50"]
        assert stats["p50"] <= stats["p95"]

    def test_compute_lst_statistics_hotspot_threshold(self):
        lst = np.arange(100.0).reshape(10, 10)
        stats = compute_lst_statistics(lst, urban_hotspot_percentile=90.0)
        assert stats["urban_hotspot_threshold"] == pytest.approx(89.1, abs=1e-3)

    def test_compute_lst_statistics_with_qa(self):
        lst = np.random.RandomState(42).uniform(290, 320, (6, 6))
        qa = np.zeros((6, 6), dtype=np.uint8)
        qa[0:2, 0:2] = CLOUD
        stats = compute_lst_statistics(lst, quality_mask=qa)
        assert stats["valid_pixels"] < 36


# --- Metadata ---

class TestMetadata:
    def test_build_lst_metadata(self):
        meta = build_lst_metadata("landsat8", "Band10")
        assert meta["satellite"] == "Landsat-8"
        assert meta["algorithm"] == "SingleChannel"
        assert "processing_timestamp" in meta
        assert len(meta["processing_chain"]) == 7

    def test_build_lst_metadata_landsat9(self):
        meta = build_lst_metadata("landsat9", "Band11")
        assert meta["satellite"] == "Landsat-9"
        assert meta["thermal_band"] == "Band11"

    def test_build_lst_metadata_with_algorithm(self):
        meta = build_lst_metadata("landsat8", algorithm="SplitWindow")
        assert meta["algorithm"] == "SplitWindow"
        assert "T_i" in meta["algorithm_formula"]

    def test_build_lst_metadata_with_k1_k2(self):
        meta = build_lst_metadata("landsat8", "Band10")
        assert meta["k1"] == 774.8853
        assert meta["k2"] == 1321.0789

    def test_build_lst_metadata_emissivity_method(self):
        meta = build_lst_metadata("landsat8", emissivity_method="Fixed")
        assert meta["emissivity_method"] == "Fixed"

    def test_build_lst_metadata_with_additional_params(self):
        meta = build_lst_metadata("landsat8", additional_params={"water_vapor": 1.5})
        assert meta["additional_params"]["water_vapor"] == 1.5

    def test_build_lst_metadata_bt_formula(self):
        meta = build_lst_metadata("landsat8")
        assert "K2" in meta["brightness_temperature_formula"]

    def test_build_lst_metadata_version(self):
        meta = build_lst_metadata("landsat8")
        assert meta["version"] == "1.0.0"


# --- Engine ---

class TestLSTEngine:
    def test_engine_initialization(self):
        engine = LSTEngine("landsat8", "Band10")
        assert engine.satellite == "landsat8"
        assert engine.thermal_band == "Band10"
        assert engine.window_size >= 256

    def test_engine_satellite_not_supported(self):
        with pytest.raises(SatelliteNotSupportedError):
            LSTEngine("unknown_satellite")

    def test_engine_compute_lst_basic(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi)
        assert "lst_kelvin" in result
        assert "lst_celsius" in result
        assert "emissivity" in result
        assert "brightness_temperature_kelvin" in result
        assert "uncertainty" in result
        assert "quality_mask" in result
        assert "statistics" in result
        assert "metadata" in result
        assert result["lst_kelvin"].shape == (HEIGHT, WIDTH)

    def test_engine_compute_lst_with_nodata(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = _thermal_data(seed=42, with_nodata=True)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi, nodata=-9999)
        assert np.isfinite(result["lst_kelvin"]).sum() > 0

    def test_engine_compute_lst_landsat9(self):
        engine = LSTEngine("landsat9", "Band10")
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi)
        assert result["satellite"] == "landsat9"

    def test_engine_compute_lst_with_water_vapor(self):
        engine = LSTEngine("landsat8", "Band10", water_vapor=2.0)
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi)
        assert np.all(np.isfinite(result["lst_kelvin"]))

    def test_engine_lst_celsius_from_kelvin(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi)
        np.testing.assert_allclose(result["lst_celsius"], result["lst_kelvin"] - 273.15)

    def test_engine_validation_thermal_none(self):
        engine = LSTEngine("landsat8", "Band10")
        ndvi = _ndvi_data()
        with pytest.raises(ValidationError):
            engine.compute_lst(None, ndvi)

    def test_engine_validation_ndvi_none(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = _thermal_data()
        with pytest.raises(ValidationError):
            engine.compute_lst(thermal, None)

    def test_engine_validation_dimension_mismatch(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = np.random.rand(20, 20).astype(np.float32)
        ndvi = np.random.rand(10, 10).astype(np.float32)
        with pytest.raises(ValidationError):
            engine.compute_lst(thermal, ndvi)

    def test_engine_statistics_in_result(self):
        engine = LSTEngine("landsat8", "Band10")
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi)
        stats = result["statistics"]
        assert stats["mean"] > 200
        assert stats["mean"] < 400
        snow_free = int(WIDTH * HEIGHT - np.sum((result["quality_mask"] & 4) > 0))
        assert stats["valid_pixels"] == snow_free

    def test_engine_windowed_processing(self):
        engine = LSTEngine("landsat8", "Band10", window_size=32)
        thermal = _thermal_data(seed=42)
        ndvi = _ndvi_data(seed=99)
        result = engine.compute_lst(thermal, ndvi, window_size=32)
        assert result["lst_kelvin"].shape == (HEIGHT, WIDTH)

    def test_engine_large_raster_simulation(self):
        engine = LSTEngine("landsat8", "Band10", window_size=64)
        thermal = np.random.RandomState(42).uniform(10000, 18000, (128, 128)).astype(np.float32)
        ndvi = np.random.RandomState(99).uniform(-0.3, 0.9, (128, 128)).astype(np.float32)
        result = engine.compute_lst(thermal, ndvi, window_size=64)
        assert result["lst_kelvin"].shape == (128, 128)
        snow_free = int(128 * 128 - np.sum((result["quality_mask"] & 4) > 0))
        assert result["statistics"]["valid_pixels"] == snow_free


# --- Visualization ---

class TestVisualization:
    def test_render_temperature_map(self):
        lst = np.random.RandomState(42).uniform(290, 320, (32, 32))
        out = os.path.join(TEST_DIR, "temp_map.png")
        result = render_temperature_map(lst, out)
        assert result == out
        assert os.path.isfile(out)

    def test_render_temperature_map_with_custom_limits(self):
        lst = np.random.RandomState(42).uniform(290, 320, (32, 32))
        out = os.path.join(TEST_DIR, "temp_map_limits.png")
        result = render_temperature_map(lst, out, lst_min=280, lst_max=330)
        assert result == out

    def test_render_histogram(self):
        lst = np.random.RandomState(42).randn(1000) * 10 + 300
        out = os.path.join(TEST_DIR, "hist.png")
        result = render_histogram(lst, out)
        assert result == out

    def test_render_hotspot_overlay(self):
        lst = np.random.RandomState(42).uniform(290, 330, (32, 32))
        out = os.path.join(TEST_DIR, "hotspot.png")
        result = render_hotspot_overlay(lst, out)
        assert result == out

    def test_render_empty_data_returns_empty(self):
        lst = np.full((4, 4), np.nan)
        out = os.path.join(TEST_DIR, "empty.png")
        result = render_temperature_map(lst, out)
        assert result == ""

