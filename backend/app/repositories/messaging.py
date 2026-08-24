"""Acceso a datos de mensajería: conversaciones, participantes, mensajes,
adjuntos y lecturas (fase 7.8).

Ver actualizaciones en vivo por POLLING (0050_conversations.sql): no hay
websocket ni tarea de fondo en este módulo, list_messages es la única
consulta que el frontend repite con un cursor `after`.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# context_type -> columna FK real en conversations. Nunca un id polimórfico
# ciego (0050_conversations.sql) — el mapeo vive acá porque es el único lugar
# que arma SQL dinámico a partir de él, y las claves son un conjunto cerrado
# que ya validó el schema Pydantic antes de llegar (Literal), no un valor
# arbitrario del cliente.
_CONTEXT_COLUMN = {
    "ORGANIZATION": "organization_id",
    "OFFERING": "offering_id",
    "REQUIREMENT": "requirement_id",
    "SOURCING_EVENT": "sourcing_event_id",
    "QUOTATION": "quotation_id",
}


async def is_participant(
    session: AsyncSession, conversation_id: UUID, organization_id: UUID
) -> bool:
    result = await session.execute(
        text(
            "select exists(select 1 from public.conversation_participants "
            "where conversation_id = :cid and organization_id = :org_id)"
        ),
        {"cid": str(conversation_id), "org_id": str(organization_id)},
    )
    return bool(result.scalar_one())


async def find_conversation_by_context(
    session: AsyncSession, *, context_type: str, context_id: UUID
) -> UUID | None:
    column = _CONTEXT_COLUMN[context_type]
    result = await session.execute(
        text(
            f"select id from public.conversations "
            f"where context_type = :context_type and {column} = :context_id"
        ),
        {"context_type": context_type, "context_id": str(context_id)},
    )
    row = result.first()
    return row[0] if row is not None else None


async def create_conversation(
    session: AsyncSession,
    *,
    context_type: str,
    context_id: UUID,
    created_by_organization_id: UUID,
    created_by: UUID,
) -> UUID:
    column = _CONTEXT_COLUMN[context_type]
    result = await session.execute(
        text(
            f"insert into public.conversations "
            f"(context_type, {column}, created_by_organization_id, created_by, updated_by) "
            f"values (:context_type, :context_id, :created_by_org, :created_by, :created_by) "
            f"returning id"
        ),
        {
            "context_type": context_type,
            "context_id": str(context_id),
            "created_by_org": str(created_by_organization_id),
            "created_by": str(created_by),
        },
    )
    return result.scalar_one()


async def add_participant(
    session: AsyncSession, *, conversation_id: UUID, organization_id: UUID
) -> None:
    await session.execute(
        text(
            "insert into public.conversation_participants (conversation_id, organization_id) "
            "values (:cid, :org_id) "
            "on conflict (conversation_id, organization_id) do nothing"
        ),
        {"cid": str(conversation_id), "org_id": str(organization_id)},
    )


async def list_conversations(
    session: AsyncSession, organization_id: UUID
) -> list[dict]:
    """unread_count cuenta mensajes posteriores al last_read_at del propio
    participante, excluyendo los que la propia organización envió. Los otros
    participantes (para mostrar "con quién es el hilo") se traen con un
    subselect correlacionado en vez de una segunda consulta con `= any(...)`
    — evita el problema de bindear un array de UUIDs contra asyncpg desde
    texto plano."""
    result = await session.execute(
        text(
            "select c.id, c.context_type, c.organization_id, c.offering_id, "
            "       c.requirement_id, c.sourcing_event_id, c.quotation_id, "
            "       c.created_at, c.updated_at, cp_self.last_read_at, "
            "       (select count(*) from public.messages m "
            "        where m.conversation_id = c.id "
            "          and m.created_at > coalesce(cp_self.last_read_at, '-infinity'::timestamptz) "
            "          and (m.sender_organization_id is null or m.sender_organization_id != :org_id) "
            "       ) as unread_count, "
            "       (select coalesce(json_agg(json_build_object("
            "           'organization_id', o.id, "
            "           'name', coalesce(o.trade_name, o.legal_name)"
            "         )), '[]'::json) "
            "        from public.conversation_participants cp2 "
            "        join public.organizations o on o.id = cp2.organization_id "
            "        where cp2.conversation_id = c.id and cp2.organization_id != :org_id "
            "       ) as participants "
            "from public.conversations c "
            "join public.conversation_participants cp_self "
            "  on cp_self.conversation_id = c.id and cp_self.organization_id = :org_id "
            "order by c.updated_at desc"
        ),
        {"org_id": str(organization_id)},
    )
    rows = []
    for row in result:
        record = dict(row._mapping)
        participants = record["participants"]
        record["participants"] = (
            json.loads(participants) if isinstance(participants, str) else participants
        )
        rows.append(record)
    return rows


async def list_messages(
    session: AsyncSession,
    conversation_id: UUID,
    *,
    after: datetime | None,
    limit: int = 200,
) -> list[dict]:
    query = (
        "select id, conversation_id, sender_id, sender_organization_id, body, "
        "is_system, created_at, edited_at, deleted_at "
        "from public.messages where conversation_id = :cid "
    )
    params: dict[str, object] = {"cid": str(conversation_id), "limit": limit}
    if after is not None:
        query += "and created_at > :after "
        params["after"] = after
    query += "order by created_at asc limit :limit"
    result = await session.execute(text(query), params)
    return [dict(row._mapping) for row in result]


async def create_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    sender_id: UUID,
    sender_organization_id: UUID,
    body: str,
) -> UUID:
    result = await session.execute(
        text(
            "insert into public.messages "
            "(conversation_id, sender_id, sender_organization_id, body) "
            "values (:cid, :sender_id, :sender_org, :body) returning id"
        ),
        {
            "cid": str(conversation_id),
            "sender_id": str(sender_id),
            "sender_org": str(sender_organization_id),
            "body": body,
        },
    )
    return result.scalar_one()


async def list_other_participant_org_ids(
    session: AsyncSession, conversation_id: UUID, exclude_organization_id: UUID
) -> list[UUID]:
    result = await session.execute(
        text(
            "select organization_id from public.conversation_participants "
            "where conversation_id = :cid and organization_id != :org_id"
        ),
        {"cid": str(conversation_id), "org_id": str(exclude_organization_id)},
    )
    return [row[0] for row in result]


async def touch_last_read(
    session: AsyncSession, *, conversation_id: UUID, organization_id: UUID
) -> None:
    await session.execute(
        text(
            "update public.conversation_participants set last_read_at = now() "
            "where conversation_id = :cid and organization_id = :org_id"
        ),
        {"cid": str(conversation_id), "org_id": str(organization_id)},
    )


async def mark_messages_read(
    session: AsyncSession, *, conversation_id: UUID, reader_id: UUID
) -> None:
    await session.execute(
        text(
            "insert into public.message_reads (message_id, reader_id) "
            "select m.id, :reader_id from public.messages m "
            "where m.conversation_id = :cid "
            "on conflict (message_id, reader_id) do nothing"
        ),
        {"cid": str(conversation_id), "reader_id": str(reader_id)},
    )


async def get_message(session: AsyncSession, message_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            "select id, conversation_id, sender_id, sender_organization_id "
            "from public.messages where id = :id"
        ),
        {"id": str(message_id)},
    )
    row = result.first()
    return dict(row._mapping) if row is not None else None


async def create_attachment(
    session: AsyncSession,
    *,
    message_id: UUID,
    name: str,
    storage_path: str,
    checksum_sha256: str,
) -> UUID:
    result = await session.execute(
        text(
            "insert into public.message_attachments "
            "(message_id, name, storage_path, checksum_sha256) "
            "values (:message_id, :name, :storage_path, :checksum) returning id"
        ),
        {
            "message_id": str(message_id),
            "name": name,
            "storage_path": storage_path,
            "checksum": checksum_sha256,
        },
    )
    return result.scalar_one()
