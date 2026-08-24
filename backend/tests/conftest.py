"""Fixtures compartidos.

Corren contra la misma base de desarrollo que usa `python seed.py` — no hay
base de test separada (ver docs/DATABASE.md: "sin Docker, conexión directa
al proyecto hospedado"). Cada fixture crea sus propios datos con un sufijo
aleatorio y los borra al terminar, para poder correr la suite repetidas
veces sin colisionar consigo misma ni con `seed.py`.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text

import app.models  # noqa: F401 — registra todos los modelos antes de cualquier flush, ver app/models/__init__.py
from app.db.rls import session_for_system
from app.repositories import accreditation as accreditation_repo
from app.repositories import members as members_repo
from app.services import auth as auth_service
from app.services import organizations as org_service

PASSWORD = "TestPass123!"


def _random_valid_rut() -> str:
    """Genera un RUT chileno con dígito verificador válido — mismo algoritmo
    que app.core.rut.is_valid_rut, para no depender de una lista fija de
    RUTs de prueba que colisionarían entre corridas paralelas."""
    body = str(random.randint(1_000_000, 24_000_000))
    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    remainder = 11 - (total % 11)
    dv = {11: "0", 10: "K"}.get(remainder, str(remainder))
    return f"{body}-{dv}"


async def _delete_user(user_id: uuid.UUID) -> None:
    async with session_for_system() as db:
        await db.execute(
            text("delete from public.platform_admins where user_id = :id"),
            {"id": str(user_id)},
        )
        await db.execute(
            text("delete from public.users where id = :id"), {"id": str(user_id)}
        )


@pytest_asyncio.fixture
async def test_user() -> AsyncIterator[uuid.UUID]:
    """Un usuario sin organización ni rol de plataforma."""
    email = f"pytest.{uuid.uuid4().hex[:12]}@example.com"
    result = await auth_service.register(
        first_name="Pytest", last_name="User", email=email, password=PASSWORD
    )
    yield result.user_id
    await _delete_user(result.user_id)


@pytest_asyncio.fixture
async def reviewer_user() -> AsyncIterator[uuid.UUID]:
    """Un usuario con el rol de plataforma ACCREDITATION_REVIEWER, análogo a
    revisor.acreditacion@directorioempresas.cl de seed.py pero desechable."""
    email = f"pytest.reviewer.{uuid.uuid4().hex[:12]}@example.com"
    result = await auth_service.register(
        first_name="Pytest", last_name="Reviewer", email=email, password=PASSWORD
    )
    async with session_for_system() as db:
        role = await members_repo.find_role_by_code(db, "ACCREDITATION_REVIEWER")
        assert role is not None, "Falta el rol de sistema ACCREDITATION_REVIEWER (0009)"
        await db.execute(
            text(
                "insert into public.platform_admins (user_id, role_id) "
                "values (:user_id, :role_id)"
            ),
            {"user_id": str(result.user_id), "role_id": str(role.id)},
        )
    yield result.user_id
    await _delete_user(result.user_id)


@pytest_asyncio.fixture
async def test_org(test_user: uuid.UUID) -> AsyncIterator[tuple[uuid.UUID, uuid.UUID]]:
    """(owner_user_id, organization_id) — el dueño hereda ORG_OWNER, que
    resuelve a todos los permisos de scope ORGANIZATION vía el comodín '*'
    (0009), incluidos accreditation.submit/manage."""
    org_id = await org_service.create_organization(
        created_by=test_user,
        legal_name=f"Pytest Org {uuid.uuid4().hex[:8]}",
        trade_name="Pytest Org",
        rut=_random_valid_rut(),
        capabilities=["SUPPLIER"],
    )
    yield test_user, org_id
    async with session_for_system() as db:
        await db.execute(
            text("delete from public.organizations where id = :id"), {"id": str(org_id)}
        )


@pytest_asyncio.fixture
async def test_program() -> AsyncIterator[dict]:
    """Programa de acreditación desechable: una sección, dos exigencias
    DECLARATION de pesos distintos (30/70) — evita depender del programa
    sembrado ACREDITACION_BASE, cuyos pesos pueden cambiar. Se crea vía
    repositorio en contexto de sistema (autoría de programas no es lo que
    este fixture ejercita; services/accreditation.py::create_program ya
    tiene su propio test de permiso)."""
    async with session_for_system() as db:
        program = await accreditation_repo.create_program(
            db,
            code=f"PYTEST_{uuid.uuid4().hex[:8].upper()}",
            name="Programa de prueba",
            owner_scope="PLATFORM",
            validity_months=12,
        )
        group = await accreditation_repo.create_requirement_group(
            db, program_id=program.id, name="Sección única", weight=1, sort_order=0
        )
        req_a = await accreditation_repo.create_requirement(
            db,
            program_id=program.id,
            group_id=group.id,
            requirement_kind="DECLARATION",
            name="Exigencia A",
            is_mandatory=True,
            weight=30,
            sort_order=0,
        )
        req_b = await accreditation_repo.create_requirement(
            db,
            program_id=program.id,
            group_id=group.id,
            requirement_kind="DECLARATION",
            name="Exigencia B",
            is_mandatory=True,
            weight=70,
            sort_order=1,
        )
        program_id, req_a_id, req_b_id = program.id, req_a.id, req_b.id

    yield {"program_id": program_id, "req_a_id": req_a_id, "req_b_id": req_b_id}

    async with session_for_system() as db:
        await db.execute(
            text("delete from public.accreditation_programs where id = :id"),
            {"id": str(program_id)},
        )
