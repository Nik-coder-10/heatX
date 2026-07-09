import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import OptimizationError

logger = logging.getLogger("app.recommendation.optimization")


@dataclass
class OptimizationResult:
    selected_recommendations: list[dict]
    total_cost: float
    total_temp_reduction: float
    total_carbon_reduction: float
    budget_utilization: float
    n_scenarios: int = 1
    pareto_front: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "selected_recommendations": self.selected_recommendations,
            "total_cost": round(self.total_cost, 2),
            "total_temperature_reduction": round(self.total_temp_reduction, 2),
            "total_carbon_reduction": round(self.total_carbon_reduction, 2),
            "budget_utilization": round(self.budget_utilization, 4),
            "n_scenarios": self.n_scenarios,
        }


def _knapsack_select(
    items: list[dict],
    budget: float,
    cost_key: str = "estimated_cost",
    value_key: str = "overall_score",
) -> list[dict]:
    n = len(items)
    if n == 0 or budget <= 0:
        return []

    costs = np.array([max(item.get(cost_key, 0), 0) for item in items])
    values = np.array([max(item.get(value_key, 0), 0) for item in items])

    int_budget = max(1, int(budget))
    int_costs = np.maximum(1, (costs / budget * int_budget).astype(np.int64))
    int_costs = np.clip(int_costs, 1, int_budget)

    dp = np.zeros(int_budget + 1, dtype=np.float64)
    choice = np.zeros((n, int_budget + 1), dtype=bool)

    for i in range(n):
        c = int_costs[i]
        v = values[i]
        for w in range(int_budget, c - 1, -1):
            if dp[w - c] + v > dp[w]:
                dp[w] = dp[w - c] + v
                choice[i, w] = True

    selected = []
    w = int_budget
    for i in range(n - 1, -1, -1):
        if choice[i, w]:
            selected.append(items[i])
            w -= int_costs[i]

    return selected


def optimize_with_budget(
    candidates: list[Any],
    budget: float,
    max_recommendations: int = 5,
    include_knapsack: bool = True,
) -> OptimizationResult:
    if not candidates:
        raise OptimizationError("No candidates to optimize")
    if budget <= 0:
        raise OptimizationError("Budget must be positive")

    items = []
    for c in candidates:
        if hasattr(c, "to_dict"):
            d = c.to_dict()
        elif isinstance(c, dict):
            d = c
        else:
            d = {"estimated_cost": 0, "overall_score": 0}
        items.append(d)

    affordable = [i for i in items if i.get("estimated_cost", 0) <= budget]
    if not affordable:
        return OptimizationResult(
            selected_recommendations=[], total_cost=0, total_temp_reduction=0,
            total_carbon_reduction=0, budget_utilization=0,
        )

    if include_knapsack:
        selected = _knapsack_select(affordable, budget)
        selected = sorted(selected, key=lambda x: x.get("priority", 999))
    else:
        sorted_items = sorted(affordable, key=lambda x: x.get("overall_score", 0), reverse=True)
        selected = []
        running_cost = 0.0
        for item in sorted_items:
            cost = item.get("estimated_cost", 0)
            if running_cost + cost <= budget and len(selected) < max_recommendations:
                selected.append(item)
                running_cost += cost

    total_cost = sum(item.get("estimated_cost", 0) for item in selected)
    total_temp = sum(item.get("expected_temperature_reduction", 0) for item in selected)
    total_carbon = sum(item.get("carbon_reduction", 0) for item in selected)

    return OptimizationResult(
        selected_recommendations=selected,
        total_cost=total_cost,
        total_temp_reduction=total_temp,
        total_carbon_reduction=total_carbon,
        budget_utilization=total_cost / budget if budget > 0 else 0,
    )


def generate_scenarios(
    candidates: list[Any],
    budgets: list[float],
) -> list[OptimizationResult]:
    if not budgets:
        raise OptimizationError("At least one budget level required")

    results = []
    for budget in sorted(budgets):
        result = optimize_with_budget(candidates, budget)
        results.append(result)
    return results
