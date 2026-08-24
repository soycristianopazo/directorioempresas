"""Datos de prueba para desarrollo.

Reutiliza los propios servicios de la aplicación (auth_service.register,
org_service.create_organization, team_service.invite_member/accept_invitation)
en vez de insertar filas a mano. Dos razones:

  1. Ejercita el mismo código que corre en producción — si el registro o la
     creación de organización tuvieran un bug, este script lo encontraría
     antes que un usuario real.
  2. Los hashes de contraseña, slugs, tokens de invitación, etc. quedan
     generados exactamente como los generaría la aplicación, no una
     aproximación a mano en SQL.

    cd backend && source .venv/bin/activate && python seed.py
"""

from __future__ import annotations

import asyncio

from app.db.rls import session_for_system
from app.services import auth as auth_service
from app.services import organizations as org_service
from app.services import team as team_service

PASSWORD = "Directorio2026!"

USERS = [
    {"first_name": "Ana", "last_name": "Rojas", "email": "ana@transportesalfa.cl"},
    {"first_name": "Bruno", "last_name": "Díaz", "email": "bruno@transportesalfa.cl"},
    {"first_name": "Carla", "last_name": "Soto", "email": "carla@minerabeta.cl"},
    {"first_name": "Diego", "last_name": "Fuentes", "email": "diego@ingenieriasur.cl"},
]


async def wipe_existing() -> None:
    """Limpia corridas previas del seed para poder ejecutarlo repetidas veces."""
    from sqlalchemy import delete

    from app.models.organization import Organization
    from app.models.user import User

    emails = tuple(u["email"] for u in USERS)

    async with session_for_system() as db:
        await db.execute(
            delete(Organization).where(
                Organization.slug.in_(
                    ["transportes-alfa", "minera-beta", "ingenieria-sur"]
                )
            )
        )
        await db.execute(delete(User).where(User.email.in_(emails)))

    print("✓ corridas anteriores del seed eliminadas (si existían)")


async def main() -> None:
    await wipe_existing()

    print("\nCreando usuarios...")
    accounts = {}
    for u in USERS:
        result = await auth_service.register(
            first_name=u["first_name"],
            last_name=u["last_name"],
            email=u["email"],
            password=PASSWORD,
        )
        accounts[u["email"]] = result.user_id
        print(f"  ✓ {u['email']} ({result.user_id})")

    print("\nCreando organizaciones...")

    alfa_id = await org_service.create_organization(
        created_by=accounts["ana@transportesalfa.cl"],
        legal_name="Transportes Alfa SpA",
        trade_name="Transportes Alfa",
        rut="76.086.428-5",
        capabilities=["SUPPLIER", "BUYER"],
    )
    print(f"  ✓ Transportes Alfa ({alfa_id}) — proveedor y comprador")

    await org_service.update_organization(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        legal_name="Transportes Alfa SpA",
        trade_name="Transportes Alfa",
        short_description="Transporte de personal para faenas mineras en la Región de Antofagasta.",
        description=(
            "Operamos flota propia de buses y minibuses con acreditación minera, "
            "GPS en línea y conductores con experiencia comprobada en faena. Más "
            "de 12 años sirviendo a la gran minería del cobre."
        ),
        value_proposition="Flota renovada, trazabilidad GPS en tiempo real y cero accidentes en los últimos 3 años.",
        website_url="https://transportesalfa.cl",
        linkedin_url=None,
        general_email="contacto@transportesalfa.cl",
        general_phone="+56 55 234 5678",
        founded_year=2011,
        company_size="MEDIUM",
        employee_count=120,
        visibility="PUBLIC",
    )
    await org_service.publish_organization(
        user_id=accounts["ana@transportesalfa.cl"], organization_id=alfa_id
    )
    print("    → perfil publicado")

    beta_id = await org_service.create_organization(
        created_by=accounts["carla@minerabeta.cl"],
        legal_name="Minera Beta S.A.",
        trade_name="Minera Beta",
        rut="77.777.777-7",
        capabilities=["BUYER"],
    )
    print(f"  ✓ Minera Beta ({beta_id}) — comprador")

    await org_service.update_organization(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        legal_name="Minera Beta S.A.",
        trade_name="Minera Beta",
        short_description="Operación minera de cobre en la Región de Antofagasta.",
        description="Compañía minera con operaciones de extracción y procesamiento de cobre.",
        value_proposition=None,
        website_url=None,
        linkedin_url=None,
        general_email=None,
        general_phone=None,
        founded_year=1998,
        company_size="ENTERPRISE",
        employee_count=2400,
        visibility="REGISTERED",
    )

    sur_id = await org_service.create_organization(
        created_by=accounts["diego@ingenieriasur.cl"],
        legal_name="Ingeniería del Sur Ltda.",
        trade_name="Ingeniería del Sur",
        rut="78.111.222-4",
        capabilities=["SUPPLIER"],
    )
    print(
        f"  ✓ Ingeniería del Sur ({sur_id}) — proveedor, perfil en borrador (a propósito)"
    )

    print("\nArmando equipo y multiempresa...")

    # Bruno se une a Alfa como Ventas.
    _, accept_url = await team_service.invite_member(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        email="bruno@transportesalfa.cl",
        role_code="SALES",
    )
    token = accept_url.rsplit("/", 1)[-1]
    await team_service.accept_invitation(
        user_id=accounts["bruno@transportesalfa.cl"],
        user_email="bruno@transportesalfa.cl",
        token=token,
    )
    print("  ✓ Bruno se unió a Transportes Alfa (Ventas)")

    # Carla también pertenece a Alfa como solo lectura — valida multiempresa real.
    _, accept_url = await team_service.invite_member(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        email="carla@minerabeta.cl",
        role_code="VIEWER",
    )
    token = accept_url.rsplit("/", 1)[-1]
    await team_service.accept_invitation(
        user_id=accounts["carla@minerabeta.cl"],
        user_email="carla@minerabeta.cl",
        token=token,
    )
    print(
        "  ✓ Carla pertenece a Minera Beta (dueña) Y a Transportes Alfa (solo lectura)"
    )

    # Invitación pendiente sin aceptar, para que la pantalla de equipo la muestre.
    _, pending_url = await team_service.invite_member(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        email="nueva.compradora@minerabeta.cl",
        role_code="BUYER",
    )
    print(f"  ✓ Invitación pendiente en Minera Beta: {pending_url}")

    print("\n" + "=" * 70)
    print("Listo. Contraseña para todas las cuentas:", PASSWORD)
    print("=" * 70)
    for u in USERS:
        print(f"  {u['email']}")
    print("\nTransportes Alfa  → publicada, pública, comprador+proveedor")
    print("Minera Beta       → activa, solo registrados, comprador")
    print("Ingeniería del Sur→ EN BORRADOR a propósito (perfil incompleto)")


if __name__ == "__main__":
    asyncio.run(main())
