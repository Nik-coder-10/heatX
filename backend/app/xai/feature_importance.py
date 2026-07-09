import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import ExplainabilityError, ModelNotSupportedError

logger = logging.getLogger("app.xai.feature_importance")


@dataclass
class FeatureImportanceResult:
    feature_names: list[str]
    importance_values: np.ndarray
    method: str
    standard_deviation: np.ndarray | None = None
    ranking: list[int] | None = None
    n_instances: int = 0
    metadata: dict | None = None

    def __post_init__(self):
        if self.ranking is None and len(self.importance_values) > 0:
            self.ranking = list(np.argsort(self.importance_values)[::-1])

    def top_features(self, n: int = 10) -> list[tuple[str, float]]:
        idx = np.argsort(self.importance_values)[::-1][:n]
        return [(self.feature_names[i], float(self.importance_values[i])) for i in idx]

    def to_dict(self) -> dict:
        return {
            "feature_names": self.feature_names,
            "importance_values": self.importance_values.tolist(),
            "method": self.method,
            "ranking": self.ranking,
            "n_instances": self.n_instances,
        }


def _normalize_importance(values: np.ndarray) -> np.ndarray:
    vmin, vmax = values.min(), values.max()
    if vmax - vmin < 1e-10:
        return np.full_like(values, 50.0)
    return 100.0 * (values - vmin) / (vmax - vmin)


def compute_shap_importance(
    model,
    X: np.ndarray,
    feature_names: list[str],
    background: np.ndarray | None = None,
    n_samples: int = 100,
    random_state: int = 42,
) -> FeatureImportanceResult:
    try:
        import shap
    except ImportError:
        raise ExplainabilityError("SHAP library is required for shap importance. Install with: pip install shap")

    if background is None:
        background = X[:min(n_samples, len(X))]

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        is_list = isinstance(shap_values, list)
        if is_list:
            shap_values = shap_values[0]
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 1]
        expected = explainer.expected_value
        if isinstance(expected, list) or isinstance(expected, np.ndarray):
            expected = expected[0] if len(expected) > 1 else expected
    except Exception:
        explainer = shap.KernelExplainer(model.predict, background, random_state=random_state)
        shap_values = explainer.shap_values(X, nsamples=n_samples)
        expected = explainer.expected_value

    abs_shap = np.abs(shap_values).mean(axis=0)
    if isinstance(abs_shap, np.ndarray) and abs_shap.ndim == 0:
        abs_shap = np.array([float(abs_shap)])
    if abs_shap.ndim == 0:
        abs_shap = np.array([float(abs_shap)])

    std = np.std(shap_values, axis=0)
    if isinstance(std, np.ndarray) and std.ndim == 0:
        std = np.array([float(std)])
    if std.ndim == 0:
        std = np.array([float(std)])

    importance = _normalize_importance(abs_shap)

    if isinstance(expected, np.ndarray):
        expected_val = float(expected.item()) if expected.size <= 1 else float(expected[0])
    elif hasattr(expected, "__float__"):
        expected_val = float(expected)
    else:
        expected_val = float(expected[0])

    result = FeatureImportanceResult(
        feature_names=list(feature_names),
        importance_values=importance,
        method="shap",
        standard_deviation=std,
        n_instances=X.shape[0],
        metadata={"expected_value": expected_val},
    )
    return result


def compute_permutation_importance(
    model,
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    n_repeats: int = 5,
    random_state: int = 42,
    scoring: str = "r2",
) -> FeatureImportanceResult:
    rng = np.random.RandomState(random_state)
    baseline_pred = model.predict(X)
    if y.ndim == 1:
        y = y.ravel()

    from sklearn.metrics import r2_score, mean_squared_error
    if scoring == "r2":
        baseline_score = r2_score(y, baseline_pred)
    else:
        baseline_score = -mean_squared_error(y, baseline_pred)

    importances = np.zeros((n_repeats, X.shape[1]))
    for rep in range(n_repeats):
        for col in range(X.shape[1]):
            X_perm = X.copy()
            X_perm[:, col] = X_perm[rng.permutation(X.shape[0]), col]
            perm_pred = model.predict(X_perm)
            if scoring == "r2":
                perm_score = r2_score(y, perm_pred)
            else:
                perm_score = -mean_squared_error(y, perm_pred)
            importances[rep, col] = baseline_score - perm_score

    mean_importance = importances.mean(axis=0)
    std_importance = importances.std(axis=0)

    importance = _normalize_importance(mean_importance)

    return FeatureImportanceResult(
        feature_names=list(feature_names),
        importance_values=importance,
        method="permutation",
        standard_deviation=std_importance,
        n_instances=X.shape[0],
    )


def compute_tree_importance(
    model,
    feature_names: list[str],
    importance_type: str = "gain",
) -> FeatureImportanceResult:
    if not hasattr(model, "feature_importances_"):
        raise ModelNotSupportedError("Model does not have feature_importances_ attribute")

    raw = model.feature_importances_.copy()
    if raw.ndim == 0:
        raw = np.array([float(raw)])
    if raw.ndim > 1:
        raw = raw.mean(axis=0)

    importance = _normalize_importance(raw)

    return FeatureImportanceResult(
        feature_names=list(feature_names),
        importance_values=importance,
        method=f"tree_{importance_type}",
        standard_deviation=None,
        n_instances=0,
        metadata={"importance_type": importance_type},
    )


def compute_correlation_importance(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    method: str = "mutual_info",
    random_state: int = 42,
) -> FeatureImportanceResult:
    if method == "mutual_info":
        from sklearn.feature_selection import mutual_info_regression
        mi = mutual_info_regression(X, y.ravel(), random_state=random_state)
        importance = _normalize_importance(mi)
        std = None
    else:
        correlations = []
        for col in range(X.shape[1]):
            corr = np.corrcoef(X[:, col], y.ravel())[0, 1]
            correlations.append(abs(corr) if np.isfinite(corr) else 0.0)
        importance = _normalize_importance(np.array(correlations))
        std = None

    return FeatureImportanceResult(
        feature_names=list(feature_names),
        importance_values=importance,
        method=f"correlation_{method}",
        standard_deviation=std,
        n_instances=X.shape[0],
    )


import inspect


def _filter_kwargs(fn, kwargs):
    sig = inspect.signature(fn)
    valid = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in valid}


def compute_importance(
    model,
    X: np.ndarray,
    y: np.ndarray | None = None,
    feature_names: list[str] | None = None,
    method: str = "shap",
    **kwargs,
) -> FeatureImportanceResult:
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

    method_map = {
        "shap": compute_shap_importance,
        "permutation": compute_permutation_importance,
        "tree_importance": compute_tree_importance,
        "tree_gain": compute_tree_importance,
        "correlation": lambda **kw: compute_correlation_importance(**kw, method="pearson"),
        "mutual_info": lambda **kw: compute_correlation_importance(**kw, method="mutual_info"),
    }

    if method not in method_map:
        raise ExplainabilityError(f"Unsupported importance method: {method}")

    fn = method_map[method]
    filtered = _filter_kwargs(fn, kwargs)
    if method in ("shap",):
        return fn(model=model, X=X, feature_names=feature_names, **filtered)
    elif method in ("permutation",):
        if y is None:
            raise ExplainabilityError("y is required for permutation importance")
        return fn(model=model, X=X, y=y, feature_names=feature_names, **filtered)
    elif method in ("tree_importance", "tree_gain"):
        return fn(model=model, feature_names=feature_names, **filtered)
    elif method in ("correlation", "mutual_info"):
        if y is None:
            raise ExplainabilityError("y is required for correlation importance")
        return fn(X=X, y=y, feature_names=feature_names, **filtered)
    else:
        raise ExplainabilityError(f"Unsupported importance method: {method}")
