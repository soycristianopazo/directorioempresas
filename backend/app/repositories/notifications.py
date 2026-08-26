"""Acceso a datos de notificaciones in-app y preferencias (fase 7.9)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationPreference


async def list_active_member_user_ids(
    session: AsyncSession, organization_id: UUID
) -> list[UUID]:
    result = await session.execute(
        text(
            "select user_id from public.organization_members "
            "where organization_id = :org_id and status = 'ACTIVE'"
        ),
        {"org_id": str(organization_id)},
    )
    return [row[0] for row in result]


async def get_users_with_type_disabled(
    session: AsyncSession, user_ids: list[UUID], channel: str, event_type: str
) -> set[UUID]:
    """De `user_ids`, cuáles deshabilitaron `event_type` en `channel`.

    Una sola query para todo el lote en vez de `get_disabled_event_types`
    por usuario — es lo que evita el N+1 de `notify_org`.
    """
    if not user_ids:
        return set()
    result = await session.execute(
        select(NotificationPreference.user_id).where(
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
            NotificationPreference.enabled.is_(False),
        )
    )
    return set(result.scalars())


async def create_notification(session: AsyncSession, **fields: object) -> Notification:
    notification = Notification(**fields)
    session.add(notification)
    await session.flush()
    return notification


async def create_notifications_bulk(
    session: AsyncSession, *, recipient_ids: list[UUID], **fields: object
) -> None:
    """Un solo `flush()` para todos los destinatarios, en vez de uno por
    fila — así `notify_org` no paga un round trip por miembro."""
    if not recipient_ids:
        return
    session.add_all(
        Notification(recipient_id=recipient_id, **fields) for recipient_id in recipient_ids
    )
    await session.flush()


async def list_notifications(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    # Sin limit acá, GET /api/notifications (la campanita, disparada en cada
    # carga de página) devolvía el historial completo del usuario — crece sin
    # tope con el tiempo. El índice notifications_recipient_idx (recipient_id,
    # created_at desc, ver 0051_notifications.sql) ya está pensado para este
    # order_by + limit.
    stmt = select(Notification).where(Notification.recipient_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars())


async def mark_read(session: AsyncSession, user_id: UUID, notification_id: UUID) -> int:
    """UPDATE idempotente: si ya estaba leída, conserva el read_at original
    pero igual cuenta como fila afectada (rowcount > 0) siempre que la
    notificación exista y pertenezca al usuario — eso es lo que el caller usa
    para distinguir "no encontrada / no visible" de "ya estaba leída"."""
    result = await session.execute(
        text(
            "update public.notifications set read_at = coalesce(read_at, now()) "
            "where id = :id and recipient_id = :user_id"
        ),
        {"id": str(notification_id), "user_id": str(user_id)},
    )
    return result.rowcount  # type: ignore[attr-defined]


async def mark_all_read(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text(
            "update public.notifications set read_at = now() "
            "where recipient_id = :user_id and read_at is null"
        ),
        {"user_id": str(user_id)},
    )


async def list_preferences(
    session: AsyncSession, user_id: UUID
) -> list[NotificationPreference]:
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return list(result.scalars())


async def upsert_preference(
    session: AsyncSession,
    *,
    user_id: UUID,
    channel: str,
    event_type: str,
    enabled: bool,
) -> None:
    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
        )
    )
    preference = result.scalar_one_or_none()
    if preference is None:
        session.add(
            NotificationPreference(
                user_id=user_id, channel=channel, event_type=event_type, enabled=enabled
            )
        )
    else:
        preference.enabled = enabled
    await session.flush()
