import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import ForecastError, InvalidParameterError
from .templates import ScenarioTemplate, get_template

logger = logging.getLogger("app.scenario.simulator")


@dataclass
class SimulationResult:
    scenario_name: str
    baseline_lst: np.ndarray
    simulated_lst: np.ndarray
    lst_change: np.ndarray
    mean_lst_baseline: float
    mean_lst_simulated: float
    mean_lst_change: float
    max_lst_change: float
    pct_improvement: float
    total_area_ha: float = 0.0
    estimated_cost: float = 0.0
    estimated_co2_reduction: float = 0.0
    cost_effectiveness: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        stat = {
            "scenario_name": self.scenario_name,
            "mean_lst_baseline": round(self.mean_lst_baseline, 2),
            "mean_lst_simulated": round(self.mean_lst_simulated, 2),
            "mean_lst_change": round(self.mean_lst_change, 2),
            "max_lst_change": round(self.max_lst_change, 2),
            "pct_improvement": round(self.pct_improvement, 2),
            "total_area_ha": round(self.total_area_ha, 2),
            "estimated_cost": round(self.estimated_cost, 2),
            "estimated_co2_reduction": round(self.estimated_co2_reduction, 2),
            "cost_effectiveness": round(self.cost_effectiveness, 4),
            "parameters": self.parameters,
        }
        return stat

    def summary(self) -> dict:
        return {
            "scenario": self.scenario_name,
            "temp_reduction_c": round(self.mean_lst_change, 2),
            "max_reduction_c": round(self.max_lst_change, 2),
            "improvement_pct": round(self.pct_improvement, 2),
            "cost_effectiveness": round(self.cost_effectiveness, 4),
        }


def _compute_feature_modifiers(template: ScenarioTemplate, X: np.ndarray,
                                feature_names: list[str], intensity: float) -> dict:
    modifiers = {}
    for feature, modifier in template.feature_modifiers.items():
        if feature not in feature_names:
            logger.debug("Feature '%s' not found in feature_names, skipping", feature)
            continue
        idx = feature_names.index(feature)
        op = modifier.get("op", "add")
        value = modifier.get("value", 0.0) * intensity
        lo = modifier.get("min", -np.inf)
        hi = modifier.get("max", np.inf)
        modifiers[feature] = {"idx": idx, "op": op, "value": value, "min": lo, "max": hi}
    return modifiers


def _apply_modifiers(X: np.ndarray, modifiers: dict) -> np.ndarray:
    X_mod = X.copy().astype(np.float64)
    for feature, mod in modifiers.items():
        idx = mod["idx"]
        op = mod["op"]
        value = mod["value"]
        if op == "add":
            X_mod[:, idx] = X_mod[:, idx] + value
        elif op == "mul":
            X_mod[:, idx] = X_mod[:, idx] * (1.0 + value)
        elif op == "set":
            X_mod[:, idx] = value
        elif op == "scale_to":
            target = value
            current = X_mod[:, idx]
            offset = target - current.mean()
            X_mod[:, idx] = current + offset
        X_mod[:, idx] = np.clip(X_mod[:, idx], mod["min"], mod["max"])
    return X_mod


def simulate_scenario(
    template: ScenarioTemplate | str,
    X: np.ndarray,
    y: np.ndarray | None,
    feature_names: list[str],
    model: Any,
    intensity: float = 1.0,
    task: str = "regression",
    area_ha: float = 1.0,
    params: dict | None = None,
) -> SimulationResult:
    if isinstance(template, str):
        template = get_template(template)

    if len(feature_names) != X.shape[1]:
        raise InvalidParameterError(
            f"Feature names length ({len(feature_names)}) must match X columns ({X.shape[1]})"
        )

    modifiers = _compute_feature_modifiers(template, X, feature_names, intensity)
    X_sim = _apply_modifiers(X, modifiers)

    if hasattr(model, "predict"):
        try:
            baseline_pred = model.predict(X)
            simulated_pred = model.predict(X_sim)
        except Exception as e:
            raise ForecastError(f"Model prediction failed: {e}") from e
    else:
        baseline_pred = np.zeros(X.shape[0])
        simulated_pred = np.zeros(X.shape[0])

    lst_col = None
    for candidate in ["lst", "lst_celsius", "temperature", "target"]:
        if candidate in feature_names:
            lst_col = feature_names.index(candidate)
            break

    if lst_col is not None:
        baseline_lst = X[:, lst_col]
    elif y is not None:
        baseline_lst = y.flatten() if isinstance(y, np.ndarray) else np.array(y).flatten()
    else:
        baseline_lst = baseline_pred

    baseline_lst = baseline_lst.flatten().astype(np.float64)
    simulated_lst = simulated_pred.flatten().astype(np.float64)

    lst_change = simulated_lst - baseline_lst
    mean_baseline = float(np.mean(baseline_lst))
    mean_simulated = float(np.mean(simulated_lst))
    mean_change = float(np.mean(lst_change))
    max_change = float(np.min(lst_change))

    if abs(mean_baseline) > 1e-10:
        pct_improvement = abs(mean_change) / abs(mean_baseline) * 100.0
    else:
        pct_improvement = 0.0

    cost = template.cost_per_hectare * area_ha
    co2_reduction = template.co2_reduction_factor * area_ha
    cost_eff = abs(mean_change) / cost * 1e6 if cost > 0 else 0.0

    return SimulationResult(
        scenario_name=template.name,
        baseline_lst=baseline_lst,
        simulated_lst=simulated_lst,
        lst_change=lst_change,
        mean_lst_baseline=mean_baseline,
        mean_lst_simulated=mean_simulated,
        mean_lst_change=mean_change,
        max_lst_change=max_change,
        pct_improvement=pct_improvement,
        total_area_ha=area_ha,
        estimated_cost=cost,
        estimated_co2_reduction=co2_reduction,
        cost_effectiveness=cost_eff,
        parameters=params or {},
        metadata={"feature_modifiers": list(modifiers.keys()), "intensity": intensity},
    )


def batch_simulate(
    template_names: list[str],
    X: np.ndarray,
    y: np.ndarray | None,
    feature_names: list[str],
    model: Any,
    intensities: list[float] | None = None,
    area_ha: float = 1.0,
) -> list[SimulationResult]:
    if intensities is None:
        intensities = [1.0]

    results = []
    for name in template_names:
        try:
            template = get_template(name)
        except KeyError:
            logger.warning("Template '%s' not found, skipping", name)
            continue
        for intensity in intensities:
            try:
                result = simulate_scenario(
                    template, X, y, feature_names, model,
                    intensity=intensity, area_ha=area_ha,
                )
                results.append(result)
            except Exception as e:
                logger.error("Simulation failed for %s at intensity %.1f: %s", name, intensity, e)
    return results
