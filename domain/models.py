from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    symbol: str
    name: str
    market: str
    sector: str
    score: float
    action: str
    reason: str
    listed: bool = True


class DashboardData(BaseModel):
    date: str
    indices: list[dict[str, Any]] = Field(default_factory=list)
    sectors: list[dict[str, Any]] = Field(default_factory=list)
    recommended_buy: list[Recommendation] = Field(default_factory=list)


class PipelineReport(BaseModel):
    date: str
    steps: list[dict[str, Any]]
    status: str


class ReplayRequest(BaseModel):
    as_of: str | None = None
    symbols: list[str] = Field(default_factory=list)
    sample_size: int = 20


class ReplayReport(BaseModel):
    as_of: str
    sample_size: int
    mae: float
    updated_weights: dict[str, float]
