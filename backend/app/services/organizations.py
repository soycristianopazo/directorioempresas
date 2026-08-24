"""Creación y edición de organizaciones.

`create_organization` reemplaza al RPC plpgsql del diseño original: misma
atomicidad (una transacción de SQLAlchemy), mismo resultado, pero orquestado
en Python. Corre en contexto de sistema porque inserta en `roles`/`profiles`
de otros — el creador aún no tiene membresía cuando empieza la operación, así
que RLS ordinario lo bloquearía en el primer INSERT.
"""

from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from app.core.rut import format_rut, is_valid_rut
from app.db.rls import session_for_system, session_for_user
from app.models.user import Profile
from app.repositories import members as members_repo
from app.repositories import organization_profile as profile_repo
from app.repositories import organizations as orgs_repo


class OrganizationError(Exception):
    pass


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "empresa"


async def create_organization(
    *,
    created_by: UUID,
    legal_name: str,
    trade_name: str | None,
    rut: str,
    capabilities: list[str],
    country_code: str = "CL",
) -> UUID:
    if not is_valid_rut(rut):
        raise OrganizationError(f"RUT inválido: {rut}")
    normalized_rut = format_rut(rut)

    async with session_for_system() as db:
        base_slug = _slugify(trade_name or legal_name)[:90]
        slug = base_slug
        suffix = 0
        while await orgs_repo.slug_exists(db, slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        org = await orgs_repo.create(
            db,
            legal_name=legal_name.strip(),
            trade_name=(trade_name or "").strip() or None,
            slug=slug,
            country_code=country_code,
            created_by=created_by,
        )

        for capability in capabilities:
            await orgs_repo.add_capability(
                db, organization_id=org.id, capability=capability, enabled_by=created_by
            )

        await orgs_repo.add_legal_identifier(
            db,
            organization_id=org.id,
            identifier_type="RUT",
            country_code=country_code,
            value=normalized_rut,
            value_normalized=normalized_rut,
        )

        member = await members_repo.create_member(
            db, user_id=created_by, organization_id=org.id
        )

        owner_role = await members_repo.get_default_owner_role(db)
        if owner_role is None:
            raise OrganizationError("No existe el rol por defecto de dueño (ORG_OWNER)")
        await members_repo.assign_role(
            db, member_id=member.id, role_id=owner_role.id, assigned_by=created_by
        )

        await profile_repo.create_default_settings(db, org.id)

        organization_id = org.id

    return organization_id


async def update_organization(
    *, user_id: UUID, organization_id: UUID, **fields: object
) -> None:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(
            db, organization_id, "organization.update"
        ):
            raise OrganizationError("Sin permiso para editar esta organización")

        org = await orgs_repo.update_fields(db, organization_id, **fields)
        if org is None:
            raise OrganizationError("Organización no encontrada")


async def publish_organization(*, user_id: UUID, organization_id: UUID) -> None:
    async with session_for_user(user_id) as db:
        if not await orgs_repo.has_permission(
            db, organization_id, "organization.update"
        ):
            raise OrganizationError("Sin permiso para publicar esta organización")

        org = await orgs_repo.get_by_id(db, organization_id)
        if org is None:
            raise OrganizationError("Organización no encontrada")

        missing = []
        if not org.short_description:
            missing.append("descripción corta")
        if not org.description:
            missing.append("descripción corporativa")
        if not org.trade_name:
            missing.append("nombre comercial")

        identifier = await orgs_repo.get_primary_legal_identifier(db, organization_id)
        if identifier is None:
            missing.append("RUT")

        if missing:
            raise OrganizationError(
                f"Faltan datos para publicar el perfil: {', '.join(missing)}"
            )

        org.status = "ACTIVE"


async def switch_organization(*, user_id: UUID, organization_id: UUID) -> None:
    """Persiste la organización activa como preferencia de UI.

    No es una fuente de autorización: cada request que siga revalida contra
    la membresía real. Aquí solo se valida UNA vez, al guardar la preferencia,
    para no dejar que el usuario guarde un id de una organización a la que no
    pertenece.
    """
    async with session_for_user(user_id) as db:
        membership = await members_repo.get_membership(
            db, user_id=user_id, organization_id=organization_id
        )
        if membership is None or membership.status != "ACTIVE":
            raise OrganizationError("No perteneces a esa organización")

        profile = await db.get(Profile, user_id)
        if profile is not None:
            profile.last_org_id = organization_id


async def get_organization_detail(
    *, user_id: UUID, organization_id: UUID
) -> dict | None:
    async with session_for_user(user_id) as db:
        org = await orgs_repo.get_by_id(db, organization_id)
        if org is None:
            return None
        capabilities = await orgs_repo.list_capabilities(db, organization_id)
        identifier = await orgs_repo.get_primary_legal_identifier(db, organization_id)

        return {
            "id": org.id,
            "legal_name": org.legal_name,
            "trade_name": org.trade_name,
            "slug": org.slug,
            "status": org.status,
            "visibility": org.visibility,
            "short_description": org.short_description,
            "description": org.description,
            "value_proposition": org.value_proposition,
            "website_url": org.website_url,
            "linkedin_url": org.linkedin_url,
            "general_email": org.general_email,
            "general_phone": org.general_phone,
            "founded_year": org.founded_year,
            "company_size": org.company_size,
            "employee_count": org.employee_count,
            "completion_pct": org.completion_pct,
            "capabilities": capabilities,
            "primary_identifier": identifier.value if identifier else None,
        }
