"""Acceso a datos de analítica agregada (fase 8.9).

marketplace_metrics_daily solo cubre "ayer hacia atrás" — el día corriente
se calcula en vivo aquí mismo, con queries directas a las tablas fuente,
porque es más barato que esperar al cron manual de
scripts/aggregate_marketplace_metrics.py. Ver el comentario de esa tabla en
alembic/sql/0069_marketplace_metrics.sql.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import MarketplaceMetricsDaily


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def get_org_metrics(
    session: AsyncSession, organization_id: UUID, since_date: date
) -> list[MarketplaceMetricsDaily]:
    result = await session.execute(
        select(MarketplaceMetricsDaily)
        .where(
            MarketplaceMetricsDaily.dimension == "organization",
            MarketplaceMetricsDaily.dimension_id == organization_id,
            MarketplaceMetricsDaily.metric_date >= since_date,
        )
        .order_by(MarketplaceMetricsDaily.metric_date)
    )
    return list(result.scalars())


# ─── "Hoy en vivo": lado comprador ────────────────────────────────────────────


async def count_sourcing_events_published_today(
    session: AsyncSession, organization_id: UUID
) -> int:
    result = await session.execute(
        text(
            "select count(*) from public.sourcing_events "
            "where organization_id = :org_id "
            "and published_at::date = current_date"
        ),
        {"org_id": str(organization_id)},
    )
    return int(result.scalar_one())


async def count_quotations_received_today(
    session: AsyncSession, organization_id: UUID
) -> int:
    result = await session.execute(
        text(
            "select count(*) from public.quotations q "
            "join public.sourcing_events se on se.id = q.sourcing_event_id "
            "where se.organization_id = :org_id "
            "and q.first_submitted_at::date = current_date"
        ),
        {"org_id": str(organization_id)},
    )
    return int(result.scalar_one())


# ─── "Hoy en vivo": lado proveedor ────────────────────────────────────────────


async def count_profile_views_today(
    session: AsyncSession, organization_id: UUID
) -> int:
    result = await session.execute(
        text(
            "select count(*) from public.profile_views "
            "where organization_id = :org_id "
            "and created_at::date = current_date"
        ),
        {"org_id": str(organization_id)},
    )
    return int(result.scalar_one())


async def count_offering_views_today(
    session: AsyncSession, organization_id: UUID
) -> int:
    result = await session.execute(
        text(
            "select count(*) from public.offering_views "
            "where organization_id = :org_id "
            "and created_at::date = current_date"
        ),
        {"org_id": str(organization_id)},
    )
    return int(result.scalar_one())
