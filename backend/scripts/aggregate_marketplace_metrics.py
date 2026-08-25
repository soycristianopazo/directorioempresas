"""Agrega las métricas del día anterior en marketplace_metrics_daily
(fase 8.9).

Job manual — no hay scheduler/cron real en este stack todavía (mismo
criterio que scripts/reindex_search.py). Se corre a mano una vez al día
(o las veces que haga falta: el upsert es idempotente).

Calcula, para el día `date.today() - timedelta(days=1)`:
  · una fila por organización activa (dimension='organization'), con las
    cuatro métricas combinadas de lado comprador y lado proveedor.
  · una fila 'global' (dimension_id NULL) con los totales del marketplace,
    sin filtrar por organizaciones activas — es el pulso real de la
    plataforma, no solo el de las organizaciones que hoy están ACTIVE.

Nota de idempotencia: la fila 'global' tiene dimension_id NULL, y el
constraint UNIQUE (metric_date, dimension, dimension_id) de Postgres NO
trata dos NULL como iguales — así que un ON CONFLICT normal nunca detecta
esa fila como duplicada en una segunda corrida del mismo día. Para las filas
'organization' (dimension_id siempre no-nulo) el ON CONFLICT funciona tal
cual. Para la fila 'global' se hace un DELETE previo del mismo metric_date
antes del INSERT, logrando el mismo resultado idempotente sin tocar la
migración ya aplicada.

Uso:
    cd backend && source .venv/bin/activate && python scripts/aggregate_marketplace_metrics.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

from sqlalchemy import text

from app.db.rls import session_for_system

_UPSERT_ORG_SQL = text(
    """
    insert into public.marketplace_metrics_daily
        (metric_date, dimension, dimension_id, metrics)
    values
        (:metric_date, 'organization', :dimension_id, cast(:metrics as jsonb))
    on conflict (metric_date, dimension, dimension_id)
    do update set metrics = excluded.metrics, computed_at = now()
    """
)

_DELETE_GLOBAL_SQL = text(
    """
    delete from public.marketplace_metrics_daily
    where metric_date = :metric_date and dimension = 'global'
    """
)

_INSERT_GLOBAL_SQL = text(
    """
    insert into public.marketplace_metrics_daily
        (metric_date, dimension, dimension_id, metrics)
    values
        (:metric_date, 'global', null, cast(:metrics as jsonb))
    """
)


async def _grouped_counts(db, sql: str, target_date: date) -> dict[str, int]:
    result = await db.execute(text(sql), {"d": target_date})
    return {str(org_id): count for org_id, count in result.all()}


async def main() -> None:
    target_date = date.today() - timedelta(days=1)
    print(f"Agregando métricas de marketplace para {target_date}…")

    async with session_for_system() as db:
        active_org_ids = [
            str(row[0])
            for row in (
                await db.execute(
                    text("select id from public.organizations where status = 'ACTIVE'")
                )
            ).all()
        ]

        sourcing_events_by_org = await _grouped_counts(
            db,
            """
            select organization_id, count(*)
            from public.sourcing_events
            where published_at::date = :d
            group by organization_id
            """,
            target_date,
        )
        quotations_by_org = await _grouped_counts(
            db,
            """
            select se.organization_id, count(*)
            from public.quotations q
            join public.sourcing_events se on se.id = q.sourcing_event_id
            where q.first_submitted_at::date = :d
            group by se.organization_id
            """,
            target_date,
        )
        profile_views_by_org = await _grouped_counts(
            db,
            """
            select organization_id, count(*)
            from public.profile_views
            where created_at::date = :d
            group by organization_id
            """,
            target_date,
        )
        offering_views_by_org = await _grouped_counts(
            db,
            """
            select organization_id, count(*)
            from public.offering_views
            where created_at::date = :d
            group by organization_id
            """,
            target_date,
        )

        for org_id in active_org_ids:
            metrics = {
                "sourcing_events_published": sourcing_events_by_org.get(org_id, 0),
                "quotations_received": quotations_by_org.get(org_id, 0),
                "profile_views": profile_views_by_org.get(org_id, 0),
                "offering_views": offering_views_by_org.get(org_id, 0),
            }
            await db.execute(
                _UPSERT_ORG_SQL,
                {
                    "metric_date": target_date,
                    "dimension_id": org_id,
                    "metrics": json.dumps(metrics),
                },
            )

        global_metrics = {
            "sourcing_events_published": sum(sourcing_events_by_org.values()),
            "quotations_received": sum(quotations_by_org.values()),
            "profile_views": sum(profile_views_by_org.values()),
            "offering_views": sum(offering_views_by_org.values()),
            "active_organizations": len(active_org_ids),
        }
        await db.execute(_DELETE_GLOBAL_SQL, {"metric_date": target_date})
        await db.execute(
            _INSERT_GLOBAL_SQL,
            {"metric_date": target_date, "metrics": json.dumps(global_metrics)},
        )

    print(
        f"✓ {len(active_org_ids)} organizaciones + 1 fila global agregadas "
        f"para {target_date}."
    )


if __name__ == "__main__":
    asyncio.run(main())
