import logging
from dataclasses import dataclass, field

from .exceptions import ModelNotSupportedError

logger = logging.getLogger("app.ml.models")

MODEL_REGISTRY: dict[str, type] = {}
MODEL_METADATA: dict[str, dict] = {}


@dataclass
class ModelDef:
    name: str
    description: str
    advantages: list[str]
    disadvantages: list[str]
    typical_use_case: str
    training_complexity: str
    inference_complexity: str
    urban_heat_applicability: str
    supported_tasks: list[str] = field(default_factory=lambda: ["regression", "classification"])
    requires_gpu: bool = False
    supports_warm_start: bool = False
    supports_incremental: bool = False


def register_model(name: str, model_class: type, metadata: ModelDef) -> None:
    MODEL_REGISTRY[name.lower()] = model_class
    MODEL_METADATA[name.lower()] = metadata


def get_model_class(name: str) -> type:
    key = name.lower()
    if key not in MODEL_REGISTRY:
        raise ModelNotSupportedError(
            f"Model '{name}' not found. Available: {list(MODEL_REGISTRY)}"
        )
    return MODEL_REGISTRY[key]


def list_models() -> list[str]:
    return list(MODEL_REGISTRY.keys())


def get_model_metadata(name: str) -> dict:
    key = name.lower()
    if key not in MODEL_METADATA:
        raise ModelNotSupportedError(f"No metadata for model '{name}'")
    return MODEL_METADATA[key]


def create_model(model_type: str, **kwargs) -> object:
    cls = get_model_class(model_type)
    return cls(**kwargs)


register_model("random_forest", None, ModelDef(
    name="random_forest",
    description="Random Forest ensemble of decision trees with bootstrap aggregation",
    advantages=[
        "Handles non-linear relationships well",
        "Built-in feature importance",
        "Robust to outliers and overfitting",
        "No scaling required",
        "Handles mixed data types",
    ],
    disadvantages=[
        "Less interpretable than single trees",
        "Can overfit on noisy datasets",
        "Slower inference than gradient boosting",
        "Large model size",
    ],
    typical_use_case="Baseline UHI intensity prediction, feature importance analysis",
    training_complexity="O(n_estimators * n_samples * log(n_samples))",
    inference_complexity="O(n_estimators * depth)",
    urban_heat_applicability="Reliable baseline for LST and hotspot prediction with feature importance",
    supports_warm_start=True,
))

register_model("extra_trees", None, ModelDef(
    name="extra_trees",
    description="Extremely Randomized Trees with random split thresholds",
    advantages=[
        "More randomized than RF, reduces variance further",
        "Faster training than Random Forest",
        "Good for high-dimensional data",
        "Built-in feature importance",
    ],
    disadvantages=[
        "Slightly higher bias than Random Forest",
        "Still large model size",
        "May underfit on small datasets",
    ],
    typical_use_case="Fast training baseline for large-scale UHI datasets",
    training_complexity="O(n_estimators * n_samples * log(n_samples))",
    inference_complexity="O(n_estimators * depth)",
    urban_heat_applicability="Fast alternative to RF for large urban extents",
))

register_model("gradient_boosting", None, ModelDef(
    name="gradient_boosting",
    description="Gradient Boosted Decision Trees with sequential additive training",
    advantages=[
        "Often best-in-class accuracy for tabular data",
        "Handles heterogeneous features",
        "Built-in feature importance",
        "Handles missing values (histogram-based)",
    ],
    disadvantages=[
        "More hyperparameters to tune",
        "Can overfit without regularization",
        "Sequential training is slow",
        "Sensitive to noisy data",
    ],
    typical_use_case="High-accuracy UHI intensity and hotspot prediction",
    training_complexity="O(n_estimators * n_samples * depth)",
    inference_complexity="O(n_estimators * depth)",
    urban_heat_applicability="High-accuracy model for LST forecasting and hotspot probability",
    supports_warm_start=True,
))

register_model("xgboost", None, ModelDef(
    name="xgboost",
    description="XGBoost: Optimized Gradient Boosting with L1/L2 regularization",
    advantages=[
        "State-of-the-art accuracy for tabular data",
        "Built-in L1/L2 regularization",
        "Handles missing values natively",
        "GPU-accelerated training",
        "Optimized tree pruning",
    ],
    disadvantages=[
        "Many hyperparameters requiring tuning",
        "Memory-intensive for very large datasets",
        "Less interpretable than linear models",
    ],
    typical_use_case="Production UHI intensity prediction and hotspot classification",
    training_complexity="O(n_estimators * n_samples * depth)",
    inference_complexity="O(n_estimators * depth)",
    urban_heat_applicability="Primary production model for all UHI prediction tasks",
    supports_warm_start=True,
))

register_model("lightgbm", None, ModelDef(
    name="lightgbm",
    description="LightGBM: Gradient boosting with leaf-wise tree growth and GOSS/EFB",
    advantages=[
        "Fastest training among gradient boosting methods",
        "Leaf-wise growth is more efficient",
        "Low memory usage",
        "Native categorical feature support",
        "GPU-accelerated",
    ],
    disadvantages=[
        "Can overfit on small datasets",
        "Leaf-wise growth may need depth constraints",
        "Sensitive to hyperparameter tuning",
    ],
    typical_use_case="Large-scale UHI forecasting with many features",
    training_complexity="O(n_estimators * n_samples * leaves)",
    inference_complexity="O(n_estimators * leaves)",
    urban_heat_applicability="Fast training and inference for large urban areas",
    supports_incremental=True,
))

register_model("catboost", None, ModelDef(
    name="catboost",
    description="CatBoost: Gradient boosting with ordered boosting and symmetric trees",
    advantages=[
        "Excellent categorical feature handling",
        "Ordered boosting reduces overfitting",
        "Symmetric trees for fast inference",
        "Built-in cross-validation",
        "GPU-accelerated",
    ],
    disadvantages=[
        "Slower training than LightGBM",
        "Larger model size",
        "Less common in research benchmarks",
    ],
    typical_use_case="UHI prediction with categorical urban features",
    training_complexity="O(n_estimators * n_samples * depth)",
    inference_complexity="O(n_estimators * depth)",
    urban_heat_applicability="Best for datasets with categorical land cover types",
))

register_model("linear_regression", None, ModelDef(
    name="linear_regression",
    description="Ordinary Least Squares Linear Regression",
    advantages=[
        "Highly interpretable",
        "Fast training and inference",
        "Well-understood statistical properties",
        "Closed-form solution available",
    ],
    disadvantages=[
        "Assumes linear relationships",
        "Sensitive to outliers",
        "Requires feature scaling",
        "No feature interactions",
    ],
    typical_use_case="Baseline model, interpretable UHI driver analysis",
    training_complexity="O(n_features^2 * n)",
    inference_complexity="O(n_features)",
    urban_heat_applicability="Interpretable baseline: quantify each feature's effect on LST",
))

register_model("elasticnet", None, ModelDef(
    name="elasticnet",
    description="ElasticNet: Linear regression with combined L1/L2 regularization",
    advantages=[
        "Feature selection via L1 regularization",
        "Handles multicollinearity",
        "More stable than pure Lasso",
        "Interpretable coefficients",
    ],
    disadvantages=[
        "Still assumes linearity",
        "Requires careful alpha/l1_ratio tuning",
        "No feature interactions",
    ],
    typical_use_case="Feature selection and interpretable UHI driver identification",
    training_complexity="O(n_features^2 * n)",
    inference_complexity="O(n_features)",
    urban_heat_applicability="Identify key UHI drivers while handling correlated features",
))


_MODEL_CLASSES = {}


def _lazy_import(model_type: str) -> type:
    key = model_type.lower()
    if key in _MODEL_CLASSES:
        return _MODEL_CLASSES[key]

    imports = {
        "random_forest": ("sklearn.ensemble", "RandomForestRegressor"),
        "extra_trees": ("sklearn.ensemble", "ExtraTreesRegressor"),
        "gradient_boosting": ("sklearn.ensemble", "GradientBoostingRegressor"),
        "xgboost": ("xgboost", "XGBRegressor"),
        "lightgbm": ("lightgbm", "LGBMRegressor"),
        "catboost": ("catboost", "CatBoostRegressor"),
        "linear_regression": ("sklearn.linear_model", "LinearRegression"),
        "elasticnet": ("sklearn.linear_model", "ElasticNet"),
    }

    if key not in imports:
        raise ModelNotSupportedError(f"Unknown model type: {model_type}")

    module_name, class_name = imports[key]
    try:
        import importlib
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        _MODEL_CLASSES[key] = cls
        MODEL_REGISTRY[key] = cls
        return cls
    except ImportError as e:
        raise ModelNotSupportedError(
            f"Required package for {model_type} not installed: {e}"
        )


def create_model(model_type: str, **kwargs) -> object:
    cls = _lazy_import(model_type)
    import inspect
    sig = inspect.signature(cls.__init__)
    valid_params = set(sig.parameters.keys())

    params = {}
    if "random_state" in valid_params:
        params["random_state"] = kwargs.pop("random_state", 42)
    if model_type in ("catboost",) and "verbose" in valid_params:
        params["verbose"] = False
    params.update(kwargs)

    return cls(**params)


def create_classifier(model_type: str, **kwargs) -> object:
    key = model_type.lower()
    classifier_map = {
        "random_forest": ("sklearn.ensemble", "RandomForestClassifier"),
        "extra_trees": ("sklearn.ensemble", "ExtraTreesClassifier"),
        "gradient_boosting": ("sklearn.ensemble", "GradientBoostingClassifier"),
        "xgboost": ("xgboost", "XGBClassifier"),
        "lightgbm": ("lightgbm", "LGBMClassifier"),
        "catboost": ("catboost", "CatBoostClassifier"),
    }
    if key not in classifier_map:
        raise ModelNotSupportedError(f"No classifier for model type: {model_type}")

    module_name, class_name = classifier_map[key]
    import importlib
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)
    default_params = {"random_state": 42}
    if model_type in ("catboost",):
        default_params["verbose"] = False
    params = {**default_params, **kwargs}
    return cls(**params)
