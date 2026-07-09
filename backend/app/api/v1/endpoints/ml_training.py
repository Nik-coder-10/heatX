import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

from app.ml import (
    MLForecastEngine, TrainingError, ModelNotSupportedError,
    cross_validate, optimize_hyperparameters, ValidationError,
)
from app.schemas.ml import (
    TrainRequest, TrainResponse,
    CrossValidateRequest, HyperparameterRequest,
)

router = APIRouter()


def _to_numpy(X: list[list[float]]) -> np.ndarray:
    return np.array(X, dtype=np.float64)


@router.post("/train", response_model=TrainResponse)
async def train_model_endpoint(req: TrainRequest):
    try:
        engine = MLForecastEngine()
        X = _to_numpy(req.X)
        y = np.array(req.y, dtype=np.float64)
        kw = req.model_kwargs or {}
        kw.pop("prediction_task", None)
        result = engine.train(X, y, model_type=req.model_type,
                               feature_names=req.feature_names or None,
                               prediction_task=req.task,
                               **kw)
        metrics = {}
        ev = getattr(result, "evaluation", None)
        if ev is not None:
            if hasattr(ev, "train_metrics") and ev.train_metrics:
                metrics = {k: round(float(v), 4) for k, v in ev.train_metrics.items() if isinstance(v, (int, float))}
        return TrainResponse(
            model_type=req.model_type,
            task=req.task,
            metrics=metrics or None,
            n_samples=int(X.shape[0]),
            n_features=int(X.shape[1]),
            message="Training completed successfully",
        )
    except (TrainingError, ModelNotSupportedError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cross-validate", response_model=dict)
async def cross_validate_endpoint(req: CrossValidateRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y, dtype=np.float64)
        result = cross_validate(X, y, model_type=req.model_type,
                                 strategy=req.strategy, n_folds=req.n_folds,
                                 task=req.task)
        return {
            "status": "success",
            "mean_score": round(float(np.mean(result.scores)), 4) if hasattr(result, "scores") and result.scores else 0,
            "std_score": round(float(np.std(result.scores)), 4) if hasattr(result, "scores") and result.scores else 0,
            "n_folds": req.n_folds,
            "strategy": req.strategy,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/hyperparameter-optimization", response_model=dict)
async def hyperparameter_optimization_endpoint(req: HyperparameterRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y, dtype=np.float64)
        result = optimize_hyperparameters(X, y, model_type=req.model_type,
                                           method=req.method,
                                           n_trials=req.n_trials,
                                           task=req.task)
        best = result.best_params if hasattr(result, "best_params") else {}
        best_score = result.best_score if hasattr(result, "best_score") else 0
        return {
            "status": "success",
            "best_params": best,
            "best_score": round(float(best_score), 4),
            "method": req.method,
            "n_trials": req.n_trials,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=dict)
async def read_training_jobs(skip: int = 0, limit: int = 100):
    return {"status": "ok", "message": "ML training API ready", "endpoints": ["train", "cross-validate", "hyperparameter-optimization"]}


@router.get("/{job_id}", response_model=dict)
async def read_training_job(job_id: str):
    return {"id": job_id, "status": "completed", "message": "Training job API ready"}


@router.post("/", response_model=dict)
async def create_training_job(training_job: dict):
    return {**training_job, "id": "pending"}


@router.put("/{job_id}", response_model=dict)
async def update_training_job(job_id: str, training_job: dict):
    return {**training_job, "id": job_id}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_job(job_id: str):
    return None
