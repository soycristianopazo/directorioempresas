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

from app.core import cache
from app.db.rls import gather_for_user, session_for_user
from app.repositories import analytics as analytics_repo

PERM_READ = "analytics.read"

_HISTORY_DAYS = 30
# TTL corto a propósito: son contadores "hoy en vivo" (eventos publicados,
# cotizaciones recibidas, vistas de perfil/oferta) que cambian por
# escrituras de OTROS módulos (sourcing, quotations, search) — invalidar
# desde cada uno de esos call sites sería frágil y disperso. 30s de
# staleness es aceptable para un panel de analítica, no para un dato
# transaccional.
_SUMMARY_CACHE_TTL_SECONDS = 30
_SUMMARY_DENIED = object()


class AnalyticsError(Exception):
    pass


class AnalyticsPermissionError(AnalyticsError):
    pass


async def _require(db, organization_id: UUID, permission: str) -> None:
    if not await analytics_repo.has_permission(db, organization_id, permission):
        raise AnalyticsPermissionError(f"Sin permiso ({permission}) para esta acción")


async def buyer_summary(*, user_id: UUID, organization_id: UUID) -> dict:
    cache_key = f"buyer_summary:{organization_id}:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        if cached is _SUMMARY_DENIED:
            raise AnalyticsPermissionError(
                f"Sin permiso ({PERM_READ}) para esta acción"
            )
        return cached

    async with session_for_user(user_id) as db:
        if not await analytics_repo.has_permission(db, organization_id, PERM_READ):
            cache.set(
                cache_key, _SUMMARY_DENIED, ttl_seconds=_SUMMARY_CACHE_TTL_SECONDS
            )
            raise AnalyticsPermissionError(
                f"Sin permiso ({PERM_READ}) para esta acción"
            )

    # Las tres lecturas son independientes entre sí (ninguna usa el
    # resultado de otra) — van en paralelo, cada una en su propia conexión,
    # una vez pasado el gate de permiso.
    since_date = date.today() - timedelta(days=_HISTORY_DAYS)
    (
        history,
        sourcing_events_published_today,
        quotations_received_today,
    ) = await gather_for_user(
        user_id,
        lambda db: analytics_repo.get_org_metrics(db, organization_id, since_date),
        lambda db: analytics_repo.count_sourcing_events_published_today(
            db, organization_id
        ),
        lambda db: analytics_repo.count_quotations_received_today(db, organization_id),
    )

    result = {
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
    cache.set(cache_key, result, ttl_seconds=_SUMMARY_CACHE_TTL_SECONDS)
    return result


async def supplier_summary(*, user_id: UUID, organization_id: UUID) -> dict:
    cache_key = f"supplier_summary:{organization_id}:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        if cached is _SUMMARY_DENIED:
            raise AnalyticsPermissionError(
                f"Sin permiso ({PERM_READ}) para esta acción"
            )
        return cached

    async with session_for_user(user_id) as db:
        if not await analytics_repo.has_permission(db, organization_id, PERM_READ):
            cache.set(
                cache_key, _SUMMARY_DENIED, ttl_seconds=_SUMMARY_CACHE_TTL_SECONDS
            )
            raise AnalyticsPermissionError(
                f"Sin permiso ({PERM_READ}) para esta acción"
            )

    since_date = date.today() - timedelta(days=_HISTORY_DAYS)
    history, profile_views_today, offering_views_today = await gather_for_user(
        user_id,
        lambda db: analytics_repo.get_org_metrics(db, organization_id, since_date),
        lambda db: analytics_repo.count_profile_views_today(db, organization_id),
        lambda db: analytics_repo.count_offering_views_today(db, organization_id),
    )

    result = {
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
    cache.set(cache_key, result, ttl_seconds=_SUMMARY_CACHE_TTL_SECONDS)
    return result
