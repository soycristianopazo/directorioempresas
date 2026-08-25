"""Analítica agregada del marketplace (fase 8.9)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MarketplaceMetricsDaily(Base):
    __tablename__ = "marketplace_metrics_daily"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    dimension_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
