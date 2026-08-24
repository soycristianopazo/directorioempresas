"""Esquemas del motor de matching (fase 6.4-6.7)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RunMatchingRequest(BaseModel):
    weights: dict[str, float] | None = None


class MatchResultOut(BaseModel):
    offering_id: UUID
    organization_id: UUID
    total_score: float
    is_eligible: bool
    blocking_reasons: list[str]
    score_breakdown: dict
    rank: int | None = None


class RunMatchingResponse(BaseModel):
    match_run_id: UUID | None = None
    engine_version: str
    weights: dict[str, float]
    candidates_evaluated: int
    eligible_count: int
    duration_ms: int
    results: list[MatchResultOut]


class MatchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    engine_version: str
    weights_snapshot: dict
    candidates_evaluated: int
    eligible_count: int
    duration_ms: int
    executed_at: datetime


class LatestResultsOut(BaseModel):
    run: MatchRunOut
    results: list[MatchResultOut]
