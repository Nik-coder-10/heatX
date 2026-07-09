import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import ComparisonError
from .simulator import SimulationResult

logger = logging.getLogger("app.scenario.comparator")


@dataclass
class ComparisonReport:
    baseline: SimulationResult | None
    scenarios: dict[str, SimulationResult]
    rankings: list[dict[str, Any]]
    best_scenario: str | None
    temperature_range: dict[str, float]
    cost_range: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "best_scenario": self.best_scenario,
            "rankings": self.rankings,
            "temperature_range": self.temperature_range,
            "cost_range": self.cost_range,
            "scenarios": {k: v.to_dict() for k, v in self.scenarios.items()},
            "metadata": self.metadata,
        }

    def summary(self) -> dict:
        return {
            "n_scenarios": len(self.scenarios),
            "best_scenario": self.best_scenario,
            "best_temp_reduction": self.rankings[0]["temp_reduction"] if self.rankings else 0,
            "best_cost_effectiveness": self.rankings[0]["cost_effectiveness"] if self.rankings else 0,
            "temp_range": self.temperature_range,
            "cost_range": self.cost_range,
        }


def compare_scenarios(
    results: list[SimulationResult],
    metric: str = "cost_effectiveness",
) -> ComparisonReport:
    if not results:
        raise ComparisonError("No simulation results to compare")

    scenarios = {r.scenario_name: r for r in results}

    rankings = []
    for r in results:
        rankings.append({
            "scenario": r.scenario_name,
            "temp_reduction": abs(r.mean_lst_change),
            "max_temp_reduction": abs(r.max_lst_change),
            "improvement_pct": r.pct_improvement,
            "cost": r.estimated_cost,
            "co2_reduction": r.estimated_co2_reduction,
            "cost_effectiveness": r.cost_effectiveness,
        })

    reverse = metric != "cost"
    rankings.sort(key=lambda x: x.get(metric, 0), reverse=reverse)

    best = rankings[0]["scenario"] if rankings else None

    temp_changes = [abs(r.mean_lst_change) for r in results]
    costs = [r.estimated_cost for r in results]

    baseline = next((r for r in results if r.scenario_name == "baseline"), None)

    return ComparisonReport(
        baseline=baseline,
        scenarios=scenarios,
        rankings=rankings,
        best_scenario=best,
        temperature_range={
            "min": round(min(temp_changes), 2) if temp_changes else 0,
            "max": round(max(temp_changes), 2) if temp_changes else 0,
            "mean": round(float(np.mean(temp_changes)), 2) if temp_changes else 0,
        },
        cost_range={
            "min": round(min(costs), 2) if costs else 0,
            "max": round(max(costs), 2) if costs else 0,
            "mean": round(float(np.mean(costs)), 2) if costs else 0,
        },
        metadata={"ranking_metric": metric},
    )
