import logging
import time
from dataclasses import dataclass, field

import numpy as np

from .configuration import MLForecastConfig
from .exceptions import MLError, PredictionError, TrainingError
from .models import create_model, create_classifier, list_models
from .feature_pipeline import FeaturePipeline, build_pipeline_from_cube
from .training import train_model, TrainingResult
from .prediction import (
    predict,
    predict_hotspot_probability,
    predict_uhi_intensity,
    predict_severity,
    PredictionResult,
    batch_predict,
)
from .forecasting import (
    ForecastResult,
    forecast_current_intensity,
    forecast_future_lst,
    forecast_hotspot_probability,
    forecast_severity,
    forecast_hotspot_growth,
    generate_risk_map,
)
from .evaluation import evaluate_regression, evaluate_classification, EvaluationResult
from .metrics import MetricsResult, compute_regression_metrics
from .cross_validation import cross_validate, CVResult
from .validation import validate_model, ValidationReport
from .hyperparameter import optimize_hyperparameters, HyperparameterResult
from .ensemble import Ensemble, EnsembleResult, build_stacking_ensemble, build_blending_ensemble
from .drift_detection import generate_drift_report, DriftReport
from .model_registry import register_model, get_model, list_models as list_registered_models, get_latest_version, get_git_commit
from .serialization import serialize_model, deserialize_model
from .deployment import export_model, load_model, deploy_model
from .metadata import build_ml_metadata

logger = logging.getLogger("app.ml.engine")


class MLForecastEngine:
    def __init__(self, config: MLForecastConfig | dict | None = None):
        if config is None:
            self.config = MLForecastConfig.defaults()
        elif isinstance(config, dict):
            self.config = MLForecastConfig.from_dict(config)
        else:
            self.config = config
        self._model = None
        self._pipeline: FeaturePipeline | None = None
        self._feature_names: list[str] | None = None

    def set_model(self, model) -> None:
        self._model = model

    def get_model(self) -> object:
        return self._model

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
        model_type: str | None = None,
        **kwargs,
    ) -> TrainingResult:
        mt = model_type or self.config.model_type
        kwargs.pop("prediction_task", None)
        result = train_model(
            X_train=X, y_train=y,
            config=self.config,
            feature_names=feature_names,
            prediction_task=self.config.prediction_task,
            model_type=mt,
            **kwargs,
        )
        self._model = result.model
        self._feature_names = feature_names
        return result

    def train_from_cube(
        self,
        cube,
        y: np.ndarray,
        model_type: str | None = None,
        **kwargs,
    ) -> TrainingResult:
        self._pipeline, X, fn = build_pipeline_from_cube(cube, self.config)
        X_t = self._pipeline.fit_transform(X, y)
        self._feature_names = self._pipeline.get_selected_feature_names()
        return self.train(X_t, y, feature_names=self._feature_names, model_type=model_type, **kwargs)

    def predict(self, X: np.ndarray, **kwargs) -> PredictionResult:
        if self._model is None:
            raise PredictionError("No model trained. Call train() or set_model() first.")
        if self._pipeline is not None:
            X = self._pipeline.transform(X)
        return predict(self._model, X, feature_names=self._feature_names, model_type=self.config.model_type, task=self.config.prediction_task, **kwargs)

    def predict_from_cube(self, cube, **kwargs) -> PredictionResult:
        if self._pipeline is None:
            _, X, _, _ = build_pipeline_from_cube(cube, self.config)
            X = self._pipeline.transform(X)
        else:
            X = cube.to_flat_array()
            X = self._pipeline.transform(X)
        return self.predict(X, **kwargs)

    def forecast(self, X: np.ndarray, **kwargs) -> ForecastResult:
        if self._model is None:
            raise PredictionError("No model trained. Call train() or set_model() first.")

        intensity = forecast_current_intensity(self._model, X, self._pipeline, self._feature_names)
        risk = generate_risk_map(self._model, X, self._pipeline)

        return ForecastResult(
            current_intensity=intensity,
            risk_map=risk,
        )

    def forecast_future(self, X: np.ndarray, delta_years: int = 10, **kwargs) -> ForecastResult:
        if self._model is None:
            raise PredictionError("No model trained. Call train() or set_model() first.")

        intensity = forecast_current_intensity(self._model, X, self._pipeline, self._feature_names)
        future_lst = forecast_future_lst(self._model, X, delta_years, pipeline=self._pipeline, feature_names=self._feature_names)
        hotspot_probs = forecast_hotspot_probability(self._model, X, self._pipeline)
        severities = forecast_severity(self._model, X, self._pipeline)
        risk = generate_risk_map(self._model, X, self._pipeline)

        return ForecastResult(
            current_intensity=intensity,
            future_lst=future_lst,
            hotspot_probability=hotspot_probs[0] if hotspot_probs else None,
            future_severity=severities[0] if severities else None,
            risk_map=risk,
        )

    def cross_validate(self, X: np.ndarray, y: np.ndarray, **kwargs) -> CVResult:
        return cross_validate(
            X, y,
            model_type=self.config.model_type,
            strategy=self.config.cv_strategy,
            n_folds=self.config.cv_folds,
            task=self.config.prediction_task,
        )

    def optimize_hyperparameters(self, X: np.ndarray, y: np.ndarray, **kwargs) -> HyperparameterResult:
        return optimize_hyperparameters(
            X, y,
            model_type=self.config.model_type,
            method=self.config.hyperparameter_method,
            n_trials=self.config.n_trials,
            cv_folds=self.config.cv_folds,
            task=self.config.prediction_task,
        )

    def validate(self, X_train, y_train, X_test, y_test, **kwargs) -> ValidationReport:
        return validate_model(
            X_train, y_train, X_test, y_test,
            model_type=self.config.model_type,
            cv_strategy=self.config.cv_strategy,
            cv_folds=self.config.cv_folds,
            task=self.config.prediction_task,
        )

    def detect_drift(self, X_ref, X_cur, pred_ref, pred_cur, y_true_ref, y_pred_ref, y_true_cur, y_pred_cur, **kwargs) -> DriftReport:
        return generate_drift_report(
            X_ref, X_cur, pred_ref, pred_cur,
            y_true_ref, y_pred_ref, y_true_cur, y_pred_cur,
            feature_names=self._feature_names,
            alert_threshold=self.config.drift_alert_threshold,
        )

    def register(self, model_id: str, metrics: dict, **kwargs):
        return register_model(
            model_id=model_id,
            model_type=self.config.model_type,
            model_version="1.0.0",
            hyperparameters=self.config.__dict__.copy(),
            metrics=metrics,
            git_commit=get_git_commit(),
            feature_set=self._feature_names or [],
            task=self.config.prediction_task,
            **kwargs,
        )

    def save(self, path: str, format: str = "joblib") -> str:
        return serialize_model(self._model, path, format)

    def load(self, path: str, format: str = "joblib") -> object:
        self._model = deserialize_model(path, format)
        return self._model

    def build_ensemble(self, models: list[object], method: str = "weighted") -> Ensemble:
        ens = Ensemble(method=method)
        for m in models:
            ens.add_model(m)
        return ens

    def batch_predict(self, X: np.ndarray, batch_size: int = 1000) -> np.ndarray:
        return batch_predict(self._model, X, batch_size, self._pipeline)

    def summary(self) -> dict:
        return {
            "model_type": self.config.model_type,
            "model_loaded": self._model is not None,
            "pipeline_fitted": self._pipeline is not None if self._pipeline else False,
            "n_features": len(self._feature_names) if self._feature_names else 0,
            "config": self.config.__dict__.copy(),
        }


def create_forecast_engine(config: MLForecastConfig | None = None) -> MLForecastEngine:
    return MLForecastEngine(config)
