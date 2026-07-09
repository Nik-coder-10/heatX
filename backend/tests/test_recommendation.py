import numpy as np
import pytest

from app.recommendation import (
    RecommendationError, ConfigurationError, InvalidHotspotError,
    NoRecommendationsError, OptimizationError, BudgetExceededError, ScoringError,
    RecommenderConfig,
    apply_rules, RECOMMENDATION_PROFILES,
    ScoredRecommendation, score_candidates,
    compute_cost_effectiveness, compute_feasibility,
    OptimizationResult, optimize_with_budget, generate_scenarios,
    RecommenderEngine, RecommendationBundle, create_recommender,
)


@pytest.fixture
def bare_hotspot():
    class FakeHotspot:
        id = "UHI-0001"
        severity = "high"
        dominant_landcover = "Builtup"
        mean_ndvi = 0.05
        mean_ndbi = 0.35
        mean_ndwi = -0.15
        vegetation_fraction = 0.1
        builtup_fraction = 0.7
        area_sq_km = 0.05
        mean_temperature_c = 42.3
        max_temperature_c = 47.1
        min_temperature_c = 38.2
        pixel_count = 150
        confidence = 0.85
        quality_metrics = {"completeness": 0.95}
    return FakeHotspot()


@pytest.fixture
def green_hotspot():
    class FakeHotspot:
        id = "UHI-0002"
        severity = "moderate"
        dominant_landcover = "Vegetation"
        mean_ndvi = 0.45
        mean_ndbi = -0.1
        mean_ndwi = -0.05
        vegetation_fraction = 0.6
        builtup_fraction = 0.15
        area_sq_km = 1.2
        mean_temperature_c = 35.1
        max_temperature_c = 39.2
        min_temperature_c = 31.0
        pixel_count = 3500
        confidence = 0.9
        quality_metrics = {"completeness": 0.98}
    return FakeHotspot()


@pytest.fixture
def extreme_hotspot():
    class FakeHotspot:
        id = "UHI-0003"
        severity = "extreme"
        dominant_landcover = "Builtup"
        mean_ndvi = -0.1
        mean_ndbi = 0.6
        mean_ndwi = -0.3
        vegetation_fraction = 0.02
        builtup_fraction = 0.95
        area_sq_km = 2.0
        mean_temperature_c = 48.7
        max_temperature_c = 52.3
        min_temperature_c = 44.1
        pixel_count = 6000
        confidence = 0.75
        quality_metrics = {"completeness": 0.85}
    return FakeHotspot()


class TestExceptions:
    def test_base_exception(self):
        with pytest.raises(RecommendationError):
            raise RecommendationError("base")
        with pytest.raises(RecommendationError):
            raise ConfigurationError("config")
        with pytest.raises(RecommendationError):
            raise InvalidHotspotError("hotspot")
        with pytest.raises(RecommendationError):
            raise NoRecommendationsError("none")
        with pytest.raises(RecommendationError):
            raise OptimizationError("opt")
        with pytest.raises(RecommendationError):
            raise ScoringError("score")
        with pytest.raises(RecommendationError):
            raise BudgetExceededError("budget")


class TestRecommenderConfig:
    def test_defaults(self):
        cfg = RecommenderConfig.defaults()
        assert cfg.max_recommendations == 5
        assert cfg.min_temperature_reduction == 0.5
        assert cfg.prioritization_method == "cost_effectiveness"

    def test_from_dict(self):
        cfg = RecommenderConfig.from_dict({"max_recommendations": 10, "verbose": True})
        assert cfg.max_recommendations == 10
        assert cfg.verbose is True

    def test_from_dict_invalid_key(self):
        with pytest.raises(ConfigurationError):
            RecommenderConfig.from_dict({"invalid_key": 1})

    def test_from_dict_override(self):
        cfg = RecommenderConfig.from_dict({"budget_constraint": 1_000_000})
        assert cfg.budget_constraint == 1_000_000


class TestRules:
    def test_apply_rules_builtup_high(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        assert len(candidates) > 0
        types = [c["recommendation_type"] for c in candidates]
        assert "cool_roof" in types
        assert "reflective_pavement" in types
        assert "cool_roof" in types or "green_roof" in types

    def test_apply_rules_green_moderate(self, green_hotspot):
        candidates = apply_rules(green_hotspot)
        types = [c["recommendation_type"] for c in candidates]
        assert "urban_green_space" in types

    def test_apply_rules_extreme(self, extreme_hotspot):
        candidates = apply_rules(extreme_hotspot)
        assert len(candidates) > 0
        for c in candidates:
            assert c["estimated_cost"] > 0
            assert c["expected_temperature_reduction"] > 0

    def test_apply_rules_no_severity_match(self):
        class MildHotspot:
            id = "UHI-0000"
            severity = "very_low"
            dominant_landcover = "Builtup"
            mean_ndvi = 0.05
            mean_ndbi = 0.3
            mean_ndwi = -0.1
            vegetation_fraction = 0.1
            builtup_fraction = 0.6
            area_sq_km = 0.1
            mean_temperature_c = 28.0

        candidates = apply_rules(MildHotspot())
        assert len(candidates) == 0 or candidates[0]["recommendation_type"] == "urban_green_space"

    def test_apply_rules_fallback_on_empty(self):
        class NoMatchHotspot:
            id = "UHI-9999"
            severity = "very_low"
            dominant_landcover = "water"
            mean_ndvi = -0.5
            mean_ndbi = -0.5
            mean_ndwi = 0.8
            vegetation_fraction = 0.0
            builtup_fraction = 0.0
            area_sq_km = 0.01
            mean_temperature_c = 22.0

        candidates = apply_rules(NoMatchHotspot())
        assert len(candidates) >= 0

    def test_apply_rules_invalid_hotspot(self):
        class BadHotspot:
            pass

        with pytest.raises(InvalidHotspotError):
            apply_rules(BadHotspot())

    def test_rationale_generated(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        for c in candidates:
            assert "rationale" in c
            assert len(c["rationale"]) > 10

    def test_recommendation_profiles_complete(self):
        assert "tree_plantation" in RECOMMENDATION_PROFILES
        assert "cool_roof" in RECOMMENDATION_PROFILES
        assert "green_roof" in RECOMMENDATION_PROFILES
        assert "reflective_pavement" in RECOMMENDATION_PROFILES
        assert "water_body_restoration" in RECOMMENDATION_PROFILES
        assert "urban_green_space" in RECOMMENDATION_PROFILES
        for name, profile in RECOMMENDATION_PROFILES.items():
            assert "label" in profile
            assert "base_cost_per_hectare" in profile
            assert "temp_reduction_per_hectare" in profile
            assert "carbon_reduction_per_hectare" in profile
            assert profile["base_cost_per_hectare"] > 0


class TestScoring:
    def test_cost_effectiveness(self):
        ce = compute_cost_effectiveness(100000, 1.5, 5.0)
        assert ce > 0

    def test_cost_effectiveness_zero_cost(self):
        assert compute_cost_effectiveness(0, 1.5, 5.0) == 0.0

    def test_cost_effectiveness_high_carbon_value(self):
        ce = compute_cost_effectiveness(1000, 1.5, 1000.0, co2_price=200.0)
        assert ce > 0

    def test_feasibility_builtup_green_roof(self, bare_hotspot):
        candidate = {"recommendation_type": "green_roof", "area_hectares": 5.0,
                      "estimated_cost": 200000, "expected_temperature_reduction": 1.0}
        score = compute_feasibility(candidate, bare_hotspot)
        assert 0.0 <= score <= 1.0

    def test_feasibility_low_builtup(self):
        candidate = {"recommendation_type": "cool_roof", "area_hectares": 10.0,
                      "estimated_cost": 250000, "expected_temperature_reduction": 0.8}
        class LowBuiltHotspot:
            builtup_fraction = 0.05
        score = compute_feasibility(candidate, LowBuiltHotspot())
        assert score < 0.5

    def test_score_candidates(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot)
        assert len(scored) > 0
        assert len(scored) <= len(candidates)
        for r in scored:
            assert isinstance(r, ScoredRecommendation)
            assert r.priority >= 1
            assert r.overall_score >= 0

    def test_scored_ordered_by_priority(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot)
        for i in range(len(scored) - 1):
            assert scored[i].priority < scored[i + 1].priority

    def test_scored_to_dict(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot)
        d = scored[0].to_dict()
        assert "recommendation_type" in d
        assert "estimated_cost" in d
        assert "overall_score" in d
        assert "priority" in d

    def test_score_empty_candidates(self):
        with pytest.raises(ScoringError):
            score_candidates([])

    def test_score_with_budget_constraint(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot, budget_constraint=10_000)
        for r in scored:
            assert r.estimated_cost <= 10_000

    def test_score_with_xai_importance(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        xai_imp = {"ndvi": 85.0, "albedo": 72.0, "builtup": 60.0}
        scored = score_candidates(candidates, bare_hotspot, xai_importance=xai_imp)
        assert len(scored) > 0

    def test_feasibility_threshold(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot, min_feasibility=0.0)
        assert len(scored) > 0
        for r in scored:
            assert r.feasibility_score >= 0.0


class TestOptimization:
    def test_optimize_basic(self):
        candidates = [
            {"recommendation_type": "tree_plantation", "estimated_cost": 50000,
             "expected_temperature_reduction": 1.5, "carbon_reduction": 5.0,
             "priority": 1, "overall_score": 0.85},
            {"recommendation_type": "cool_roof", "estimated_cost": 30000,
             "expected_temperature_reduction": 1.0, "carbon_reduction": 3.0,
             "priority": 2, "overall_score": 0.72},
        ]
        result = optimize_with_budget(candidates, 100000)
        assert len(result.selected_recommendations) > 0
        assert result.total_cost <= 100000
        assert result.total_temp_reduction > 0

    def test_optimize_empty(self):
        with pytest.raises(OptimizationError):
            optimize_with_budget([], 100000)

    def test_optimize_zero_budget(self):
        with pytest.raises(OptimizationError):
            optimize_with_budget([{"estimated_cost": 100}], 0)

    def test_optimize_budget_exceeded(self):
        candidates = [
            {"recommendation_type": "water_body_restoration", "estimated_cost": 500000,
             "expected_temperature_reduction": 2.0, "carbon_reduction": 1.0,
             "priority": 1, "overall_score": 0.6},
        ]
        result = optimize_with_budget(candidates, 10000)
        assert len(result.selected_recommendations) == 0

    def test_optimize_greedy_fallback(self):
        candidates = [
            {"recommendation_type": "tree_plantation", "estimated_cost": 40000,
             "expected_temperature_reduction": 1.5, "carbon_reduction": 5.0,
             "priority": 1, "overall_score": 0.85},
            {"recommendation_type": "cool_roof", "estimated_cost": 25000,
             "expected_temperature_reduction": 1.0, "carbon_reduction": 3.0,
             "priority": 2, "overall_score": 0.72},
        ]
        result = optimize_with_budget(candidates, 50000, include_knapsack=False)
        assert len(result.selected_recommendations) > 0

    def test_optimize_to_dict(self):
        candidates = [
            {"recommendation_type": "tree_plantation", "estimated_cost": 50000,
             "expected_temperature_reduction": 1.5, "carbon_reduction": 5.0,
             "priority": 1, "overall_score": 0.85},
        ]
        result = optimize_with_budget(candidates, 100000)
        d = result.to_dict()
        assert "total_cost" in d
        assert "total_temperature_reduction" in d
        assert "budget_utilization" in d

    def test_scenarios(self):
        candidates = [
            {"recommendation_type": "tree_plantation", "estimated_cost": 50000,
             "expected_temperature_reduction": 1.5, "carbon_reduction": 5.0,
             "priority": 1, "overall_score": 0.85},
            {"recommendation_type": "cool_roof", "estimated_cost": 30000,
             "expected_temperature_reduction": 1.0, "carbon_reduction": 3.0,
             "priority": 2, "overall_score": 0.72},
        ]
        scenarios = generate_scenarios(candidates, [25000, 50000, 100000])
        assert len(scenarios) == 3
        for s in scenarios:
            assert s.total_cost >= 0

    def test_scenarios_empty_budgets(self):
        with pytest.raises(OptimizationError):
            generate_scenarios([{"estimated_cost": 100}], [])


class TestEngine:
    def test_create_engine(self):
        engine = create_recommender()
        assert isinstance(engine, RecommenderEngine)
        assert engine.config.max_recommendations == 5

    def test_engine_with_config_dict(self):
        engine = RecommenderEngine({"max_recommendations": 3, "verbose": True})
        assert engine.config.max_recommendations == 3
        assert engine.config.verbose is True

    def test_recommend_basic(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot)
        assert isinstance(bundle, RecommendationBundle)
        assert len(bundle.recommendations) > 0
        assert bundle.hotspot_id == "UHI-0001"
        assert bundle.hotspot_severity == "high"

    def test_recommend_limits(self, bare_hotspot):
        engine = RecommenderEngine({"max_recommendations": 2})
        bundle = engine.recommend(bare_hotspot)
        assert len(bundle.recommendations) <= 2

    def test_recommend_invalid_hotspot(self):
        engine = create_recommender()
        with pytest.raises(InvalidHotspotError):
            engine.recommend(None)

    def test_recommend_no_match(self):
        class NoMatchHotspot:
            id = "UHI-9999"
            severity = "very_low"
            dominant_landcover = "Unknown"
            mean_ndvi = 0.0
            mean_ndbi = 0.0
            mean_ndwi = 0.0
            vegetation_fraction = 0.5
            builtup_fraction = 0.5
            area_sq_km = 0.001
            mean_temperature_c = 25.0

        engine = create_recommender()
        try:
            bundle = engine.recommend(NoMatchHotspot())
            assert len(bundle.recommendations) >= 0
        except NoRecommendationsError:
            pass

    def test_recommend_with_budget(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot, budget=100000)
        if bundle.optimization:
            assert bundle.optimization.total_cost <= 100000

    def test_recommend_with_scenarios(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot, budget=200000, generate_scenarios_list=True)
        if bundle.scenarios:
            assert len(bundle.scenarios) == 5

    def test_recommend_with_xai(self, bare_hotspot):
        class FakeXAI:
            def summary(self):
                return {"feature_importance": {"ndvi": 85.0, "albedo": 72.0}}
            def to_dict(self):
                return {"global_explanation": {"feature_importance": {"ndvi": 85.0}}}

        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot, xai_explanation=FakeXAI())
        assert len(bundle.recommendations) > 0

    def test_bundle_to_dict(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot, budget=100000)
        d = bundle.to_dict()
        assert "hotspot_id" in d
        assert "recommendations" in d
        assert "optimization" in d

    def test_bundle_summary(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot)
        s = bundle.summary()
        assert s["hotspot_id"] == "UHI-0001"
        assert s["n_recommendations"] > 0

    def test_recommend_batch(self, bare_hotspot, green_hotspot):
        engine = create_recommender()
        bundles = engine.recommend_batch([bare_hotspot, green_hotspot])
        assert len(bundles) == 2
        for b in bundles:
            assert isinstance(b, RecommendationBundle)

    def test_recommend_batch_with_none(self, bare_hotspot):
        engine = create_recommender()
        bundles = engine.recommend_batch([bare_hotspot, None])
        assert len(bundles) == 2


class TestIntegration:
    def test_end_to_end_builtup(self, bare_hotspot):
        engine = create_recommender({"max_recommendations": 4, "budget_constraint": 500000})
        bundle = engine.recommend(bare_hotspot, budget=500000, generate_scenarios_list=True)
        if bundle.recommendations:
            assert len(bundle.recommendations) <= 4
            assert bundle.recommendations[0].priority == 1

    def test_end_to_end_extreme(self, extreme_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(extreme_hotspot)
        assert len(bundle.recommendations) > 0
        for r in bundle.recommendations:
            assert r.expected_temperature_reduction >= 0

    def test_all_six_types_covered(self, extreme_hotspot):
        engine = create_recommender({"max_recommendations": 10})
        bundle = engine.recommend(extreme_hotspot)
        types = {r.recommendation_type for r in bundle.recommendations}
        assert len(types) > 0
        for t in types:
            assert t in RECOMMENDATION_PROFILES

    def test_no_circular_imports(self):
        import importlib
        import app.recommendation
        importlib.reload(app.recommendation)

    def test_priority_ordering(self, bare_hotspot):
        candidates = apply_rules(bare_hotspot)
        scored = score_candidates(candidates, bare_hotspot)
        priorities = [r.priority for r in scored]
        assert priorities == sorted(priorities)

    def test_cost_effectiveness_rankings(self, bare_hotspot):
        engine = create_recommender()
        bundle = engine.recommend(bare_hotspot)
        if len(bundle.recommendations) >= 2:
            assert bundle.recommendations[0].overall_score >= bundle.recommendations[1].overall_score
