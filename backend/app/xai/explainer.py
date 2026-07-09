import logging
import time
from typing import Any

import numpy as np

from .configuration import XAIConfig
from .exceptions import ExplainabilityError, ModelNotSupportedError
from .feature_importance import (
    compute_importance,
    compute_shap_importance,
    compute_permutation_importance,
    compute_tree_importance,
    FeatureImportanceResult,
)
from .local_explanation import explain_instance, LocalExplanation
from .global_explanation import compute_global_explanation, GlobalExplanation
from .counterfactual import generate_counterfactual, batch_counterfactuals, CounterfactualExplanation
from .confidence import compute_overall_confidence, ConfidenceMetrics
from .uncertainty import compute_uncertainty as _compute_uncertainty_func, UncertaintyMetrics
from .metadata import build_xai_metadata
from .validator import (
    validate_prediction_exists,
    validate_model_compatibility,
    validate_missing_values,
    validate_feature_names_consistent,
)
from .visualization import (
    render_shap_summary,
    render_shap_waterfall,
    render_feature_importance_bar,
    render_dependence_plot,
    render_interaction_heatmap,
    render_counterfactual_comparison,
    render_confidence_dashboard,
)

logger = logging.getLogger("app.xai.explainer")


class Explainer:
    def __init__(self, config: XAIConfig | None = None):
        self.config = config or XAIConfig.defaults()
        self._cache = {}
        self._model = None

    def set_model(self, model) -> None:
        validate_model_compatibility(model)
        self._model = model

    def explain(
        self,
        X: np.ndarray,
        y: np.ndarray | None = None,
        feature_names: list[str] | None = None,
        method: str | None = None,
        instance_ids: list[str] | None = None,
        compute_local: bool = True,
        compute_global: bool = True,
        compute_counterfactual: bool = False,
        compute_confidence: bool = True,
        compute_uncertainty: bool = False,
        quality_flags: np.ndarray | None = None,
        output_dir: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        method = method or self.config.method
        model = self._model or kwargs.get("model")
        if model is None:
            raise ExplainabilityError("No model set. Call set_model() or pass 'model' kwarg.")

        validate_prediction_exists(model, X)
        validate_missing_values(X, max_nan_fraction=0.3)

        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        validate_feature_names_consistent(X, feature_names)

        result = {
            "method": method,
            "n_instances": X.shape[0],
            "n_features": X.shape[1],
            "feature_names": feature_names,
        }

        t_start = time.time()

        if compute_global:
            logger.info("Computing global explanation using %s...", method)
            result["global_explanation"] = compute_global_explanation(
                model=model,
                X=X,
                y=y,
                feature_names=feature_names,
                method=method,
                compute_correlations=True,
                compute_interactions=kwargs.get("compute_interactions", False),
                n_samples=self.config.n_samples,
                background_size=self.config.background_size,
                random_state=self.config.random_state,
            )

        if compute_local:
            logger.info("Computing local explanations for %d instances...", X.shape[0])
            local_results = []
            n = min(X.shape[0], self.config.batch_size)
            for i in range(n):
                iid = instance_ids[i] if instance_ids else str(i)
                try:
                    local = explain_instance(
                        model=model,
                        X_row=X[i:i+1],
                        feature_names=feature_names,
                        method=method,
                        instance_id=iid,
                        n_samples=self.config.n_samples,
                    )
                    local_results.append(local)
                except Exception as e:
                    logger.warning("Local explanation failed for instance %s: %s", iid, e)
            result["local_explanations"] = local_results

        if compute_counterfactual:
            logger.info("Computing counterfactual explanations...")
            cf_results = batch_counterfactuals(
                model=model,
                X=X[:min(X.shape[0], self.config.counterfactual_steps)],
                feature_names=feature_names,
                target_reduction=kwargs.get("target_reduction", 2.0),
                max_changes=self.config.counterfactual_max_changes,
                steps=self.config.counterfactual_steps,
            )
            result["counterfactuals"] = cf_results

        if compute_confidence:
            logger.info("Computing confidence metrics...")
            all_conf = []
            for i in range(min(X.shape[0], 10)):
                X_row = X[i:i+1]
                shap_vals = None
                if "local_explanations" in result and i < len(result["local_explanations"]):
                    shap_vals = result["local_explanations"][i].shap_values
                conf = compute_overall_confidence(
                    model=model,
                    X=X,
                    X_row=X_row,
                    shap_values=shap_vals,
                    quality_flags=quality_flags,
                )
                all_conf.append(conf)
            if all_conf:
                result["confidence"] = ConfidenceMetrics(
                    prediction_confidence=float(np.mean([c.prediction_confidence for c in all_conf])),
                    explanation_confidence=float(np.mean([c.explanation_confidence for c in all_conf])),
                    model_confidence=float(np.mean([c.model_confidence for c in all_conf])),
                    data_quality_confidence=float(np.mean([c.data_quality_confidence for c in all_conf])),
                    overall_confidence=float(np.mean([c.overall_confidence for c in all_conf])),
                )

        if compute_uncertainty:
            logger.info("Computing uncertainty metrics...")
            first_row = X[:1]
            result["uncertainty"] = _compute_uncertainty_func(
                model=model,
                X=X,
                X_row=first_row,
                feature_names=feature_names,
                quality_flags=quality_flags,
                alpha=self.config.uncertainty_alpha,
            )

        t_elapsed = (time.time() - t_start) * 1000
        result["metadata"] = build_xai_metadata(
            model_name=kwargs.get("model_name", "unknown"),
            algorithm=method,
            n_features=X.shape[1],
            n_instances=X.shape[0],
            execution_time_ms=t_elapsed,
        )

        if output_dir:
            result["visualizations"] = self._generate_visualizations(
                result, X, feature_names, output_dir
            )

        result["success"] = True
        return result

    def _generate_visualizations(
        self,
        result: dict,
        X: np.ndarray,
        feature_names: list[str],
        output_dir: str,
    ) -> dict[str, str]:
        import os
        os.makedirs(output_dir, exist_ok=True)
        viz_paths = {}

        fmt = self.config.visualization_format
        dpi = self.config.visualization_dpi

        global_exp = result.get("global_explanation")
        if global_exp:
            fi = global_exp.feature_importance
            path = os.path.join(output_dir, f"feature_importance.{fmt}")
            try:
                render_feature_importance_bar(
                    fi.feature_names, fi.importance_values, path,
                    title=f"Feature Importance ({fi.method})",
                    dpi=dpi, format=fmt,
                )
                viz_paths["feature_importance"] = path
            except Exception as e:
                logger.warning("Failed to render feature importance bar: %s", e)

        local_exps = result.get("local_explanations", [])
        if local_exps and len(local_exps) > 0:
            first = local_exps[0]
            if first.shap_values is not None:
                path = os.path.join(output_dir, f"shap_summary.{fmt}")
                try:
                    render_shap_summary(
                        np.array([e.shap_values for e in local_exps[:min(100, len(local_exps))]
                                  if e.shap_values is not None]),
                        X[:min(100, len(local_exps))],
                        feature_names, path,
                        max_features=self.config.max_features,
                        dpi=dpi, format=fmt,
                    )
                    viz_paths["shap_summary"] = path
                except Exception as e:
                    logger.warning("Failed to render SHAP summary: %s", e)

            for i, exp in enumerate(local_exps[:5]):
                if exp.shap_values is not None:
                    path = os.path.join(output_dir, f"waterfall_{i}.{fmt}")
                    try:
                        render_shap_waterfall(
                            exp.shap_values, exp.feature_values,
                            exp.feature_names,
                            exp.expected_value or 0,
                            exp.predicted_value or 0,
                            path, dpi=dpi, format=fmt,
                        )
                        viz_paths[f"waterfall_{i}"] = path
                    except Exception as e:
                        logger.warning("Failed to render waterfall %d: %s", i, e)

        cfs = result.get("counterfactuals", [])
        if cfs:
            for i, cf in enumerate(cfs[:5]):
                path = os.path.join(output_dir, f"counterfactual_{i}.{fmt}")
                try:
                    render_counterfactual_comparison(
                        cf.current_features,
                        cf.suggested_changes,
                        path, dpi=dpi, format=fmt,
                    )
                    viz_paths[f"counterfactual_{i}"] = path
                except Exception as e:
                    logger.warning("Failed to render counterfactual %d: %s", i, e)

        conf = result.get("confidence")
        if conf:
            path = os.path.join(output_dir, f"confidence_dashboard.{fmt}")
            try:
                render_confidence_dashboard(
                    conf.to_dict(), path, dpi=dpi, format=fmt,
                )
                viz_paths["confidence_dashboard"] = path
            except Exception as e:
                logger.warning("Failed to render confidence dashboard: %s", e)

        return viz_paths
