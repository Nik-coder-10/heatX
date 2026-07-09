from .exceptions import (
    XAIError,
    ExplainabilityError,
    ModelNotSupportedError,
    MissingFeaturesError,
    ExplanationError,
    CounterfactualError,
    VisualizationError,
    ConfigurationError,
    UncertaintyError,
    ConfidenceError,
    ValidationError,
)
from .configuration import XAIConfig
from .registry import (
    EXPLANATION_REGISTRY,
    ExplanationMethodDef,
    register_method,
    get_method,
    list_methods,
    register_backend,
    get_backend,
    list_backends,
)
from .feature_importance import (
    FeatureImportanceResult,
    compute_shap_importance,
    compute_permutation_importance,
    compute_tree_importance,
    compute_correlation_importance,
    compute_importance,
)
from .local_explanation import LocalExplanation, explain_instance
from .global_explanation import GlobalExplanation, compute_global_explanation
from .counterfactual import CounterfactualExplanation, generate_counterfactual, batch_counterfactuals
from .confidence import ConfidenceMetrics, compute_overall_confidence
from .uncertainty import UncertaintyMetrics, compute_uncertainty
from .visualization import (
    render_shap_summary,
    render_shap_waterfall,
    render_feature_importance_bar,
    render_dependence_plot,
    render_interaction_heatmap,
    render_counterfactual_comparison,
    render_confidence_dashboard,
)
from .metadata import build_xai_metadata
from .validator import (
    validate_prediction_exists,
    validate_required_features,
    validate_feature_names_consistent,
    validate_model_compatibility,
    validate_missing_values,
    validate_geo_feature_cube,
    validate_hotspot,
)
from .explainer import Explainer
from .engine import XAIEngine, ExplanationResult, create_explanation

__all__ = [
    "XAIError", "ExplainabilityError", "ModelNotSupportedError",
    "MissingFeaturesError", "ExplanationError", "CounterfactualError",
    "VisualizationError", "ConfigurationError", "UncertaintyError",
    "ConfidenceError", "ValidationError",
    "XAIConfig",
    "EXPLANATION_REGISTRY", "ExplanationMethodDef",
    "register_method", "get_method", "list_methods",
    "register_backend", "get_backend", "list_backends",
    "FeatureImportanceResult",
    "compute_shap_importance", "compute_permutation_importance",
    "compute_tree_importance", "compute_correlation_importance",
    "compute_importance",
    "LocalExplanation", "explain_instance",
    "GlobalExplanation", "compute_global_explanation",
    "CounterfactualExplanation", "generate_counterfactual", "batch_counterfactuals",
    "ConfidenceMetrics", "compute_overall_confidence",
    "UncertaintyMetrics", "compute_uncertainty",
    "render_shap_summary", "render_shap_waterfall",
    "render_feature_importance_bar", "render_dependence_plot",
    "render_interaction_heatmap", "render_counterfactual_comparison",
    "render_confidence_dashboard",
    "build_xai_metadata",
    "validate_prediction_exists", "validate_required_features",
    "validate_feature_names_consistent", "validate_model_compatibility",
    "validate_missing_values", "validate_geo_feature_cube", "validate_hotspot",
    "Explainer",
    "XAIEngine", "ExplanationResult", "create_explanation",
]
