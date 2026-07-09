import logging

import numpy as np
import rasterio

from .exceptions import (
    MissingBandError,
    DimensionMismatchError,
    CRSMismatchError,
    ResolutionMismatchError,
    NoDataPropagationError,
    InvalidRangeError,
)

logger = logging.getLogger("app.indices.validator")


def check_bands_exist(band_paths: dict[str, str], required: list[str]) -> None:
    missing = [b for b in required if b not in band_paths]
    if missing:
        raise MissingBandError(
            f"Missing required bands: {missing}. "
            f"Provided: {list(band_paths)}"
        )


def check_band_paths(band_paths: dict[str, str]) -> dict[str, dict]:
    infos = {}
    for name, path in band_paths.items():
        with rasterio.open(path) as src:
            infos[name] = {
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "crs": src.crs,
                "transform": src.transform,
                "nodata": src.nodata,
                "dtypes": src.dtypes,
                "bounds": src.bounds,
            }
    return infos


def check_dimensions(band_infos: dict[str, dict]) -> None:
    ref = next(iter(band_infos.values()))
    ref_shape = (ref["height"], ref["width"])
    for name, info in band_infos.items():
        shape = (info["height"], info["width"])
        if shape != ref_shape:
            raise DimensionMismatchError(
                f"Band '{name}' has dimensions {shape}, "
                f"expected {ref_shape} from reference band"
            )


def check_crs_consistency(band_infos: dict[str, dict]) -> None:
    ref = next(iter(band_infos.values()))
    ref_crs = ref["crs"]
    for name, info in band_infos.items():
        if info["crs"] != ref_crs:
            raise CRSMismatchError(
                f"Band '{name}' has CRS {info['crs']}, "
                f"expected {ref_crs}"
            )


def check_resolution_consistency(band_infos: dict[str, dict], tolerance: float = 0.01) -> None:
    ref = next(iter(band_infos.values()))
    ref_res = (abs(ref["transform"].a), abs(ref["transform"].e))
    for name, info in band_infos.items():
        res = (abs(info["transform"].a), abs(info["transform"].e))
        if abs(res[0] - ref_res[0]) > tolerance * ref_res[0] or \
           abs(res[1] - ref_res[1]) > tolerance * ref_res[1]:
            raise ResolutionMismatchError(
                f"Band '{name}' has resolution {res}, "
                f"expected ~{ref_res}"
            )


def check_nodata(array: np.ndarray, nodata: float | None = None) -> dict[str, float]:
    mask = np.zeros(array.shape[-2:], dtype=bool)
    if nodata is not None:
        if np.isnan(nodata):
            mask |= np.isnan(array)
        else:
            mask |= np.abs(array.astype(np.float64) - nodata) < 1e-8
    if array.ndim == 3:
        for i in range(array.shape[0]):
            mask |= np.isnan(array[i]) | np.isinf(array[i])
    else:
        mask |= np.isnan(array) | np.isinf(array)
    total = mask.size
    invalid = int(mask.sum())
    return {
        "invalid_pixels": invalid,
        "total_pixels": total,
        "invalid_pct": float(invalid) / float(total) * 100.0 if total > 0 else 0.0,
    }


def check_range(array: np.ndarray, expected_range: tuple[float, float]) -> dict[str, float]:
    vals = array[~np.isnan(array) & ~np.isinf(array)]
    if len(vals) == 0:
        return {"min": 0.0, "max": 0.0, "in_range": True}
    arr_min = float(vals.min())
    arr_max = float(vals.max())
    in_range = arr_min >= expected_range[0] and arr_max <= expected_range[1]
    if not in_range:
        raise InvalidRangeError(
            f"Array values [{arr_min:.4f}, {arr_max:.4f}] outside expected range "
            f"{expected_range}. Consider checking input data."
        )
    return {"min": arr_min, "max": arr_max, "in_range": True}


def validate_all(
    band_paths: dict[str, str],
    required_bands: list[str],
    expected_range: tuple[float, float] = (-1.0, 1.0),
) -> dict:
    issues = []
    warnings_list = []
    try:
        check_bands_exist(band_paths, required_bands)
    except MissingBandError as e:
        issues.append(str(e))
        return {"valid": False, "issues": issues, "warnings": warnings_list}

    try:
        infos = check_band_paths(band_paths)
    except Exception as e:
        issues.append(f"Cannot read band metadata: {e}")
        return {"valid": False, "issues": issues, "warnings": warnings_list}

    try:
        check_dimensions(infos)
    except DimensionMismatchError as e:
        issues.append(str(e))

    try:
        check_crs_consistency(infos)
    except CRSMismatchError as e:
        issues.append(str(e))

    try:
        check_resolution_consistency(infos)
    except ResolutionMismatchError as e:
        warnings_list.append(str(e))

    for name, path in band_paths.items():
        try:
            with rasterio.open(path) as src:
                data = src.read()
                nodata_check = check_nodata(data, src.nodata)
                if nodata_check["invalid_pct"] > 10:
                    warnings_list.append(
                        f"Band '{name}' has {nodata_check['invalid_pct']:.1f}% invalid pixels"
                    )
        except Exception as e:
            issues.append(f"Cannot read band '{name}': {e}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings_list,
        "n_bands_checked": len(band_paths),
    }
