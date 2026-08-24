"""Preguntas y respuestas del evento (fase 7.4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SourcingAnswerVisibilityEnum = ENUM(
    "PRIVATE_TO_ASKER",
    "ALL_PARTICIPANTS",
    name="sourcing_answer_visibility",
    schema="app",
    create_type=False,
)


class SourcingQuestion(Base):
    __tablename__ = "sourcing_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    asked_by_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    asked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_answered: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    asked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class SourcingAnswer(Base):
    __tablename__ = "sourcing_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_questions.id", ondelete="CASCADE")
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(
        SourcingAnswerVisibilityEnum, nullable=False, server_default="ALL_PARTICIPANTS"
    )
    answered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    answered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
