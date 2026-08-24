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
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.rls import session_for_system
from app.repositories import members as members_repo
from app.services import auth as auth_service
from app.services import invitations as invitations_service
from app.services import organizations as org_service
from app.services import quotations as quotations_service
from app.services import requirements as requirements_service
from app.services import sourcing as sourcing_service
from app.services import team as team_service

PASSWORD = "Directorio2026!"

USERS = [
    {"first_name": "Ana", "last_name": "Rojas", "email": "ana@transportesalfa.cl"},
    {"first_name": "Bruno", "last_name": "Díaz", "email": "bruno@transportesalfa.cl"},
    {"first_name": "Carla", "last_name": "Soto", "email": "carla@minerabeta.cl"},
    {"first_name": "Diego", "last_name": "Fuentes", "email": "diego@ingenieriasur.cl"},
    {"first_name": "Eva", "last_name": "Navarro", "email": "eva@australis.cl"},
]

# Cuenta de backoffice: no pertenece a ninguna organización, solo tiene un rol
# de plataforma. Se usa para probar /admin/taxonomia de punta a punta (fase 2).
PLATFORM_ADMIN_EMAIL = "admin@directorioempresas.cl"

# Igual que el admin de arriba, pero con el rol de plataforma acotado que usa
# la fase 5: platform.review_accreditation vía ACCREDITATION_REVIEWER, no
# platform.manage_taxonomy. Sin esta cuenta, cada verificación de
# /admin/acreditacion obligaba a registrar un usuario y otorgarle el rol a
# mano contra la base real — ver docs/RLS.md, "Un revisor de plataforma se
# verifica con app.has_platform_permission(), nunca con app.has_permission()".
ACCREDITATION_REVIEWER_EMAIL = "revisor.acreditacion@directorioempresas.cl"


async def wipe_existing() -> None:
    """Limpia corridas previas del seed para poder ejecutarlo repetidas veces."""
    from sqlalchemy import delete

    from app.models.organization import Organization
    from app.models.user import User

    emails = tuple(u["email"] for u in USERS) + (
        PLATFORM_ADMIN_EMAIL,
        ACCREDITATION_REVIEWER_EMAIL,
    )

    async with session_for_system() as db:
        await db.execute(
            delete(Organization).where(
                Organization.slug.in_(
                    [
                        "transportes-alfa",
                        "minera-beta",
                        "ingenieria-del-sur",
                        "servicios-australis",
                    ]
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

    # Segunda proveedora publicada — Alfa es la única publicada hasta acá, y
    # fase 7 (sellado) necesita DOS proveedoras compitiendo por el mismo
    # evento para que el punto de control ("Proveedor B no ve la oferta del
    # Proveedor A") sea demostrable en el navegador, no solo en un test.
    australis_id = await org_service.create_organization(
        created_by=accounts["eva@australis.cl"],
        legal_name="Servicios Australis Ltda.",
        trade_name="Australis",
        rut="79.222.333-8",
        capabilities=["SUPPLIER"],
    )
    await org_service.update_organization(
        user_id=accounts["eva@australis.cl"],
        organization_id=australis_id,
        legal_name="Servicios Australis Ltda.",
        trade_name="Australis",
        short_description="Transporte de personal y carga para faenas mineras en el norte de Chile.",
        description=(
            "Flota propia y subcontratada para traslado de personal y carga "
            "liviana en faenas mineras. Operamos en Antofagasta y Atacama "
            "con protocolos de seguridad vial certificados."
        ),
        value_proposition="Cobertura regional flexible y tiempos de respuesta cortos frente a eventos no programados.",
        website_url="https://australis.cl",
        linkedin_url=None,
        general_email="contacto@australis.cl",
        general_phone="+56 55 987 6543",
        founded_year=2015,
        company_size="SMALL",
        employee_count=35,
        visibility="PUBLIC",
    )
    await org_service.publish_organization(
        user_id=accounts["eva@australis.cl"], organization_id=australis_id
    )
    print(f"  ✓ Australis ({australis_id}) — proveedor, publicada (compite con Alfa)")

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

    print("\nCreando recorrido de fase 7 (sellado, dos proveedoras compitiendo)...")

    requirement_id = await requirements_service.create_requirement(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        name="Transporte de personal a faena — turno 2026",
    )
    event_id = await sourcing_service.create_event(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        requirement_id=requirement_id,
        name="RFQ Transporte de personal — turno 2026",
        event_type="RFQ",
        bid_mode="SEALED",
        currency_code="CLP",
        requires_nda=True,
    )
    item_id = await sourcing_service.add_item(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        event_id=event_id,
        description="Traslado de personal — 40 pasajeros/día, turno diurno",
        quantity=40,
    )
    await sourcing_service.upsert_stage(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        event_id=event_id,
        stage_type="BID_DEADLINE",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await invitations_service.upsert_nda(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        sourcing_event_id=event_id,
        title="Acuerdo de confidencialidad — RFQ Transporte de personal",
        body_text=(
            "Toda la información compartida en este proceso (bases, precios, "
            "condiciones) es confidencial y no puede divulgarse a terceros."
        ),
    )
    await sourcing_service.publish_event(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        event_id=event_id,
    )
    print(f"  ✓ Evento sellado publicado ({event_id}), NDA exigido, cierra en 7 días")

    alfa_invitation_id = await invitations_service.invite_supplier(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        sourcing_event_id=event_id,
        supplier_organization_id=alfa_id,
    )
    australis_invitation_id = await invitations_service.invite_supplier(
        user_id=accounts["carla@minerabeta.cl"],
        organization_id=beta_id,
        sourcing_event_id=event_id,
        supplier_organization_id=australis_id,
    )
    print("  ✓ Invitadas Transportes Alfa y Australis")

    # Alfa recorre el flujo completo y cotiza — el proveedor "A" del punto de
    # control 7 (docs/04-ROADMAP.md): el que sí tiene una oferta que Australis
    # nunca debe poder leer.
    await invitations_service.get_invitation_detail(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        invitation_id=alfa_invitation_id,
    )
    await invitations_service.accept_nda(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        invitation_id=alfa_invitation_id,
        ip_address="127.0.0.1",
        user_agent="seed.py",
    )
    await invitations_service.express_interest(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        invitation_id=alfa_invitation_id,
    )
    await invitations_service.confirm_participation(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        invitation_id=alfa_invitation_id,
    )
    await quotations_service.submit_revision(
        user_id=accounts["ana@transportesalfa.cl"],
        organization_id=alfa_id,
        sourcing_event_id=event_id,
        currency_code="CLP",
        valid_until=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
        subtotal=8_500_000,
        tax_amount=1_615_000,
        total_amount=10_115_000,
        payment_terms="30 días fin de mes",
        delivery_days=15,
        warranty_terms=None,
        exclusions=None,
        notes="Incluye buses con acreditación minera vigente.",
        items=[
            {
                "sourcing_event_item_id": item_id,
                "quantity": 40,
                "unit_price": 212_500,
            }
        ],
    )
    print("  ✓ Transportes Alfa cotizó (PARTICIPATING → QUOTED)")

    # Australis solo llega a VIEWED — todavía interesada, sin cotizar. Deja
    # la bandeja de invitaciones del proveedor con más de un estado real.
    await invitations_service.get_invitation_detail(
        user_id=accounts["eva@australis.cl"],
        organization_id=australis_id,
        invitation_id=australis_invitation_id,
    )
    print("  ✓ Australis vio la invitación (INVITED → VIEWED), sin cotizar todavía")

    print("\nCreando cuenta de backoffice...")
    admin_result = await auth_service.register(
        first_name="Admin",
        last_name="Plataforma",
        email=PLATFORM_ADMIN_EMAIL,
        password=PASSWORD,
    )
    async with session_for_system() as db:
        platform_admin_role = await members_repo.find_role_by_code(db, "PLATFORM_ADMIN")
        if platform_admin_role is None:
            raise RuntimeError("No existe el rol de sistema PLATFORM_ADMIN")
        await db.execute(
            text(
                "insert into public.platform_admins (user_id, role_id) "
                "values (:user_id, :role_id)"
            ),
            {
                "user_id": str(admin_result.user_id),
                "role_id": str(platform_admin_role.id),
            },
        )
    print(f"  ✓ {PLATFORM_ADMIN_EMAIL} ({admin_result.user_id}) — rol PLATFORM_ADMIN")

    print("\nCreando cuenta de revisor de acreditación...")
    reviewer_result = await auth_service.register(
        first_name="Revisor",
        last_name="Acreditación",
        email=ACCREDITATION_REVIEWER_EMAIL,
        password=PASSWORD,
    )
    async with session_for_system() as db:
        reviewer_role = await members_repo.find_role_by_code(
            db, "ACCREDITATION_REVIEWER"
        )
        if reviewer_role is None:
            raise RuntimeError("No existe el rol de sistema ACCREDITATION_REVIEWER")
        await db.execute(
            text(
                "insert into public.platform_admins (user_id, role_id) "
                "values (:user_id, :role_id)"
            ),
            {
                "user_id": str(reviewer_result.user_id),
                "role_id": str(reviewer_role.id),
            },
        )
    print(
        f"  ✓ {ACCREDITATION_REVIEWER_EMAIL} ({reviewer_result.user_id}) "
        "— rol ACCREDITATION_REVIEWER"
    )

    print("\n" + "=" * 70)
    print("Listo. Contraseña para todas las cuentas:", PASSWORD)
    print("=" * 70)
    for u in USERS:
        print(f"  {u['email']}")
    print(f"  {PLATFORM_ADMIN_EMAIL} (backoffice, sin organización)")
    print(f"  {ACCREDITATION_REVIEWER_EMAIL} (backoffice, sin organización)")
    print("\nTransportes Alfa  → publicada, pública, comprador+proveedor")
    print("Minera Beta       → activa, solo registrados, comprador")
    print("Ingeniería del Sur→ EN BORRADOR a propósito (perfil incompleto)")
    print("Australis         → publicada, pública, proveedor (compite con Alfa)")
    print(
        "\nRecorrido fase 7: Minera Beta publicó un RFQ SELLADO con NDA, "
        "invitó a Alfa y Australis — Alfa cotizó (QUOTED), Australis solo vio "
        "la invitación (VIEWED). Iniciar sesión como carla@minerabeta.cl para "
        "ver el evento sellado; como ana@transportesalfa.cl o "
        "eva@australis.cl para ver la bandeja de invitaciones de cada una."
    )


if __name__ == "__main__":
    asyncio.run(main())
