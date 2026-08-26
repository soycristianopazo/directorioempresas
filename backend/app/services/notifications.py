"""Notificaciones in-app: creación, lectura y preferencias (fase 7.9).

notify_user/notify_org son el contrato público que usan otros módulos de esta
misma fase (qa, messaging, y — construidos en paralelo por otro módulo —
invitations, quotations) para avisarle a alguien que NO es quien está
ejecutando la acción actual. Por eso cada una abre su propia
session_for_system() en vez de recibir una sesión de quien llama: escribir
una notificación para un tercero es exactamente el caso de "contexto de
sistema legítimo" documentado en app/db/rls.py, y no debe depender de ni
compartir la transacción de usuario que disparó el evento de negocio.

notification_deliveries (envío por canal) no se toca desde esta fase: EMAIL
queda stub, sin proveedor externo decidido — mismo gap ya aceptado en fase
5.10/accreditation. Solo el canal IN_APP tiene efecto real hoy.
"""

from __future__ import annotations

from uuid import UUID

from app.db.rls import session_for_system, session_for_user
from app.repositories import notifications as notifications_repo

_CHANNEL_IN_APP = "IN_APP"
_VALID_CHANNELS = ("IN_APP", "EMAIL")


class NotificationError(Exception):
    pass


class NotificationPermissionError(NotificationError):
    pass


class NotificationNotFoundError(NotificationError):
    pass


class NotificationValidationError(NotificationError):
    pass


# ─── Contrato público para otros módulos (contexto de sistema) ───────────────


async def notify_user(
    *,
    recipient_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    action_url: str | None = None,
    priority: str = "NORMAL",
) -> None:
    """Notifica a un usuario puntual. Abre su propio session_for_system()."""
    async with session_for_system() as db:
        await notifications_repo.create_notification(
            db,
            recipient_id=recipient_id,
            type=type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            priority=priority,
        )


async def notify_org(
    *,
    organization_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    action_url: str | None = None,
    priority: str = "NORMAL",
) -> None:
    """Notifica a todos los miembros activos de la organización (una fila por
    miembro). Respeta notification_preferences: si existe una fila
    (user_id, 'IN_APP', type) con enabled=false, ese usuario se salta. Sin
    fila = default habilitado."""
    async with session_for_system() as db:
        member_ids = await notifications_repo.list_active_member_user_ids(
            db, organization_id
        )
        if not member_ids:
            return
        # Una sola consulta para el lote completo de miembros, y un único
        # insert masivo — antes eran hasta 2 round trips por miembro.
        disabled_ids = await notifications_repo.get_users_with_type_disabled(
            db, member_ids, _CHANNEL_IN_APP, type
        )
        recipient_ids = [m for m in member_ids if m not in disabled_ids]
        await notifications_repo.create_notifications_bulk(
            db,
            recipient_ids=recipient_ids,
            type=type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            priority=priority,
        )


# ─── Bandeja propia del usuario ───────────────────────────────────────────────


async def list_notifications(
    *, user_id: UUID, unread_only: bool = False, limit: int = 50
) -> list[dict]:
    async with session_for_user(user_id) as db:
        rows = await notifications_repo.list_notifications(
            db, user_id, unread_only=unread_only, limit=limit
        )
        return [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "body": r.body,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "action_url": r.action_url,
                "priority": r.priority,
                "read_at": r.read_at,
                "created_at": r.created_at,
            }
            for r in rows
        ]


async def mark_read(*, user_id: UUID, notification_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        rowcount = await notifications_repo.mark_read(db, user_id, notification_id)
        if rowcount == 0:
            raise NotificationNotFoundError("Notificación no encontrada")


async def mark_all_read(*, user_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        await notifications_repo.mark_all_read(db, user_id)


async def list_preferences(*, user_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        rows = await notifications_repo.list_preferences(db, user_id)
        return [
            {
                "id": r.id,
                "channel": r.channel,
                "event_type": r.event_type,
                "enabled": r.enabled,
            }
            for r in rows
        ]


async def set_preference(
    *, user_id: UUID, channel: str, event_type: str, enabled: bool
) -> None:
    if channel not in _VALID_CHANNELS:
        raise NotificationValidationError("Canal inválido")
    async with session_for_user(user_id) as db:
        await notifications_repo.upsert_preference(
            db, user_id=user_id, channel=channel, event_type=event_type, enabled=enabled
        )
