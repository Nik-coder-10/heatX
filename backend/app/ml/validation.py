import logging
from dataclasses import dataclass, field

import numpy as np

from .exceptions import ValidationError
from .cross_validation import cross_validate, CVResult
from .evaluation import evaluate_regression, evaluate_classification, EvaluationResult
from .training import train_model, TrainingResult

logger = logging.getLogger("app.ml.validation")


@dataclass
class ValidationReport:
    cv_result: CVResult | None = None
    evaluation: EvaluationResult | None = None
    train_result: TrainingResult | None = None
    n_validated: int = 0

    def summary(self) -> dict:
        s: dict = {}
        if self.cv_result:
            s["cross_validation"] = self.cv_result.summary()
        if self.evaluation:
            s["evaluation"] = self.evaluation.summary()
        return s


def validate_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_type: str = "random_forest",
    cv_strategy: str = "kfold",
    cv_folds: int = 5,
    task: str = "regression",
    **kwargs,
) -> ValidationReport:
    cv_result = cross_validate(
        X_train, y_train, model_type,
        strategy=cv_strategy, n_folds=cv_folds, task=task,
    )

    train_result = train_model(
        X_train, y_train, X_test, y_test,
        feature_names=kwargs.get("feature_names"),
        model_type=model_type, prediction_task=task,
    )

    return ValidationReport(
        cv_result=cv_result,
        evaluation=train_result.evaluation,
        train_result=train_result,
        n_validated=1,
    )
