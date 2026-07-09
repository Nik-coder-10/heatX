import logging
from dataclasses import dataclass, field
from typing import Any

from .configuration import RecommenderConfig
from .exceptions import InvalidHotspotError, NoRecommendationsError
from .rules import apply_rules
from .scoring import ScoredRecommendation, score_candidates
from .optimization import OptimizationResult, optimize_with_budget, generate_scenarios

logger = logging.getLogger("app.recommendation.engine")


@dataclass
class RecommendationBundle:
    hotspot_id: str
    hotspot_severity: str
    recommendations: list[ScoredRecommendation]
    optimization: OptimizationResult | None = None
    scenarios: list[OptimizationResult] | None = None
    xai_summary: dict | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "hotspot_id": self.hotspot_id,
            "hotspot_severity": self.hotspot_severity,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "optimization": self.optimization.to_dict() if self.optimization else None,
            "scenarios": [s.to_dict() for s in self.scenarios] if self.scenarios else None,
            "xai_summary": self.xai_summary,
            "metadata": self.metadata or {},
        }

    def summary(self) -> dict:
        n = len(self.recommendations)
        top = self.recommendations[0] if self.recommendations else None
        return {
            "hotspot_id": self.hotspot_id,
            "hotspot_severity": self.hotspot_severity,
            "n_recommendations": n,
            "top_recommendation": top.label if top else None,
            "top_priority": top.priority if top else None,
            "top_cost": top.estimated_cost if top else None,
            "top_temp_reduction": top.expected_temperature_reduction if top else None,
            "optimization": bool(self.optimization),
        }


class RecommenderEngine:
    def __init__(self, config: RecommenderConfig | dict | None = None):
        if config is None:
            self.config = RecommenderConfig.defaults()
        elif isinstance(config, dict):
            self.config = RecommenderConfig.from_dict(config)
        else:
            self.config = config

    def recommend(self, hotspot: Any,
                  xai_explanation: Any | None = None,
                  ml_forecast: Any | None = None,
                  budget: float | None = None,
                  generate_scenarios_list: bool = False) -> RecommendationBundle:
        if hotspot is None:
            raise InvalidHotspotError("Hotspot must not be None")

        hotspot_id = getattr(hotspot, "id", "unknown")
        hotspot_severity = getattr(hotspot, "severity", "unknown")

        candidates = apply_rules(hotspot, self.config)
        if not candidates:
            raise NoRecommendationsError(
                f"No recommendations could be generated for hotspot {hotspot_id}"
            )

        xai_importance = None
        if xai_explanation is not None:
            global_exp = getattr(xai_explanation, "global_explanation", None)
            if global_exp is not None:
                xai_importance = getattr(global_exp, "feature_importance", None)
            if xai_importance is None:
                try:
                    xai_summary = xai_explanation.summary() if callable(xai_explanation.summary) else None
                except Exception:
                    xai_summary = None
                if xai_summary:
                    xai_importance = xai_summary.get("feature_importance")

        budget_constraint = budget or getattr(self.config, "budget_constraint", None)

        scored = score_candidates(
            candidates, hotspot, self.config, xai_importance,
            budget_constraint=budget_constraint,
            min_feasibility=self.config.min_feasibility_score,
        )
        if self.config.max_recommendations > 0:
            scored = scored[:self.config.max_recommendations]

        xai_summary = None
        if xai_explanation is not None:
            try:
                if hasattr(xai_explanation, "summary"):
                    xai_summary = xai_explanation.summary()
                elif hasattr(xai_explanation, "to_dict"):
                    xai_summary = xai_explanation.to_dict()
            except Exception:
                pass

        optimization = None
        if budget_constraint and scored:
            opt_candidates = [r.to_dict() for r in scored]
            try:
                optimization = optimize_with_budget(
                    opt_candidates, budget_constraint,
                    max_recommendations=self.config.max_recommendations,
                )
            except Exception as exc:
                logger.warning("Budget optimization failed: %s", exc)

        scenarios = None
        if generate_scenarios_list:
            budget_levels = [budget_constraint * m for m in [0.5, 0.75, 1.0, 1.25, 1.5]]
            try:
                opt_candidates = [r.to_dict() for r in scored]
                scenarios = generate_scenarios(opt_candidates, budget_levels)
            except Exception as exc:
                logger.warning("Scenario generation failed: %s", exc)

        return RecommendationBundle(
            hotspot_id=hotspot_id,
            hotspot_severity=hotspot_severity,
            recommendations=scored,
            optimization=optimization,
            scenarios=scenarios,
            xai_summary=xai_summary,
            metadata={"config_summary": str(self.config)},
        )

    def recommend_batch(self, hotspots: list[Any],
                        xai_results: list[Any] | None = None,
                        ml_results: list[Any] | None = None,
                        budget: float | None = None) -> list[RecommendationBundle]:
        results = []
        for i, hotspot in enumerate(hotspots):
            xai_exp = xai_results[i] if xai_results and i < len(xai_results) else None
            ml_fore = ml_results[i] if ml_results and i < len(ml_results) else None
            if hotspot is None:
                logger.info("Skipping None hotspot at index %d", i)
                bundle = RecommendationBundle(
                    hotspot_id=f"hotspot_{i}",
                    hotspot_severity="unknown",
                    recommendations=[],
                )
                results.append(bundle)
                continue
            try:
                bundle = self.recommend(hotspot, xai_exp, ml_fore, budget)
                results.append(bundle)
            except NoRecommendationsError:
                logger.info("No recommendations for hotspot %s", getattr(hotspot, "id", i))
                bundle = RecommendationBundle(
                    hotspot_id=getattr(hotspot, "id", f"hotspot_{i}"),
                    hotspot_severity=getattr(hotspot, "severity", "unknown"),
                    recommendations=[],
                )
                results.append(bundle)
        return results


def create_recommender(config: RecommenderConfig | dict | None = None) -> RecommenderEngine:
    return RecommenderEngine(config)
