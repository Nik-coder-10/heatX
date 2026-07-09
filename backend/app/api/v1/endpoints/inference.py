import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

from app.ml import (
    MLForecastEngine, PredictionError, ForecastResult,
    predict, create_model, train_model,
)
from app.xai import XAIEngine, ExplanationError
from app.schemas.ml import (
    PredictRequest, PredictResponse,
    ForecastRequest, ForecastResponse,
)
from app.schemas.xai import ExplainRequest, ExplainHotspotRequest

router = APIRouter()


def _to_numpy(X: list[list[float]]) -> np.ndarray:
    return np.array(X, dtype=np.float64)


def _make_model(model_type: str = "random_forest"):
    return create_model(model_type)


@router.post("/predict", response_model=PredictResponse)
async def predict_endpoint(req: PredictRequest):
    try:
        X = _to_numpy(req.X)
        y_dummy = X[:, 0] + 0.1 * X[:, 1] if X.shape[1] >= 2 else X[:, 0]
        from app.ml import train_model
        train_result = train_model(X_train=X, y_train=y_dummy, model_type="random_forest")
        model = train_result.model
        result = predict(model, X)
        preds = result.values.flatten().tolist() if hasattr(result, "values") else []
        confidence = result.confidence if hasattr(result, "confidence") else None
        if isinstance(confidence, np.ndarray):
            confidence = confidence.flatten().tolist()
        fi = {}
        if hasattr(result, "feature_importance") and result.feature_importance is not None:
            fi_list = result.feature_importance.flatten().tolist() if isinstance(result.feature_importance, np.ndarray) else []
            if req.feature_names:
                for i, name in enumerate(req.feature_names):
                    if i < len(fi_list):
                        fi[name] = round(float(fi_list[i]), 4)
            else:
                for i, v in enumerate(fi_list):
                    fi[f"feature_{i}"] = round(float(v), 4) if isinstance(v, (int, float)) else 0
        uncertainty = None
        if hasattr(result, "uncertainty") and result.uncertainty is not None:
            uncertainty = {"std": round(float(np.std(preds) if preds else 0), 4)}
        return PredictResponse(
            predictions=[round(float(p), 4) for p in preds],
            confidence=confidence,
            uncertainty=uncertainty,
            feature_importance=fi or None,
        )
    except PredictionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/forecast", response_model=ForecastResponse)
async def forecast_endpoint(req: ForecastRequest):
    try:
        X = _to_numpy(req.X)
        y_dummy = X[:, 0] + 0.1 * X[:, 1] if X.shape[1] >= 2 else X[:, 0]
        from app.ml import train_model
        train_result = train_model(X_train=X, y_train=y_dummy, model_type="random_forest")
        model = train_result.model
        from app.ml.forecasting import forecast_future_lst
        f_result = forecast_future_lst(model, X, delta_years=req.delta_years)
        return ForecastResponse(
            current_intensity=round(float(f_result.current_intensity), 2) if hasattr(f_result, "current_intensity") else None,
            future_lst=f_result.future_lst.tolist() if hasattr(f_result, "future_lst") and f_result.future_lst is not None else None,
            hotspot_probability=f_result.hotspot_probability if hasattr(f_result, "hotspot_probability") else None,
            future_severity=getattr(f_result, "future_severity", None),
            hotspot_growth=f_result.hotspot_growth if hasattr(f_result, "hotspot_growth") else None,
        )
    except PredictionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/explain", response_model=dict)
async def explain_endpoint(req: ExplainRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y) if req.y else None
        xai = XAIEngine()
        model = _make_model("random_forest")
        if y is not None and X.shape[0] >= 5:
            train_result = train_model(X_train=X, y_train=y, model_type="random_forest")
            model = train_result.model
        result = xai.explain(
            X, y=y, feature_names=req.feature_names,
            method=req.method,
            compute_local=req.compute_local,
            compute_global=req.compute_global,
            compute_counterfactual=req.compute_counterfactual,
            compute_confidence=req.compute_confidence,
            compute_uncertainty=req.compute_uncertainty,
        )
        return {"status": "success", "data": result.to_dict() if hasattr(result, "to_dict") else str(result)}
    except ExplanationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/explain-hotspot", response_model=dict)
async def explain_hotspot_endpoint(req: ExplainHotspotRequest):
    try:
        X = _to_numpy(req.X)
        xai = XAIEngine()
        model = _make_model("random_forest")
        hotspot = type("Hotspot", (), req.hotspot)()
        result = xai.explain_hotspot(hotspot, model, X, req.feature_names,
                                      target_reduction=req.target_reduction)
        return {"status": "success", "data": result.to_dict() if hasattr(result, "to_dict") else str(result)}
    except ExplanationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=dict)
async def read_inference_requests(skip: int = 0, limit: int = 100):
    return {"status": "ok", "message": "ML inference API ready", "endpoints": ["predict", "forecast", "explain", "explain-hotspot"]}


@router.get("/{request_id}", response_model=dict)
async def read_inference_request(request_id: str):
    return {"id": request_id, "status": "completed"}


@router.post("/", response_model=dict)
async def create_inference_request(inference_request: dict):
    return {**inference_request, "id": "pending"}


@router.put("/{request_id}", response_model=dict)
async def update_inference_request(request_id: str, inference_request: dict):
    return {**inference_request, "id": request_id}


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inference_request(request_id: str):
    return None
