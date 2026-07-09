from fastapi import APIRouter, Depends, HTTPException, status

from app.recommendation import (
    RecommenderEngine, InvalidHotspotError, NoRecommendationsError,
)
from app.recommendation import RecommendationBundle
from app.schemas.recommendation import (
    RecommendRequest, RecommendBatchRequest, RecommendationResponse,
)

router = APIRouter()


def _make_hotspot(data: dict):
    return type("Hotspot", (), {
        "id": data.get("id", "unknown"),
        "severity": data.get("severity", "moderate"),
        "dominant_landcover": data.get("dominant_landcover", "Builtup"),
        "mean_ndvi": data.get("mean_ndvi", 0.0),
        "mean_ndbi": data.get("mean_ndbi", 0.0),
        "mean_ndwi": data.get("mean_ndwi", 0.0),
        "vegetation_fraction": data.get("vegetation_fraction", 0.0),
        "builtup_fraction": data.get("builtup_fraction", 0.0),
        "area_sq_km": data.get("area_sq_km", 0.0),
        "mean_temperature_c": data.get("mean_temperature_c", 0.0),
        "max_temperature_c": data.get("max_temperature_c", 0.0),
        "min_temperature_c": data.get("min_temperature_c", 0.0),
        "pixel_count": data.get("pixel_count", 0),
        "confidence": data.get("confidence", 0.5),
        "quality_metrics": data.get("quality_metrics", {}),
    })


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(req: RecommendRequest):
    try:
        engine = RecommenderEngine()
        hotspot = _make_hotspot(req.hotspot)
        xai_obj = None
        if req.xai_explanation:
            xai_obj = type("XAIResult", (), {"summary": lambda self=None: req.xai_explanation})()
        bundle = engine.recommend(hotspot, xai_explanation=xai_obj,
                                   budget=req.budget,
                                   generate_scenarios_list=req.generate_scenarios)
        return RecommendationResponse(
            hotspot_id=bundle.hotspot_id,
            hotspot_severity=bundle.hotspot_severity,
            recommendations=[r.to_dict() for r in bundle.recommendations],
            optimization=bundle.optimization.to_dict() if bundle.optimization else None,
            scenarios=[s.to_dict() for s in bundle.scenarios] if bundle.scenarios else None,
        )
    except InvalidHotspotError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NoRecommendationsError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/generate-batch", response_model=dict)
async def generate_recommendations_batch(req: RecommendBatchRequest):
    try:
        engine = RecommenderEngine()
        hotspots = [_make_hotspot(h) for h in req.hotspots]
        bundles = engine.recommend_batch(hotspots, budget=req.budget)
        return {
            "status": "success",
            "results": [
                {
                    "hotspot_id": b.hotspot_id,
                    "hotspot_severity": b.hotspot_severity,
                    "recommendations": [r.to_dict() for r in b.recommendations],
                }
                for b in bundles
            ],
        }
    except InvalidHotspotError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=dict)
async def read_recommendations(skip: int = 0, limit: int = 100):
    return {"status": "ok", "message": "Recommendation API ready", "endpoints": ["generate", "generate-batch"]}


@router.get("/{rec_id}", response_model=dict)
async def read_recommendation(rec_id: str):
    return {"id": rec_id, "message": "Recommendation API ready"}


@router.post("/", response_model=dict)
async def create_recommendation(recommendation: dict):
    return {**recommendation, "id": "pending"}


@router.put("/{rec_id}", response_model=dict)
async def update_recommendation(rec_id: str, recommendation: dict):
    return {**recommendation, "id": rec_id}


@router.delete("/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recommendation(rec_id: str):
    return None
