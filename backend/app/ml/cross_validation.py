import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import ValidationError
from .metrics import compute_regression_metrics, compute_classification_metrics
from .models import create_model, create_classifier

logger = logging.getLogger("app.ml.cross_validation")


@dataclass
class CVResult:
    scores: list[float]
    mean_score: float
    std_score: float
    n_folds: int
    strategy: str
    metrics: list[dict] | None = None

    def summary(self) -> dict:
        return {
            "mean_score": round(self.mean_score, 4),
            "std_score": round(self.std_score, 4),
            "n_folds": self.n_folds,
            "strategy": self.strategy,
            "scores": [round(s, 4) for s in self.scores],
        }


def _train_eval_fold(model_fn, X_train, y_train, X_val, y_val, task):
    model = model_fn()
    model.fit(X_train, y_train.ravel())
    pred = model.predict(X_val)
    if task == "regression":
        m = compute_regression_metrics(y_val.ravel(), pred)
        return m.r2, m
    else:
        m = compute_classification_metrics(y_val.ravel(), pred.astype(int))
        return m.f1, m


def kfold_cv(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    n_folds: int = 5,
    task: str = "regression",
    shuffle: bool = True,
    random_state: int = 42,
    **model_kwargs,
) -> CVResult:
    n = len(X)
    indices = np.arange(n)
    if shuffle:
        rng = np.random.RandomState(random_state)
        rng.shuffle(indices)

    fold_size = n // n_folds
    scores = []
    metrics_list = []
    model_fn = lambda: create_classifier(model_type, **model_kwargs) if task in ("classification", "binary") else create_model(model_type, **model_kwargs)

    for fold in range(n_folds):
        val_start = fold * fold_size
        val_end = (fold + 1) * fold_size if fold < n_folds - 1 else n
        val_idx = indices[val_start:val_end]
        train_idx = np.concatenate([indices[:val_start], indices[val_end:]])

        if len(train_idx) == 0 or len(val_idx) == 0:
            continue

        score, m = _train_eval_fold(
            model_fn, X[train_idx], y[train_idx], X[val_idx], y[val_idx], task
        )
        if np.isfinite(score):
            scores.append(score)
            metrics_list.append(m.to_dict())

    return CVResult(
        scores=scores,
        mean_score=float(np.mean(scores)) if scores else 0.0,
        std_score=float(np.std(scores)) if scores else 0.0,
        n_folds=n_folds,
        strategy="kfold",
        metrics=metrics_list,
    )


def stratified_kfold_cv(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    n_folds: int = 5,
    task: str = "classification",
    random_state: int = 42,
    **model_kwargs,
) -> CVResult:
    from sklearn.model_selection import StratifiedKFold
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    scores = []
    metrics_list = []
    model_fn = lambda: create_classifier(model_type, **model_kwargs)

    for train_idx, val_idx in skf.split(X, y.ravel()):
        score, m = _train_eval_fold(
            model_fn, X[train_idx], y[train_idx], X[val_idx], y[val_idx], task
        )
        if np.isfinite(score):
            scores.append(score)
            metrics_list.append(m.to_dict())

    return CVResult(
        scores=scores,
        mean_score=float(np.mean(scores)) if scores else 0.0,
        std_score=float(np.std(scores)) if scores else 0.0,
        n_folds=n_folds,
        strategy="stratified_kfold",
        metrics=metrics_list,
    )


def timeseries_cv(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    n_splits: int = 5,
    task: str = "regression",
    **model_kwargs,
) -> CVResult:
    scores = []
    metrics_list = []
    n = len(X)
    model_fn = lambda: create_classifier(model_type, **model_kwargs) if task in ("classification", "binary") else create_model(model_type, **model_kwargs)

    for split in range(1, min(n_splits + 1, n // 2)):
        train_end = int(n * split / (n_splits + 1))
        val_end = int(n * (split + 1) / (n_splits + 1))
        if train_end >= val_end or val_end > n:
            continue
        train_idx = np.arange(train_end)
        val_idx = np.arange(train_end, val_end)
        if len(train_idx) < 2 or len(val_idx) < 2:
            continue
        score, m = _train_eval_fold(
            model_fn, X[train_idx], y[train_idx], X[val_idx], y[val_idx], task
        )
        if np.isfinite(score):
            scores.append(score)
            metrics_list.append(m.to_dict())

    return CVResult(
        scores=scores,
        mean_score=float(np.mean(scores)) if scores else 0.0,
        std_score=float(np.std(scores)) if scores else 0.0,
        n_folds=len(scores),
        strategy="timeseries",
        metrics=metrics_list,
    )


def spatial_cv(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    coordinates: np.ndarray | None = None,
    n_clusters: int = 5,
    task: str = "regression",
    random_state: int = 42,
    **model_kwargs,
) -> CVResult:
    if coordinates is None and X.shape[1] >= 2:
        coordinates = X[:, :2]

    if coordinates is None:
        raise ValidationError("Coordinates required for spatial cross-validation")

    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=5)
    clusters = kmeans.fit_predict(coordinates)

    scores = []
    metrics_list = []
    model_fn = lambda: create_classifier(model_type, **model_kwargs) if task in ("classification", "binary") else create_model(model_type, **model_kwargs)

    for cluster_id in range(n_clusters):
        val_idx = np.where(clusters == cluster_id)[0]
        train_idx = np.where(clusters != cluster_id)[0]
        if len(train_idx) < 2 or len(val_idx) < 2:
            continue
        score, m = _train_eval_fold(
            model_fn, X[train_idx], y[train_idx], X[val_idx], y[val_idx], task
        )
        if np.isfinite(score):
            scores.append(score)
            metrics_list.append(m.to_dict())

    return CVResult(
        scores=scores,
        mean_score=float(np.mean(scores)) if scores else 0.0,
        std_score=float(np.std(scores)) if scores else 0.0,
        n_folds=len(scores),
        strategy="spatial",
        metrics=metrics_list,
    )


def cross_validate(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    strategy: str = "kfold",
    n_folds: int = 5,
    task: str = "regression",
    **kwargs,
) -> CVResult:
    strategies = {
        "kfold": kfold_cv,
        "stratified": stratified_kfold_cv,
        "timeseries": timeseries_cv,
        "spatial": spatial_cv,
    }
    if strategy not in strategies:
        raise ValidationError(f"Unknown CV strategy: {strategy}")

    cv_args = {k: v for k, v in kwargs.items()
               if k not in ("n_folds", "strategy", "task", "model_type")}
    fn = strategies[strategy]
    fold_param = {"kfold": n_folds, "stratified": n_folds, "timeseries": n_folds, "spatial": n_folds}
    fold_kwargs = {"n_folds": n_folds}
    if strategy == "timeseries":
        fold_kwargs = {"n_splits": n_folds}
    elif strategy == "spatial":
        fold_kwargs = {"n_clusters": n_folds}
    return fn(X, y, model_type, task=task, **fold_kwargs, **cv_args)
