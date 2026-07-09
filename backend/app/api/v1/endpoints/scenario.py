import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

from app.scenario import (
    ScenarioEngine, ScenarioNotFoundError, InvalidParameterError,
    list_templates, get_template,
)
from app.schemas.scenario import (
    ScenarioRunRequest, ScenarioCompareRequest, ScenarioRunAllRequest,
)

router = APIRouter()


def _to_numpy(X: list[list[float]]) -> np.ndarray:
    return np.array(X, dtype=np.float64)


def _build_dummy_model(X: np.ndarray, y: np.ndarray | None):
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    if y is not None:
        model.fit(X, y)
    return model


@router.get("/templates", response_model=dict)
async def list_scenario_templates(category: str | None = None):
    templates = list_templates(category)
    return {
        "status": "success",
        "templates": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "cost_per_hectare": t.cost_per_hectare,
                "co2_reduction_factor": t.co2_reduction_factor,
                "features_affected": list(t.feature_modifiers.keys()),
            }
            for t in templates
        ],
    }


@router.get("/templates/{name}", response_model=dict)
async def get_scenario_template(name: str):
    try:
        t = get_template(name)
        return {
            "status": "success",
            "template": {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "cost_per_hectare": t.cost_per_hectare,
                "co2_reduction_factor": t.co2_reduction_factor,
                "default_parameters": t.default_parameters,
                "feature_modifiers": {
                    k: {mk: mv for mk, mv in v.items() if mk != "idx"}
                    for k, v in t.feature_modifiers.items()
                },
            },
        }
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template '{name}' not found")


@router.post("/run", response_model=dict)
async def run_scenario(req: ScenarioRunRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y) if req.y else None
        model = _build_dummy_model(X, y)
        engine = ScenarioEngine()
        result = engine.run_scenario(
            req.scenario_name, X, y, req.feature_names, model,
            intensity=req.intensity, area_ha=req.area_ha,
        )
        return {"status": "success", "result": result.to_dict()}
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidParameterError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/compare", response_model=dict)
async def compare_scenarios(req: ScenarioCompareRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y) if req.y else None
        model = _build_dummy_model(X, y)
        engine = ScenarioEngine()
        results, report = engine.run_multiple(
            req.scenario_names, X, y, req.feature_names, model,
            area_ha=req.area_ha, compare=True,
        )
        return {
            "status": "success",
            "results": [r.to_dict() for r in results],
            "comparison": report.to_dict(),
        }
    except ScenarioNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/run-all", response_model=dict)
async def run_all_scenarios(req: ScenarioRunAllRequest):
    try:
        X = _to_numpy(req.X)
        y = np.array(req.y) if req.y else None
        model = _build_dummy_model(X, y)
        engine = ScenarioEngine()
        results, report = engine.run_all(
            X, y, req.feature_names, model, area_ha=req.area_ha,
        )
        return {
            "status": "success",
            "results": [r.to_dict() for r in results],
            "comparison": report.to_dict() if report else None,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
