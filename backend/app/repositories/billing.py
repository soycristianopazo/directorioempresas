"""Acceso a datos de planes, entitlements, suscripciones y contadores de uso
(fase 8.10)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Plan, PlanEntitlement, Subscription, UsageCounter


async def list_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
    )
    return list(result.scalars())


async def get_plan_by_code(session: AsyncSession, code: str) -> Plan | None:
    result = await session.execute(select(Plan).where(Plan.code == code))
    return result.scalar_one_or_none()


async def get_subscription(
    session: AsyncSession, organization_id: UUID
) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def create_subscription(session: AsyncSession, **fields: object) -> Subscription:
    subscription = Subscription(**fields)
    session.add(subscription)
    await session.flush()
    return subscription


async def get_entitlement(
    session: AsyncSession, plan_id: UUID, feature_code: str
) -> PlanEntitlement | None:
    result = await session.execute(
        select(PlanEntitlement).where(
            PlanEntitlement.plan_id == plan_id,
            PlanEntitlement.feature_code == feature_code,
        )
    )
    return result.scalar_one_or_none()


async def get_usage_counter(
    session: AsyncSession, organization_id: UUID, feature_code: str, period_key: str
) -> UsageCounter | None:
    result = await session.execute(
        select(UsageCounter).where(
            UsageCounter.organization_id == organization_id,
            UsageCounter.feature_code == feature_code,
            UsageCounter.period_key == period_key,
        )
    )
    return result.scalar_one_or_none()


async def upsert_usage_counter_increment(
    session: AsyncSession, organization_id: UUID, feature_code: str, period_key: str
) -> int:
    """Incrementa el contador de forma atómica (insert-o-suma-1 en una sola
    sentencia) — mismo criterio de atomicidad que la secuencia real de
    alembic/sql/0053_sourcing_event_code_seq.sql: un leer-luego-escribir en
    dos pasos deja una ventana de condición de carrera entre dos requests
    concurrentes del mismo feature_code/periodo, y "on conflict do update"
    resuelve eso en una sola operación en el servidor."""
    result = await session.execute(
        text(
            """
            insert into public.usage_counters
                (organization_id, feature_code, period_key, count)
            values
                (:org_id, :feature, :period, 1)
            on conflict (organization_id, feature_code, period_key)
            do update set count = usage_counters.count + 1, updated_at = now()
            returning count
            """
        ),
        {
            "org_id": str(organization_id),
            "feature": feature_code,
            "period": period_key,
        },
    )
    return int(result.scalar_one())
