"""Mensajería: conversaciones, mensajes y adjuntos por hilo con contexto
tipado (fase 7.8).

Ser participante ES el criterio de acceso — no hay permiso de recurso de por
medio, RLS ya lo resuelve (Patrón F, ver 0052_fase7_rls_messaging_notifications.sql).
El service revalida la membresía en las escrituras solo para devolver un
error de negocio legible en vez de la violación de policy genérica, mismo
criterio que qa.py con la invitación activa.

Actualizaciones en vivo por POLLING (decisión de fase 7, no de este módulo):
GET .../messages?after=<cursor> devuelve solo lo nuevo, sin websocket ni tarea
de fondo.

Adjuntos: misma secuencia que services/documents.py (permiso -> subida a
Storage -> checksum -> commit -> URL firmada generada DESPUÉS de cerrar la
transacción con RLS), mismo bucket privado único de este proyecto
(org-documents).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from uuid import UUID, uuid4

from app.core.file_validation import matches_declared_image_type, matches_pdf
from app.core.storage import StorageError, create_signed_url, upload_object
from app.db.rls import session_for_user
from app.repositories import messaging as messaging_repo
from app.services import notifications as notifications_service

ATTACHMENTS_BUCKET = "org-documents"
_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = ("application/pdf", "image/png", "image/jpeg")


class MessagingError(Exception):
    pass


class MessagingPermissionError(MessagingError):
    pass


class MessagingNotFoundError(MessagingError):
    pass


class MessagingValidationError(MessagingError):
    pass


async def _require_participant(
    db, conversation_id: UUID, organization_id: UUID
) -> None:
    if not await messaging_repo.is_participant(db, conversation_id, organization_id):
        raise MessagingPermissionError(
            "Solo un participante del hilo puede realizar esta acción"
        )


async def get_or_create_conversation(
    *,
    user_id: UUID,
    organization_id: UUID,
    context_type: str,
    context_id: UUID,
    participant_organization_ids: list[UUID],
) -> UUID:
    async with session_for_user(user_id) as db:
        conversation_id = await messaging_repo.find_conversation_by_context(
            db, context_type=context_type, context_id=context_id
        )
        if conversation_id is None:
            conversation_id = await messaging_repo.create_conversation(
                db,
                context_type=context_type,
                context_id=context_id,
                created_by_organization_id=organization_id,
                created_by=user_id,
            )
        # add_participant es upsert (on conflict do nothing) — se llama
        # siempre, no solo al crear: find_conversation_by_context matchea
        # por (context_type, context_id) sin mirar quién ya participa, así
        # que una conversación ORGANIZATION encontrada (no creada por mí)
        # podía devolverse sin que el propio caller quedara como
        # participante — el siguiente listMessages/sendMessage fallaba con
        # 403 "solo un participante puede...". Bug preexistente, encontrado
        # en vivo probando la bandeja de Chat nueva.
        await messaging_repo.add_participant(
            db, conversation_id=conversation_id, organization_id=organization_id
        )
        for participant_org_id in participant_organization_ids:
            if participant_org_id == organization_id:
                continue
            await messaging_repo.add_participant(
                db, conversation_id=conversation_id, organization_id=participant_org_id
            )
    return conversation_id


async def list_conversations(*, user_id: UUID, organization_id: UUID) -> list[dict]:
    async with session_for_user(user_id) as db:
        return await messaging_repo.list_conversations(db, organization_id)


async def list_messages(
    *,
    user_id: UUID,
    organization_id: UUID,
    conversation_id: UUID,
    after: str | None,
) -> list[dict]:
    after_dt: datetime | None = None
    if after:
        try:
            after_dt = datetime.fromisoformat(after)
        except ValueError as exc:
            raise MessagingValidationError(
                "El parámetro 'after' debe ser una fecha ISO 8601 válida"
            ) from exc

    async with session_for_user(user_id) as db:
        await _require_participant(db, conversation_id, organization_id)
        return await messaging_repo.list_messages(db, conversation_id, after=after_dt)


async def send_message(
    *, user_id: UUID, organization_id: UUID, conversation_id: UUID, body: str
) -> UUID:
    async with session_for_user(user_id) as db:
        await _require_participant(db, conversation_id, organization_id)
        message_id = await messaging_repo.create_message(
            db,
            conversation_id=conversation_id,
            sender_id=user_id,
            sender_organization_id=organization_id,
            body=body,
        )
        other_org_ids = await messaging_repo.list_other_participant_org_ids(
            db, conversation_id, organization_id
        )

    # Cada notify_org abre su propia sesión de sistema (ver el docstring de
    # notify_org) — son transacciones independientes entre sí, así que
    # avisar a varias organizaciones participantes va en paralelo.
    await asyncio.gather(
        *(
            notifications_service.notify_org(
                organization_id=other_org_id,
                type="message.received",
                title="Nuevo mensaje",
                body=body[:100],
                entity_type="conversation",
                entity_id=conversation_id,
                action_url=f"/empresa/mensajes?conversationId={conversation_id}",
            )
            for other_org_id in other_org_ids
        )
    )
    return message_id


async def mark_read(
    *, user_id: UUID, organization_id: UUID, conversation_id: UUID
) -> None:
    async with session_for_user(user_id) as db:
        await _require_participant(db, conversation_id, organization_id)
        await messaging_repo.touch_last_read(
            db, conversation_id=conversation_id, organization_id=organization_id
        )
        await messaging_repo.mark_messages_read(
            db, conversation_id=conversation_id, reader_id=user_id
        )


async def add_attachment(
    *,
    user_id: UUID,
    organization_id: UUID,
    message_id: UUID,
    content: bytes,
    content_type: str,
    filename: str,
) -> dict:
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise MessagingValidationError(f"Tipo de archivo no soportado: {content_type}")
    if len(content) > _MAX_ATTACHMENT_BYTES:
        raise MessagingValidationError("El archivo supera el máximo de 20 MB")

    if content_type == "application/pdf":
        content_ok = matches_pdf(content)
    else:
        content_ok = matches_declared_image_type(content, content_type)
    if not content_ok:
        raise MessagingValidationError(
            "El contenido del archivo no coincide con el tipo declarado"
        )

    async with session_for_user(user_id) as db:
        message = await messaging_repo.get_message(db, message_id)
        if message is None:
            raise MessagingNotFoundError("Mensaje no encontrado")
        if message["sender_organization_id"] != organization_id:
            raise MessagingPermissionError(
                "Solo la organización que envió el mensaje puede adjuntar archivos"
            )

        conversation_id = message["conversation_id"]
        slug = filename.replace(" ", "-")
        storage_path = f"{organization_id}/messages/{conversation_id}/{uuid4()}_{slug}"
        try:
            await upload_object(
                bucket=ATTACHMENTS_BUCKET,
                path=storage_path,
                content=content,
                content_type=content_type,
            )
        except StorageError as exc:
            raise MessagingError(str(exc)) from exc

        checksum = hashlib.sha256(content).hexdigest()
        attachment_id = await messaging_repo.create_attachment(
            db,
            message_id=message_id,
            name=filename,
            storage_path=storage_path,
            checksum_sha256=checksum,
        )
        path = storage_path

    try:
        url = await create_signed_url(
            bucket=ATTACHMENTS_BUCKET, path=path, expires_in=3600
        )
    except StorageError:
        url = None
    return {"id": attachment_id, "url": url}
