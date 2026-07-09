from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class ScenarioTemplate:
    name: str
    description: str
    category: str
    feature_modifiers: dict[str, dict[str, Any]]
    default_parameters: dict[str, Any] = field(default_factory=dict)
    co2_reduction_factor: float = 0.0
    cost_per_hectare: float = 0.0

    def apply(self, X: np.ndarray, feature_names: list[str],
              intensity: float = 1.0, **params) -> np.ndarray:
        X_mod = X.copy().astype(np.float64)
        for feature, modifier in self.feature_modifiers.items():
            if feature not in feature_names:
                continue
            idx = feature_names.index(feature)
            op = modifier.get("op", "add")
            value = modifier.get("value", 0.0) * intensity
            if op == "add":
                X_mod[:, idx] = X_mod[:, idx] + value
            elif op == "mul":
                X_mod[:, idx] = X_mod[:, idx] * (1.0 + value)
            elif op == "set":
                X_mod[:, idx] = value
            elif op == "clip":
                lo = modifier.get("min", -np.inf)
                hi = modifier.get("max", np.inf)
                X_mod[:, idx] = np.clip(X_mod[:, idx], lo, hi)
            elif op == "scale_to":
                target = modifier.get("target", 0.0) * intensity
                current = X_mod[:, idx]
                X_mod[:, idx] = current + (target - current.mean()) if current.std() > 0 else target
            lo = modifier.get("min", -np.inf)
            hi = modifier.get("max", np.inf)
            X_mod[:, idx] = np.clip(X_mod[:, idx], lo, hi)
        return X_mod


SCENARIO_TEMPLATES: dict[str, ScenarioTemplate] = {
    "tree_plantation": ScenarioTemplate(
        name="tree_plantation",
        description="Large-scale tree plantation to increase canopy cover",
        category="vegetation",
        feature_modifiers={
            "ndvi": {"op": "add", "value": 0.15, "min": -1.0, "max": 1.0},
            "albedo": {"op": "add", "value": -0.02, "min": 0.0, "max": 1.0},
            "lst": {"op": "add", "value": -1.5, "min": -50.0},
            "vegetation_fraction": {"op": "add", "value": 0.2, "min": 0.0, "max": 1.0},
        },
        default_parameters={"trees_per_hectare": 500, "growth_years": 10},
        co2_reduction_factor=5.0,
        cost_per_hectare=15000.0,
    ),
    "cool_roof": ScenarioTemplate(
        name="cool_roof",
        description="Install reflective cool roofs on buildings",
        category="builtup",
        feature_modifiers={
            "albedo": {"op": "add", "value": 0.25, "min": 0.0, "max": 1.0},
            "ndvi": {"op": "add", "value": -0.02, "min": -1.0, "max": 1.0},
            "lst": {"op": "add", "value": -1.0, "min": -50.0},
            "builtup_fraction": {"op": "add", "value": 0.0},
        },
        default_parameters={"roof_area_pct": 0.3, "solar_reflectance": 0.7},
        co2_reduction_factor=3.0,
        cost_per_hectare=25000.0,
    ),
    "green_roof": ScenarioTemplate(
        name="green_roof",
        description="Install vegetated green roofs on buildings",
        category="builtup",
        feature_modifiers={
            "ndvi": {"op": "add", "value": 0.1, "min": -1.0, "max": 1.0},
            "albedo": {"op": "add", "value": 0.05, "min": 0.0, "max": 1.0},
            "lst": {"op": "add", "value": -1.2, "min": -50.0},
            "vegetation_fraction": {"op": "add", "value": 0.15, "min": 0.0, "max": 1.0},
        },
        default_parameters={"roof_area_pct": 0.2, "soil_depth_cm": 15},
        co2_reduction_factor=4.0,
        cost_per_hectare=40000.0,
    ),
    "reflective_pavement": ScenarioTemplate(
        name="reflective_pavement",
        description="Replace dark asphalt with high-albedo reflective pavement",
        category="builtup",
        feature_modifiers={
            "albedo": {"op": "add", "value": 0.3, "min": 0.0, "max": 1.0},
            "lst": {"op": "add", "value": -0.8, "min": -50.0},
        },
        default_parameters={"pavement_area_pct": 0.2, "target_albedo": 0.5},
        co2_reduction_factor=2.0,
        cost_per_hectare=35000.0,
    ),
    "water_body_restoration": ScenarioTemplate(
        name="water_body_restoration",
        description="Restore or create water bodies for evaporative cooling",
        category="water",
        feature_modifiers={
            "ndwi": {"op": "add", "value": 0.2, "min": -1.0, "max": 1.0},
            "ndvi": {"op": "add", "value": 0.05, "min": -1.0, "max": 1.0},
            "lst": {"op": "add", "value": -2.0, "min": -50.0},
            "albedo": {"op": "add", "value": 0.03, "min": 0.0, "max": 1.0},
        },
        default_parameters={"water_area_ha": 1.0, "depth_m": 2.0},
        co2_reduction_factor=1.0,
        cost_per_hectare=50000.0,
    ),
    "urban_green_space": ScenarioTemplate(
        name="urban_green_space",
        description="Develop parks, gardens, and green corridors",
        category="vegetation",
        feature_modifiers={
            "ndvi": {"op": "add", "value": 0.12, "min": -1.0, "max": 1.0},
            "lst": {"op": "add", "value": -1.8, "min": -50.0},
            "vegetation_fraction": {"op": "add", "value": 0.25, "min": 0.0, "max": 1.0},
            "albedo": {"op": "add", "value": 0.02, "min": 0.0, "max": 1.0},
            "builtup_fraction": {"op": "add", "value": -0.1, "min": 0.0, "max": 1.0},
        },
        default_parameters={"green_area_ha": 2.0, "tree_density": 0.4},
        co2_reduction_factor=3.5,
        cost_per_hectare=30000.0,
    ),
    "combined_mitigation": ScenarioTemplate(
        name="combined_mitigation",
        description="Combined strategy: trees + cool roofs + green spaces",
        category="combined",
        feature_modifiers={
            "ndvi": {"op": "add", "value": 0.2, "min": -1.0, "max": 1.0},
            "albedo": {"op": "add", "value": 0.15, "min": 0.0, "max": 1.0},
            "lst": {"op": "add", "value": -3.0, "min": -50.0},
            "vegetation_fraction": {"op": "add", "value": 0.3, "min": 0.0, "max": 1.0},
            "builtup_fraction": {"op": "add", "value": -0.05, "min": 0.0, "max": 1.0},
        },
        default_parameters={"intensity": 1.0},
        co2_reduction_factor=8.0,
        cost_per_hectare=60000.0,
    ),
}


def list_templates(category: str | None = None) -> list[ScenarioTemplate]:
    if category:
        return [t for t in SCENARIO_TEMPLATES.values() if t.category == category]
    return list(SCENARIO_TEMPLATES.values())


def get_template(name: str) -> ScenarioTemplate:
    if name not in SCENARIO_TEMPLATES:
        raise KeyError(f"Scenario template '{name}' not found. Available: {list(SCENARIO_TEMPLATES.keys())}")
    return SCENARIO_TEMPLATES[name]
