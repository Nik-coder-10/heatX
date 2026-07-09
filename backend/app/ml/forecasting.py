import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .exceptions import PredictionError
from .prediction import predict, PredictionResult
from .feature_pipeline import FeaturePipeline

logger = logging.getLogger("app.ml.forecasting")


@dataclass
class ForecastResult:
    current_intensity: PredictionResult | None = None
    future_lst: PredictionResult | None = None
    hotspot_probability: PredictionResult | None = None
    future_severity: PredictionResult | None = None
    hotspot_growth: PredictionResult | None = None
    risk_map: PredictionResult | None = None
    metadata: dict | None = None

    def summary(self) -> dict:
        s = {}
        if self.current_intensity:
            s["current_intensity"] = self.current_intensity.to_dict()
        if self.future_lst:
            s["future_lst"] = self.future_lst.to_dict()
        if self.hotspot_probability:
            s["hotspot_probability"] = self.hotspot_probability.to_dict()
        if self.future_severity:
            s["future_severity"] = self.future_severity.to_dict()
        if self.hotspot_growth:
            s["hotspot_growth"] = self.hotspot_growth.to_dict()
        if self.risk_map:
            s["risk_map"] = self.risk_map.to_dict()
        return s

    def to_dict(self) -> dict:
        return self.summary()


def forecast_current_intensity(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    feature_names: list[str] | None = None,
) -> PredictionResult:
    return predict(model, X, pipeline, task="regression", feature_names=feature_names)


def forecast_future_lst(
    model,
    X_current: np.ndarray,
    delta_years: int = 10,
    trend_rate: float = 0.05,
    pipeline: FeaturePipeline | None = None,
    feature_names: list[str] | None = None,
) -> PredictionResult:
    X_future = X_current.copy()
    for i, name in enumerate(feature_names or []):
        if "lst" in name.lower():
            X_future[:, i] += trend_rate * delta_years
        if "temperature" in name.lower():
            X_future[:, i] += trend_rate * delta_years

    pred = predict(model, X_future, pipeline, task="regression", feature_names=feature_names)
    pred.metadata = {
        "delta_years": delta_years,
        "trend_rate": trend_rate,
        "forecast_type": "future_lst",
    }
    return pred


def forecast_hotspot_probability(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    threshold: float = 0.5,
    future_years: list[int] | None = None,
) -> list[PredictionResult]:
    from .prediction import predict_hotspot_probability
    future_years = future_years or [1, 5, 10, 20]

    results = []
    for years in future_years:
        X_future = X.copy()
        X_future[:, 0] += years * 0.5
        prob = predict_hotspot_probability(model, X_future, pipeline, threshold)
        prob.metadata = {"horizon_years": years, "forecast_type": "hotspot_probability"}
        results.append(prob)

    return results


def forecast_severity(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    future_years: list[int] | None = None,
    severity_levels: list[str] | None = None,
) -> list[PredictionResult]:
    from .prediction import predict_severity
    future_years = future_years or [1, 5, 10, 20]
    results = []
    for years in future_years:
        X_future = X.copy()
        X_future[:, 0] += years * 0.5
        sev = predict_severity(model, X_future, pipeline, severity_levels)
        sev.metadata = {"horizon_years": years, "forecast_type": "severity"}
        results.append(sev)
    return results


def forecast_hotspot_growth(
    model,
    X_current: np.ndarray,
    X_future_scenario: np.ndarray,
    pipeline: FeaturePipeline | None = None,
) -> PredictionResult:
    current_pred = predict(model, X_current, pipeline)
    future_pred = predict(model, X_future_scenario, pipeline)

    growth = future_pred.values - current_pred.values
    growth_rate = growth / (np.abs(current_pred.values) + 1e-10)

    result = PredictionResult(
        values=growth,
        confidence=min(current_pred.confidence, future_pred.confidence),
        uncertainty=max(current_pred.uncertainty, future_pred.uncertainty),
        model_type="growth_model",
        task="regression",
        metadata={
            "current_mean": float(np.mean(current_pred.values)),
            "future_mean": float(np.mean(future_pred.values)),
            "growth_rate_mean": float(np.mean(growth_rate)),
            "forecast_type": "hotspot_growth",
        },
    )
    return result


def generate_risk_map(
    model,
    X: np.ndarray,
    pipeline: FeaturePipeline | None = None,
    thresholds: list[float] | None = None,
    shape: tuple[int, int] | None = None,
) -> PredictionResult:
    thresholds = thresholds or [0.25, 0.50, 0.75]
    intensity = predict(model, X, pipeline)

    values = intensity.values
    risk = np.zeros_like(values)
    for i, t in enumerate(sorted(thresholds)):
        risk[values > np.percentile(values, t * 100)] = i + 1

    risk_result = PredictionResult(
        values=risk,
        confidence=intensity.confidence,
        uncertainty=intensity.uncertainty,
        model_type="risk_map",
        task="classification",
        metadata={
            "thresholds": thresholds,
            "risk_levels": len(thresholds) + 1,
            "forecast_type": "risk_map",
        },
    )
    return risk_result
