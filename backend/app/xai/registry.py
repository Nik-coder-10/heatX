from dataclasses import dataclass, field

from .exceptions import ExplainabilityError


EXPLANATION_REGISTRY: dict[str, "ExplanationMethodDef"] = {}
BACKEND_REGISTRY: dict[str, dict] = {}


@dataclass
class ExplanationMethodDef:
    name: str
    description: str
    scientific_rationale: str
    strengths: list[str]
    weaknesses: list[str]
    interpretation_guide: str
    computational_complexity: str
    supported_model_types: list[str] = field(default_factory=lambda: ["sklearn", "xgboost", "lightgbm", "any"])


def register_method(method: ExplanationMethodDef) -> None:
    EXPLANATION_REGISTRY[method.name.lower()] = method


def get_method(name: str) -> ExplanationMethodDef:
    key = name.lower()
    if key not in EXPLANATION_REGISTRY:
        raise ExplainabilityError(
            f"Explanation method '{name}' not found. Available: {list(EXPLANATION_REGISTRY)}"
        )
    return EXPLANATION_REGISTRY[key]


def list_methods() -> list[ExplanationMethodDef]:
    return list(EXPLANATION_REGISTRY.values())


register_method(ExplanationMethodDef(
    name="shap",
    description="SHapley Additive exPlanations using Shapley values from cooperative game theory",
    scientific_rationale="Shapley values distribute the prediction among features fairly by "
    "considering all possible feature subsets. SHAP provides additive feature "
    "attribution that satisfies local accuracy, missingness, and consistency.",
    strengths=[
        "Solid game-theoretic foundation",
        "Consistent and locally accurate",
        "Works with any model via model-agnostic KernelSHAP",
        "Fast for tree-based models via TreeSHAP",
        "Provides both global and local explanations",
    ],
    weaknesses=[
        "Computationally expensive for KernelSHAP",
        "Assumes feature independence in KernelSHAP",
        "Can be slow for high-dimensional data",
        "Dependence on background dataset for KernelSHAP",
    ],
    interpretation_guide="SHAP values are in the same units as the prediction. Positive values "
    "push the prediction higher; negative values push it lower. The sum of "
    "SHAP values equals the prediction minus the expected value.",
    computational_complexity="O(2^F) exact, O(n_samples * F) approximate for KernelSHAP; "
    "O(T * D * L) for TreeSHAP where T=trees, D=depth, L=leaves",
    supported_model_types=["sklearn", "xgboost", "lightgbm", "any"],
))

register_method(ExplanationMethodDef(
    name="permutation",
    description="Permutation feature importance measuring increase in prediction error after "
    "shuffling a feature",
    scientific_rationale="A feature is important if shuffling its values increases the model "
    "error, breaking the association between the feature and the target. "
    "This is a model-agnostic approach based on the principle of random "
    "permutation tests.",
    strengths=[
        "Model agnostic",
        "Intuitive interpretation",
        "Accounts for feature interactions",
        "Well-established statistical foundation",
        "Computationally efficient relative to SHAP",
    ],
    weaknesses=[
        "Can be unstable for correlated features",
        "Requires access to ground truth labels",
        "May overestimate importance of correlated features",
        "Randomness across runs can yield different results",
    ],
    interpretation_guide="Importance is measured as the increase in error when a feature is "
    "permuted. Higher values indicate more important features. Negative "
    "values suggest the feature may harm model performance.",
    computational_complexity="O(M * N * F) where M=model evaluations per permutation, "
    "N=number of permutations, F=number of features",
    supported_model_types=["sklearn", "xgboost", "lightgbm", "any"],
))

register_method(ExplanationMethodDef(
    name="tree_importance",
    description="Feature importance derived from tree-based model internal metrics "
    "(gain, split count, coverage)",
    scientific_rationale="Tree-based models naturally rank features by how often they are used "
    "for splitting (split count) and the improvement in purity/gain from "
    "each split. These provide fast, built-in importance estimates without "
    "additional computation.",
    strengths=[
        "Extremely fast (built into model training)",
        "No additional model evaluations needed",
        "Gain-based importance correlates well with SHAP",
        "Available for all tree ensemble models",
    ],
    weaknesses=[
        "Bias toward high-cardinality features",
        "Only available for tree-based models",
        "Can be misleading for correlated features",
        "No local explanation capability",
    ],
    interpretation_guide="Higher values indicate features used more frequently or with greater "
    "impact in decision splits. Gain-based importance (improvement in "
    "splitting criterion) is generally preferred over split count.",
    computational_complexity="O(1) after model training",
    supported_model_types=["sklearn", "xgboost", "lightgbm"],
))

register_method(ExplanationMethodDef(
    name="correlation",
    description="Feature-target correlation analysis including Pearson, Spearman, and "
    "mutual information",
    scientific_rationale="Correlation measures quantify the statistical relationship between "
    "features and the target variable. Mutual information captures "
    "non-linear dependencies that Pearson correlation may miss.",
    strengths=[
        "Fast to compute",
        "Captures linear and non-linear relationships",
        "No model required (data-only)",
        "Mutual information detects non-linear patterns",
    ],
    weaknesses=[
        "Pearson only captures linear relationships",
        "Does not account for feature interactions",
        "Mutual information requires discretization or estimation",
        "Not model-specific (feature-target relationship only)",
    ],
    interpretation_guide="Absolute values indicate strength of relationship. For Pearson, values "
    "near 1 or -1 indicate strong linear correlation. Mutual information is "
    "always non-negative; higher values indicate stronger dependency.",
    computational_complexity="O(N * F) for correlation, O(N * F * bins) for mutual information",
    supported_model_types=["any"],
))

register_method(ExplanationMethodDef(
    name="partial_dependence",
    description="Partial Dependence Plots showing the marginal effect of features on predictions",
    scientific_rationale="PDPs show how predictions change as a feature varies, averaging over "
    "the values of all other features. This provides the average marginal "
    "effect of a feature on the model output.",
    strengths=[
        "Clear visualization of feature effect direction",
        "Model agnostic",
        "Handles non-linear relationships",
        "Shows average behavior across all instances",
    ],
    weaknesses=[
        "Assumes feature independence",
        "Can mask heterogeneous effects",
        "Computationally expensive for many features",
        "May extrapolate to unrealistic feature combinations",
    ],
    interpretation_guide="The y-axis shows the average prediction as the feature varies. "
    "Steep slopes indicate strong feature influence. Flat lines indicate "
    "the feature has little average effect on predictions.",
    computational_complexity="O(M * N_grid * F) per feature",
    supported_model_types=["any"],
))

register_method(ExplanationMethodDef(
    name="ale",
    description="Accumulated Local Effects showing how features influence predictions "
    "while avoiding feature independence assumptions",
    scientific_rationale="ALE plots address PDP limitations by using conditional distributions "
    "rather than marginal. They accumulate local gradients across feature "
    "intervals, avoiding extrapolation to unrealistic feature combinations.",
    strengths=[
        "No feature independence assumption",
        "Computationally efficient",
        "More reliable than PDP for correlated features",
        "Unbiased effect estimation",
    ],
    weaknesses=[
        "Less intuitive than PDP",
        "Requires interval definition",
        "Can be unstable with small sample sizes",
        "Higher order interactions not captured",
    ],
    interpretation_guide="ALE values represent the feature effect relative to the average "
    "prediction. The y-axis shows the accumulated local effect centered "
    "around zero. Values above/below zero indicate positive/negative effect.",
    computational_complexity="O(M * N_intervals * F) per feature",
    supported_model_types=["any"],
))


def register_backend(name: str, implementation: dict) -> None:
    BACKEND_REGISTRY[name.lower()] = implementation


def get_backend(name: str) -> dict:
    key = name.lower()
    if key not in BACKEND_REGISTRY:
        raise ExplainabilityError(
            f"Backend '{name}' not found. Available: {list(BACKEND_REGISTRY)}"
        )
    return BACKEND_REGISTRY[key]


def list_backends() -> list[str]:
    return list(BACKEND_REGISTRY.keys())
