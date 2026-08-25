"""Analítica agregada del marketplace, vista por organización (fase 8.9).

Combina el histórico ya agregado en marketplace_metrics_daily (ayer hacia
atrás, escrito por scripts/aggregate_marketplace_metrics.py) con conteos
"hoy en vivo" calculados directamente sobre las tablas fuente — el día
corriente todavía no tiene fila agregada, y esperar al cron manual sería más
caro que calcularlo al vuelo.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import analytics as analytics_repo

PERM_READ = "analytics.read"

_HISTORY_DAYS = 30


class AnalyticsError(Exception):
    pass


class AnalyticsPermissionError(AnalyticsError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await analytics_repo.has_permission(db, organization_id, permission):
        raise AnalyticsPermissionError(f"Sin permiso ({permission}) para esta acción")


async def buyer_summary(*, user_id: UUID, organization_id: UUID) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)

        since_date = date.today() - timedelta(days=_HISTORY_DAYS)
        history = await analytics_repo.get_org_metrics(db, organization_id, since_date)

        sourcing_events_published_today = (
            await analytics_repo.count_sourcing_events_published_today(
                db, organization_id
            )
        )
        quotations_received_today = (
            await analytics_repo.count_quotations_received_today(db, organization_id)
        )

        return {
            "today": {
                "sourcing_events_published": sourcing_events_published_today,
                "quotations_received": quotations_received_today,
            },
            "last_30_days": [
                {
                    "metric_date": row.metric_date,
                    **row.metrics,
                }
                for row in history
            ],
        }


async def supplier_summary(*, user_id: UUID, organization_id: UUID) -> dict:
    async with session_for_user(user_id) as db:
        await _require(db, organization_id, PERM_READ)

        since_date = date.today() - timedelta(days=_HISTORY_DAYS)
        history = await analytics_repo.get_org_metrics(db, organization_id, since_date)

        profile_views_today = await analytics_repo.count_profile_views_today(
            db, organization_id
        )
        offering_views_today = await analytics_repo.count_offering_views_today(
            db, organization_id
        )

        return {
            "today": {
                "profile_views": profile_views_today,
                "offering_views": offering_views_today,
            },
            "last_30_days": [
                {
                    "metric_date": row.metric_date,
                    **row.metrics,
                }
                for row in history
            ],
        }
