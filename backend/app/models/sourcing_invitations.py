"""Invitaciones a proveedores y su historial de estado (fase 7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SourcingInvitationStatusEnum = ENUM(
    "INVITED",
    "VIEWED",
    "NDA_ACCEPTED",
    "INTERESTED",
    "PARTICIPATING",
    "QUOTED",
    "DECLINED",
    "NO_RESPONSE",
    "WITHDRAWN",
    "DISQUALIFIED",
    "EXPIRED",
    # Agregados por 0065 (fase 8.7) al tipo de Postgres — nunca se agregaron
    # acá. Bug real encontrado en vivo: SQLAlchemy valida cada valor leído
    # contra ESTA lista de Python, no contra el tipo real de la base, así
    # que cualquier fila con uno de estos cuatro estados (negociación o
    # cierre de evento con adjudicación) reventaba con
    # "LookupError: 'NEGOTIATING' is not among the defined enum values" al
    # leerla — no al escribirla, que pasa por SQL crudo y nunca pasó por
    # esta validación.
    "SHORTLISTED",
    "NEGOTIATING",
    "AWARDED",
    "NOT_AWARDED",
    name="sourcing_invitation_status",
    schema="app",
    create_type=False,
)
SourcingInvitationSourceEnum = ENUM(
    "MATCH",
    "MANUAL",
    "LIST",
    "PUBLIC_APPLY",
    name="sourcing_invitation_source",
    schema="app",
    create_type=False,
)


class SourcingEventInvitation(Base):
    __tablename__ = "sourcing_event_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sourcing_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sourcing_events.id", ondelete="CASCADE")
    )
    supplier_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    status: Mapped[str] = mapped_column(
        SourcingInvitationStatusEnum, nullable=False, server_default="INVITED"
    )
    source: Mapped[str] = mapped_column(
        SourcingInvitationSourceEnum, nullable=False, server_default="MANUAL"
    )
    match_score_snapshot: Mapped[float | None] = mapped_column(Numeric)

    invited_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    viewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    decline_reason_code: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )


class InvitationStatusHistory(Base):
    __tablename__ = "invitation_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    invitation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_event_invitations.id", ondelete="CASCADE"),
    )
    from_status: Mapped[str | None] = mapped_column(SourcingInvitationStatusEnum)
    to_status: Mapped[str] = mapped_column(SourcingInvitationStatusEnum, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
