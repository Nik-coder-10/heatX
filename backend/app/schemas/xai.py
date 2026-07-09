from pydantic import BaseModel, Field
from typing import Any


class ExplainRequest(BaseModel):
    X: list[list[float]] = Field(..., description="Features to explain")
    y: list[float] | None = None
    feature_names: list[str] | None = None
    method: str = Field(default="shap", description="Explanation method: shap, permutation, tree")
    compute_global: bool = True
    compute_local: bool = True
    compute_counterfactual: bool = False
    compute_confidence: bool = True
    compute_uncertainty: bool = False


class ExplainHotspotRequest(BaseModel):
    hotspot: dict = Field(..., description="Hotspot data dict")
    X: list[list[float]] = Field(..., description="Feature matrix")
    feature_names: list[str]
    target_reduction: float = Field(default=2.0, description="Target temperature reduction")
