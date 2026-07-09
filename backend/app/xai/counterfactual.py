import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import CounterfactualError

logger = logging.getLogger("app.xai.counterfactual")


FEATURE_CONSTRAINTS = {
    "ndvi": {"min": -1.0, "max": 1.0, "increase_means": "vegetation_growth"},
    "ndbi": {"min": -1.0, "max": 1.0, "increase_means": "builtup_increase"},
    "ndwi": {"min": -1.0, "max": 1.0, "increase_means": "water_increase"},
    "lst_celsius": {"min": -50.0, "max": 80.0, "increase_means": "warming"},
    "albedo": {"min": 0.0, "max": 1.0, "increase_means": "reflectivity_increase"},
    "elevation": {"min": -500.0, "max": 9000.0, "increase_means": "higher_elevation"},
    "slope": {"min": 0.0, "max": 90.0, "increase_means": "steeper"},
    "builtup_fraction": {"min": 0.0, "max": 1.0, "increase_means": "more_builtup"},
    "vegetation_fraction": {"min": 0.0, "max": 1.0, "increase_means": "more_vegetation"},
    "water_fraction": {"min": 0.0, "max": 1.0, "increase_means": "more_water"},
}


@dataclass
class CounterfactualExplanation:
    instance_id: str
    current_features: dict[str, float]
    suggested_changes: dict[str, dict]
    expected_temperature_reduction: float
    confidence: float = 1.0
    n_valid_counterfactuals: int = 0
    method: str = "feature_perturbation"
    feature_constraints: dict[str, dict] | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "current_features": self.current_features,
            "suggested_changes": self.suggested_changes,
            "expected_temperature_reduction": round(self.expected_temperature_reduction, 2),
            "confidence": round(self.confidence, 3),
            "n_valid_counterfactuals": self.n_valid_counterfactuals,
            "method": self.method,
        }


def _constrain(value, feature_name, default_min=-1e6, default_max=1e6):
    if feature_name in FEATURE_CONSTRAINTS:
        c = FEATURE_CONSTRAINTS[feature_name]
        return max(c["min"], min(c["max"], value))
    return max(default_min, min(default_max, value))


def estimate_temperature_reduction(
    model,
    X_row: np.ndarray,
    feature_names: list[str],
    changes: dict[str, float],
) -> float:
    X_modified = X_row.copy()
    for idx, name in enumerate(feature_names):
        if name in changes:
            X_modified[0, idx] = changes[name]

    original_temp = float(model.predict(X_row)[0])
    modified_temp = float(model.predict(X_modified)[0])
    return original_temp - modified_temp


def generate_counterfactual(
    model,
    X_row: np.ndarray,
    feature_names: list[str],
    target_reduction: float = 2.0,
    max_changes: int = 5,
    steps: int = 10,
    instance_id: str = "0",
) -> CounterfactualExplanation:
    if X_row.ndim == 1:
        X_row = X_row.reshape(1, -1)

    current_values = {name: float(X_row[0, i]) for i, name in enumerate(feature_names)}

    base_pred = float(model.predict(X_row)[0])

    sensitivities = {}
    perturbation = 0.01
    for i, name in enumerate(feature_names):
        X_up = X_row.copy()
        X_up[0, i] *= (1 + perturbation)
        pred_up = float(model.predict(X_up)[0])
        X_down = X_row.copy()
        X_down[0, i] *= (1 - perturbation)
        pred_down = float(model.predict(X_down)[0])
        sensitivities[name] = (pred_up - pred_down) / (2 * perturbation * float(abs(X_row[0, i])) + 1e-10)

    feature_order = sorted(
        [(name, abs(sens)) for name, sens in sensitivities.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    changes = {}
    total_reduction = 0.0

    strategies = {
        "ndvi": 0.15,
        "vegetation_fraction": 0.10,
        "albedo": 0.20,
        "ndbi": -0.10,
        "builtup_fraction": -0.05,
        "ndwi": 0.10,
        "water_fraction": 0.05,
    }

    for feat_name, _ in feature_order:
        if len(changes) >= max_changes:
            break
        if feat_name not in strategies:
            continue

        step = strategies[feat_name] / steps
        best_so_far = 0.0
        best_val = float(X_row[0, feature_names.index(feat_name)])

        for s in range(1, steps + 1):
            delta = step * s
            new_val = _constrain(
                float(X_row[0, feature_names.index(feat_name)]) + delta,
                feat_name,
            )
            if feat_name in FEATURE_CONSTRAINTS:
                c = FEATURE_CONSTRAINTS[feat_name]
                new_val = max(c["min"], min(c["max"], new_val))

            X_test = X_row.copy()
            X_test[0, feature_names.index(feat_name)] = new_val
            new_pred = float(model.predict(X_test)[0])
            reduction = base_pred - new_pred

            if reduction > best_so_far:
                best_so_far = reduction
                best_val = new_val

        if best_so_far > 0.1:
            changes[feat_name] = {
                "current": float(X_row[0, feature_names.index(feat_name)]),
                "suggested": float(best_val),
                "delta": float(best_val) - float(X_row[0, feature_names.index(feat_name)]),
                "expected_temperature_reduction": float(best_so_far),
                "action": _get_action_for_feature(feat_name, best_val),
            }
            total_reduction += best_so_far

    full_reduction = estimate_temperature_reduction(model, X_row, feature_names, {
        name: info["suggested"] for name, info in changes.items()
    })

    explanation = CounterfactualExplanation(
        instance_id=instance_id,
        current_features=current_values,
        suggested_changes=changes,
        expected_temperature_reduction=max(0.0, full_reduction),
        confidence=min(1.0, max(0.0, full_reduction / target_reduction)) if target_reduction > 0 else 0.5,
        n_valid_counterfactuals=len(changes),
        feature_constraints=FEATURE_CONSTRAINTS,
        metadata={"target_reduction": target_reduction, "base_prediction": float(base_pred)},
    )

    return explanation


def _get_action_for_feature(feature_name: str, suggested_value: float) -> str:
    actions = {
        "ndvi": "Increase vegetation cover / NDVI",
        "vegetation_fraction": "Increase vegetation fraction through greening",
        "albedo": "Improve roof and surface albedo (cool roofs)",
        "ndbi": "Reduce impervious surfaces / NDBI",
        "builtup_fraction": "Reduce built-up fraction, increase pervious surfaces",
        "ndwi": "Restore water bodies / increase NDWI",
        "water_fraction": "Increase water surface fraction",
        "lst_celsius": "Reduce land surface temperature",
        "elevation": "N/A (elevation cannot be changed)",
        "slope": "N/A (slope cannot be changed)",
    }
    return actions.get(feature_name, f"Optimize {feature_name}")


def batch_counterfactuals(
    model,
    X: np.ndarray,
    feature_names: list[str],
    target_reduction: float = 2.0,
    max_changes: int = 5,
    steps: int = 10,
) -> list[CounterfactualExplanation]:
    results = []
    for i in range(X.shape[0]):
        cf = generate_counterfactual(
            model,
            X[i:i+1],
            feature_names,
            target_reduction,
            max_changes,
            steps,
            instance_id=str(i),
        )
        results.append(cf)
    return results
