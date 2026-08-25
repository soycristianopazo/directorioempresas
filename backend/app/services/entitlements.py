"""Guardia de límites de plan (fase 8.10).

assert_entitlement() es el contrato público que consumen otros services
(requirements, sourcing, team) DESDE DENTRO de su propia transacción de
usuario ya abierta — por eso abre su propia session_for_system() en vez de
recibir la sesión de quien llama, mismo criterio exacto que
services/notifications.py::notify_org: verificar/incrementar el uso de la
ORGANIZACIÓN es un efecto de sistema (no depende de ni comparte la
transacción RLS-scoped del usuario que disparó la acción de negocio), y
subscriptions/usage_counters no tienen policy de escritura para app_user de
todas formas (0072) — session_for_user no podría escribir ahí aunque
quisiera.

RBAC (permission_code, verificado por cada service con has_permission)
decide SI el usuario puede intentar la acción. Este módulo decide algo
distinto: si la ORGANIZACIÓN ya se quedó sin cupo del plan. Son chequeos
independientes y ambos corren antes de mutar.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.db.rls import session_for_system
from app.repositories import billing as billing_repo

_FREE_PLAN_CODE = "FREE"
_PERIOD_TOTAL = "TOTAL"


class EntitlementExceededError(Exception):
    pass


def _period_key(limit_period: str) -> str:
    if limit_period == _PERIOD_TOTAL:
        return _PERIOD_TOTAL
    return date.today().strftime("%Y-%m")


async def assert_entitlement(organization_id: UUID, feature_code: str) -> None:
    async with session_for_system() as db:
        subscription = await billing_repo.get_subscription(db, organization_id)
        if subscription is not None:
            plan_id = subscription.plan_id
        else:
            # Sin suscripción registrada: se trata como si tuviera el plan
            # FREE implícito, en vez de fallar — una organización recién
            # creada todavía no tiene fila en subscriptions (la asigna
            # seed.py/onboarding), y eso no debe bloquear su primer uso.
            free_plan = await billing_repo.get_plan_by_code(db, _FREE_PLAN_CODE)
            if free_plan is None:
                # El catálogo de planes es una migración de datos ya
                # aplicada (0073) — si ni siquiera FREE existe, es un
                # problema de datos, no algo que debamos bloquear al
                # usuario por.
                return
            plan_id = free_plan.id

        entitlement = await billing_repo.get_entitlement(db, plan_id, feature_code)
        if entitlement is None:
            # Feature no modelada en plan_entitlements: fail-open, no
            # bloquea nada.
            return

        if entitlement.is_unlimited:
            # Se incrementa igual, para que quede historial de uso aunque
            # no haya límite que chequear.
            await billing_repo.upsert_usage_counter_increment(
                db, organization_id, feature_code, _period_key(entitlement.limit_period)
            )
            return

        period_key = _period_key(entitlement.limit_period)
        current = await billing_repo.get_usage_counter(
            db, organization_id, feature_code, period_key
        )
        current_count = current.count if current is not None else 0
        if entitlement.limit_value is None:
            # No debería pasar (0071: is_unlimited or limit_value is not
            # null), pero si el dato queda inconsistente, fail-open en vez
            # de bloquear al usuario por un problema de datos ajeno a él.
            return

        if current_count >= entitlement.limit_value:
            raise EntitlementExceededError(
                f"Límite del plan alcanzado para {feature_code}"
            )

        await billing_repo.upsert_usage_counter_increment(
            db, organization_id, feature_code, period_key
        )
