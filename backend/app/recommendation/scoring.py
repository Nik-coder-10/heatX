import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import ScoringError

logger = logging.getLogger("app.recommendation.scoring")


@dataclass
class ScoredRecommendation:
    recommendation_type: str
    label: str
    description: str
    estimated_cost: float
    expected_temperature_reduction: float
    carbon_reduction: float
    priority: int
    priority_weight: float
    cost_effectiveness: float
    feasibility_score: float
    overall_score: float
    area_hectares: float
    current_temperature_c: float
    rationale: str = ""
    feature_attribution: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "recommendation_type": self.recommendation_type,
            "label": self.label,
            "description": self.description,
            "estimated_cost": self.estimated_cost,
            "expected_temperature_reduction": self.expected_temperature_reduction,
            "carbon_reduction": self.carbon_reduction,
            "priority": self.priority,
            "priority_weight": self.priority_weight,
            "cost_effectiveness": self.cost_effectiveness,
            "feasibility_score": self.feasibility_score,
            "overall_score": self.overall_score,
            "area_hectares": self.area_hectares,
            "current_temperature_c": self.current_temperature_c,
            "rationale": self.rationale,
            "feature_attribution": self.feature_attribution,
        }


def compute_cost_effectiveness(cost: float, temp_reduction: float, carbon_reduction: float,
                               co2_price: float = 50.0, discount_rate: float = 0.05,
                               time_horizon: int = 20) -> float:
    if cost <= 0:
        return 0.0
    pv_carbon_benefit = carbon_reduction * co2_price * (
        (1 - (1 + discount_rate) ** -time_horizon) / discount_rate
    )
    net_cost = cost - pv_carbon_benefit
    if net_cost <= 0:
        return 100.0
    return round(temp_reduction / net_cost * 1e6, 4)


def compute_feasibility(candidate: dict, hotspot: Any | None = None) -> float:
    score = 0.5
    area_ha = candidate.get("area_hectares", 0.0)
    if area_ha <= 0:
        score -= 0.2
    elif area_ha > 100:
        score -= 0.1
    elif area_ha < 0.5:
        score -= 0.1

    cost = candidate.get("estimated_cost", 0.0)
    if cost > 10_000_000:
        score -= 0.15
    elif cost < 10_000:
        score += 0.1

    rec_type = candidate.get("recommendation_type", "")
    temp_reduction = candidate.get("expected_temperature_reduction", 0.0)
    if temp_reduction < 0.3:
        score -= 0.1

    built_frac = getattr(hotspot, "builtup_fraction", 0.5) if hotspot else 0.5
    if rec_type in ("cool_roof", "green_roof", "reflective_pavement") and built_frac < 0.2:
        score -= 0.15
    if rec_type in ("water_body_restoration", "tree_plantation") and built_frac > 0.8:
        score -= 0.1

    return round(max(0.0, min(1.0, score)), 4)


def score_candidates(candidates: list[dict], hotspot: Any | None = None,
                     config: Any | None = None, xai_importance: dict[str, float] | None = None,
                     budget_constraint: float | None = None,
                     min_feasibility: float = 0.2) -> list[ScoredRecommendation]:
    if not candidates:
        raise ScoringError("No candidates to score")

    co2_price = getattr(config, "co2_price_per_ton", 50.0) if config else 50.0
    discount_rate = getattr(config, "discount_rate", 0.05) if config else 0.05
    time_horizon = getattr(config, "time_horizon_years", 20) if config else 20
    if budget_constraint is None:
        budget_constraint = getattr(config, "budget_constraint", None) if config else None

    scored = []
    for candidate in candidates:
        if budget_constraint and candidate.get("estimated_cost", 0) > budget_constraint:
            logger.debug("Skipping %s: cost %.0f exceeds budget %.0f",
                         candidate["recommendation_type"], candidate["estimated_cost"], budget_constraint)
            continue

        cost_effectiveness = compute_cost_effectiveness(
            candidate["estimated_cost"],
            candidate["expected_temperature_reduction"],
            candidate["carbon_reduction"],
            co2_price, discount_rate, time_horizon,
        )
        feasibility = compute_feasibility(candidate, hotspot)
        if feasibility < min_feasibility:
            logger.debug("Skipping %s: feasibility %.2f below threshold %.2f",
                         candidate["recommendation_type"], feasibility, min_feasibility)
            continue

        priority_weight = candidate.get("priority_weight", 0.5)
        temp_reduction = candidate["expected_temperature_reduction"]

        attribution = {}
        if xai_importance and candidate["recommendation_type"] in ("tree_plantation", "urban_green_space"):
            ndvi_score = xai_importance.get("ndvi", 0.0)
            attribution["ndvi_importance"] = ndvi_score
        if xai_importance and candidate["recommendation_type"] in ("cool_roof", "reflective_pavement"):
            albedo_score = xai_importance.get("albedo", 0.0)
            attribution["albedo_importance"] = albedo_score

        overall = (
            cost_effectiveness * 0.3 +
            feasibility * 0.25 +
            temp_reduction * 10.0 * 0.2 +
            priority_weight * 0.15 +
            np.log1p(candidate["carbon_reduction"]) * 0.02 * 0.1
        )
        overall = round(overall, 4)

        scored.append(ScoredRecommendation(
            recommendation_type=candidate["recommendation_type"],
            label=candidate["label"],
            description=candidate["description"],
            estimated_cost=candidate["estimated_cost"],
            expected_temperature_reduction=temp_reduction,
            carbon_reduction=candidate["carbon_reduction"],
            priority=0,
            priority_weight=priority_weight,
            cost_effectiveness=cost_effectiveness,
            feasibility_score=feasibility,
            overall_score=overall,
            area_hectares=candidate["area_hectares"],
            current_temperature_c=candidate["current_temperature_c"],
            rationale=candidate.get("rationale", ""),
            feature_attribution=attribution,
        ))

    scored.sort(key=lambda r: r.overall_score, reverse=True)
    for i, rec in enumerate(scored):
        rec.priority = i + 1

    return scored
