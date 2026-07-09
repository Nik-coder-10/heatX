import logging
import numpy as np
from scipy import ndimage

from .exceptions import ExtractionError, MissingDependencyError
from .registry import get, list_feature_names

logger = logging.getLogger("app.features.extractor")


def extract_thermal_features(
    lst_kelvin=None, brightness_temp=None, emissivity=None,
    compute_gradient=True, compute_variance=True, compute_hotspot_distance=True,
    gradient_window=3, variance_window=3, hotspot_percentile=90.0, resolution=30.0,
):
    result = {}
    if lst_kelvin is not None:
        result["lst_kelvin"] = lst_kelvin.astype(np.float32)
        result["lst_celsius"] = (lst_kelvin - 273.15).astype(np.float32)
    if brightness_temp is not None:
        result["brightness_temperature"] = brightness_temp.astype(np.float32)
    if emissivity is not None:
        result["emissivity"] = emissivity.astype(np.float32)
    if lst_kelvin is not None and compute_gradient:
        result["thermal_gradient"] = _compute_gradient(lst_kelvin)
    if lst_kelvin is not None and compute_variance:
        result["local_temp_variance"] = _compute_local_variance(lst_kelvin, variance_window)
    if lst_kelvin is not None and compute_hotspot_distance:
        result["hotspot_distance"] = _compute_hotspot_distance(lst_kelvin, hotspot_percentile, resolution)
    return result

def _compute_gradient(arr):
    dy = ndimage.sobel(arr.astype(np.float64), axis=0)
    dx = ndimage.sobel(arr.astype(np.float64), axis=1)
    return np.sqrt(dx**2 + dy**2).astype(np.float32)

def _compute_local_variance(arr, window=3):
    from scipy.ndimage import uniform_filter
    arr_f = arr.astype(np.float64)
    mean = uniform_filter(arr_f, size=window)
    sq_mean = uniform_filter(arr_f**2, size=window)
    return np.clip(sq_mean - mean**2, 0, None).astype(np.float32)

def _compute_hotspot_distance(arr, percentile=90.0, resolution=30.0):
    from scipy.ndimage import distance_transform_edt
    threshold = np.percentile(arr.astype(np.float64), percentile)
    hotspot_mask = arr > threshold
    dist = distance_transform_edt(~hotspot_mask)
    return (dist * resolution).astype(np.float32)


def extract_vegetation_features(
    red=None, nir=None, green=None, blue=None, ndvi=None,
    compute_savi=True, compute_evi=True, compute_msavi=True,
    compute_gndvi=True, compute_fvc=True, compute_density_class=True,
    compute_distance=True, ndvi_soil=0.2, ndvi_veg=0.5, resolution=30.0,
):
    result = {}
    if red is not None and nir is not None and ndvi is None:
        ndvi = _safe_ndvi(red, nir)
    if ndvi is None:
        return result
    result["ndvi"] = ndvi.astype(np.float32)
    if compute_savi and red is not None and nir is not None:
        result["savi"] = _safe_savi(red, nir)
    if compute_evi and red is not None and nir is not None and blue is not None:
        result["evi"] = _safe_evi(red, nir, blue)
    if compute_msavi and red is not None and nir is not None:
        result["msavi"] = _safe_msavi(red, nir)
    if compute_gndvi and green is not None and nir is not None:
        result["gndvi"] = _safe_gndvi(green, nir)
    if compute_fvc:
        fvc = _compute_fvc(ndvi, ndvi_soil, ndvi_veg)
        result["vegetation_fraction"] = fvc
        if compute_density_class:
            result["vegetation_density_class"] = _compute_veg_density_class(fvc)
        if compute_distance:
            result["distance_to_vegetation"] = _compute_distance_to_vegetation(fvc, resolution)
    return result

def _safe_ndvi(red, nir):
    rf = red.astype(np.float64); nf = nir.astype(np.float64)
    denom = np.where(rf + nf == 0, 1e-10, rf + nf)
    return ((nf - rf) / denom).astype(np.float32)

def _safe_savi(red, nir, L=0.5):
    rf = red.astype(np.float64); nf = nir.astype(np.float64)
    denom = np.where(nf + rf + L == 0, 1e-10, nf + rf + L)
    return ((nf - rf) * (1.0 + L) / denom).astype(np.float32)

def _safe_evi(red, nir, blue, L=1.0, C1=6.0, C2=7.5, G=2.5):
    rf = red.astype(np.float64); nf = nir.astype(np.float64); bf = blue.astype(np.float64)
    denom = np.where(nf + C1*rf - C2*bf + L == 0, 1e-10, nf + C1*rf - C2*bf + L)
    return (G * (nf - rf) / denom).astype(np.float32)

def _safe_msavi(red, nir):
    rf = red.astype(np.float64); nf = nir.astype(np.float64)
    d = np.maximum((2.0*nf + 1.0)**2 - 8.0*(nf - rf), 0)
    return ((2.0*nf + 1.0 - np.sqrt(d)) / 2.0).astype(np.float32)

def _safe_gndvi(green, nir):
    gf = green.astype(np.float64); nf = nir.astype(np.float64)
    denom = np.where(nf + gf == 0, 1e-10, nf + gf)
    return ((nf - gf) / denom).astype(np.float32)

def _compute_fvc(ndvi, ndvi_soil=0.2, ndvi_veg=0.5):
    ndvi_f = ndvi.astype(np.float64)
    fvc = np.zeros_like(ndvi_f)
    mask = ndvi_f > ndvi_soil
    fvc[mask] = ((ndvi_f[mask] - ndvi_soil) / (ndvi_veg - ndvi_soil))**2
    return np.clip(fvc, 0.0, 1.0).astype(np.float32)

def _compute_veg_density_class(fvc):
    dc = np.zeros_like(fvc, dtype=np.int32)
    dc[fvc > 0.1] = 1
    dc[fvc > 0.3] = 2
    dc[fvc > 0.6] = 3
    dc[fvc > 0.85] = 4
    return dc

def _compute_distance_to_vegetation(fvc, resolution=30.0, threshold=0.3):
    from scipy.ndimage import distance_transform_edt
    veg_mask = fvc > threshold
    dist = distance_transform_edt(veg_mask)
    return (dist * resolution).astype(np.float32)


def extract_builtup_features(
    red=None, nir=None, swir1=None, swir2=None,
    ndvi=None, savi=None, mndwi=None, ndbi=None,
    compute_ibi=True, compute_urban_index=True, compute_impervious=True,
    compute_building_density=True, compute_builtup_ratio=True, compute_road_density=True,
):
    result = {}
    if nir is not None and swir1 is not None and ndbi is None:
        ndbi = _safe_ndbi(nir, swir1)
    if ndbi is not None:
        result["ndbi"] = ndbi.astype(np.float32)
    if swir2 is not None and nir is not None and compute_urban_index:
        result["urban_index"] = _safe_urban_index(nir, swir2)
    if ndbi is not None and savi is not None and mndwi is not None and compute_ibi:
        result["ibi"] = _safe_ibi(ndbi, savi, mndwi)
    if ndbi is not None and compute_impervious:
        result["impervious_surface_pct"] = _compute_impervious_pct(ndbi)
    if ndbi is not None and compute_building_density:
        result["building_density"] = _compute_building_density(ndbi)
    if ndbi is not None and ndvi is not None and compute_builtup_ratio:
        result["builtup_ratio"] = _compute_builtup_ratio(ndbi, ndvi)
    if ndbi is not None and compute_road_density:
        result["road_density"] = _compute_road_density(ndbi)
    return result

def _safe_ndbi(nir, swir1):
    nf = nir.astype(np.float64); sf = swir1.astype(np.float64)
    denom = np.where(sf + nf == 0, 1e-10, sf + nf)
    return ((sf - nf) / denom).astype(np.float32)

def _safe_urban_index(nir, swir2):
    nf = nir.astype(np.float64); sf = swir2.astype(np.float64)
    denom = np.where(sf + nf == 0, 1e-10, sf + nf)
    return ((sf - nf) / denom).astype(np.float32)

def _safe_ibi(ndbi, savi, mndwi):
    nf = ndbi.astype(np.float64); sf = savi.astype(np.float64); mf = mndwi.astype(np.float64)
    num = nf - (sf + mf) / 2.0
    denom = np.where(nf + (sf + mf) / 2.0 == 0, 1e-10, nf + (sf + mf) / 2.0)
    return (num / denom).astype(np.float32)

def _compute_impervious_pct(ndbi):
    return np.clip((ndbi.astype(np.float64) + 0.5) * 100.0, 0.0, 100.0).astype(np.float32)

def _compute_building_density(ndbi):
    return np.clip((ndbi.astype(np.float64) + 0.3) / 0.6, 0.0, 1.0).astype(np.float32)

def _compute_builtup_ratio(ndbi, ndvi):
    b = np.maximum(ndbi.astype(np.float64), 0)
    v = np.maximum(ndvi.astype(np.float64), 0)
    denom = np.where(b + v == 0, 1e-10, b + v)
    return np.clip(b / denom, 0.0, 1.0).astype(np.float32)

def _compute_road_density(ndbi):
    from scipy.ndimage import uniform_filter
    road = np.maximum(ndbi.astype(np.float64) - 0.1, 0)
    return np.clip(uniform_filter(road, size=5) * 20.0, 0.0, 20.0).astype(np.float32)


def extract_water_features(
    green=None, nir=None, swir1=None,
    ndwi=None, mndwi=None,
    compute_distance=True, compute_density=True, compute_moisture=True,
    resolution=30.0,
):
    result = {}
    if green is not None and nir is not None and ndwi is None:
        ndwi = _safe_ndwi(green, nir)
    if ndwi is not None:
        result["ndwi"] = ndwi.astype(np.float32)
    if green is not None and swir1 is not None and mndwi is None:
        mndwi = _safe_mndwi(green, swir1)
    if mndwi is not None:
        result["mndwi"] = mndwi.astype(np.float32)
        if compute_distance:
            result["distance_to_water"] = _compute_distance_to_water(mndwi, resolution)
        if compute_density:
            result["water_density"] = _compute_water_density(mndwi)
    if nir is not None and swir1 is not None and compute_moisture:
        result["moisture_index"] = _safe_moisture_index(nir, swir1)
    return result

def _safe_ndwi(green, nir):
    gf = green.astype(np.float64); nf = nir.astype(np.float64)
    denom = np.where(gf + nf == 0, 1e-10, gf + nf)
    return ((gf - nf) / denom).astype(np.float32)

def _safe_mndwi(green, swir1):
    gf = green.astype(np.float64); sf = swir1.astype(np.float64)
    denom = np.where(gf + sf == 0, 1e-10, gf + sf)
    return ((gf - sf) / denom).astype(np.float32)

def _safe_moisture_index(nir, swir1):
    nf = nir.astype(np.float64); sf = swir1.astype(np.float64)
    denom = np.where(nf + sf == 0, 1e-10, nf + sf)
    return ((nf - sf) / denom).astype(np.float32)

def _compute_distance_to_water(mndwi, resolution=30.0, threshold=0.3):
    from scipy.ndimage import distance_transform_edt
    water_mask = mndwi > threshold
    dist = distance_transform_edt(water_mask)
    return (dist * resolution).astype(np.float32)

def _compute_water_density(mndwi, window=5):
    from scipy.ndimage import uniform_filter
    mask = (mndwi > 0.3).astype(np.float64)
    return uniform_filter(mask, size=window).astype(np.float32)


def extract_baresoil_features(
    red=None, nir=None, blue=None, swir1=None,
    bsi=None, impervious_surface_pct=None,
    compute_pct=True, compute_exposed=True,
):
    result = {}
    if all(x is not None for x in [red, nir, blue, swir1]) and bsi is None:
        bsi = _safe_bsi(red, nir, blue, swir1)
    if bsi is not None:
        result["bsi"] = bsi.astype(np.float32)
        if compute_pct:
            result["bare_soil_pct"] = _compute_bare_soil_pct(bsi)
    if impervious_surface_pct is not None and bsi is not None and compute_exposed:
        bsp = result.get("bare_soil_pct", np.zeros_like(impervious_surface_pct, dtype=np.float32))
        result["exposed_surface_pct"] = np.clip(bsp * 0.5 + impervious_surface_pct.astype(np.float32) * 0.5, 0.0, 100.0)
    return result

def _safe_bsi(red, nir, blue, swir1):
    r = red.astype(np.float64); n = nir.astype(np.float64)
    b = blue.astype(np.float64); s = swir1.astype(np.float64)
    num = (s + r) - (n + b)
    denom = np.where((s + r) + (n + b) == 0, 1e-10, (s + r) + (n + b))
    return (num / denom).astype(np.float32)

def _compute_bare_soil_pct(bsi):
    return np.clip((bsi.astype(np.float64) + 0.3) * 100.0, 0.0, 100.0).astype(np.float32)


def extract_all_features(
    lst_kelvin=None, brightness_temp=None, emissivity=None,
    red=None, nir=None, green=None, blue=None,
    swir1=None, swir2=None, ndvi=None,
    elevation=None, transform=None,
    acquisition_date=None, quality_mask=None, uncertainty=None,
    config=None, resolution=30.0,
):
    cfg = config or {}
    features = {}

    thermal = extract_thermal_features(
        lst_kelvin=lst_kelvin, brightness_temp=brightness_temp,
        emissivity=emissivity, resolution=resolution,
    )
    features.update(thermal)

    veg = extract_vegetation_features(
        red=red, nir=nir, green=green, blue=blue, ndvi=ndvi,
        compute_savi=cfg.get("compute_savi", True),
        compute_evi=cfg.get("compute_evi", True) and blue is not None,
        compute_msavi=cfg.get("compute_msavi", True),
        compute_gndvi=cfg.get("compute_gndvi", True) and green is not None,
        resolution=resolution,
    )
    features.update(veg)

    ndvi_arr = features.get("ndvi", ndvi)
    savi_arr = features.get("savi")
    mndwi_arr = None

    builtup = extract_builtup_features(
        red=red, nir=nir, swir1=swir1, swir2=swir2,
        ndvi=ndvi_arr, savi=savi_arr, mndwi=mndwi_arr,
    )
    features.update(builtup)

    water = extract_water_features(
        green=green, nir=nir, swir1=swir1, resolution=resolution,
    )
    features.update(water)
    mndwi_arr = features.get("mndwi")

    baresoil = extract_baresoil_features(
        red=red, nir=nir, blue=blue, swir1=swir1,
        impervious_surface_pct=features.get("impervious_surface_pct"),
    )
    features.update(baresoil)

    if transform is not None:
        from .spatial_features import extract_spatial_features
        height, width = features.get("lst_kelvin", np.zeros((1, 1))).shape[:2]
        spatial = extract_spatial_features(transform, height, width)
        features.update(spatial)

    if elevation is not None:
        from .terrain_features import extract_terrain_features
        terrain = extract_terrain_features(elevation, resolution)
        features.update(terrain)

    temporal = _extract_temporal(acquisition_date)
    if temporal and features:
        first_key = next(iter(features.keys()))
        ref_shape = features[first_key].shape
        for k, v in temporal.items():
            if v.ndim < 2 or v.shape != ref_shape:
                val = float(v.item()) if v.size > 0 else 0.0
                temporal[k] = np.full(ref_shape, val, dtype=np.float32)
    features.update(temporal)

    quality_feat = _extract_quality(quality_mask, uncertainty)
    if quality_feat and features:
        first_key = next(iter(features.keys()))
        ref_shape = features[first_key].shape
        for k, v in quality_feat.items():
            if v.ndim < 2 or v.shape != ref_shape:
                if v.size > 0 and np.issubdtype(v.dtype, np.floating):
                    val = float(v.item())
                else:
                    val = 0.0
                quality_feat[k] = np.full(ref_shape, val, dtype=np.float32 if np.issubdtype(v.dtype, np.floating) else v.dtype)
    features.update(quality_feat)

    return features


def _extract_temporal(acquisition_date):
    from .temporal_features import extract_temporal_features
    return extract_temporal_features(acquisition_date=acquisition_date)


def _extract_quality(quality_mask, uncertainty):
    from .quality import compute_quality_features
    return compute_quality_features(quality_mask=quality_mask, uncertainty=uncertainty)
