import numpy as np
import pytest
from sklearn.ensemble import RandomForestRegressor

from app.ml import (
    MLError, TrainingError, PredictionError, ModelNotSupportedError,
    ConfigurationError, ValidationError, DriftDetectedError,
    SerializationError, ModelNotFoundError, FeaturePipelineError,
    EnsembleError,
    MLForecastConfig,
    register_model, get_model_class, list_models, get_model_metadata,
    create_model, create_classifier,
    FeaturePipeline, build_pipeline_from_cube,
    MetricsResult, compute_regression_metrics, compute_classification_metrics,
    EvaluationResult, evaluate_regression, evaluate_classification,
    TrainingResult, train_model,
    HyperparameterResult, optimize_hyperparameters,
    CVResult, cross_validate,
    ValidationReport, validate_model,
    Ensemble, EnsembleResult,
    PredictionResult, predict, predict_hotspot_probability,
    predict_uhi_intensity, predict_severity, batch_predict,
    ForecastResult,
    forecast_current_intensity, forecast_future_lst,
    forecast_hotspot_probability, forecast_severity,
    forecast_hotspot_growth, generate_risk_map,
    DriftReport, generate_drift_report,
    ModelRecord,
    serialize_model, deserialize_model,
    DeploymentPackage, export_model, load_model, deploy_model,
    build_ml_metadata,
    MLForecastEngine, create_forecast_engine,
)


@pytest.fixture
def rng():
    return np.random.RandomState(42)


@pytest.fixture
def X(rng):
    n = 200
    X = rng.rand(n, 5)
    X[:, 0] = 20 + X[:, 0] * 25
    X[:, 1] = X[:, 1] * 1.0 - 0.2
    X[:, 2] = X[:, 2] * 0.8 - 0.3
    X[:, 3] = X[:, 3] * 0.8 - 0.5
    X[:, 4] = X[:, 4]
    return X.astype(np.float64)


@pytest.fixture
def y(X, rng):
    return (30.0 + 0.5 * X[:, 0] - 5.0 * X[:, 1] + 3.0 * X[:, 2]
            - 2.0 * X[:, 3] + 1.0 * X[:, 4] + rng.normal(0, 1.0, X.shape[0]))


@pytest.fixture
def feature_names():
    return ["lst_celsius", "ndvi", "ndbi", "ndwi", "albedo"]


@pytest.fixture
def X_class(rng):
    X = rng.rand(200, 4)
    y = (X[:, 0] * 5 + X[:, 1] * 3 + X[:, 2] * (-2) + rng.randn(200) * 0.5) > 3.0
    return X.astype(np.float64), y.astype(np.int32)


@pytest.fixture
def cube():
    class FakeCube:
        feature_names = ["lst_celsius", "ndvi", "ndbi", "ndwi", "albedo"]
        features = {
            "lst_celsius": np.random.RandomState(42).uniform(20, 45, (25, 25)),
            "ndvi": np.random.RandomState(42).uniform(-0.2, 0.8, (25, 25)),
            "ndbi": np.random.RandomState(42).uniform(-0.3, 0.5, (25, 25)),
            "ndwi": np.random.RandomState(42).uniform(-0.5, 0.3, (25, 25)),
            "albedo": np.random.RandomState(42).uniform(0, 1, (25, 25)),
        }
        def to_flat_array(self):
            rows = [self.features[n].ravel() for n in self.feature_names]
            return np.column_stack(rows)
    return FakeCube()


class TestMLExceptions:
    def test_base_error(self):
        assert issubclass(MLError, Exception)

    def test_training_error(self):
        assert issubclass(TrainingError, MLError)

    def test_prediction_error(self):
        assert issubclass(PredictionError, MLError)

    def test_model_not_supported(self):
        assert issubclass(ModelNotSupportedError, MLError)

    def test_serialization_error(self):
        e = SerializationError("test")
        assert str(e) == "test"


class TestMLConfig:
    def test_defaults(self):
        c = MLForecastConfig.defaults()
        assert c.model_type == "random_forest"

    def test_from_dict(self):
        c = MLForecastConfig.from_dict({"model_type": "xgboost", "n_estimators": 200})
        assert c.model_type == "xgboost"

    def test_invalid_key(self):
        with pytest.raises(ConfigurationError):
            MLForecastConfig.from_dict({"bad_key": 1})


class TestModels:
    def test_list_models(self):
        models = list_models()
        assert "random_forest" in models
        assert "xgboost" in models
        assert "lightgbm" in models

    def test_create_rf(self):
        model = create_model("random_forest", n_estimators=10)
        assert model is not None
        assert hasattr(model, "fit")

    def test_create_linear(self):
        model = create_model("linear_regression")
        assert model is not None

    def test_create_invalid(self):
        with pytest.raises(ModelNotSupportedError):
            create_model("nonexistent_model")

    def test_get_metadata(self):
        meta = get_model_metadata("xgboost")
        assert meta.name == "xgboost"
        assert len(meta.advantages) > 0
        assert len(meta.disadvantages) > 0

    def test_model_metadata_has_required_fields(self):
        for model_name in list_models():
            meta = get_model_metadata(model_name)
            assert meta.name
            assert meta.training_complexity
            assert meta.inference_complexity
            assert meta.urban_heat_applicability

    def test_create_classifier(self):
        clf = create_classifier("random_forest", n_estimators=10)
        assert clf is not None

    def test_register_model_temp(self):
        from app.ml.models import register_model as reg, ModelDef
        reg("test_model", None, ModelDef(name="test", description="", advantages=[], disadvantages=[], typical_use_case="", training_complexity="", inference_complexity="", urban_heat_applicability=""))
        assert "test_model" in list_models()


class TestFeaturePipeline:
    def test_fit_transform_standard(self, X):
        pipe = FeaturePipeline(normalization="standard")
        Xt = pipe.fit_transform(X)
        assert Xt.shape == X.shape
        assert abs(Xt.mean()) < 0.5

    def test_fit_transform_minmax(self, X):
        pipe = FeaturePipeline(normalization="minmax")
        Xt = pipe.fit_transform(X)
        assert Xt.min() >= 0.0
        assert Xt.max() <= 1.0

    def test_missing_values_mean(self, X):
        X_missing = X.copy()
        X_missing[0, 0] = np.nan
        pipe = FeaturePipeline(normalization="none", missing_strategy="mean")
        Xt = pipe.fit_transform(X_missing)
        assert np.all(np.isfinite(Xt))

    def test_no_normalization(self, X):
        pipe = FeaturePipeline(normalization="none")
        Xt = pipe.fit_transform(X)
        assert np.allclose(X, Xt)

    def test_transform_without_fit(self, X):
        pipe = FeaturePipeline()
        with pytest.raises(FeaturePipelineError):
            pipe.transform(X)

    def test_feature_selection_variance(self, X):
        X_c = X.copy()
        X_c[:, 0] = 1.0
        pipe = FeaturePipeline(normalization="none", feature_selection="variance")
        Xt = pipe.fit_transform(X_c)
        assert Xt.shape[1] >= 4

    def test_empty_data(self):
        pipe = FeaturePipeline()
        with pytest.raises(FeaturePipelineError):
            pipe.fit(np.array([]).reshape(0, 5))

    def test_to_config(self):
        pipe = FeaturePipeline(normalization="minmax", missing_strategy="zero")
        cfg = pipe.to_config()
        assert cfg["normalization"] == "minmax"


class TestMetrics:
    def test_regression_metrics(self, y):
        y_pred = y + np.random.RandomState(42).randn(len(y)) * 0.5
        m = compute_regression_metrics(y, y_pred)
        assert m.mae > 0
        assert m.rmse > 0
        assert isinstance(m.r2, float)

    def test_classification_metrics(self, X_class):
        X, y = X_class
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        clf.fit(X, y)
        pred = clf.predict(X)
        prob = clf.predict_proba(X)[:, 1]
        m = compute_classification_metrics(y, pred, prob)
        assert m.accuracy > 0
        assert m.f1 > 0

    def test_metrics_to_dict(self, y):
        y_pred = y + np.random.RandomState(42).randn(len(y)) * 0.5
        m = compute_regression_metrics(y, y_pred)
        d = m.to_dict()
        assert "mae" in d
        assert "rmse" in d


class TestTraining:
    def test_train_model(self, X, y, feature_names):
        result = train_model(X, y, X, y, feature_names=feature_names, model_type="random_forest", n_estimators=10)
        assert isinstance(result, TrainingResult)
        assert result.model is not None
        assert result.evaluation is not None
        assert result.evaluation.test_metrics is not None
        assert result.training_time_s > 0

    def test_train_model_no_test(self, X, y):
        result = train_model(X, y, model_type="random_forest", n_estimators=10)
        assert result.model is not None
        assert result.evaluation is None

    def test_train_model_with_pipeline(self, X, y):
        pipe = FeaturePipeline(normalization="standard")
        pipe.fit(X, y)
        result = train_model(X, y, X, y, pipeline=pipe, model_type="random_forest", n_estimators=10)
        assert result.model is not None

    def test_train_classification(self, X_class):
        X, y = X_class
        result = train_model(X, y, X, y, model_type="random_forest", prediction_task="classification", n_estimators=10)
        assert result.model is not None


class TestCrossValidation:
    def test_kfold_cv(self, X, y):
        cv = cross_validate(X, y, "random_forest", n_folds=3, n_estimators=10)
        assert isinstance(cv, CVResult)
        assert cv.mean_score > -1
        assert cv.n_folds > 0

    def test_stratified_cv(self, X_class):
        X, y = X_class
        cv = cross_validate(X, y, "random_forest", strategy="stratified", n_folds=3,
                           task="classification", n_estimators=10)
        assert cv.mean_score > 0

    def test_timeseries_cv(self, X, y):
        cv = cross_validate(X, y, "random_forest", strategy="timeseries", n_folds=3, n_estimators=10)
        assert cv.mean_score > -1

    def test_invalid_strategy(self, X, y):
        with pytest.raises(ValidationError):
            cross_validate(X, y, "random_forest", strategy="invalid")


class TestPrediction:
    def test_predict(self, X, y, feature_names):
        result = train_model(X[:150], y[:150], X[150:], y[150:], feature_names=feature_names, model_type="random_forest", n_estimators=10)
        pred = predict(result.model, X[150:], feature_names=feature_names)
        assert isinstance(pred, PredictionResult)
        assert len(pred.values) == 50
        assert pred.confidence > 0
        assert pred.uncertainty >= 0

    def test_predict_hotspot_probability(self, X_class):
        X, y = X_class
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        clf.fit(X, y)
        pred = predict_hotspot_probability(clf, X[:10])
        assert pred.values.ndim == 1

    def test_predict_uhi_intensity(self, X, y, feature_names):
        result = train_model(X[:150], y[:150], X[150:], y[150:], feature_names=feature_names, model_type="random_forest", n_estimators=10)
        pred = predict_uhi_intensity(result.model, X[150:], feature_names=feature_names)
        assert pred.metadata["prediction_type"] == "uhi_intensity"

    def test_predict_severity(self, X, y):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        pred = predict_severity(result.model, X[150:])
        assert pred.values is not None

    def test_batch_predict(self, X, y):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        preds = batch_predict(result.model, X, batch_size=20)
        assert len(preds) == 200


class TestForecasting:
    def test_current_intensity(self, X, y, feature_names):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        fc = forecast_current_intensity(result.model, X[:5], feature_names=feature_names)
        assert fc.values is not None

    def test_future_lst(self, X, y, feature_names):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        fc = forecast_future_lst(result.model, X[:5], delta_years=10, feature_names=feature_names)
        assert fc.metadata["forecast_type"] == "future_lst"
        assert fc.metadata["delta_years"] == 10

    def test_hotspot_probability_forecast(self, X_class):
        X, y = X_class
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        clf.fit(X, y)
        results = forecast_hotspot_probability(clf, X[:5])
        assert len(results) == 4
        for r in results:
            assert r.metadata["forecast_type"] == "hotspot_probability"

    def test_severity_forecast(self, X, y):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        results = forecast_severity(result.model, X[:5])
        assert len(results) > 0

    def test_hotspot_growth(self, X, y):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        growth = forecast_hotspot_growth(result.model, X[:5], X[:5] * 1.1)
        assert growth.metadata["forecast_type"] == "hotspot_growth"

    def test_risk_map(self, X, y):
        result = train_model(X[:150], y[:150], X[150:], y[150:], model_type="random_forest", n_estimators=10)
        risk = generate_risk_map(result.model, X)
        assert risk.metadata["forecast_type"] == "risk_map"


class TestEnsemble:
    def test_weighted_ensemble(self, X, y):
        m1 = create_model("random_forest", n_estimators=10)
        m2 = create_model("random_forest", n_estimators=10)
        m1.fit(X[:150], y[:150])
        m2.fit(X[:150], y[:150])
        ens = Ensemble(method="weighted")
        ens.add_model(m1, 0.6).add_model(m2, 0.4)
        ens.fit(X[:150], y[:150])
        pred = ens.predict(X[150:])
        assert len(pred) == 50

    def test_ensemble_not_fitted(self, X):
        ens = Ensemble()
        with pytest.raises(EnsembleError):
            ens.predict(X[:5])

    def test_ensemble_voting(self, X, y):
        m1 = create_model("random_forest", n_estimators=10)
        m2 = create_model("random_forest", n_estimators=10)
        m1.fit(X, y)
        m2.fit(X, y)
        ens = Ensemble(method="voting")
        ens.add_model(m1).add_model(m2)
        ens.fit(X, y)
        pred = ens.predict(X[:5])
        assert len(pred) == 5


class TestDriftDetection:
    def test_drift_report(self, X, y):
        X_new = X + np.random.RandomState(42).randn(*X.shape) * 0.05
        pred = np.random.RandomState(42).randn(len(y))
        drift = generate_drift_report(X, X_new, pred, pred, y, pred, y, pred)
        assert isinstance(drift, DriftReport)
        assert drift.overall_drift >= 0
        assert drift.overall_drift <= 1

    def test_drift_alert(self, X, y):
        X_new = X * 2.0
        drift = generate_drift_report(X, X_new, y, y, y, y, y, y, alert_threshold=0.01)
        assert bool(drift.alert_triggered) is True


class TestModelRegistry:
    def test_register_and_get(self):
        from app.ml.model_registry import register_model as reg, get_model, list_models as lm
        record = reg("test_model_v1", "random_forest", "1.0.0",
                     hyperparameters={"n_estimators": 100}, metrics={"r2": 0.85})
        assert record.model_id == "test_model_v1"
        got = get_model("test_model_v1")
        assert got.model_type == "random_forest"

    def test_get_nonexistent(self):
        from app.ml.model_registry import get_model
        with pytest.raises(ModelNotFoundError):
            get_model("nonexistent")

    def test_registry_to_dict(self):
        from app.ml.model_registry import register_model as reg
        record = reg("test_dict", "xgboost", "2.0.0", hyperparameters={}, metrics={})
        d = record.to_dict()
        assert d["model_id"] == "test_dict"


class TestSerialization:
    def test_joblib_roundtrip(self, X, y, tmp_path):
        result = train_model(X[:150], y[:150], model_type="random_forest", n_estimators=10)
        path = str(tmp_path / "model.joblib")
        serialize_model(result.model, path, "joblib")
        loaded = deserialize_model(path, "joblib")
        pred1 = result.model.predict(X[:3])
        pred2 = loaded.predict(X[:3])
        assert np.allclose(pred1, pred2)


class TestEngine:
    def test_engine_creation(self):
        engine = MLForecastEngine()
        assert engine.config.model_type == "random_forest"

    def test_engine_with_dict_config(self):
        engine = MLForecastEngine({"model_type": "xgboost"})
        assert engine.config.model_type == "xgboost"

    def test_train_and_predict(self, X, y, feature_names):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        result = engine.train(X[:150], y[:150], feature_names=feature_names)
        assert result.model is not None
        pred = engine.predict(X[150:])
        assert len(pred.values) == 50

    def test_forecast(self, X, y, feature_names):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        engine.train(X, y, feature_names=feature_names)
        fc = engine.forecast(X[:5])
        assert isinstance(fc, ForecastResult)
        assert fc.current_intensity is not None

    def test_forecast_future(self, X, y, feature_names):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        engine.train(X, y, feature_names=feature_names)
        fc = engine.forecast_future(X[:5], delta_years=10)
        assert isinstance(fc, ForecastResult)
        assert fc.future_lst is not None

    def test_cross_validate(self, X, y):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        cv = engine.cross_validate(X[:150], y[:150], n_folds=3)
        assert cv.mean_score > -1

    def test_predict_without_model(self, X):
        engine = MLForecastEngine()
        with pytest.raises(PredictionError):
            engine.predict(X[:5])

    def test_set_model(self, X, y):
        model = create_model("random_forest", n_estimators=10)
        model.fit(X, y)
        engine = MLForecastEngine()
        engine.set_model(model)
        pred = engine.predict(X[:5])
        assert len(pred.values) == 5

    def test_save_load(self, X, y, tmp_path):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        engine.train(X, y)
        path = str(tmp_path / "engine_model.joblib")
        engine.save(path)
        engine2 = MLForecastEngine()
        loaded = engine2.load(path)
        assert loaded is not None

    def test_summary(self, X, y):
        engine = MLForecastEngine()
        s = engine.summary()
        assert "model_type" in s
        assert s["model_loaded"] is False
        engine.train(X, y)
        s = engine.summary()
        assert s["model_loaded"] is True

    def test_batch_predict(self, X, y):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        engine.train(X, y)
        preds = engine.batch_predict(X, batch_size=50)
        assert len(preds) == 200

    def test_train_from_cube(self, cube):
        rng = np.random.RandomState(42)
        y = rng.rand(625)
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        result = engine.train_from_cube(cube, y)
        assert result.model is not None

    def test_validate(self, X, y):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        vr = engine.validate(X[:150], y[:150], X[150:], y[150:])
        assert isinstance(vr, ValidationReport)
        assert vr.cv_result is not None


class TestIntegration:
    def test_full_pipeline_regression(self, X, y, feature_names):
        engine = MLForecastEngine(MLForecastConfig(
            model_type="random_forest", n_estimators=20, cv_folds=3,
        ))
        result = engine.train(X[:150], y[:150], feature_names=feature_names)
        assert result.model is not None

        cv = engine.cross_validate(X, y)
        assert cv.mean_score > -1

        pred = engine.predict(X[150:])
        assert len(pred.values) == 50

        fc = engine.forecast(X[:5])
        assert fc.current_intensity is not None

        hp = engine.optimize_hyperparameters(X[:100], y[:100], n_trials=3, method="random", cv_folds=2)
        assert hp.best_score > -1

    def test_different_model_types(self, X, y):
        for model_type in ["random_forest", "linear_regression", "elasticnet"]:
            try:
                engine = MLForecastEngine(MLForecastConfig(model_type=model_type))
                engine.train(X[:100], y[:100])
                pred = engine.predict(X[100:105])
                assert len(pred.values) == 5
            except Exception as e:
                pytest.fail(f"Model {model_type} failed: {e}")

    def test_hyperparameter_grid(self, X, y):
        hp = optimize_hyperparameters(X[:100], y[:100], "random_forest", method="grid",
                                       cv_folds=2, param_grid={"n_estimators": [10, 20], "max_depth": [5, 10]})
        assert hp.best_score > -1
        assert hp.search_method == "grid"

    def test_ensemble_different_models(self, X, y):
        m1 = create_model("random_forest", n_estimators=10)
        m2 = create_model("linear_regression")
        m1.fit(X, y)
        m2.fit(X, y)
        ens = Ensemble(method="average")
        ens.add_model(m1).add_model(m2)
        ens.fit(X, y)
        pred = ens.predict(X[:5])
        assert len(pred) == 5

    def test_data_quality(self, X, y):
        X_bad = X.copy()
        X_bad[0, 0] = np.nan
        pipe = FeaturePipeline(missing_strategy="mean")
        X_clean = pipe.fit_transform(X_bad)
        assert np.all(np.isfinite(X_clean))

    def test_drift_and_registry(self, X, y):
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=10))
        engine.train(X, y)
        X_new = X + np.random.RandomState(42).randn(*X.shape) * 0.1
        pred_ref = engine.predict(X).values
        pred_cur = engine.predict(X_new).values
        drift = engine.detect_drift(X, X_new, pred_ref, pred_cur, y, pred_ref, y, pred_cur)
        assert isinstance(drift, DriftReport)
        record = engine.register("integration_test", metrics={"r2": 0.85})
        assert record.model_id == "integration_test"

    def test_no_circular_imports(self):
        import app.ml.engine
        import app.ml.training
        import app.ml.prediction
        import app.ml.forecasting
        import app.ml.models
        import app.ml.ensemble
        assert True


class TestDeployment:
    def test_export_joblib(self, X, y, tmp_path):
        model = create_model("random_forest", n_estimators=10)
        model.fit(X, y)
        pkg = export_model(model, "test_model", "random_forest",
                          output_dir=str(tmp_path), format="joblib",
                          hyperparameters={"n": 10}, metrics={"r2": 0.9},
                          feature_set=["a", "b", "c"])
        assert isinstance(pkg, DeploymentPackage)
        assert pkg.format == "joblib"

    def test_deploy_multi_format(self, X, y, tmp_path):
        model = create_model("random_forest", n_estimators=10)
        model.fit(X, y)
        pkgs = deploy_model(model, "test_multi", "random_forest",
                           output_dir=str(tmp_path), formats=["joblib", "pickle"])
        assert len(pkgs) == 2
        for pkg in pkgs:
            assert pkg.model_path is not None


class TestMetadata:
    def test_build_ml_metadata(self):
        meta = build_ml_metadata(
            model_type="random_forest",
            task="regression",
            n_features=5,
            n_samples=100,
            hyperparameters={"n_estimators": 100},
            metrics={"r2": 0.85},
        )
        assert meta["model_type"] == "random_forest"
        assert meta["ml_version"] == "1.0.0"
        assert "timestamp" in meta
        assert "processing_history" in meta

    def test_cross_provider_compatibility(self):
        meta = build_ml_metadata(
            model_type="xgboost",
            framework="xgboost",
        )
        assert meta["framework"] == "xgboost"


class TestLargeDataset:
    def test_large_dataset(self):
        rng = np.random.RandomState(42)
        n = 2000
        X = rng.rand(n, 10)
        y = X[:, 0] * 2 + X[:, 1] * (-1) + rng.randn(n) * 0.5
        engine = MLForecastEngine(MLForecastConfig(model_type="random_forest", n_estimators=20))
        engine.train(X[:1500], y[:1500])
        pred = engine.batch_predict(X, batch_size=500)
        assert len(pred) == n
