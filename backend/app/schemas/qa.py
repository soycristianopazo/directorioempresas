"""Esquemas de preguntas y respuestas del evento de sourcing (fase 7.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

QaVisibility = Literal["PRIVATE_TO_ASKER", "ALL_PARTICIPANTS"]


class AskQuestionRequest(BaseModel):
    body: str = Field(min_length=2, max_length=4000)


class AnswerQuestionRequest(BaseModel):
    body: str = Field(min_length=2, max_length=4000)
    visibility: QaVisibility = "ALL_PARTICIPANTS"


class QuestionOut(BaseModel):
    id: UUID
    sourcing_event_id: UUID
    asked_by_organization_id: UUID
    asked_by: UUID | None
    body: str
    is_answered: bool
    asked_at: datetime
    answer_id: UUID | None
    answer_body: str | None
    answer_visibility: QaVisibility | None
    answered_by: UUID | None
    answered_at: datetime | None
    published_at: datetime | None
