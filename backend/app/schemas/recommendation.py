from pydantic import BaseModel, Field
from typing import Any


class RecommendRequest(BaseModel):
    hotspot: dict = Field(..., description="Hotspot data dict")
    xai_explanation: dict | None = None
    budget: float | None = None
    generate_scenarios: bool = False


class RecommendBatchRequest(BaseModel):
    hotspots: list[dict] = Field(..., description="List of hotspot data dicts")
    budget: float | None = None


class RecommendationResponse(BaseModel):
    status: str = "success"
    hotspot_id: str
    hotspot_severity: str
    recommendations: list[dict]
    optimization: dict | None = None
    scenarios: list[dict] | None = None
