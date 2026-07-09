import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from app.xai import (
    XAIError, ExplainabilityError, ModelNotSupportedError,
    MissingFeaturesError, ExplanationError, CounterfactualError,
    VisualizationError, ConfigurationError, UncertaintyError,
    ConfidenceError, ValidationError,
    XAIConfig,
    EXPLANATION_REGISTRY, ExplanationMethodDef,
    register_method, get_method, list_methods,
    register_backend, get_backend, list_backends,
    FeatureImportanceResult,
    compute_shap_importance, compute_permutation_importance,
    compute_tree_importance, compute_correlation_importance,
    compute_importance,
    LocalExplanation, explain_instance,
    GlobalExplanation, compute_global_explanation,
    CounterfactualExplanation, generate_counterfactual,
    batch_counterfactuals,
    ConfidenceMetrics, compute_overall_confidence,
    UncertaintyMetrics, compute_uncertainty,
    render_shap_summary, render_shap_waterfall,
    render_feature_importance_bar, render_dependence_plot,
    render_interaction_heatmap, render_counterfactual_comparison,
    render_confidence_dashboard,
    build_xai_metadata,
    validate_prediction_exists, validate_required_features,
    validate_feature_names_consistent, validate_model_compatibility,
    validate_missing_values, validate_geo_feature_cube,
    validate_hotspot,
    Explainer,
    XAIEngine, ExplanationResult, create_explanation,
)


@pytest.fixture
def rng():
    return np.random.RandomState(42)


@pytest.fixture
def X(rng):
    n = 200
    X = np.zeros((n, 5))
    X[:, 0] = rng.uniform(20, 45, n)
    X[:, 1] = rng.uniform(-0.2, 0.8, n)
    X[:, 2] = rng.uniform(-0.3, 0.5, n)
    X[:, 3] = rng.uniform(-0.5, 0.3, n)
    X[:, 4] = rng.uniform(0, 1, n)
    return X.astype(np.float64)


@pytest.fixture
def y(X, rng):
    return (30.0
            + 0.5 * X[:, 0]
            - 5.0 * X[:, 1]
            + 3.0 * X[:, 2]
            - 2.0 * X[:, 3]
            + 1.0 * X[:, 4]
            + rng.normal(0, 0.5, X.shape[0]))


@pytest.fixture
def feature_names():
    return ["lst_celsius", "ndvi", "ndbi", "ndwi", "albedo"]


@pytest.fixture
def model(X, y):
    m = RandomForestRegressor(n_estimators=20, max_depth=5, random_state=42)
    m.fit(X, y)
    return m


@pytest.fixture
def simple_model(rng):
    m = LinearRegression()
    X_simple = rng.rand(100, 3)
    y_simple = X_simple[:, 0] * 2 + X_simple[:, 1] * (-1) + rng.randn(100) * 0.1
    m.fit(X_simple, y_simple)
    return m


@pytest.fixture
def cube():
    class FakeCube:
        feature_names = ["lst_celsius", "ndvi", "ndbi", "ndwi", "albedo"]
        features = {
            "lst_celsius": np.random.RandomState(42).uniform(20, 45, (50, 50)),
            "ndvi": np.random.RandomState(42).uniform(-0.2, 0.8, (50, 50)),
            "ndbi": np.random.RandomState(42).uniform(-0.3, 0.5, (50, 50)),
            "ndwi": np.random.RandomState(42).uniform(-0.5, 0.3, (50, 50)),
            "albedo": np.random.RandomState(42).uniform(0, 1, (50, 50)),
        }

        def to_flat_array(self):
            rows = [self.features[n].ravel() for n in self.feature_names]
            return np.column_stack(rows)
    return FakeCube()


@pytest.fixture
def hotspot():
    class FakeHotspot:
        id = "hs_001"
        severity = "high"
        confidence = 0.85
        mean_temperature_c = 42.3
        ndvi = 0.12
        ndbi = 0.45
        ndwi = -0.3
        albedo = 0.15
    return FakeHotspot()


class TestXAIExceptions:
    def test_xai_error(self):
        assert issubclass(XAIError, Exception)

    def test_explainability_error(self):
        e = ExplainabilityError("test error")
        assert str(e) == "test error"

    def test_model_not_supported(self):
        assert issubclass(ModelNotSupportedError, XAIError)

    def test_configuration_error(self):
        assert issubclass(ConfigurationError, XAIError)

    def test_validation_error(self):
        assert issubclass(ValidationError, XAIError)

    def test_counterfactual_error(self):
        assert issubclass(CounterfactualError, XAIError)

    def test_visualization_error(self):
        assert issubclass(VisualizationError, XAIError)

    def test_uncertainty_error(self):
        assert issubclass(UncertaintyError, XAIError)

    def test_confidence_error(self):
        error = ConfidenceError("test")
        assert str(error) == "test"


class TestXAIConfig:
    def test_defaults(self):
        c = XAIConfig.defaults()
        assert c.method == "shap"
        assert c.background_size == 50

    def test_from_dict(self):
        c = XAIConfig.from_dict({"method": "permutation", "n_samples": 200})
        assert c.method == "permutation"
        assert c.n_samples == 200

    def test_from_dict_invalid_key(self):
        with pytest.raises(ConfigurationError):
            XAIConfig.from_dict({"invalid_key": 42})

    def test_defaults_returns_new_instance(self):
        c1 = XAIConfig.defaults()
        c2 = XAIConfig.defaults()
        assert c1 is not c2


class TestRegistry:
    def test_methods_registered(self):
        assert "shap" in EXPLANATION_REGISTRY
        assert "permutation" in EXPLANATION_REGISTRY
        assert "tree_importance" in EXPLANATION_REGISTRY

    def test_get_method(self):
        m = get_method("shap")
        assert isinstance(m, ExplanationMethodDef)
        assert m.name == "shap"
        assert len(m.strengths) > 0

    def test_get_method_case_insensitive(self):
        m = get_method("SHAP")
        assert m.name == "shap"

    def test_get_method_not_found(self):
        with pytest.raises(ExplainabilityError):
            get_method("nonexistent_method")

    def test_list_methods(self):
        methods = list_methods()
        assert len(methods) >= 5

    def test_register_backend(self):
        register_backend("test_backend", {"fn": lambda: None})
        assert "test_backend" in list_backends()
        backend = get_backend("test_backend")
        assert "fn" in backend

    def test_get_backend_not_found(self):
        with pytest.raises(ExplainabilityError):
            get_backend("nonexistent")


class TestFeatureImportanceResult:
    def test_creation(self):
        fi = FeatureImportanceResult(
            feature_names=["a", "b", "c"],
            importance_values=np.array([80.0, 50.0, 20.0]),
            method="shap",
        )
        assert fi.ranking == [0, 1, 2]

    def test_top_features(self):
        fi = FeatureImportanceResult(
            feature_names=["a", "b", "c"],
            importance_values=np.array([20.0, 80.0, 50.0]),
            method="shap",
        )
        top = fi.top_features(2)
        assert len(top) == 2
        assert top[0][0] == "b"
        assert top[1][0] == "c"

    def test_to_dict(self):
        fi = FeatureImportanceResult(
            feature_names=["a", "b"],
            importance_values=np.array([100.0, 0.0]),
            method="test",
        )
        d = fi.to_dict()
        assert d["method"] == "test"
        assert len(d["feature_names"]) == 2


class TestComputeShapImportance:
    def test_shap_importance(self, model, X, feature_names):
        result = compute_shap_importance(model, X, feature_names, n_samples=50)
        assert isinstance(result, FeatureImportanceResult)
        assert len(result.feature_names) == 5
        assert result.importance_values.shape == (5,)
        assert 0 <= result.importance_values.min() <= result.importance_values.max() <= 100
        assert result.method == "shap"
        assert result.n_instances == 200

    def test_shap_values_sum_correctly(self, model, X, feature_names):
        result = compute_shap_importance(model, X[:5], feature_names, n_samples=30)
        assert np.all(np.isfinite(result.importance_values))
        assert result.importance_values.sum() > 0

    def test_shap_with_linear_model(self, simple_model):
        X_small = np.random.RandomState(42).rand(20, 3)
        result = compute_shap_importance(simple_model, X_small, ["a", "b", "c"], n_samples=20)
        assert result.method == "shap"


class TestComputePermutationImportance:
    def test_permutation_importance(self, model, X, y, feature_names):
        result = compute_permutation_importance(model, X, y, feature_names, n_repeats=3)
        assert isinstance(result, FeatureImportanceResult)
        assert result.method == "permutation"
        assert result.standard_deviation is not None
        assert result.standard_deviation.shape == (5,)

    def test_permutation_scoring(self, model, X, y, feature_names):
        result = compute_permutation_importance(model, X, y, feature_names, n_repeats=2, scoring="neg_mse")
        assert np.all(np.isfinite(result.importance_values))


class TestComputeTreeImportance:
    def test_tree_importance(self, model, feature_names):
        result = compute_tree_importance(model, feature_names)
        assert result.method.startswith("tree_")
        assert result.importance_values.shape == (5,)

    def test_tree_importance_not_supported(self):
        lr = LinearRegression()
        lr.fit([[1], [2], [3]], [1, 2, 3])
        with pytest.raises(ModelNotSupportedError):
            compute_tree_importance(lr, ["x"])


class TestComputeCorrelationImportance:
    def test_mutual_info(self, X, y, feature_names):
        result = compute_correlation_importance(X, y, feature_names, method="mutual_info")
        assert result.method == "correlation_mutual_info"
        assert result.importance_values.shape == (5,)

    def test_pearson(self, X, y, feature_names):
        result = compute_correlation_importance(X, y, feature_names, method="pearson")
        assert result.method == "correlation_pearson"


class TestComputeImportance:
    def test_shap_method(self, model, X, feature_names):
        result = compute_importance(model, X, feature_names=feature_names, method="shap", n_samples=50)
        assert result.method == "shap"

    def test_permutation_method(self, model, X, y, feature_names):
        result = compute_importance(model, X, y=y, feature_names=feature_names, method="permutation", n_repeats=2)
        assert result.method == "permutation"

    def test_tree_method(self, model, feature_names):
        result = compute_importance(model, X=None, feature_names=feature_names, method="tree_importance")
        assert result.method.startswith("tree_")

    def test_invalid_method(self, model, X, feature_names):
        with pytest.raises(ExplainabilityError):
            compute_importance(model, X, feature_names=feature_names, method="invalid")

    def test_auto_feature_names(self, model, X):
        result = compute_importance(model, X, method="tree_importance")
        assert result.feature_names == ["feature_0", "feature_1", "feature_2", "feature_3", "feature_4"]


class TestLocalExplanation:
    def test_explain_instance_shap(self, model, X, feature_names):
        exp = explain_instance(model, X[0], feature_names, method="shap", instance_id="test_0")
        assert isinstance(exp, LocalExplanation)
        assert exp.instance_id == "test_0"
        assert exp.shap_values is not None
        assert len(exp.shap_values) == 5
        assert exp.predicted_value is not None
        assert exp.expected_value is not None

    def test_explain_instance_permutation(self, model, X, feature_names):
        exp = explain_instance(model, X[0], feature_names, method="permutation", instance_id="test_0")
        assert isinstance(exp, LocalExplanation)
        assert exp.method == "permutation"

    def test_explain_instance_invalid(self, model, X, feature_names):
        with pytest.raises(ExplanationError):
            explain_instance(model, X[0], feature_names, method="invalid")

    def test_local_explanation_creates_top_features(self):
        exp = LocalExplanation(
            instance_id="test",
            feature_names=["a", "b", "c"],
            feature_values=np.array([1.0, 2.0, 3.0]),
            contribution_scores=np.array([0.5, -0.3, 0.1]),
        )
        assert exp.top_contributing_features is not None
        assert len(exp.top_contributing_features) == 3

    def test_local_explanation_to_dict(self):
        exp = LocalExplanation(
            instance_id="test",
            feature_names=["a", "b"],
            feature_values=np.array([1.0, 2.0]),
            contribution_scores=np.array([0.5, -0.3]),
        )
        d = exp.to_dict()
        assert d["instance_id"] == "test"
        assert "positive_factors" in d
        assert "negative_factors" in d

    def test_positive_and_negative_factors(self, model, X, feature_names):
        exp = explain_instance(model, X[0], feature_names)
        if exp.positive_factors:
            name, val = exp.positive_factors[0]
            assert val >= 0
        if exp.negative_factors:
            name, val = exp.negative_factors[0]
            assert val >= 0


class TestGlobalExplanation:
    def test_compute_global_explanation(self, model, X, y, feature_names):
        ge = compute_global_explanation(model, X, y, feature_names, method="shap", n_samples=50)
        assert isinstance(ge, GlobalExplanation)
        assert ge.feature_importance.method == "shap"
        assert ge.correlation_matrix is not None
        assert ge.correlation_matrix.shape == (5, 5)

    def test_global_top_features(self, model, X, y, feature_names):
        ge = compute_global_explanation(model, X, y, feature_names, method="shap", n_samples=50)
        top = ge.top_features(3)
        assert len(top) == 3

    def test_global_to_dict(self, model, X, y, feature_names):
        ge = compute_global_explanation(model, X, y, feature_names, method="shap", n_samples=50)
        d = ge.to_dict()
        assert "feature_importance" in d
        assert d["n_instances"] == 200


class TestCounterfactual:
    def test_generate_counterfactual(self, model, X, feature_names):
        cf = generate_counterfactual(model, X[0], feature_names, target_reduction=2.0, steps=5)
        assert isinstance(cf, CounterfactualExplanation)
        assert cf.instance_id == "0"
        assert cf.current_features is not None
        assert cf.expected_temperature_reduction >= 0

    def test_counterfactual_to_dict(self, model, X, feature_names):
        cf = generate_counterfactual(model, X[0], feature_names, target_reduction=2.0, steps=5)
        d = cf.to_dict()
        assert "instance_id" in d
        assert "expected_temperature_reduction" in d

    def test_batch_counterfactuals(self, model, X, feature_names):
        cfs = batch_counterfactuals(model, X[:5], feature_names, target_reduction=1.0, steps=5)
        assert len(cfs) == 5
        for cf in cfs:
            assert isinstance(cf, CounterfactualExplanation)

    def test_counterfactual_ndvi_increase(self, model, X, feature_names):
        row = X[0:1].copy()
        row[0, 0] = 40.0
        row[0, 1] = 0.1
        cf = generate_counterfactual(model, row, feature_names, target_reduction=2.0, steps=5)
        changes = cf.suggested_changes
        if "ndvi" in changes:
            suggested = changes["ndvi"]["suggested"]
            assert -1.0 <= suggested <= 1.0


class TestConfidence:
    def test_compute_overall_confidence(self, model, X, feature_names):
        conf = compute_overall_confidence(model, X, X[:1])
        assert isinstance(conf, ConfidenceMetrics)
        assert 0 <= conf.overall_confidence <= 1
        assert 0 <= conf.prediction_confidence <= 1
        assert 0 <= conf.explanation_confidence <= 1
        assert 0 <= conf.model_confidence <= 1
        assert 0 <= conf.data_quality_confidence <= 1

    def test_confidence_with_shap(self, model, X, feature_names):
        from app.xai.feature_importance import compute_shap_importance
        result = compute_shap_importance(model, X[:10], feature_names, n_samples=30)
        conf = compute_overall_confidence(model, X[:10], X[0:1])
        assert conf.overall_confidence > 0

    def test_confidence_to_dict(self, model, X, feature_names):
        conf = compute_overall_confidence(model, X, X[:1])
        d = conf.to_dict()
        assert "overall_confidence" in d
        assert all(0 <= v <= 1 for v in d.values() if isinstance(v, (int, float)))

    def test_confidence_with_quality_flags(self, model, X, feature_names):
        qf = np.ones(len(X), dtype=np.uint8)
        conf = compute_overall_confidence(model, X, X[:1], quality_flags=qf)
        assert conf.data_quality_confidence > 0.5


class TestUncertainty:
    def test_compute_uncertainty(self, model, X, feature_names):
        unc = compute_uncertainty(model, X, X[:1], feature_names)
        assert isinstance(unc, UncertaintyMetrics)
        assert 0 <= unc.overall_uncertainty <= 1
        assert unc.overall_uncertainty > 0

    def test_uncertainty_confidence_interval(self, model, X, feature_names):
        unc = compute_uncertainty(model, X, X[:1], feature_names, alpha=0.05)
        assert isinstance(unc.confidence_interval, tuple)
        assert len(unc.confidence_interval) == 2
        assert unc.confidence_interval[0] <= unc.confidence_interval[1]

    def test_uncertainty_to_dict(self, model, X, feature_names):
        unc = compute_uncertainty(model, X, X[:1], feature_names)
        d = unc.to_dict()
        assert "model_uncertainty" in d
        assert "confidence_interval" in d

    def test_uncertainty_with_quality_flags(self, model, X, feature_names):
        qf = np.ones((X.shape[0],), dtype=np.uint8)
        unc = compute_uncertainty(model, X, X[:1], feature_names, quality_flags=qf)
        assert 0 <= unc.measurement_uncertainty <= 1


class TestValidator:
    def test_validate_prediction_exists(self, model, X):
        assert validate_prediction_exists(model, X) is True

    def test_validate_prediction_fails(self):
        class BadModel:
            def predict(self, X):
                raise ValueError("fail")
        with pytest.raises(ValidationError):
            validate_prediction_exists(BadModel(), np.ones((1, 3)))

    def test_validate_required_features(self, feature_names):
        assert validate_required_features(np.ones((1, 5)), feature_names, ["lst_celsius", "ndvi"]) is True

    def test_validate_required_features_missing(self, feature_names):
        with pytest.raises(ValidationError):
            validate_required_features(np.ones((1, 5)), feature_names, ["missing_feature"])

    def test_validate_feature_names_consistent(self, feature_names):
        X = np.ones((10, 5))
        assert validate_feature_names_consistent(X, feature_names) is True

    def test_validate_feature_names_inconsistent(self, feature_names):
        X = np.ones((10, 3))
        with pytest.raises(ValidationError):
            validate_feature_names_consistent(X, feature_names)

    def test_validate_model_compatibility(self, model):
        assert validate_model_compatibility(model) is True

    def test_validate_model_no_predict(self):
        class BadModel:
            pass
        with pytest.raises(ValidationError):
            validate_model_compatibility(BadModel())

    def test_validate_missing_values(self, X):
        assert validate_missing_values(X) is True

    def test_validate_missing_values_excessive(self):
        X_bad = np.full((10, 5), np.nan)
        with pytest.raises(ValidationError):
            validate_missing_values(X_bad, max_nan_fraction=0.1)

    def test_validate_geo_feature_cube(self, cube):
        assert validate_geo_feature_cube(cube) is True

    def test_validate_geo_feature_cube_invalid(self):
        with pytest.raises(ValidationError):
            validate_geo_feature_cube(object())

    def test_validate_hotspot(self, hotspot):
        assert validate_hotspot(hotspot) is True

    def test_validate_hotspot_invalid(self):
        with pytest.raises(ValidationError):
            validate_hotspot(object())


class TestMetadata:
    def test_build_xai_metadata(self):
        meta = build_xai_metadata(
            model_name="RandomForest",
            feature_set=["lst_celsius", "ndvi"],
            algorithm="shap",
            n_features=5,
            n_instances=100,
        )
        assert meta["model"] == "RandomForest"
        assert meta["algorithm"] == "shap"
        assert meta["xai_version"] == "1.0.0"
        assert "timestamp" in meta
        assert "processing_history" in meta

    def test_metadata_with_execution_time(self):
        meta = build_xai_metadata(execution_time_ms=150.5)
        assert meta["execution_time_ms"] == 150.5

    def test_metadata_with_additional(self):
        meta = build_xai_metadata(additional={"custom_key": "custom_value"})
        assert meta["custom_key"] == "custom_value"


class TestVisualization:
    def test_render_feature_importance_bar(self, tmp_path):
        output = tmp_path / "fi_bar.png"
        render_feature_importance_bar(
            ["a", "b", "c"],
            np.array([100.0, 50.0, 20.0]),
            str(output),
        )
        assert output.exists()

    def test_render_feature_importance_pdf(self, tmp_path):
        output = tmp_path / "fi_bar.svg"
        render_feature_importance_bar(
            ["a", "b", "c"],
            np.array([80.0, 60.0, 40.0]),
            str(output), format="svg",
        )
        assert output.exists()

    def test_render_shap_summary(self, tmp_path):
        output = tmp_path / "shap_summary.png"
        shap_vals = np.random.RandomState(42).randn(50, 5)
        X_viz = np.random.RandomState(42).rand(50, 5)
        render_shap_summary(shap_vals, X_viz, ["a", "b", "c", "d", "e"], str(output))
        assert output.exists()

    def test_render_shap_waterfall(self, tmp_path):
        output = tmp_path / "waterfall.png"
        render_shap_waterfall(
            np.array([0.5, -0.3, 0.1]),
            np.array([30.0, 0.2, -0.1]),
            ["lst", "ndvi", "ndbi"],
            25.0, 35.0, str(output),
        )
        assert output.exists()

    def test_render_dependence_plot(self, tmp_path):
        output = tmp_path / "dep.png"
        shap_vals = np.random.RandomState(42).randn(100, 5)
        X_viz = np.random.RandomState(42).rand(100, 5)
        render_dependence_plot(shap_vals, X_viz, ["a", "b", "c", "d", "e"], 0, str(output))
        assert output.exists()

    def test_render_interaction_heatmap(self, tmp_path):
        output = tmp_path / "interaction.png"
        im = np.random.RandomState(42).rand(5, 5)
        render_interaction_heatmap(im, ["a", "b", "c", "d", "e"], str(output))
        assert output.exists()

    def test_render_counterfactual_comparison(self, tmp_path):
        output = tmp_path / "cf.png"
        current = {"ndvi": 0.2, "ndbi": 0.4}
        changes = {
            "ndvi": {"current": 0.2, "suggested": 0.5, "expected_temperature_reduction": 1.2},
            "ndbi": {"current": 0.4, "suggested": 0.25, "expected_temperature_reduction": 0.8},
        }
        render_counterfactual_comparison(current, changes, str(output))
        assert output.exists()

    def test_render_confidence_dashboard(self, tmp_path):
        output = tmp_path / "confidence.png"
        metrics = {"prediction": 0.85, "explanation": 0.72, "model": 0.9, "data_quality": 0.78, "overall": 0.81}
        render_confidence_dashboard(metrics, str(output))
        assert output.exists()


class TestXAIEngine:
    def test_engine_creation(self):
        engine = XAIEngine()
        assert engine.config.method == "shap"

    def test_engine_with_config(self):
        config = XAIConfig(method="permutation")
        engine = XAIEngine(config)
        assert engine.config.method == "permutation"

    def test_engine_set_model(self, model):
        engine = XAIEngine()
        engine.set_model(model)
        assert engine._model is not None

    def test_engine_explain_global_only(self, model, X, y, feature_names):
        engine = XAIEngine()
        engine.set_model(model)
        result = engine.explain(
            X=X[:30], y=y[:30], feature_names=feature_names,
            method="tree_importance",
            compute_local=False, compute_global=True,
            compute_confidence=False, compute_uncertainty=False,
        )
        assert isinstance(result, ExplanationResult)
        assert result.success
        assert result.global_explanation is not None
        assert result.local_explanations is None

    def test_engine_explain_full(self, model, X, y, feature_names):
        engine = XAIEngine()
        engine.set_model(model)
        result = engine.explain(
            X=X[:20], y=y[:20], feature_names=feature_names,
            method="shap",
            compute_local=True, compute_global=True,
            compute_confidence=True, compute_counterfactual=True,
            n_samples=30,
        )
        assert result.success
        assert result.global_explanation is not None
        if result.local_explanations:
            assert len(result.local_explanations) > 0

    def test_engine_explain_with_output_dir(self, model, X, y, feature_names, tmp_path):
        engine = XAIEngine()
        engine.set_model(model)
        result = engine.explain(
            X=X[:10], y=y[:10], feature_names=feature_names,
            method="tree_importance",
            output_dir=str(tmp_path),
        )
        assert result.success

    def test_engine_summary(self, model, X, y, feature_names):
        engine = XAIEngine()
        engine.set_model(model)
        result = engine.explain(
            X=X[:20], y=y[:20], feature_names=feature_names,
            method="shap", compute_confidence=True,
            n_samples=30,
        )
        s = result.summary()
        assert "success" in s
        assert "top_features" in s

    def test_engine_to_dict(self, model, X, y, feature_names):
        engine = XAIEngine()
        engine.set_model(model)
        result = engine.explain(
            X=X[:10], y=y[:10], feature_names=feature_names,
            method="tree_importance",
        )
        d = result.to_dict()
        assert "success" in d

    def test_engine_no_model_error(self, X, feature_names):
        engine = XAIEngine()
        with pytest.raises(ExplainabilityError):
            engine.explain(X=X[:5], feature_names=feature_names)

    def test_explain_hotspot(self, model, X, feature_names, hotspot):
        engine = XAIEngine()
        engine.set_model(model)
        local = engine.explain_hotspot(hotspot, model, X[:1], feature_names)
        assert isinstance(local, LocalExplanation)
        assert local.instance_id == "hs_001"

    def test_explain_feature_cube(self, model, cube):
        engine = XAIEngine()
        result = engine.explain_feature_cube(cube, model, method="tree_importance")
        assert result.success


class TestCreateExplanation:
    def test_create_explanation(self, model, X, y, feature_names):
        result = create_explanation(
            model, X[:20], y=y[:20],
            feature_names=feature_names, method="tree_importance",
        )
        assert isinstance(result, ExplanationResult)
        assert result.success
        assert result.global_explanation is not None


class TestExplainerDirect:
    def test_explainer_direct(self, model, X, y, feature_names):
        explainer = Explainer()
        explainer.set_model(model)
        result = explainer.explain(
            X=X[:15], y=y[:15], feature_names=feature_names,
            compute_global=True, compute_local=True,
            compute_confidence=True,
        )
        assert result["success"] is True
        assert "global_explanation" in result

    def test_explainer_local_explanations_count(self, model, X, y, feature_names):
        explainer = Explainer()
        explainer.set_model(model)
        result = explainer.explain(
            X=X[:5], y=y[:5], feature_names=feature_names,
            compute_local=True, compute_global=False,
            compute_confidence=False,
        )
        assert len(result.get("local_explanations", [])) == 5


class TestIntegration:
    def test_full_pipeline(self, model, X, y, feature_names):
        engine = XAIEngine(XAIConfig(method="shap", n_samples=50))
        engine.set_model(model)
        result = engine.explain(
            X=X[:15], y=y[:15],
            feature_names=feature_names,
            method="shap",
            compute_local=True,
            compute_global=True,
            compute_counterfactual=True,
            compute_confidence=True,
            compute_uncertainty=True,
        )
        assert result.success
        assert result.global_explanation is not None
        assert len(result.local_explanations) >= 1
        assert result.confidence is not None
        assert result.metadata is not None

    def test_different_methods_produce_different_results(self, model, X, y, feature_names):
        engine1 = XAIEngine()
        engine1.set_model(model)
        r1 = engine1.explain(X[:20], y=y[:20], feature_names=feature_names, method="tree_importance")

        engine2 = XAIEngine()
        engine2.set_model(model)
        r2 = engine2.explain(X[:20], y=y[:20], feature_names=feature_names, method="shap", n_samples=30)

        assert r1.success and r2.success
        fi1 = r1.global_explanation.feature_importance.importance_values
        fi2 = r2.global_explanation.feature_importance.importance_values
        assert not np.array_equal(fi1, fi2)

    def test_large_dataset(self):
        rng = np.random.RandomState(42)
        X_large = rng.rand(500, 8)
        y_large = X_large[:, 0] * 2 + X_large[:, 1] * (-1) + rng.randn(500) * 0.1
        names = [f"f{i}" for i in range(8)]
        big_model = RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42)
        big_model.fit(X_large, y_large)
        engine = XAIEngine(XAIConfig(method="tree_importance", batch_size=100))
        engine.set_model(big_model)
        result = engine.explain(X_large, y=y_large, feature_names=names, compute_local=True)
        assert result.success
        assert result.global_explanation is not None

    def test_consistency_rankings(self, model, X, y, feature_names):
        r1 = create_explanation(model, X[:50], y=y[:50], feature_names=feature_names, method="tree_importance")
        r2 = create_explanation(model, X[:50], y=y[:50], feature_names=feature_names, method="tree_importance")
        assert r1.global_explanation.feature_importance.ranking == r2.global_explanation.feature_importance.ranking

    def test_no_duplicated_explanation_logic(self):
        from app.xai import explainer, engine
        assert hasattr(explainer.Explainer, "explain")
        assert hasattr(engine.XAIEngine, "explain")
        assert engine.XAIEngine.explain is not explainer.Explainer.explain
