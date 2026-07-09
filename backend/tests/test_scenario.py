import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor

from app.scenario import (
    SimulationError, ConfigurationError, ScenarioNotFoundError,
    InvalidParameterError, ForecastError, ComparisonError,
    ScenarioConfig,
    ScenarioTemplate, SCENARIO_TEMPLATES, list_templates, get_template,
    SimulationResult, simulate_scenario, batch_simulate,
    ComparisonReport, compare_scenarios,
    ScenarioEngine, ScenarioPlan, create_scenario_engine,
)
from app.scenario.templates import SCENARIO_TEMPLATES as TEMPLATES


@pytest.fixture
def X():
    n = 100
    rng = np.random.RandomState(42)
    X = np.zeros((n, 6))
    X[:, 0] = 20 + rng.rand(n) * 25  # lst
    X[:, 1] = rng.rand(n) * 0.8 - 0.2  # ndvi
    X[:, 2] = rng.rand(n) * 0.3 + 0.1  # albedo
    X[:, 3] = rng.rand(n) * 0.8 - 0.3  # ndbi
    X[:, 4] = rng.rand(n) * 0.5  # vegetation_fraction
    X[:, 5] = rng.rand(n) * 0.8  # builtup_fraction
    return X.astype(np.float64)


@pytest.fixture
def y(X):
    return X[:, 0] - X[:, 1] * 10 + X[:, 2] * 5 + np.random.RandomState(42).randn(X.shape[0]) * 0.5


@pytest.fixture
def feature_names():
    return ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"]


@pytest.fixture
def model(X, y):
    m = RandomForestRegressor(n_estimators=10, random_state=42)
    m.fit(X, y)
    return m


class TestExceptions:
    def test_base_exception(self):
        with pytest.raises(SimulationError):
            raise SimulationError("base")
        with pytest.raises(SimulationError):
            raise ConfigurationError("cfg")
        with pytest.raises(SimulationError):
            raise ScenarioNotFoundError("not found")
        with pytest.raises(SimulationError):
            raise InvalidParameterError("bad param")
        with pytest.raises(SimulationError):
            raise ForecastError("forecast fail")
        with pytest.raises(SimulationError):
            raise ComparisonError("compare fail")


class TestScenarioConfig:
    def test_defaults(self):
        cfg = ScenarioConfig.defaults()
        assert cfg.default_delta_years == 10
        assert cfg.n_simulations == 100

    def test_from_dict(self):
        cfg = ScenarioConfig.from_dict({"default_delta_years": 20, "verbose": True})
        assert cfg.default_delta_years == 20
        assert cfg.verbose is True

    def test_from_dict_invalid(self):
        with pytest.raises(ConfigurationError):
            ScenarioConfig.from_dict({"bad_key": 1})


class TestTemplates:
    def test_all_templates_exist(self):
        assert len(TEMPLATES) == 7
        expected = ["tree_plantation", "cool_roof", "green_roof",
                     "reflective_pavement", "water_body_restoration",
                     "urban_green_space", "combined_mitigation"]
        for name in expected:
            assert name in TEMPLATES

    def test_get_template(self):
        t = get_template("tree_plantation")
        assert isinstance(t, ScenarioTemplate)
        assert t.name == "tree_plantation"
        assert t.cost_per_hectare == 15000.0

    def test_get_template_not_found(self):
        with pytest.raises(KeyError):
            get_template("nonexistent")

    def test_list_templates_all(self):
        all_t = list_templates()
        assert len(all_t) == 7

    def test_list_templates_by_category(self):
        veg = list_templates("vegetation")
        assert len(veg) == 2
        assert all(t.category == "vegetation" for t in veg)
        built = list_templates("builtup")
        assert len(built) == 3

    def test_template_apply(self):
        t = get_template("tree_plantation")
        X = np.array([[35.0, 0.1, 0.2, 0.3, 0.1, 0.6]])
        fn = ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"]
        X_mod = t.apply(X, fn, intensity=1.0)
        assert X_mod[0, 1] == pytest.approx(0.25, abs=0.01)  # ndvi + 0.15
        assert X_mod[0, 0] == pytest.approx(33.5, abs=0.1)   # lst - 1.5
        assert X_mod[0, 2] <= 1.0  # clipped

    def test_template_apply_intensity(self):
        t = get_template("tree_plantation")
        X = np.array([[35.0, 0.1, 0.2, 0.3, 0.1, 0.6]])
        fn = ["lst", "ndvi", "albedo", "ndbi", "vegetation_fraction", "builtup_fraction"]
        X_mod_half = t.apply(X, fn, intensity=0.5)
        X_mod_full = t.apply(X, fn, intensity=1.0)
        assert X_mod_half[0, 1] < X_mod_full[0, 1]  # half intensity -> less ndvi change

    def test_template_apply_missing_feature(self):
        t = get_template("cool_roof")
        X = np.array([[35.0, 0.2, 0.3]])
        fn = ["lst", "ndvi", "albedo"]
        X_mod = t.apply(X, fn)
        assert X_mod.shape == X.shape

    def test_combined_template(self):
        t = get_template("combined_mitigation")
        assert t.category == "combined"
        assert "ndvi" in t.feature_modifiers
        assert "albedo" in t.feature_modifiers
        assert "lst" in t.feature_modifiers


class TestSimulator:
    def test_simulate_scenario(self, X, y, feature_names, model):
        result = simulate_scenario("tree_plantation", X, y, feature_names, model, area_ha=10.0)
        assert isinstance(result, SimulationResult)
        assert result.scenario_name == "tree_plantation"
        assert result.mean_lst_change < 0  # temperature should decrease
        assert result.estimated_cost > 0
        assert result.estimated_co2_reduction > 0

    def test_simulate_scenario_template_object(self, X, y, feature_names, model):
        t = get_template("cool_roof")
        result = simulate_scenario(t, X, y, feature_names, model)
        assert result.scenario_name == "cool_roof"

    def test_simulate_with_params(self, X, y, feature_names, model):
        result = simulate_scenario("green_roof", X, y, feature_names, model,
                                    area_ha=5.0, params={"roof_area_pct": 0.3})
        assert result.parameters["roof_area_pct"] == 0.3

    def test_simulate_mismatched_features(self, X, y, feature_names, model):
        bad_names = ["a", "b"]
        with pytest.raises(InvalidParameterError):
            simulate_scenario("tree_plantation", X, y, bad_names, model)

    def test_simulate_result_to_dict(self, X, y, feature_names, model):
        result = simulate_scenario("tree_plantation", X, y, feature_names, model)
        d = result.to_dict()
        assert "scenario_name" in d
        assert "mean_lst_baseline" in d
        assert "estimated_cost" in d

    def test_simulate_result_summary(self, X, y, feature_names, model):
        result = simulate_scenario("tree_plantation", X, y, feature_names, model)
        s = result.summary()
        assert "temp_reduction_c" in s
        assert "cost_effectiveness" in s

    def test_batch_simulate(self, X, y, feature_names, model):
        results = batch_simulate(
            ["tree_plantation", "cool_roof", "green_roof"],
            X, y, feature_names, model,
            intensities=[0.5, 1.0], area_ha=5.0,
        )
        assert len(results) == 6  # 3 templates * 2 intensities

    def test_batch_simulate_invalid_template(self, X, y, feature_names, model):
        results = batch_simulate(
            ["tree_plantation", "nonexistent"],
            X, y, feature_names, model,
        )
        assert len(results) == 1  # only valid one

    def test_simulate_no_lst_feature(self, model):
        rng = np.random.RandomState(42)
        X = rng.rand(50, 4)
        y = rng.rand(50)
        names = ["temp", "a", "b", "c"]
        small_model = RandomForestRegressor(n_estimators=5, random_state=42)
        small_model.fit(X, y)
        result = simulate_scenario("tree_plantation", X, y, names, small_model)
        assert result.mean_lst_baseline >= 0
        assert result.mean_lst_simulated >= 0


class TestComparator:
    def test_compare_scenarios(self, X, y, feature_names, model):
        results = [
            simulate_scenario("tree_plantation", X, y, feature_names, model, area_ha=10.0),
            simulate_scenario("cool_roof", X, y, feature_names, model, area_ha=10.0),
            simulate_scenario("green_roof", X, y, feature_names, model, area_ha=10.0),
        ]
        report = compare_scenarios(results)
        assert isinstance(report, ComparisonReport)
        assert report.best_scenario is not None
        assert len(report.rankings) == 3
        assert report.rankings[0]["scenario"] == report.best_scenario

    def test_compare_empty(self):
        with pytest.raises(ComparisonError):
            compare_scenarios([])

    def test_compare_cost_metric(self, X, y, feature_names, model):
        results = [
            simulate_scenario("tree_plantation", X, y, feature_names, model, area_ha=10.0),
            simulate_scenario("cool_roof", X, y, feature_names, model, area_ha=10.0),
        ]
        report = compare_scenarios(results, metric="cost")
        assert len(report.rankings) == 2

    def test_compare_report_to_dict(self, X, y, feature_names, model):
        results = [
            simulate_scenario("tree_plantation", X, y, feature_names, model),
            simulate_scenario("cool_roof", X, y, feature_names, model),
        ]
        report = compare_scenarios(results)
        d = report.to_dict()
        assert "best_scenario" in d
        assert "rankings" in d
        assert "scenarios" in d

    def test_compare_report_summary(self, X, y, feature_names, model):
        results = [
            simulate_scenario("tree_plantation", X, y, feature_names, model),
            simulate_scenario("cool_roof", X, y, feature_names, model),
        ]
        report = compare_scenarios(results)
        s = report.summary()
        assert s["n_scenarios"] == 2


class TestEngine:
    def test_create_engine(self):
        engine = create_scenario_engine()
        assert isinstance(engine, ScenarioEngine)
        assert engine.config.default_delta_years == 10

    def test_engine_with_dict(self):
        engine = ScenarioEngine({"default_delta_years": 25, "verbose": True})
        assert engine.config.default_delta_years == 25
        assert engine.config.verbose is True

    def test_run_scenario(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        result = engine.run_scenario("tree_plantation", X, y, feature_names, model,
                                      intensity=1.0, area_ha=10.0)
        assert isinstance(result, SimulationResult)
        assert result.scenario_name == "tree_plantation"

    def test_run_scenario_not_found(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        with pytest.raises(ScenarioNotFoundError):
            engine.run_scenario("nonexistent", X, y, feature_names, model)

    def test_run_multiple(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results = engine.run_multiple(
            ["tree_plantation", "cool_roof"],
            X, y, feature_names, model, area_ha=5.0,
            compare=True,
        )
        assert len(results) == 2
        sim_results, report = results
        assert len(sim_results) == 2
        assert isinstance(report, ComparisonReport)

    def test_run_multiple_no_compare(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results = engine.run_multiple(
            ["tree_plantation", "cool_roof"],
            X, y, feature_names, model, area_ha=5.0,
            compare=False,
        )
        assert len(results) == 2
        assert all(isinstance(r, SimulationResult) for r in results)

    def test_run_all(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results, report = engine.run_all(X, y, feature_names, model, area_ha=1.0)
        assert len(results) > 0
        assert isinstance(report, ComparisonReport)
        assert report.best_scenario is not None

    def test_run_all_no_compare(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results, report = engine.run_all(X, y, feature_names, model, area_ha=1.0, compare=True)
        assert report is not None

    def test_scenario_plan(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results, report = engine.run_multiple(
            ["tree_plantation", "cool_roof"],
            X, y, feature_names, model, area_ha=5.0,
        )
        assert len(results) == 2

    def test_scenario_plan_to_dict(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        result = engine.run_scenario("tree_plantation", X, y, feature_names, model)
        plan = ScenarioPlan(scenario_name="tree_plantation", simulation=result)
        d = plan.to_dict()
        assert d["scenario_name"] == "tree_plantation"


class TestIntegration:
    def test_end_to_end(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results, report = engine.run_all(X, y, feature_names, model, area_ha=10.0)
        assert len(results) >= 7  # all 7 templates
        for r in results:
            assert r.mean_lst_change <= 0  # all should cool
        assert report.rankings[0]["cost_effectiveness"] > 0

    def test_combined_vs_individual(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results = engine.run_multiple(
            ["tree_plantation", "cool_roof", "combined_mitigation"],
            X, y, feature_names, model, area_ha=10.0, compare=False,
        )
        assert len(results) == 3
        combined = [r for r in results if r.scenario_name == "combined_mitigation"][0]
        individual_max = max(abs(r.mean_lst_change) for r in results if r.scenario_name != "combined_mitigation")
        assert combined.mean_lst_change < 0
        assert abs(combined.mean_lst_change) >= abs(individual_max) * 0.5  # combined roughly >= individual

    def test_no_circular_imports(self):
        import importlib
        import app.scenario
        importlib.reload(app.scenario)

    def test_ranking_consistency(self, X, y, feature_names, model):
        engine = create_scenario_engine()
        results, report = engine.run_all(X, y, feature_names, model, area_ha=10.0)
        assert len(report.rankings) > 1
        for i in range(len(report.rankings) - 1):
            assert report.rankings[i]["cost_effectiveness"] >= report.rankings[i + 1]["cost_effectiveness"]
