"""Router de mensajería: /api/organizations/{id}/conversations/*.

GET .../messages es el endpoint de polling (`after=<cursor ISO 8601>`) — ver
la nota de diseño en app/services/messaging.py y en
0050_conversations.sql: no hay websocket en este proyecto.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUserId
from app.schemas.messaging import (
    AttachmentOut,
    ConversationOut,
    GetOrCreateConversationRequest,
    MessageOut,
    SendMessageRequest,
)
from app.schemas.sourcing import CreatedOut
from app.services import messaging as messaging_service

router = APIRouter(
    prefix="/organizations/{organization_id}/conversations", tags=["messaging"]
)

_STATUS_BY_ERROR = {
    messaging_service.MessagingPermissionError: status.HTTP_403_FORBIDDEN,
    messaging_service.MessagingNotFoundError: status.HTTP_404_NOT_FOUND,
    messaging_service.MessagingValidationError: status.HTTP_400_BAD_REQUEST,
}


def _as_http_exception(exc: messaging_service.MessagingError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST),
        detail=str(exc),
    )


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    organization_id: UUID, user_id: CurrentUserId
) -> list[ConversationOut]:
    try:
        rows = await messaging_service.list_conversations(
            user_id=user_id, organization_id=organization_id
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc
    return [ConversationOut(**r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatedOut)
async def get_or_create_conversation(
    organization_id: UUID,
    payload: GetOrCreateConversationRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        conversation_id = await messaging_service.get_or_create_conversation(
            user_id=user_id, organization_id=organization_id, **payload.model_dump()
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=conversation_id)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    organization_id: UUID,
    conversation_id: UUID,
    user_id: CurrentUserId,
    after: str | None = Query(default=None),
) -> list[MessageOut]:
    try:
        rows = await messaging_service.list_messages(
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
            after=after,
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc
    return [MessageOut(**r) for r in rows]


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=CreatedOut,
)
async def send_message(
    organization_id: UUID,
    conversation_id: UUID,
    payload: SendMessageRequest,
    user_id: CurrentUserId,
) -> CreatedOut:
    try:
        message_id = await messaging_service.send_message(
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
            **payload.model_dump(),
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc
    return CreatedOut(id=message_id)


@router.post(
    "/{conversation_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def mark_read(
    organization_id: UUID, conversation_id: UUID, user_id: CurrentUserId
) -> None:
    try:
        await messaging_service.mark_read(
            user_id=user_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc


@router.post(
    "/{conversation_id}/attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=AttachmentOut,
)
async def add_attachment(
    organization_id: UUID,
    conversation_id: UUID,
    user_id: CurrentUserId,
    message_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> AttachmentOut:
    # conversation_id (ruta) solo da forma a la URL: el mensaje adjuntado se
    # identifica por message_id (form), igual que el contrato de
    # services.messaging.add_attachment — ver esa función para el detalle.
    content = await file.read()
    try:
        result = await messaging_service.add_attachment(
            user_id=user_id,
            organization_id=organization_id,
            message_id=message_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "archivo",
        )
    except messaging_service.MessagingError as exc:
        raise _as_http_exception(exc) from exc
    return AttachmentOut(**result)
