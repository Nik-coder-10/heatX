from pydantic import BaseModel, Field
from typing import Any


class ScenarioRunRequest(BaseModel):
    scenario_name: str = Field(..., description="Name of the scenario template")
    X: list[list[float]] = Field(..., description="Feature matrix")
    y: list[float] | None = None
    feature_names: list[str]
    intensity: float = Field(default=1.0, ge=0.0, le=2.0)
    area_ha: float = 1.0


class ScenarioCompareRequest(BaseModel):
    scenario_names: list[str] = Field(..., min_length=2)
    X: list[list[float]]
    y: list[float] | None = None
    feature_names: list[str]
    area_ha: float = 1.0


class ScenarioRunAllRequest(BaseModel):
    X: list[list[float]]
    y: list[float] | None = None
    feature_names: list[str]
    area_ha: float = 1.0
