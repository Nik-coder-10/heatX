import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import EnsembleError
from .models import create_model, create_classifier
from .metrics import compute_regression_metrics

logger = logging.getLogger("app.ml.ensemble")


@dataclass
class EnsembleResult:
    models: list[object]
    weights: list[float]
    method: str
    predictions: np.ndarray | None = None
    ensemble_score: float = 0.0
    individual_scores: list[float] | None = None

    def summary(self) -> dict:
        return {
            "method": self.method,
            "n_models": len(self.models),
            "ensemble_score": round(self.ensemble_score, 4),
            "weights": [round(w, 4) for w in self.weights],
        }


class Ensemble:
    def __init__(self, method: str = "weighted"):
        self.method = method
        self.models: list[object] = []
        self.weights: list[float] = []
        self._fitted = False

    def add_model(self, model: object, weight: float = 1.0) -> "Ensemble":
        self.models.append(model)
        self.weights.append(weight)
        return self

    def fit(self, X: np.ndarray, y: np.ndarray) -> "Ensemble":
        for i, model in enumerate(self.models):
            model.fit(X, y.ravel())
        self._fitted = True
        if self.method in ("weighted",):
            total = sum(self.weights)
            if total > 0:
                self.weights = [w / total for w in self.weights]
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise EnsembleError("Ensemble not fitted")
        if not self.models:
            raise EnsembleError("No models in ensemble")

        if self.method == "voting":
            predictions = np.array([m.predict(X) for m in self.models])
            return np.round(np.mean(predictions, axis=0)).astype(int) if predictions.ndim > 1 else predictions

        elif self.method == "weighted":
            predictions = np.zeros(X.shape[0])
            for model, weight in zip(self.models, self.weights):
                pred = model.predict(X)
                if hasattr(pred, "__len__") and len(pred) == X.shape[0]:
                    predictions += pred.ravel() * weight
            return predictions

        elif self.method == "average":
            predictions = np.array([m.predict(X) for m in self.models])
            return np.mean(predictions, axis=0)

        elif self.method == "median":
            predictions = np.array([m.predict(X) for m in self.models])
            return np.median(predictions, axis=0)

        else:
            raise EnsembleError(f"Unknown ensemble method: {self.method}")


def build_stacking_ensemble(
    base_models: list[tuple[str, object]],
    X: np.ndarray,
    y: np.ndarray,
    meta_model_type: str = "linear_regression",
    cv_folds: int = 3,
    task: str = "regression",
) -> EnsembleResult:
    n = len(X)
    fold_size = n // max(1, cv_folds)
    meta_features = np.zeros((n, len(base_models)))

    for fold in range(cv_folds):
        vs = fold * fold_size
        ve = (fold + 1) * fold_size if fold < cv_folds - 1 else n
        train_idx = np.concatenate([np.arange(vs), np.arange(ve, n)])
        val_idx = np.arange(vs, ve)
        if len(train_idx) == 0 or len(val_idx) == 0:
            continue

        for i, (name, model) in enumerate(base_models):
            from copy import deepcopy
            m = deepcopy(model)
            m.fit(X[train_idx], y[train_idx].ravel())
            meta_features[val_idx, i] = m.predict(X[val_idx]).ravel()

    meta_model = create_model(meta_model_type)
    meta_model.fit(meta_features, y.ravel())

    for name, model in base_models:
        model.fit(X, y.ravel())

    class StackingEnsemble:
        def __init__(self, base_models, meta_model):
            self.base_models = base_models
            self.meta_model = meta_model

        def predict(self, X):
            meta = np.column_stack([m.predict(X) for _, m in self.base_models])
            return self.meta_model.predict(meta)

    ensemble_model = StackingEnsemble(base_models, meta_model)
    weights = [1.0 / len(base_models)] * len(base_models)

    return EnsembleResult(
        models=[m for _, m in base_models] + [meta_model],
        weights=weights,
        method="stacking",
    )


def build_blending_ensemble(
    base_models: list[tuple[str, object]],
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    task: str = "regression",
) -> EnsembleResult:
    for name, model in base_models:
        model.fit(X_train, y_train.ravel())

    scores = []
    for name, model in base_models:
        pred = model.predict(X_val)
        m = compute_regression_metrics(y_val.ravel(), pred)
        scores.append(max(0.0, m.r2))

    total = sum(scores)
    weights = [s / total if total > 0 else 1.0 / len(scores) for s in scores]

    ensemble = Ensemble(method="weighted")
    for (name, model), weight in zip(base_models, weights):
        ensemble.add_model(model, weight)

    return EnsembleResult(
        models=[m for _, m in base_models],
        weights=weights,
        method="blending",
        ensemble_score=float(np.mean(scores)) if scores else 0.0,
        individual_scores=scores,
    )
