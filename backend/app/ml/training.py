import logging
import os
import time
from dataclasses import dataclass, field

import numpy as np

from .configuration import MLForecastConfig
from .exceptions import TrainingError
from .models import create_model, create_classifier
from .feature_pipeline import FeaturePipeline
from .evaluation import evaluate_regression, evaluate_classification, EvaluationResult
from .metrics import compute_regression_metrics, compute_classification_metrics

logger = logging.getLogger("app.ml.training")


@dataclass
class TrainingResult:
    model: object | None = None
    pipeline: FeaturePipeline | None = None
    evaluation: EvaluationResult | None = None
    training_time_s: float = 0.0
    n_epochs_trained: int = 0
    early_stopped: bool = False
    config: dict | None = None

    def summary(self) -> dict:
        s = {
            "training_time_s": round(self.training_time_s, 2),
            "n_epochs_trained": self.n_epochs_trained,
            "early_stopped": self.early_stopped,
        }
        if self.evaluation:
            s["evaluation"] = self.evaluation.summary()
        return s


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray | None = None,
    y_test: np.ndarray | None = None,
    config: MLForecastConfig | None = None,
    feature_names: list[str] | None = None,
    pipeline: FeaturePipeline | None = None,
    **model_kwargs,
) -> TrainingResult:
    cfg = config or MLForecastConfig.defaults()
    t0 = time.time()

    mt = model_kwargs.pop("model_type", cfg.model_type)
    task = model_kwargs.pop("prediction_task", cfg.prediction_task)

    if pipeline is not None:
        X_train_t = pipeline.transform(X_train)
    else:
        X_train_t = X_train

    if task in ("classification", "binary"):
        model = create_classifier(mt, **model_kwargs)
        y_t = y_train.ravel()
    else:
        model = create_model(mt, **model_kwargs)
        y_t = y_train.ravel()

    model.fit(X_train_t, y_t)
    elapsed = time.time() - t0

    eval_result = None
    if X_test is not None and y_test is not None:
        X_test_t = pipeline.transform(X_test) if pipeline else X_test
        if cfg.prediction_task in ("classification", "binary"):
            eval_result = evaluate_classification(
                model, X_train_t, y_t, X_test_t, y_test.ravel(), feature_names
            )
        else:
            eval_result = evaluate_regression(
                model, X_train_t, y_t, X_test_t, y_test.ravel(), feature_names
            )

    return TrainingResult(
        model=model,
        pipeline=pipeline,
        evaluation=eval_result,
        training_time_s=elapsed,
        n_epochs_trained=1,
        config=cfg.__dict__.copy(),
    )


def train_with_early_stopping(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    early_stopping_rounds: int = 10,
    task: str = "regression",
    **fit_kwargs,
) -> TrainingResult:
    t0 = time.time()
    best_score = -np.inf if task == "regression" else 0.0
    best_model = None
    no_improve = 0
    n_epochs = 0
    early_stopped = False

    if hasattr(model, "fit") and hasattr(model, "predict"):
        if hasattr(model, "early_stopping"):
            if task == "regression":
                model.fit(
                    X_train, y_train.ravel(),
                    eval_set=[(X_val, y_val.ravel())],
                    early_stopping_rounds=early_stopping_rounds,
                    **fit_kwargs,
                )
            n_epochs = getattr(model, "best_iteration_", 0) or 0
        else:
            for epoch in range(100):
                if hasattr(model, "partial_fit"):
                    model.partial_fit(X_train, y_train.ravel())
                else:
                    model.fit(X_train, y_train.ravel())

                val_pred = model.predict(X_val)
                if task == "regression":
                    metrics = compute_regression_metrics(y_val.ravel(), val_pred)
                    score = metrics.r2
                else:
                    metrics = compute_classification_metrics(y_val.ravel(), val_pred.astype(int))
                    score = metrics.f1

                n_epochs = epoch + 1
                if score > best_score:
                    best_score = score
                    best_model = model.__class__.__name__
                    no_improve = 0
                else:
                    no_improve += 1
                    if no_improve >= early_stopping_rounds:
                        early_stopped = True
                        break

    elapsed = time.time() - t0
    return TrainingResult(
        model=model,
        training_time_s=elapsed,
        n_epochs_trained=n_epochs,
        early_stopped=early_stopped,
    )


def train_with_checkpointing(
    model,
    X: np.ndarray,
    y: np.ndarray,
    checkpoint_dir: str = "checkpoints",
    **fit_kwargs,
) -> TrainingResult:
    import os
    os.makedirs(checkpoint_dir, exist_ok=True)
    t0 = time.time()

    model.fit(X, y.ravel())

    import joblib
    path = os.path.join(checkpoint_dir, "model_checkpoint.joblib")
    joblib.dump(model, path)
    logger.info("Checkpoint saved to %s", path)

    elapsed = time.time() - t0
    return TrainingResult(
        model=model,
        training_time_s=elapsed,
        n_epochs_trained=1,
    )


def warm_start_train(
    model,
    X: np.ndarray,
    y: np.ndarray,
    n_iterations: int = 5,
    **fit_kwargs,
) -> TrainingResult:
    t0 = time.time()
    for i in range(n_iterations):
        if hasattr(model, "warm_start"):
            if hasattr(model, "n_estimators"):
                current = getattr(model, "n_estimators", 0)
                model.set_params(n_estimators=current + 10)
        model.fit(X, y.ravel())

    elapsed = time.time() - t0
    return TrainingResult(model=model, training_time_s=elapsed, n_epochs_trained=n_iterations)
