from pydantic import BaseModel, Field
from typing import Any


class TrainRequest(BaseModel):
    X: list[list[float]] = Field(..., description="Training features")
    y: list[float] = Field(..., description="Target values")
    model_type: str = Field(default="random_forest", description="Model type identifier")
    feature_names: list[str] | None = None
    task: str = Field(default="regression", description="Prediction task: regression or classification")
    model_kwargs: dict[str, Any] | None = None


class TrainResponse(BaseModel):
    status: str = "success"
    model_type: str
    task: str
    metrics: dict[str, float] | None = None
    n_samples: int
    n_features: int
    message: str


class PredictRequest(BaseModel):
    X: list[list[float]] = Field(..., description="Features to predict on")
    feature_names: list[str] | None = None


class PredictResponse(BaseModel):
    status: str = "success"
    predictions: list[float]
    confidence: float | list[float] | None = None
    uncertainty: dict[str, float] | None = None
    feature_importance: dict[str, float] | None = None


class ForecastRequest(BaseModel):
    X: list[list[float]] = Field(..., description="Current feature data")
    feature_names: list[str] | None = None
    delta_years: int = Field(default=10, ge=1, le=100)


class ForecastResponse(BaseModel):
    status: str = "success"
    current_intensity: float | None = None
    future_lst: list[float] | None = None
    hotspot_probability: float | None = None
    future_severity: str | None = None
    hotspot_growth: float | None = None
    risk_map: list[float] | None = None


class CrossValidateRequest(BaseModel):
    X: list[list[float]]
    y: list[float]
    model_type: str = "random_forest"
    strategy: str = "kfold"
    n_folds: int = 5
    task: str = "regression"


class HyperparameterRequest(BaseModel):
    X: list[list[float]]
    y: list[float]
    model_type: str = "random_forest"
    method: str = "optuna"
    n_trials: int = 20
    task: str = "regression"
