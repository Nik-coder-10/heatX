import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import TrainingError
from .models import create_model, create_classifier
from .metrics import compute_regression_metrics, compute_classification_metrics

logger = logging.getLogger("app.ml.hyperparameter")


@dataclass
class HyperparameterResult:
    best_params: dict
    best_score: float
    n_trials: int
    search_method: str
    cv_scores: list[float] | None = None
    all_results: list[dict] | None = None

    def summary(self) -> dict:
        return {
            "best_params": self.best_params,
            "best_score": round(self.best_score, 4),
            "n_trials": self.n_trials,
            "search_method": self.search_method,
        }


_RF_PARAMS = {
    "n_estimators": [50, 100, 200, 500],
    "max_depth": [None, 10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", "log2", None],
}

_XGB_PARAMS = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 5, 7, 10],
    "learning_rate": [0.01, 0.05, 0.1, 0.3],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "reg_alpha": [0, 0.1, 1],
    "reg_lambda": [0, 0.1, 1],
}

_LGB_PARAMS = {
    "n_estimators": [50, 100, 200],
    "max_depth": [-1, 5, 10, 15],
    "learning_rate": [0.01, 0.05, 0.1],
    "num_leaves": [15, 31, 63],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
}


def get_param_grid(model_type: str) -> dict:
    grids = {
        "random_forest": _RF_PARAMS,
        "extra_trees": _RF_PARAMS,
        "gradient_boosting": _XGB_PARAMS,
        "xgboost": _XGB_PARAMS,
        "lightgbm": _LGB_PARAMS,
    }
    return grids.get(model_type.lower(), {"n_estimators": [50, 100]})


def grid_search(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    param_grid: dict | None = None,
    cv_folds: int = 3,
    task: str = "regression",
) -> HyperparameterResult:
    from itertools import product

    grid = param_grid or get_param_grid(model_type)
    keys = list(grid.keys())
    values = list(grid.values())

    best_score = -np.inf
    best_params = {}
    all_results = []

    model_fn = create_classifier if task in ("classification", "binary") else create_model

    for combo in product(*values):
        params = dict(zip(keys, combo))
        fold_scores = []
        fold_size = len(X) // cv_folds

        for fold in range(cv_folds):
            val_start = fold * fold_size
            val_end = (fold + 1) * fold_size if fold < cv_folds - 1 else len(X)
            X_tr = np.concatenate([X[:val_start], X[val_end:]])
            y_tr = np.concatenate([y[:val_start], y[val_end:]])
            X_val = X[val_start:val_end]
            y_val = y[val_start:val_end]

            if len(X_tr) == 0 or len(X_val) == 0:
                continue

            model = model_fn(model_type, **params)
            model.fit(X_tr, y_tr.ravel())
            pred = model.predict(X_val)

            if task == "regression":
                score = compute_regression_metrics(y_val.ravel(), pred).r2
            else:
                score = compute_classification_metrics(y_val.ravel(), pred.astype(int)).f1

            if np.isfinite(score):
                fold_scores.append(score)

        if fold_scores:
            mean_score = np.mean(fold_scores)
            all_results.append({"params": params, "score": float(mean_score)})
            if mean_score > best_score:
                best_score = mean_score
                best_params = params

    return HyperparameterResult(
        best_params=best_params,
        best_score=float(best_score),
        n_trials=len(all_results),
        search_method="grid",
        all_results=all_results,
    )


def random_search(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    param_dist: dict | None = None,
    n_trials: int = 20,
    cv_folds: int = 3,
    task: str = "regression",
    random_state: int = 42,
) -> HyperparameterResult:
    rng = np.random.RandomState(random_state)
    grid = param_dist or get_param_grid(model_type)
    model_fn = create_classifier if task in ("classification", "binary") else create_model

    best_score = -np.inf
    best_params = {}
    all_results = []

    for trial in range(n_trials):
        params = {}
        for key, values in grid.items():
            if isinstance(values, list):
                params[key] = values[rng.randint(len(values))]
            elif isinstance(values, tuple):
                if isinstance(values[0], int):
                    params[key] = rng.randint(values[0], values[1])
                else:
                    params[key] = rng.uniform(values[0], values[1])
            else:
                params[key] = values

        fold_size = len(X) // max(1, cv_folds)
        fold_scores = []
        for fold in range(cv_folds):
            vs = fold * fold_size
            ve = (fold + 1) * fold_size if fold < cv_folds - 1 else len(X)
            X_tr = np.concatenate([X[:vs], X[ve:]])
            y_tr = np.concatenate([y[:vs], y[ve:]])
            X_val = X[vs:ve]
            y_val = y[vs:ve]
            if len(X_tr) == 0 or len(X_val) == 0:
                continue
            try:
                model = model_fn(model_type, **params)
                model.fit(X_tr, y_tr.ravel())
                pred = model.predict(X_val)
                if task == "regression":
                    score = compute_regression_metrics(y_val.ravel(), pred).r2
                else:
                    score = compute_classification_metrics(y_val.ravel(), pred.astype(int)).f1
                if np.isfinite(score):
                    fold_scores.append(score)
            except Exception:
                continue

        if fold_scores:
            mean_score = np.mean(fold_scores)
            all_results.append({"params": params, "score": float(mean_score)})
            if mean_score > best_score:
                best_score = mean_score
                best_params = params

    return HyperparameterResult(
        best_params=best_params,
        best_score=float(best_score),
        n_trials=len(all_results),
        search_method="random",
        all_results=all_results,
    )


def optuna_search(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    n_trials: int = 50,
    cv_folds: int = 3,
    task: str = "regression",
    direction: str = "maximize",
) -> HyperparameterResult:
    try:
        import optuna
    except ImportError:
        raise TrainingError("optuna is required for Bayesian search")

    model_fn = create_classifier if task in ("classification", "binary") else create_model

    if model_type == "xgboost":
        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            }
            scores = []
            fold_size = len(X) // max(1, cv_folds)
            for fold in range(cv_folds):
                vs = fold * fold_size
                ve = (fold + 1) * fold_size if fold < cv_folds - 1 else len(X)
                X_tr = np.concatenate([X[:vs], X[ve:]])
                y_tr = np.concatenate([y[:vs], y[ve:]])
                X_val = X[vs:ve]
                y_val = y[vs:ve]
                if len(X_tr) == 0:
                    continue
                model = model_fn(model_type, **params)
                model.fit(X_tr, y_tr.ravel())
                pred = model.predict(X_val)
                if task == "regression":
                    scores.append(compute_regression_metrics(y_val.ravel(), pred).r2)
                else:
                    scores.append(compute_classification_metrics(y_val.ravel(), pred.astype(int)).f1)
            return float(np.mean(scores)) if scores else 0.0
    elif model_type == "lightgbm":
        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 15),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 10, 100),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            }
            scores = []
            fold_size = len(X) // max(1, cv_folds)
            for fold in range(cv_folds):
                vs = fold * fold_size
                ve = (fold + 1) * fold_size if fold < cv_folds - 1 else len(X)
                X_tr = np.concatenate([X[:vs], X[ve:]])
                y_tr = np.concatenate([y[:vs], y[ve:]])
                X_val = X[vs:ve]
                y_val = y[vs:ve]
                if len(X_tr) == 0:
                    continue
                model = model_fn(model_type, **params)
                model.fit(X_tr, y_tr.ravel())
                pred = model.predict(X_val)
                if task == "regression":
                    scores.append(compute_regression_metrics(y_val.ravel(), pred).r2)
                else:
                    scores.append(compute_classification_metrics(y_val.ravel(), pred.astype(int)).f1)
            return float(np.mean(scores)) if scores else 0.0
    else:
        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 30),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
            }
            scores = []
            fold_size = len(X) // max(1, cv_folds)
            for fold in range(cv_folds):
                vs = fold * fold_size
                ve = (fold + 1) * fold_size if fold < cv_folds - 1 else len(X)
                X_tr = np.concatenate([X[:vs], X[ve:]])
                y_tr = np.concatenate([y[:vs], y[ve:]])
                X_val = X[vs:ve]
                y_val = y[vs:ve]
                if len(X_tr) == 0:
                    continue
                model = model_fn(model_type, **params)
                model.fit(X_tr, y_tr.ravel())
                pred = model.predict(X_val)
                if task == "regression":
                    scores.append(compute_regression_metrics(y_val.ravel(), pred).r2)
                else:
                    scores.append(compute_classification_metrics(y_val.ravel(), pred.astype(int)).f1)
            return float(np.mean(scores)) if scores else 0.0

    study = optuna.create_study(direction=direction)
    study.optimize(objective, n_trials=n_trials)

    return HyperparameterResult(
        best_params=study.best_params,
        best_score=float(study.best_value),
        n_trials=n_trials,
        search_method="optuna",
    )


def optimize_hyperparameters(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    method: str = "optuna",
    n_trials: int = 50,
    cv_folds: int = 3,
    task: str = "regression",
    **kwargs,
) -> HyperparameterResult:
    if method == "grid":
        return grid_search(X, y, model_type, cv_folds=cv_folds, task=task, **kwargs)
    elif method == "random":
        return random_search(X, y, model_type, n_trials=n_trials, cv_folds=cv_folds, task=task, **kwargs)
    elif method == "optuna":
        return optuna_search(X, y, model_type, n_trials=n_trials, cv_folds=cv_folds, task=task)
    else:
        raise TrainingError(f"Unknown hyperparameter method: {method}")
