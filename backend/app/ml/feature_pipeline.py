import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import FeaturePipelineError

logger = logging.getLogger("app.ml.feature_pipeline")


@dataclass
class FeaturePipeline:
    normalization: str = "standard"
    feature_selection: str = "none"
    max_features: int = 50
    missing_strategy: str = "mean"
    feature_names: list[str] | None = None
    _fitted: bool = False

    def __post_init__(self):
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None
        self._min: np.ndarray | None = None
        self._max: np.ndarray | None = None
        self._selected_indices: np.ndarray | None = None
        self._feature_names_in: list[str] | None = None

    def fit(self, X: np.ndarray, y: np.ndarray | None = None, feature_names: list[str] | None = None) -> "FeaturePipeline":
        if X.size == 0:
            raise FeaturePipelineError("Empty input data")

        self._feature_names_in = feature_names or [f"f{i}" for i in range(X.shape[1])]
        X = self._handle_missing(X, fit=True)

        if self.normalization == "standard":
            self._mean = np.nanmean(X, axis=0)
            self._std = np.nanstd(X, axis=0)
            self._std[self._std < 1e-10] = 1.0
        elif self.normalization == "minmax":
            self._min = np.nanmin(X, axis=0)
            self._max = np.nanmax(X, axis=0)
            ranges = self._max - self._min
            ranges[ranges < 1e-10] = 1.0
            self._max = self._min + ranges
        elif self.normalization == "none":
            pass
        else:
            raise FeaturePipelineError(f"Unknown normalization: {self.normalization}")

        if self.feature_selection == "variance":
            variances = np.nanvar(X, axis=0)
            self._selected_indices = np.where(variances > 1e-10)[0]
            if len(self._selected_indices) == 0:
                self._selected_indices = np.arange(X.shape[1])
        elif self.feature_selection == "correlation" and y is not None:
            correlations = []
            for col in range(X.shape[1]):
                c = np.corrcoef(X[:, col], y.ravel())[0, 1]
                correlations.append(abs(c) if np.isfinite(c) else 0.0)
            top_k = min(self.max_features, X.shape[1])
            self._selected_indices = np.argsort(correlations)[-top_k:]
        else:
            self._selected_indices = np.arange(X.shape[1])

        self._fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise FeaturePipelineError("Pipeline not fitted. Call fit() first.")

        X = self._handle_missing(X, fit=False)

        if self.normalization == "standard":
            X = (X - self._mean) / self._std
        elif self.normalization == "minmax":
            X = (X - self._min) / (self._max - self._min)

        if self._selected_indices is not None:
            X = X[:, self._selected_indices]

        return X

    def fit_transform(self, X: np.ndarray, y: np.ndarray | None = None, feature_names: list[str] | None = None) -> np.ndarray:
        self.fit(X, y, feature_names)
        return self.transform(X)

    def _handle_missing(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        X = X.copy()
        if self.missing_strategy == "mean" and fit:
            self._fill_values = np.nanmean(X, axis=0)
            self._fill_values[~np.isfinite(self._fill_values)] = 0.0
        if self.missing_strategy in ("mean", "median") and hasattr(self, "_fill_values"):
            for col in range(X.shape[1]):
                mask = ~np.isfinite(X[:, col])
                if mask.any():
                    X[mask, col] = self._fill_values[col]
        elif self.missing_strategy == "zero":
            X[~np.isfinite(X)] = 0.0
        elif self.missing_strategy == "drop":
            valid = np.all(np.isfinite(X), axis=1)
            X = X[valid]
        return X

    def get_selected_feature_names(self) -> list[str]:
        if self._feature_names_in is None:
            return []
        if self._selected_indices is not None:
            return [self._feature_names_in[i] for i in self._selected_indices]
        return self._feature_names_in

    def get_feature_importance(self, model) -> np.ndarray | None:
        if hasattr(model, "feature_importances_"):
            return model.feature_importances_
        if hasattr(model, "coef_"):
            return np.abs(model.coef_)
        return None

    def to_config(self) -> dict:
        return {
            "normalization": self.normalization,
            "feature_selection": self.feature_selection,
            "max_features": self.max_features,
            "missing_strategy": self.missing_strategy,
        }


def build_pipeline_from_cube(cube, config=None) -> tuple[FeaturePipeline, np.ndarray, list[str]]:
    from .configuration import MLForecastConfig
    cfg = config or MLForecastConfig.defaults()

    if not hasattr(cube, "to_flat_array"):
        raise FeaturePipelineError("Input must have to_flat_array() method")

    X = cube.to_flat_array()
    feature_names = getattr(cube, "feature_names", [f"f{i}" for i in range(X.shape[1])])

    pipeline = FeaturePipeline(
        normalization=cfg.normalization,
        feature_selection=cfg.feature_selection,
        max_features=cfg.max_features,
        missing_strategy=cfg.missing_strategy,
        feature_names=feature_names,
    )

    return pipeline, X, feature_names
