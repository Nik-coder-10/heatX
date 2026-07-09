import logging
from typing import Any

from .exceptions import InvalidHotspotError

logger = logging.getLogger("app.recommendation.rules")

RECOMMENDATION_PROFILES: dict[str, dict[str, Any]] = {
    "tree_plantation": {
        "label": "Tree Plantation",
        "description": "Plant native shade trees in hotspot area to increase canopy cover and reduce surface temperature.",
        "suitable_landcover": ["builtup", "barren", "agriculture"],
        "min_ndvi_threshold": -0.3,
        "max_ndvi_threshold": 0.4,
        "min_vegetation_fraction": 0.0,
        "max_vegetation_fraction": 0.4,
        "min_builtup_fraction": 0.1,
        "base_cost_per_hectare": 15000.0,
        "temp_reduction_per_hectare": 1.5,
        "carbon_reduction_per_hectare": 5.0,
        "priority_weight": 0.8,
        "applicable_severities": ["moderate", "high", "very_high", "extreme"],
    },
    "cool_roof": {
        "label": "Cool Roof Installation",
        "description": "Install reflective cool roofs on buildings to reflect solar radiation and reduce heat absorption.",
        "suitable_landcover": ["builtup"],
        "min_ndvi_threshold": -1.0,
        "max_ndvi_threshold": 0.2,
        "min_builtup_fraction": 0.3,
        "base_cost_per_hectare": 25000.0,
        "temp_reduction_per_hectare": 1.0,
        "carbon_reduction_per_hectare": 3.0,
        "priority_weight": 0.7,
        "applicable_severities": ["high", "very_high", "extreme"],
    },
    "green_roof": {
        "label": "Green Roof Installation",
        "description": "Install vegetated green roofs on buildings for insulation, stormwater retention, and cooling.",
        "suitable_landcover": ["builtup"],
        "min_ndvi_threshold": -1.0,
        "max_ndvi_threshold": 0.2,
        "min_builtup_fraction": 0.2,
        "base_cost_per_hectare": 40000.0,
        "temp_reduction_per_hectare": 1.2,
        "carbon_reduction_per_hectare": 4.0,
        "priority_weight": 0.6,
        "applicable_severities": ["high", "very_high", "extreme"],
    },
    "reflective_pavement": {
        "label": "Reflective Pavement",
        "description": "Replace dark asphalt with high-albedo reflective pavement to reduce ground surface temperature.",
        "suitable_landcover": ["builtup"],
        "min_ndvi_threshold": -1.0,
        "max_ndvi_threshold": 0.1,
        "min_builtup_fraction": 0.4,
        "base_cost_per_hectare": 35000.0,
        "temp_reduction_per_hectare": 0.8,
        "carbon_reduction_per_hectare": 2.0,
        "priority_weight": 0.5,
        "applicable_severities": ["moderate", "high", "very_high"],
    },
    "water_body_restoration": {
        "label": "Water Body Restoration",
        "description": "Restore or create water bodies (ponds, lakes) to provide evaporative cooling in hotspot zones.",
        "suitable_landcover": ["barren", "agriculture", "vegetation"],
        "min_ndwi_threshold": -0.2,
        "max_ndwi_threshold": 0.3,
        "min_ndvi_threshold": -0.2,
        "max_ndvi_threshold": 0.5,
        "min_builtup_fraction": 0.0,
        "max_builtup_fraction": 0.3,
        "base_cost_per_hectare": 50000.0,
        "temp_reduction_per_hectare": 2.0,
        "carbon_reduction_per_hectare": 1.0,
        "priority_weight": 0.4,
        "applicable_severities": ["very_high", "extreme"],
    },
    "urban_green_space": {
        "label": "Urban Green Space Development",
        "description": "Develop parks, gardens, and green corridors to create cool islands within urban heat zones.",
        "suitable_landcover": ["builtup", "barren", "agriculture"],
        "min_ndvi_threshold": -0.3,
        "max_ndvi_threshold": 0.3,
        "max_builtup_fraction": 0.7,
        "base_cost_per_hectare": 30000.0,
        "temp_reduction_per_hectare": 1.8,
        "carbon_reduction_per_hectare": 3.5,
        "priority_weight": 0.7,
        "applicable_severities": ["moderate", "high", "very_high", "extreme"],
    },
}


def apply_rules(hotspot: Any, config: Any | None = None) -> list[dict]:
    if not hasattr(hotspot, "dominant_landcover"):
        raise InvalidHotspotError("Hotspot missing dominant_landcover attribute")
    if not hasattr(hotspot, "mean_ndvi"):
        raise InvalidHotspotError("Hotspot missing mean_ndvi attribute")
    if not hasattr(hotspot, "severity"):
        raise InvalidHotspotError("Hotspot missing severity attribute")

    landcover = (hotspot.dominant_landcover or "Unknown").lower()
    ndvi = getattr(hotspot, "mean_ndvi", 0.0) or 0.0
    ndbi = getattr(hotspot, "mean_ndbi", 0.0) or 0.0
    ndwi = getattr(hotspot, "mean_ndwi", 0.0) or 0.0
    severity = (hotspot.severity or "").lower()
    veg_frac = getattr(hotspot, "vegetation_fraction", 0.0) or 0.0
    built_frac = getattr(hotspot, "builtup_fraction", 0.0) or 0.0
    area_km2 = getattr(hotspot, "area_sq_km", 0.0) or 0.0
    area_ha = area_km2 * 100.0
    mean_temp = getattr(hotspot, "mean_temperature_c", 0.0) or 0.0

    matched = []
    for rec_type, profile in RECOMMENDATION_PROFILES.items():
        if severity not in profile.get("applicable_severities", []):
            continue
        suitable = profile.get("suitable_landcover", [])
        if landcover not in suitable and "Unknown" not in suitable:
            continue
        min_ndvi = profile.get("min_ndvi_threshold", -1.0)
        max_ndvi = profile.get("max_ndvi_threshold", 1.0)
        if not (min_ndvi <= ndvi <= max_ndvi):
            continue
        min_built = profile.get("min_builtup_fraction", 0.0)
        max_built = profile.get("max_builtup_fraction", 1.0)
        if not (min_built <= built_frac <= max_built):
            continue
        min_ndwi = profile.get("min_ndwi_threshold", -1.0)
        max_ndwi = profile.get("max_ndwi_threshold", 1.0)
        if "min_ndwi_threshold" in profile and not (min_ndwi <= ndwi <= max_ndwi):
            continue
        min_veg = profile.get("min_vegetation_fraction", 0.0)
        max_veg = profile.get("max_vegetation_fraction", 1.0)
        if "min_vegetation_fraction" in profile and not (min_veg <= veg_frac <= max_veg):
            continue

        cost = profile["base_cost_per_hectare"] * area_ha
        temp_reduction = profile["temp_reduction_per_hectare"] * min(area_ha, 10.0) / 10.0
        carbon_reduction = profile["carbon_reduction_per_hectare"] * area_ha

        matched.append({
            "recommendation_type": rec_type,
            "label": profile["label"],
            "description": profile["description"],
            "estimated_cost": round(cost, 2),
            "expected_temperature_reduction": round(temp_reduction, 2),
            "carbon_reduction": round(carbon_reduction, 2),
            "priority_weight": profile["priority_weight"],
            "base_cost_per_hectare": profile["base_cost_per_hectare"],
            "area_hectares": round(area_ha, 4),
            "current_temperature_c": round(mean_temp, 2),
            "rationale": _generate_rationale(rec_type, ndvi, ndbi, ndwi, severity, built_frac, veg_frac),
        })

    if not matched:
        logger.debug("No rules matched for hotspot %s (landcover=%s, ndvi=%.2f, severity=%s)",
                     getattr(hotspot, "id", "?"), landcover, ndvi, severity)
        fallback = _fallback_recommendation(area_ha, mean_temp, severity)
        if fallback:
            matched.append(fallback)

    return matched


def _generate_rationale(rec_type: str, ndvi: float, ndbi: float, ndwi: float,
                        severity: str, built_frac: float, veg_frac: float) -> str:
    rationales = {
        "tree_plantation": (
            f"NDVI={ndvi:.2f} indicates low vegetation coverage (vegetation fraction={veg_frac:.0%}). "
            f"Tree plantation can increase canopy cover and provide shade in this {severity} severity zone."
        ),
        "cool_roof": (
            f"Built-up fraction={built_frac:.0%} and low NDVI={ndvi:.2f} suggest dense construction. "
            f"Cool roofs can reflect solar radiation and reduce indoor/outdoor temperatures."
        ),
        "green_roof": (
            f"Built-up area with limited vegetation (NDVI={ndvi:.2f}). "
            f"Green roofs provide insulation, reduce runoff, and create localized cooling."
        ),
        "reflective_pavement": (
            f"High built-up fraction={built_frac:.0%} with NDBI={ndbi:.2f}. "
            f"Reflective pavement increases albedo and reduces ground-level heat absorption."
        ),
        "water_body_restoration": (
            f"NDWI={ndwi:.2f} and vegetation fraction={veg_frac:.0%} suggest potential for water features. "
            f"Water bodies provide evaporative cooling effect up to 2 km."
        ),
        "urban_green_space": (
            f"Mixed landuse with built-up fraction={built_frac:.0%} and vegetation fraction={veg_frac:.0%}. "
            f"Developing green corridors can create cool islands and reduce ambient temperature."
        ),
    }
    return rationales.get(rec_type, f"Recommended for {severity} severity zone.")


def _fallback_recommendation(area_ha: float, mean_temp: float, severity: str) -> dict | None:
    if area_ha <= 0:
        return None
    return {
        "recommendation_type": "urban_green_space",
        "label": "Urban Green Space Development",
        "description": "Develop parks, gardens, and green corridors to create cool islands within urban heat zones.",
        "estimated_cost": round(30000.0 * area_ha, 2),
        "expected_temperature_reduction": round(1.8 * min(area_ha, 10.0) / 10.0, 2),
        "carbon_reduction": round(3.5 * area_ha, 2),
        "priority_weight": 0.5,
        "base_cost_per_hectare": 30000.0,
        "area_hectares": round(area_ha, 4),
        "current_temperature_c": round(mean_temp, 2),
        "rationale": f"Default recommendation for {severity} zone (area={area_ha:.1f} ha).",
    }
