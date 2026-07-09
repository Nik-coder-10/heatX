import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .configuration import XAIConfig
from .exceptions import ExplainabilityError, MissingFeaturesError
from .explainer import Explainer
from .feature_importance import FeatureImportanceResult
from .local_explanation import LocalExplanation, explain_instance
from .global_explanation import GlobalExplanation
from .counterfactual import CounterfactualExplanation
from .confidence import ConfidenceMetrics
from .uncertainty import UncertaintyMetrics
from .metadata import build_xai_metadata
from .registry import register_backend, get_backend, EXPLANATION_REGISTRY

logger = logging.getLogger("app.xai.engine")


@dataclass
class ExplanationResult:
    global_explanation: GlobalExplanation | None = None
    local_explanations: list[LocalExplanation] | None = None
    counterfactuals: list[CounterfactualExplanation] | None = None
    confidence: ConfidenceMetrics | None = None
    uncertainty: UncertaintyMetrics | None = None
    metadata: dict | None = None
    visualizations: dict[str, str] | None = None
    success: bool = False

    def to_dict(self) -> dict:
        d = {"success": self.success}
        if self.global_explanation:
            d["global_explanation"] = self.global_explanation.to_dict()
        if self.local_explanations:
            d["local_explanations"] = [e.to_dict() for e in self.local_explanations]
        if self.counterfactuals:
            d["counterfactuals"] = [c.to_dict() for c in self.counterfactuals]
        if self.confidence:
            d["confidence"] = self.confidence.to_dict()
        if self.uncertainty:
            d["uncertainty"] = self.uncertainty.to_dict()
        if self.metadata:
            d["metadata"] = self.metadata
        if self.visualizations:
            d["visualizations"] = self.visualizations
        return d

    def summary(self) -> dict:
        s = {"success": self.success}
        if self.global_explanation:
            top5 = self.global_explanation.top_features(5)
            s["top_features"] = top5
        if self.confidence:
            s["confidence"] = self.confidence.to_dict()
        if self.uncertainty:
            s["uncertainty"] = self.uncertainty.to_dict()
        if self.metadata:
            s["metadata"] = {
                "model": self.metadata.get("model"),
                "algorithm": self.metadata.get("algorithm"),
                "n_features": self.metadata.get("n_features"),
                "n_instances": self.metadata.get("n_instances"),
            }
        if self.counterfactuals:
            s["n_counterfactuals"] = len(self.counterfactuals)
        return s


class XAIEngine:
    def __init__(self, config: XAIConfig | None = None):
        self.config = config or XAIConfig.defaults()
        self.explainer = Explainer(self.config)
        self._model = None

    def set_model(self, model) -> None:
        self._model = model
        self.explainer.set_model(model)

    def explain(
        self,
        X: np.ndarray,
        y: np.ndarray | None = None,
        feature_names: list[str] | None = None,
        instance_ids: list[str] | None = None,
        method: str = "shap",
        compute_local: bool = True,
        compute_global: bool = True,
        compute_counterfactual: bool = False,
        compute_confidence: bool = True,
        compute_uncertainty: bool = False,
        quality_flags: np.ndarray | None = None,
        output_dir: str | None = None,
        model_name: str = "unknown",
        **kwargs,
    ) -> ExplanationResult:
        explicit_model = kwargs.pop("model", None) if "model" in kwargs else None
        if self._model is None and explicit_model is None:
            raise ExplainabilityError("No model set. Call set_model() or pass model in kwargs.")

        model = explicit_model or self._model

        t0 = time.time()
        raw = self.explainer.explain(
            X=X, y=y, feature_names=feature_names,
            method=method, instance_ids=instance_ids,
            compute_local=compute_local,
            compute_global=compute_global,
            compute_counterfactual=compute_counterfactual,
            compute_confidence=compute_confidence,
            compute_uncertainty=compute_uncertainty,
            quality_flags=quality_flags,
            output_dir=output_dir,
            model=model, model_name=model_name,
            **kwargs,
        )
        elapsed = (time.time() - t0) * 1000

        result = ExplanationResult(
            global_explanation=raw.get("global_explanation"),
            local_explanations=raw.get("local_explanations"),
            counterfactuals=raw.get("counterfactuals"),
            confidence=raw.get("confidence"),
            uncertainty=raw.get("uncertainty"),
            visualizations=raw.get("visualizations"),
            success=raw.get("success", False),
        )

        metadata = raw.get("metadata", {})
        metadata["execution_time_ms"] = round(elapsed, 2)
        result.metadata = metadata

        return result

    def explain_hotspot(
        self,
        hotspot,
        model,
        X: np.ndarray,
        feature_names: list[str],
        target_reduction: float = 2.0,
    ) -> LocalExplanation:
        hs_id = hotspot.id if hasattr(hotspot, "id") else "hotspot_0"
        X_row = X[:1] if X.shape[0] >= 1 else X
        local = explain_instance(
            model=model,
            X_row=X_row,
            feature_names=feature_names,
            method=self.config.method,
            instance_id=hs_id,
            n_samples=self.config.n_samples,
        )
        return local

    def explain_feature_cube(
        self,
        cube,
        model,
        method: str = "shap",
        compute_counterfactual: bool = False,
    ) -> ExplanationResult:
        from .validator import validate_geo_feature_cube
        validate_geo_feature_cube(cube)

        X = cube.to_flat_array()
        feature_names = cube.feature_names

        result = self.explain(
            X=X,
            feature_names=feature_names,
            model=model,
            method=method,
            compute_counterfactual=compute_counterfactual,
            model_name="GeoFeatureCube_Model",
        )
        return result


def create_explanation(
    model,
    X: np.ndarray,
    y: np.ndarray | None = None,
    feature_names: list[str] | None = None,
    method: str = "shap",
    config: XAIConfig | None = None,
) -> ExplanationResult:
    engine = XAIEngine(config)
    engine.set_model(model)
    return engine.explain(X=X, y=y, feature_names=feature_names, method=method)
