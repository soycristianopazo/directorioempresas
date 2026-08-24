"""Acceso a datos de organizaciones.

Los RPC transaccionales que existían como funciones plpgsql en el diseño
original (`create_organization`, `accept_invitation`, `remove_member`) pasan
aquí a ser transacciones de SQLAlchemy orquestadas desde el servicio: mismo
resultado atómico, un solo lenguaje para el equipo, y pruebas que no necesitan
levantar Postgres para ejercitar la lógica de negocio.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationCapability,
    OrganizationLegalIdentifier,
)


async def get_by_id(
    session: AsyncSession, organization_id: UUID
) -> Organization | None:
    result = await session.execute(
        select(Organization).where(
            Organization.id == organization_id, Organization.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def get_by_slug(session: AsyncSession, slug: str) -> Organization | None:
    result = await session.execute(
        select(Organization).where(
            Organization.slug == slug, Organization.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(
        select(Organization.id).where(
            Organization.slug == slug, Organization.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none() is not None


async def create(
    session: AsyncSession,
    *,
    legal_name: str,
    trade_name: str | None,
    slug: str,
    country_code: str,
    created_by: UUID,
) -> Organization:
    org = Organization(
        legal_name=legal_name,
        trade_name=trade_name,
        slug=slug,
        country_code=country_code,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(org)
    await session.flush()
    return org


async def add_capability(
    session: AsyncSession, *, organization_id: UUID, capability: str, enabled_by: UUID
) -> None:
    session.add(
        OrganizationCapability(
            organization_id=organization_id,
            capability=capability,
            enabled_by=enabled_by,
        )
    )


async def add_legal_identifier(
    session: AsyncSession,
    *,
    organization_id: UUID,
    identifier_type: str,
    country_code: str,
    value: str,
    value_normalized: str,
    is_primary: bool = True,
) -> OrganizationLegalIdentifier:
    record = OrganizationLegalIdentifier(
        organization_id=organization_id,
        identifier_type=identifier_type,
        country_code=country_code,
        value=value,
        value_normalized=value_normalized,
        is_primary=is_primary,
    )
    session.add(record)
    await session.flush()
    return record


async def get_primary_legal_identifier(
    session: AsyncSession, organization_id: UUID
) -> OrganizationLegalIdentifier | None:
    result = await session.execute(
        select(OrganizationLegalIdentifier).where(
            OrganizationLegalIdentifier.organization_id == organization_id,
            OrganizationLegalIdentifier.is_primary.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_capabilities(session: AsyncSession, organization_id: UUID) -> list[str]:
    result = await session.execute(
        select(OrganizationCapability.capability).where(
            OrganizationCapability.organization_id == organization_id
        )
    )
    return list(result.scalars())


async def has_permission(
    session: AsyncSession, organization_id: UUID, permission_code: str
) -> bool:
    """Espejo de app.has_permission() del SQL: permiso efectivo del usuario de
    la sesión (app.current_user_id(), fijado por SET LOCAL) en la organización.

    Se verifica ANTES de mutar, no después. La alternativa —dejar que RLS
    bloquee el UPDATE y detectarlo por sus efectos— choca con cómo SQLAlchemy
    maneja un flush que actualiza 0 filas sobre un objeto ya cargado: lo trata
    como StaleDataError y deja la sesión en estado "inactive", exigiendo un
    rollback explícito antes de poder reutilizarla. Preguntar primero evita
    esa categoría de problema por completo.
    """
    result = await session.execute(
        text("select app.has_permission(:org_id, :perm)"),
        {"org_id": str(organization_id), "perm": permission_code},
    )
    return bool(result.scalar_one())


async def update_fields(
    session: AsyncSession, organization_id: UUID, **fields: object
) -> Organization | None:
    org = await get_by_id(session, organization_id)
    if org is None:
        return None
    for key, value in fields.items():
        setattr(org, key, value)
    await session.flush()
    return org


class MembershipRow:
    """Fila de v_my_organizations. La vista es la fuente de verdad de la
    pertenencia: agrega roles y capacidades con GROUP BY, algo que sale más
    caro de replicar en Python que de reutilizar tal cual está en SQL.
    """

    __slots__ = (
        "id",
        "legal_name",
        "trade_name",
        "slug",
        "status",
        "visibility",
        "completion_pct",
        "member_id",
        "member_status",
        "joined_at",
        "role_codes",
        "capabilities",
    )

    def __init__(self, row: object) -> None:
        for field in self.__slots__:
            setattr(self, field, getattr(row, field))


async def list_my_memberships(session: AsyncSession) -> list[MembershipRow]:
    """Requiere que la sesión ya tenga app.current_user_id fijado (SET LOCAL).

    La vista lo lee internamente; sin una sesión de app.api.deps.get_db_session
    o get_authenticated_session, esto devuelve siempre una lista vacía.
    """
    result = await session.execute(
        text(
            "select id, legal_name, trade_name, slug, status, visibility, "
            "completion_pct, member_id, member_status, joined_at, role_codes, capabilities "
            "from public.v_my_organizations order by joined_at asc"
        )
    )
    return [MembershipRow(row) for row in result]
