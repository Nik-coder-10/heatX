import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .configuration import ScenarioConfig
from .exceptions import ForecastError, ScenarioNotFoundError
from .templates import ScenarioTemplate, get_template, list_templates
from .simulator import SimulationResult, simulate_scenario, batch_simulate
from .comparator import ComparisonReport, compare_scenarios

logger = logging.getLogger("app.scenario.engine")


@dataclass
class ScenarioPlan:
    scenario_name: str
    simulation: SimulationResult
    comparison: ComparisonReport | None = None

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "simulation": self.simulation.to_dict(),
            "comparison": self.comparison.to_dict() if self.comparison else None,
        }


class ScenarioEngine:
    def __init__(self, config: ScenarioConfig | dict | None = None):
        if config is None:
            self.config = ScenarioConfig.defaults()
        elif isinstance(config, dict):
            self.config = ScenarioConfig.from_dict(config)
        else:
            self.config = config

    def run_scenario(self, scenario_name: str,
                     X: np.ndarray, y: np.ndarray | None,
                     feature_names: list[str], model: Any,
                     intensity: float = 1.0,
                     area_ha: float = 1.0,
                     params: dict | None = None) -> SimulationResult:
        try:
            template = get_template(scenario_name)
        except KeyError:
            raise ScenarioNotFoundError(f"Scenario '{scenario_name}' not found")

        return simulate_scenario(
            template, X, y, feature_names, model,
            intensity=intensity, area_ha=area_ha, params=params,
        )

    def run_multiple(self, scenario_names: list[str],
                     X: np.ndarray, y: np.ndarray | None,
                     feature_names: list[str], model: Any,
                     intensities: list[float] | None = None,
                     area_ha: float = 1.0,
                     compare: bool = True) -> list[SimulationResult] | tuple[list[SimulationResult], ComparisonReport]:
        results = batch_simulate(scenario_names, X, y, feature_names, model,
                                  intensities=intensities, area_ha=area_ha)
        if compare and len(results) > 1:
            report = compare_scenarios(results, metric="cost_effectiveness")
            return results, report
        return results

    def run_all(self, X: np.ndarray, y: np.ndarray | None,
                feature_names: list[str], model: Any,
                area_ha: float = 1.0,
                compare: bool = True) -> tuple[list[SimulationResult], ComparisonReport | None]:
        names = list_templates()
        results = []
        for t in names:
            try:
                r = simulate_scenario(t, X, y, feature_names, model, area_ha=area_ha)
                results.append(r)
            except Exception as e:
                logger.warning("Scenario '%s' failed: %s", t.name, e)

        report = compare_scenarios(results, metric="cost_effectiveness") if compare and results else None
        return results, report


def create_scenario_engine(config: ScenarioConfig | dict | None = None) -> ScenarioEngine:
    return ScenarioEngine(config)
