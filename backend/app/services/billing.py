"""Lectura de planes y suscripción propia (fase 8.10).

Delgado a propósito: sin flujo de autoservicio de cambio de plan en V1
(confirmado en alembic/sql/0071_billing_plans.sql) — subscriptions/
usage_counters se gestionan por services/entitlements.py en
session_for_system(), nunca desde aquí.
"""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_user
from app.repositories import billing as billing_repo
from app.repositories import members as members_repo


class BillingError(Exception):
    pass


class BillingPermissionError(BillingError):
    pass


async def list_plans(*, user_id: UUID) -> list:
    async with session_for_user(user_id) as db:
        return await billing_repo.list_plans(db)


async def get_my_subscription(*, user_id: UUID, organization_id: UUID):
    async with session_for_user(user_id) as db:
        membership = await members_repo.get_membership(
            db, user_id=user_id, organization_id=organization_id
        )
        if membership is None:
            raise BillingPermissionError("No perteneces a esta organización")
        return await billing_repo.get_subscription(db, organization_id)
