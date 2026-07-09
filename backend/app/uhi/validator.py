import logging
import numpy as np

from .exceptions import MissingFeatureError, GeometryError

logger = logging.getLogger("app.uhi.validator")

REQUIRED_FEATURES = ["lst_celsius"]
RECOMMENDED_FEATURES = ["ndvi", "ndbi", "ndwi", "lst_kelvin", "vegetation_fraction",
                        "impervious_surface_pct", "quality_flags", "land_cover"]


def validate_feature_cube(cube) -> list[str]:
    warnings = []
    for feat in REQUIRED_FEATURES:
        if feat not in cube.feature_names:
            raise MissingFeatureError(f"Required feature missing: {feat}")
        if cube.features.get(feat) is None:
            raise MissingFeatureError(f"Required feature data is None: {feat}")

    for feat in RECOMMENDED_FEATURES:
        if feat not in cube.feature_names:
            warnings.append(f"Recommended feature missing: {feat}")

    if cube.crs is None:
        warnings.append("CRS is not set")
    if cube.transform is None:
        warnings.append("Transform is not set")

    lst = cube.features.get("lst_celsius")
    if lst is not None and lst.size == 0:
        raise MissingFeatureError("lst_celsius is empty")

    return warnings


def validate_hotspot_geometry(geom: dict) -> list[str]:
    issues = []
    if "type" not in geom:
        issues.append("Geometry missing type")
    if "coordinates" not in geom:
        issues.append("Geometry missing coordinates")
    if geom.get("type") not in ("Polygon", "MultiPolygon"):
        issues.append(f"Unsupported geometry type: {geom.get('type')}")
    return issues


def validate_hotspot(hs) -> list[str]:
    issues = []
    if not hs.id:
        issues.append("Hotspot missing ID")
    if hs.area_sq_km <= 0:
        issues.append(f"Invalid hotspot area: {hs.area_sq_km}")
    if not (0 <= hs.confidence <= 1):
        issues.append(f"Confidence out of range: {hs.confidence}")
    if not hs.geometry:
        issues.append("Hotspot missing geometry")
    else:
        issues.extend(validate_hotspot_geometry(hs.geometry))
    return issues
