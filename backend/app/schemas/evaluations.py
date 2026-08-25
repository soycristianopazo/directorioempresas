"""Esquemas de plantillas, comité y evaluaciones (fase 8.1-8.4)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CriterionIn(BaseModel):
    dimension: str
    name: str
    description: str | None = None
    weight: float = 1
    sort_order: int = 0


class CreateTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    criteria: list[CriterionIn]


class ApplyTemplateRequest(BaseModel):
    template_id: UUID


class AssignmentIn(BaseModel):
    organization_member_id: UUID
    dimension: str
    can_view_commercial: bool = False


class AssignCommitteeRequest(BaseModel):
    assignments: list[AssignmentIn]


class SubmitScoreRequest(BaseModel):
    quotation_id: UUID
    evaluation_criterion_id: UUID
    score: float
    comment: str | None = None
    evidence_document_id: UUID | None = None


class SubmitEvaluationRequest(BaseModel):
    quotation_id: UUID
    overall_comment: str | None = None
