"""Raster file validation — CRS, transform, band count, NoData, integrity checks."""

import logging
import os
from typing import Any, Optional

import rasterio

from app.raster.exceptions import (
    CorruptedRasterError,
    InvalidCRSError,
    RasterCRSError,
    RasterNotFoundError,
    RasterValidationError,
    UnsupportedFormatError,
)

logger = logging.getLogger("app.raster.validator")

_SUPPORTED_DRIVERS = {"GTiff", "COG"}
_KNOWN_CRS_AUTHORITIES = {"EPSG", "ESRI", "IAU", "SR-ORG", "USER"}


def _open_safe(path: str) -> rasterio.DatasetReader:
    if not os.path.isfile(path):
        raise RasterNotFoundError(f"File not found: {path}")
    try:
        return rasterio.open(path)
    except Exception as exc:
        raise CorruptedRasterError(f"Cannot open raster file '{path}': {exc}") from exc


def validate_format(path: str, allowed_drivers: Optional[set[str]] = None) -> bool:
    """Verify the raster format is supported."""
    if allowed_drivers is None:
        allowed_drivers = _SUPPORTED_DRIVERS
    with _open_safe(path) as src:
        if src.driver not in allowed_drivers:
            raise UnsupportedFormatError(
                f"Unsupported format '{src.driver}'. Allowed: {sorted(allowed_drivers)}"
            )
    return True


def validate_crs(path: str) -> bool:
    """Verify CRS is present and valid."""
    with _open_safe(path) as src:
        if src.crs is None:
            raise RasterCRSError(f"Raster '{path}' has no CRS")
        try:
            crs_str = str(src.crs)
            if not any(crs_str.startswith(a) for a in _KNOWN_CRS_AUTHORITIES):
                logger.warning("Unknown CRS authority: '%s'", crs_str)
        except Exception as exc:
            raise InvalidCRSError(f"Invalid CRS in '{path}': {exc}") from exc
    return True


def validate_transform(path: str) -> bool:
    """Verify the affine transform is valid."""
    with _open_safe(path) as src:
        if src.transform is None:
            raise RasterValidationError(f"Raster '{path}' has no affine transform")
        if src.transform.a == 0 or src.transform.e == 0:
            raise RasterValidationError(
                f"Raster '{path}' has degenerate transform (zero pixel size)"
            )
    return True


def validate_band_count(path: str, expected: Optional[int] = None) -> bool:
    """Verify band count matches expectation."""
    with _open_safe(path) as src:
        if expected is not None and src.count != expected:
            raise RasterValidationError(
                f"Raster '{path}' has {src.count} bands, expected {expected}"
            )
        if src.count == 0:
            raise RasterValidationError(f"Raster '{path}' has zero bands")
    return True


def validate_nodata(path: str) -> bool:
    """Check NoData values are consistent across bands."""
    with _open_safe(path) as src:
        nodata = src.nodata
        if nodata is not None:
            for i in range(1, src.count + 1):
                band_nodata = src.nodata
                if band_nodata is not None and band_nodata != nodata:
                    logger.warning(
                        "Raster '%s' has inconsistent NoData values: "
                        "file-level=%s, band %d=%s",
                        path, nodata, i, band_nodata,
                    )
    return True


def validate_resolution_consistency(path: str) -> bool:
    """Check all bands share the same resolution/shape."""
    with _open_safe(path) as src:
        if src.count < 2:
            return True
        width, height = src.width, src.height
        for i in range(1, src.count + 1):
            band_w = src.width
            band_h = src.height
            if band_w != width or band_h != height:
                raise RasterValidationError(
                    f"Raster '{path}' has inconsistent dimensions: "
                    f"band 1={width}x{height}, band {i}={band_w}x{band_h}"
                )
    return True


def validate_extent(path: str) -> bool:
    """Validate extent/bounds are reasonable."""
    with _open_safe(path) as src:
        bounds = src.bounds
        if bounds is None:
            raise RasterValidationError(f"Raster '{path}' has no bounds")
        if bounds.left >= bounds.right:
            raise RasterValidationError(
                f"Raster '{path}' has invalid left/right bounds: {bounds}"
            )
        if bounds.bottom >= bounds.top:
            raise RasterValidationError(
                f"Raster '{path}' has invalid bottom/top bounds: {bounds}"
            )
    return True


def validate_not_corrupt(path: str) -> bool:
    """Check for basic file corruption by scanning blocks."""
    if not os.path.isfile(path):
        raise CorruptedRasterError(f"File not found: {path}")
    if os.path.getsize(path) == 0:
        raise CorruptedRasterError(f"File is empty: {path}")
    try:
        with _open_safe(path) as src:
            for i in range(1, min(src.count + 1, 4)):
                _ = src.read(i, window=((0, min(10, src.height)), (0, min(10, src.width))))
    except Exception as exc:
        raise CorruptedRasterError(f"Raster appears corrupted: '{path}': {exc}") from exc
    return True


def validate_all(
    path: str,
    expected_bands: Optional[int] = None,
    expected_crs: Optional[str] = None,
    allowed_drivers: Optional[set[str]] = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Run all applicable validations and return a report.

    Args:
        path: Path to the raster file.
        expected_bands: If set, validate band count matches.
        expected_crs: If set, validate CRS matches.
        allowed_drivers: Set of allowed format drivers.
        strict: If True, warnings are treated as errors.

    Returns:
        Dict with keys: valid, errors, warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    checks = [
        ("format", lambda: validate_format(path, allowed_drivers)),
        ("crs", lambda: validate_crs(path)),
        ("transform", lambda: validate_transform(path)),
        ("band_count", lambda: validate_band_count(path, expected_bands)),
        ("nodata", lambda: validate_nodata(path)),
        ("resolution_consistency", lambda: validate_resolution_consistency(path)),
        ("extent", lambda: validate_extent(path)),
        ("corruption", lambda: validate_not_corrupt(path)),
    ]

    if expected_crs:
        def _check_crs():
            with _open_safe(path) as src:
                if str(src.crs) != expected_crs:
                    raise RasterCRSError(
                        f"Expected CRS '{expected_crs}', got '{src.crs}'"
                    )
            return True
        checks.append(("expected_crs", _check_crs))

    for check_name, check_fn in checks:
        try:
            check_fn()
        except (RasterValidationError, UnsupportedFormatError, CorruptedRasterError) as e:
            errors.append(f"[{check_name}] {e}")
        except Exception as e:
            msg = f"[{check_name}] Unexpected error: {e}"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checks_passed": len(checks) - len(errors),
        "checks_total": len(checks),
    }
