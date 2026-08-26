"""Datos de prueba para desarrollo — un mercado B2B minero con actividad real.

Reutiliza los propios servicios de la aplicación (auth_service.register,
org_service.create_organization, team_service.invite_member/accept_invitation,
sourcing_service, quotations_service, etc.) en vez de insertar filas a mano.
Dos razones:

  1. Ejercita el mismo código que corre en producción — si el registro o la
     creación de organización tuvieran un bug, este script lo encontraría
     antes que un usuario real.
  2. Los hashes de contraseña, slugs, tokens de invitación, etc. quedan
     generados exactamente como los generaría la aplicación, no una
     aproximación a mano en SQL.

Arma dos compradores (minería y construcción) y nueve proveedores, uno por
rubro: EPP, transporte de pasajeros, transporte de carga, factoring,
hotelería/campamentos, útiles de oficina, útiles de aseo, capacitaciones y
exámenes médicos. Entre ellos: RFQs publicados, cotizaciones, una ronda de
negociación, adjudicaciones, mensajes directos y acreditación — la economía
de la plataforma "moviéndose", no solo organizaciones vacías.

    cd backend && source .venv/bin/activate && python seed.py
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.db.rls import session_for_system
from app.repositories import accreditation as accreditation_repo
from app.repositories import billing as billing_repo
from app.repositories import members as members_repo
from app.services import accreditation as accreditation_service
from app.services import auth as auth_service
from app.services import awards as awards_service
from app.services import invitations as invitations_service
from app.services import messaging as messaging_service
from app.services import negotiations as negotiations_service
from app.services import offerings as offerings_service
from app.services import organization_profile as profile_service
from app.services import organizations as org_service
from app.services import quotations as quotations_service
from app.services import requirements as requirements_service
from app.services import sourcing as sourcing_service
from app.services import taxonomy as taxonomy_service
from app.services import team as team_service
from app.services import vendor_list as vendor_list_service

PASSWORD = "Directorio2026!"

PLATFORM_ADMIN_EMAIL = "admin@directorioempresas.cl"
ACCREDITATION_REVIEWER_EMAIL = "revisor.acreditacion@directorioempresas.cl"

# ─── Taxonomía (nodos existentes, fase 2) — "qué vende" cada oferta ──────────
# IDs fijos del árbol ya sembrado (backend/alembic/sql, fase 2). No se crean
# de nuevo acá; los tres que faltan (factoring, útiles de oficina, exámenes
# médicos) se crean más abajo con taxonomy_service, como PLATFORM_ADMIN.
NODE_EPP = "83634faa-5451-4b08-87ae-739034ce258d"  # Elementos de protección personal
NODE_TRANSPORTE_PERSONAS = "81c8fb50-856a-45be-a9e6-a570af6c8359"  # Traslado a faena
NODE_TRANSPORTE_CARGA = "20db522f-dc78-4736-ac00-fd24538054f6"  # Carga general
NODE_CAMPAMENTOS = "fc45e306-3ca6-4af0-9da0-1f2184a03cd0"  # Campamentos
NODE_ASEO = "d0cd3b54-9953-4410-8a6c-55eeebe611fc"  # Aseo e higiene industrial
NODE_CAPACITACION = "aed3bb3d-5f73-4bed-ad53-9e81fa403b1f"  # Capacitación (OTEC)

# ─── Industrias (a quién le vende cada proveedor) e industria de cada comprador
IND_MINERIA = "5facbd5b-aebc-4db7-a60b-222928577621"
IND_CONSTRUCCION = "5d07a8a1-ed8a-4404-89b2-f5b38c5e29a2"
IND_FINANCIERO = "6a2b433e-00ad-42e2-9281-217fa951191e"
IND_TRANSPORTE = "09f7c44b-aa6c-4ae5-bb78-9dedafd17e9f"
IND_HOTELERIA = "8b51ab14-1383-4271-83ef-360432d0b2c5"
IND_SALUD = "5fc83f03-078e-4146-bda6-7ce3601303f6"
IND_EDUCACION = "ed0e9f9b-b08f-423e-b2e7-8291332899dd"

# ─── Divisiones administrativas (región/comuna real de cada casa matriz) ─────
REGION_ANTOFAGASTA = "252164d0-dd9f-534a-a2fa-98c84026f3cb"
REGION_RM = "bdbb70ce-c773-5f5e-8d93-c5ea6dd3af3f"
COMUNA_ANTOFAGASTA = "60b922c2-923c-59c9-bada-ad084558f06b"
COMUNA_CALAMA = "681c1dee-a5d7-5744-b553-2e907a2ee94d"
COMUNA_MEJILLONES = "3b57a1a7-fc62-52b1-b8a9-b300b5339867"
COMUNA_SANTIAGO = "f3cb90e5-9edd-5f48-95df-4cae3eb298a3"
COMUNA_LAS_CONDES = "3e2f6a35-164e-50c6-a507-71c48a7600e2"
COMUNA_PROVIDENCIA = "2abab4ec-493b-5979-9960-ed6d497f7e93"


# ─── Roster de empresas ───────────────────────────────────────────────────────
# capabilities: BUYER compra, SUPPLIER vende. Los dos compradores son
# empresas reales del rubro que demanda todo lo demás (minería y
# construcción) — los nueve proveedores cubren cada rubro pedido, uno por
# organización para que el mercado se sienta poblado por actores distintos
# en vez de una sola empresa "que hace de todo".
COMPANIES = [
    {
        "key": "cordillera",
        "legal_name": "Minera Cordillera SpA",
        "trade_name": "Minera Cordillera",
        "rut": "76.111.222-8",
        "capabilities": ["BUYER"],
        "owner_email": "patricia@mineracordillera.cl",
        "owner_name": ("Patricia", "Larraín"),
        "short_description": "Operación minera de cobre en la Región de Antofagasta.",
        "description": (
            "Compañía minera con rajo abierto y planta concentradora propia en "
            "la Región de Antofagasta. Abastecimiento centralizado para "
            "faena y campamento."
        ),
        "value_proposition": None,
        "website_url": "https://mineracordillera.cl",
        "founded_year": 2003,
        "company_size": "ENTERPRISE",
        "employee_count": 1800,
        "industry_ids": [IND_MINERIA],
        "comuna_id": COMUNA_CALAMA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Camino a Faena Km 12, Calama",
        "visibility": "REGISTERED",
        "plan": "PRO",
        "publish": False,  # compradores no publican perfil público — no venden nada
    },
    {
        "key": "andes",
        "legal_name": "Constructora Andes Ltda.",
        "trade_name": "Constructora Andes",
        "rut": "76.222.333-3",
        "capabilities": ["BUYER"],
        "owner_email": "jorge@constructoraandes.cl",
        "owner_name": ("Jorge", "Espinoza"),
        "short_description": "Construcción industrial y montaje para proyectos mineros.",
        "description": (
            "Constructora especializada en obras civiles y montaje industrial "
            "para proyectos de la gran minería, con oficina central en Santiago "
            "y obras activas en el norte."
        ),
        "value_proposition": None,
        "website_url": "https://constructoraandes.cl",
        "founded_year": 2009,
        "company_size": "LARGE",
        "employee_count": 640,
        "industry_ids": [IND_CONSTRUCCION],
        "comuna_id": COMUNA_LAS_CONDES,
        "region_id": REGION_RM,
        "address": "Av. Apoquindo 4500, Las Condes",
        "visibility": "REGISTERED",
        "plan": "PRO",
        "publish": False,
    },
    {
        "key": "safetypro",
        "legal_name": "SafetyPro EPP SpA",
        "trade_name": "SafetyPro EPP",
        "rut": "76.333.444-9",
        "capabilities": ["SUPPLIER"],
        "owner_email": "camila@safetypro.cl",
        "owner_name": ("Camila", "Torres"),
        "short_description": "Venta de equipos de protección personal certificados para minería.",
        "description": (
            "Importador y distribuidor de elementos de protección personal "
            "(cascos, protección respiratoria, arneses, protección auditiva) "
            "con certificación para faenas mineras de alto riesgo."
        ),
        "value_proposition": "Stock permanente en Antofagasta — despacho a faena en 24-48 horas.",
        "website_url": "https://safetypro.cl",
        "founded_year": 2012,
        "company_size": "SMALL",
        "employee_count": 28,
        "industry_ids": [IND_MINERIA, IND_CONSTRUCCION],
        "comuna_id": COMUNA_ANTOFAGASTA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Zona Franca, Bodega 14, Antofagasta",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": True,
        "offerings": [
            {
                "name": "Cascos de seguridad certificados norma ANSI Z89.1",
                "short_description": "Cascos dieléctricos con barbiquejo de 4 puntos, venta por caja de 20 unidades.",
                "node_id": NODE_EPP,
                "price_type": "FROM",
                "amount_min": 12_500,
            },
            {
                "name": "Kit de protección respiratoria para polvo en suspensión",
                "short_description": "Respiradores media cara con filtros P100, incluye repuestos.",
                "node_id": NODE_EPP,
                "price_type": "FROM",
                "amount_min": 18_900,
            },
        ],
    },
    {
        "key": "cumbre",
        "legal_name": "Transportes Cumbre Ltda.",
        "trade_name": "Transportes Cumbre",
        "rut": "76.444.555-4",
        "capabilities": ["SUPPLIER"],
        "owner_email": "rodrigo@transportescumbre.cl",
        "owner_name": ("Rodrigo", "Salinas"),
        "short_description": "Transporte de personal a faena minera, flota propia con acreditación vigente.",
        "description": (
            "Flota propia de buses y minibuses para traslado de personal a "
            "faena. Conductores con curso de manejo defensivo en caminos "
            "mineros y GPS en línea."
        ),
        "value_proposition": "Flota renovada (menos de 5 años) y cero accidentes en los últimos 24 meses.",
        "website_url": "https://transportescumbre.cl",
        "founded_year": 2010,
        "company_size": "MEDIUM",
        "employee_count": 95,
        "industry_ids": [IND_MINERIA, IND_TRANSPORTE],
        "comuna_id": COMUNA_CALAMA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Ruta 25 Km 3, Calama",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": True,
        "offerings": [
            {
                "name": "Traslado de personal a faena — bus 45 pasajeros",
                "short_description": "Turnos diurno y nocturno, buses con acreditación minera vigente.",
                "node_id": NODE_TRANSPORTE_PERSONAS,
                "price_type": "FROM",
                "amount_min": 195_000,
            },
        ],
    },
    {
        "key": "cargaexpress",
        "legal_name": "Carga Express Norte SpA",
        "trade_name": "Carga Express Norte",
        "rut": "76.555.666-K",
        "capabilities": ["SUPPLIER"],
        "owner_email": "marcela@cargaexpress.cl",
        "owner_name": ("Marcela", "Ibáñez"),
        "short_description": "Transporte de carga general y especializada para la industria minera.",
        "description": (
            "Transporte de carga por camión entre Antofagasta y faenas del "
            "interior — carga general, insumos y equipos. Flota de camiones "
            "3/4 y rampla baja para carga sobredimensionada."
        ),
        "value_proposition": "Seguimiento GPS en tiempo real y seguro de carga incluido en toda ruta.",
        "website_url": "https://cargaexpress.cl",
        "founded_year": 2014,
        "company_size": "SMALL",
        "employee_count": 42,
        "industry_ids": [IND_MINERIA, IND_TRANSPORTE],
        "comuna_id": COMUNA_MEJILLONES,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Parque Industrial Mejillones, Sitio 8",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": False,
        "offerings": [
            {
                "name": "Transporte de carga general — camión 3/4",
                "short_description": "Retiro y entrega puerta a puerta, Antofagasta y faenas del interior.",
                "node_id": NODE_TRANSPORTE_CARGA,
                "price_type": "FROM",
                "amount_min": 420_000,
            },
        ],
    },
    {
        "key": "factoring",
        "legal_name": "Factoring Rápido SpA",
        "trade_name": "Factoring Rápido",
        "rut": "76.666.777-5",
        "capabilities": ["SUPPLIER"],
        "owner_email": "felipe@factoringrapido.cl",
        "owner_name": ("Felipe", "Concha"),
        "short_description": "Factoring de facturas para proveedores de la gran minería.",
        "description": (
            "Financiamos el capital de trabajo de proveedores mineros "
            "comprando sus facturas con descuento — liquidez en 48 horas, "
            "sin dejar de operar con el comprador original."
        ),
        "value_proposition": "Evaluación y giro en 48 horas, sin garantías adicionales para facturas con OC aprobada.",
        "website_url": "https://factoringrapido.cl",
        "founded_year": 2017,
        "company_size": "SMALL",
        "employee_count": 15,
        "industry_ids": [IND_FINANCIERO],
        "comuna_id": COMUNA_LAS_CONDES,
        "region_id": REGION_RM,
        "address": "Av. El Bosque Norte 500, oficina 802, Las Condes",
        "visibility": "PUBLIC",
        "plan": "FREE",
        "publish": True,
        "accredit": False,
        "offerings": [
            {
                "name": "Factoring de facturas a 30-90 días",
                "short_description": "Compra de facturas con orden de compra aprobada de mineras y grandes constructoras.",
                "node_id": None,  # se completa tras crear el nodo nuevo "Servicios financieros"
                "price_type": "ON_REQUEST",
                "amount_min": None,
            },
        ],
    },
    {
        "key": "campamentos",
        "legal_name": "Campamentos Atacama Hotelería SpA",
        "trade_name": "Campamentos Atacama",
        "rut": "76.777.888-0",
        "capabilities": ["SUPPLIER"],
        "owner_email": "valentina@campamentosatacama.cl",
        "owner_name": ("Valentina", "Rojas"),
        "short_description": "Arriendo y operación de campamentos modulares para faena minera.",
        "description": (
            "Instalación, arriendo y operación de campamentos modulares "
            "habitacionales para faena — habitaciones individuales, casino "
            "y áreas comunes, con estándar de la gran minería."
        ),
        "value_proposition": "Módulos propios listos para instalar en 15 días, sin subcontratar la operación.",
        "website_url": "https://campamentosatacama.cl",
        "founded_year": 2008,
        "company_size": "MEDIUM",
        "employee_count": 110,
        "industry_ids": [IND_MINERIA, IND_HOTELERIA],
        "comuna_id": COMUNA_ANTOFAGASTA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Km 8 Camino a Faena, Antofagasta",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": False,
        "offerings": [
            {
                "name": "Arriendo de campamento modular — 100 camas",
                "short_description": "Habitaciones individuales, casino y sala multiuso incluidos en la tarifa mensual.",
                "node_id": NODE_CAMPAMENTOS,
                "price_type": "FROM",
                "amount_min": 340_000,
            },
        ],
    },
    {
        "key": "ofinorte",
        "legal_name": "OfiNorte Suministros Ltda.",
        "trade_name": "OfiNorte",
        "rut": "76.888.999-6",
        "capabilities": ["SUPPLIER"],
        "owner_email": "sebastian@ofinorte.cl",
        "owner_name": ("Sebastián", "Molina"),
        "short_description": "Útiles de oficina y suministros administrativos para faena y oficina central.",
        "description": (
            "Distribuidor de útiles de oficina, insumos de impresión y "
            "suministros administrativos, con despacho programado a faena "
            "y a oficinas en Santiago."
        ),
        "value_proposition": "Reposición programada mensual — sin que administración tenga que pedir cada vez.",
        "website_url": None,
        "founded_year": 2021,
        "company_size": "MICRO",
        "employee_count": 6,
        "industry_ids": [IND_MINERIA, IND_CONSTRUCCION],
        "comuna_id": COMUNA_SANTIAGO,
        "region_id": REGION_RM,
        "address": "San Diego 350, local 12, Santiago",
        "visibility": "REGISTERED",
        "plan": "FREE",
        "publish": False,  # proveedor recién creado, perfil en borrador (a propósito)
        "accredit": False,
        "offerings": [
            {
                "name": "Pack de útiles de oficina mensual",
                "short_description": "Papelería, insumos de impresión y artículos de escritorio, reposición mensual.",
                "node_id": None,  # se completa tras crear el nodo nuevo "Útiles de oficina"
                "price_type": "FIXED",
                "amount_min": 890_000,
            },
        ],
    },
    {
        "key": "aseototal",
        "legal_name": "Aseo Total Industrial SpA",
        "trade_name": "Aseo Total",
        "rut": "76.999.111-5",
        "capabilities": ["SUPPLIER"],
        "owner_email": "daniela@aseototal.cl",
        "owner_name": ("Daniela", "Contreras"),
        "short_description": "Servicio de aseo industrial y provisión de insumos de higiene para faena y obra.",
        "description": (
            "Servicio de aseo industrial full-time con personal propio "
            "capacitado, más provisión de insumos de higiene (papel, "
            "dispensadores, desinfectantes) para faena, campamento y obra."
        ),
        "value_proposition": "Personal propio (no subcontratado) con rotación y control de asistencia diario.",
        "website_url": "https://aseototal.cl",
        "founded_year": 2016,
        "company_size": "SMALL",
        "employee_count": 55,
        "industry_ids": [IND_MINERIA, IND_CONSTRUCCION],
        "comuna_id": COMUNA_PROVIDENCIA,
        "region_id": REGION_RM,
        "address": "Av. Providencia 2140, oficina 501, Providencia",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": False,
        "offerings": [
            {
                "name": "Servicio de aseo industrial full-time",
                "short_description": "Cuadrilla de aseo con supervisión propia, contrato mensual renovable.",
                "node_id": NODE_ASEO,
                "price_type": "FROM",
                "amount_min": 2_450_000,
            },
        ],
    },
    {
        "key": "capacitamineria",
        "legal_name": "Capacita Minería OTEC Ltda.",
        "trade_name": "Capacita Minería",
        "rut": "77.111.222-6",
        "capabilities": ["SUPPLIER"],
        "owner_email": "andres@capacitamineria.cl",
        "owner_name": ("Andrés", "Pizarro"),
        "short_description": "OTEC especializado en capacitación para trabajadores de faena minera.",
        "description": (
            "Organismo Técnico de Capacitación (OTEC) acreditado SENCE, "
            "especializado en cursos de seguridad para faena minera: "
            "trabajo en altura física, espacios confinados y manejo "
            "defensivo en caminos mineros."
        ),
        "value_proposition": "Relatores con experiencia en faena, cursos dictados en terreno o en nuestra sede.",
        "website_url": "https://capacitamineria.cl",
        "founded_year": 2013,
        "company_size": "SMALL",
        "employee_count": 22,
        "industry_ids": [IND_MINERIA, IND_EDUCACION],
        "comuna_id": COMUNA_CALAMA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Av. Balmaceda 1200, Calama",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": False,
        "offerings": [
            {
                "name": "Curso DS-132 trabajo en altura física",
                "short_description": "Certificación vigente 2 años, incluye evaluación práctica en faena.",
                "node_id": NODE_CAPACITACION,
                "price_type": "FROM",
                "amount_min": 75_000,
            },
        ],
    },
    {
        "key": "clinicaocupacional",
        "legal_name": "Clínica Ocupacional Norte SpA",
        "trade_name": "Clínica Ocupacional Norte",
        "rut": "77.222.333-1",
        "capabilities": ["SUPPLIER"],
        "owner_email": "javiera@clinicaocupacional.cl",
        "owner_name": ("Javiera", "Bravo"),
        "short_description": "Exámenes médicos ocupacionales y de altura geográfica para trabajadores mineros.",
        "description": (
            "Clínica especializada en salud ocupacional minera: batería de "
            "exámenes preocupacionales, de altura geográfica y periódicos, "
            "con resultados integrados al sistema de gestión del cliente."
        ),
        "value_proposition": "Resultados en 24 horas y agenda propia en Calama, sin derivar a otro centro.",
        "website_url": "https://clinicaocupacionalnorte.cl",
        "founded_year": 2011,
        "company_size": "SMALL",
        "employee_count": 34,
        "industry_ids": [IND_MINERIA, IND_SALUD],
        "comuna_id": COMUNA_CALAMA,
        "region_id": REGION_ANTOFAGASTA,
        "address": "Av. Granaderos 890, Calama",
        "visibility": "PUBLIC",
        "plan": "PRO",
        "publish": True,
        "accredit": True,
        "offerings": [
            {
                "name": "Batería de exámenes ocupacionales mineros",
                "short_description": "Incluye examen de altura geográfica, audiometría y perfil bioquímico.",
                "node_id": None,  # se completa tras crear el nodo nuevo "Exámenes médicos"
                "price_type": "FROM",
                "amount_min": 32_000,
            },
        ],
    },
]

# Miembro adicional de Minera Cordillera — segunda persona con acceso, valida
# equipo real (no solo la dueña) para quien pruebe /empresa/equipo.
EXTRA_TEAM = [
    {
        "org_key": "cordillera",
        "email": "tomas@mineracordillera.cl",
        "name": ("Tomás", "Herrera"),
        "role_code": "BUYER_MANAGER",
    },
]


async def wipe_existing() -> None:
    """Limpia corridas previas del seed para poder ejecutarlo repetidas veces."""
    from sqlalchemy import delete

    from app.models.organization import Organization
    from app.models.user import User

    slugs = [c["trade_name"] for c in COMPANIES]
    # _slugify usa trade_name — se importa acá para no duplicar el algoritmo.
    from app.services.organizations import _slugify

    emails = (
        [c["owner_email"] for c in COMPANIES]
        + [m["email"] for m in EXTRA_TEAM]
        + [PLATFORM_ADMIN_EMAIL, ACCREDITATION_REVIEWER_EMAIL]
    )

    async with session_for_system() as db:
        await db.execute(
            delete(Organization).where(
                Organization.slug.in_([_slugify(s) for s in slugs])
            )
        )
        await db.execute(delete(User).where(User.email.in_(emails)))

    print("✓ corridas anteriores del seed eliminadas (si existían)")


async def _find_root_taxonomy_node_by_slug(slug: str) -> str | None:
    async with session_for_system() as db:
        result = await db.execute(
            text(
                "select id from public.taxonomy_nodes "
                "where parent_id is null and slug = :slug"
            ),
            {"slug": slug},
        )
        row = result.first()
        return str(row.id) if row else None


async def ensure_new_taxonomy_nodes(admin_user_id) -> dict[str, str]:
    """Tres rubros pedidos (factoring, útiles de oficina, exámenes médicos) no
    tienen categoría en el árbol de taxonomía sembrado en fase 2 — se crean
    acá, como PLATFORM_ADMIN, en vez de forzar la oferta a una categoría
    existente que no calza.

    Idempotente por slug: son datos de PLATAFORMA, no de organización, así
    que wipe_existing() (que solo borra organizaciones/usuarios) no los
    limpia entre corridas — si ya existen (de una corrida anterior, incluso
    una que falló después de este paso), se reusan en vez de fallar."""
    created = {}
    for key, name, description, slug in (
        (
            "factoring",
            "Servicios financieros",
            "Factoring, leasing y financiamiento de capital de trabajo para proveedores.",
            "servicios-financieros",
        ),
        (
            "oficina",
            "Útiles de oficina",
            "Papelería, insumos de impresión y suministros administrativos.",
            "utiles-de-oficina",
        ),
        (
            "examenes",
            "Exámenes médicos y salud ocupacional",
            "Exámenes preocupacionales, periódicos y de altura geográfica.",
            "examenes-medicos-y-salud-ocupacional",
        ),
    ):
        existing_id = await _find_root_taxonomy_node_by_slug(slug)
        if existing_id is not None:
            created[key] = existing_id
            continue
        node_id = await taxonomy_service.create_taxonomy_node(
            user_id=admin_user_id,
            parent_id=None,
            name=name,
            node_type="CATEGORY",
            description=description,
            slug=slug,
        )
        created[key] = str(node_id)
    print(f"  ✓ 3 categorías nuevas creadas: {', '.join(created.values())}")
    return created


async def main() -> None:
    await wipe_existing()

    print("\nCreando cuentas de backoffice...")
    admin_result = await auth_service.register(
        first_name="Admin", last_name="Plataforma",
        email=PLATFORM_ADMIN_EMAIL, password=PASSWORD,
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
            {"user_id": str(admin_result.user_id), "role_id": str(platform_admin_role.id)},
        )
    print(f"  ✓ {PLATFORM_ADMIN_EMAIL} — rol PLATFORM_ADMIN")

    reviewer_result = await auth_service.register(
        first_name="Revisor", last_name="Acreditación",
        email=ACCREDITATION_REVIEWER_EMAIL, password=PASSWORD,
    )
    async with session_for_system() as db:
        reviewer_role = await members_repo.find_role_by_code(db, "ACCREDITATION_REVIEWER")
        if reviewer_role is None:
            raise RuntimeError("No existe el rol de sistema ACCREDITATION_REVIEWER")
        await db.execute(
            text(
                "insert into public.platform_admins (user_id, role_id) "
                "values (:user_id, :role_id)"
            ),
            {"user_id": str(reviewer_result.user_id), "role_id": str(reviewer_role.id)},
        )
    print(f"  ✓ {ACCREDITATION_REVIEWER_EMAIL} — rol ACCREDITATION_REVIEWER")

    print("\nCreando categorías de taxonomía que faltan (factoring, oficina, exámenes)...")
    new_nodes = await ensure_new_taxonomy_nodes(admin_result.user_id)
    node_by_key = {
        "factoring": new_nodes["factoring"],
        "ofinorte": new_nodes["oficina"],
        "clinicaocupacional": new_nodes["examenes"],
    }

    print("\nCreando usuarios y organizaciones...")
    accounts: dict[str, object] = {}
    org_ids: dict[str, object] = {}

    for company in COMPANIES:
        first, last = company["owner_name"]
        result = await auth_service.register(
            first_name=first, last_name=last,
            email=company["owner_email"], password=PASSWORD,
        )
        accounts[company["owner_email"]] = result.user_id

        org_id = await org_service.create_organization(
            created_by=result.user_id,
            legal_name=company["legal_name"],
            trade_name=company["trade_name"],
            rut=company["rut"],
            capabilities=company["capabilities"],
        )
        org_ids[company["key"]] = org_id

        await org_service.update_organization(
            user_id=result.user_id,
            organization_id=org_id,
            legal_name=company["legal_name"],
            trade_name=company["trade_name"],
            short_description=company["short_description"],
            description=company["description"],
            value_proposition=company["value_proposition"],
            website_url=company["website_url"],
            linkedin_url=None,
            general_email=f"contacto@{company['trade_name'].lower().replace(' ', '')}.cl",
            general_phone="+56 9 " + company["rut"].replace(".", "").replace("-", "")[:8],
            founded_year=company["founded_year"],
            company_size=company["company_size"],
            employee_count=company["employee_count"],
            visibility=company["visibility"],
        )

        for industry_id in company["industry_ids"]:
            await profile_service.set_industry(
                user_id=result.user_id,
                organization_id=org_id,
                industry_id=industry_id,
                years_experience=max(1, date.today().year - company["founded_year"]),
                is_primary=(industry_id == company["industry_ids"][0]),
            )

        await profile_service.create_location(
            user_id=result.user_id,
            organization_id=org_id,
            location_type="HEADQUARTERS",
            address_line=company["address"],
            admin_division_id=company["comuna_id"],
            is_headquarters=True,
            lat=None,
            lng=None,
        )

        async with session_for_system() as db:
            plan = await billing_repo.get_plan_by_code(db, company["plan"])
            await billing_repo.create_subscription(
                db, organization_id=org_id, plan_id=plan.id, status="ACTIVE"
            )

        if company.get("publish"):
            await org_service.publish_organization(
                user_id=result.user_id, organization_id=org_id
            )

        status_note = "publicada" if company.get("publish") else "en borrador"
        print(f"  ✓ {company['trade_name']} ({org_id}) — {status_note}, plan {company['plan']}")

    for member in EXTRA_TEAM:
        first, last = member["name"]
        result = await auth_service.register(
            first_name=first, last_name=last, email=member["email"], password=PASSWORD,
        )
        accounts[member["email"]] = result.user_id
        owner_email = next(
            c["owner_email"] for c in COMPANIES if c["key"] == member["org_key"]
        )
        _, accept_url = await team_service.invite_member(
            user_id=accounts[owner_email],
            organization_id=org_ids[member["org_key"]],
            email=member["email"],
            role_code=member["role_code"],
        )
        token = accept_url.rsplit("/", 1)[-1]
        await team_service.accept_invitation(
            user_id=accounts[member["email"]], user_email=member["email"], token=token
        )
        print(f"  ✓ {member['email']} se unió a {member['org_key']} ({member['role_code']})")

    print("\nCreando catálogo de ofertas...")
    offering_ids: dict[str, list] = {}
    for company in COMPANIES:
        offerings = company.get("offerings")
        if not offerings:
            continue
        owner_id = accounts[company["owner_email"]]
        org_id = org_ids[company["key"]]
        offering_ids[company["key"]] = []
        for spec in offerings:
            offering_id = await offerings_service.create_offering(
                user_id=owner_id,
                organization_id=org_id,
                offering_type="SERVICE",
                name=spec["name"],
                short_description=spec["short_description"],
            )
            node_id = spec["node_id"] or node_by_key.get(company["key"])
            await offerings_service.set_taxonomy_nodes(
                user_id=owner_id,
                organization_id=org_id,
                offering_id=offering_id,
                nodes=[{"node_id": node_id, "is_primary": True}],
            )
            await offerings_service.set_pricing(
                user_id=owner_id,
                organization_id=org_id,
                offering_id=offering_id,
                price_type=spec["price_type"],
                amount_min=spec["amount_min"],
                currency_code="CLP",
                is_public=True,
            )
            await offerings_service.publish_offering(
                user_id=owner_id, organization_id=org_id, offering_id=offering_id
            )
            offering_ids[company["key"]].append(offering_id)
        print(f"  ✓ {company['trade_name']}: {len(offerings)} oferta(s) publicada(s)")

    print("\nAcreditando proveedores (ACREDITACION_BASE)...")
    async with session_for_system() as db:
        base_program = await accreditation_repo.get_program_by_code(db, "ACREDITACION_BASE")
        if base_program is None:
            raise RuntimeError("No existe el programa ACREDITACION_BASE")
        base_program_id = base_program.id
        mandatory_requirement_ids = [
            r.id
            for r in await accreditation_repo.list_requirements(db, base_program_id)
            if r.is_mandatory
        ]

    for company in COMPANIES:
        if not company.get("accredit"):
            continue
        owner_id = accounts[company["owner_email"]]
        org_id = org_ids[company["key"]]
        enrollment_id = await accreditation_service.enroll(
            user_id=owner_id, organization_id=org_id, program_id=base_program_id
        )
        for requirement_id in mandatory_requirement_ids:
            await accreditation_service.submit_evidence(
                user_id=owner_id,
                organization_id=org_id,
                enrollment_id=enrollment_id,
                requirement_id=requirement_id,
                declared_value="Evidencia de prueba (seed) — sin documento real adjunto.",
            )
        await accreditation_service.submit_for_review(
            user_id=owner_id, organization_id=org_id, enrollment_id=enrollment_id
        )
        await accreditation_service.decide_enrollment(
            user_id=reviewer_result.user_id,
            enrollment_id=enrollment_id,
            decision="ACCREDITED",
            reason="Cumple exigencias mínimas (seed).",
        )
        print(f"  ✓ {company['trade_name']} ACREDITADA en ACREDITACION_BASE")

    # ─── Procesos de compra (RFQ) ────────────────────────────────────────────
    print("\nPublicando procesos de compra y generando cotizaciones...")

    async def run_rfq(
        *,
        buyer_key: str,
        supplier_key: str,
        requirement_name: str,
        event_name: str,
        item_description: str,
        item_quantity: float,
        node_id: str | None,
        unit_price: float,
        outcome: str,  # "award" | "negotiate_award" | "open" | "decline"
    ) -> dict:
        buyer_owner = accounts[next(c["owner_email"] for c in COMPANIES if c["key"] == buyer_key)]
        buyer_org = org_ids[buyer_key]
        supplier_owner = accounts[next(c["owner_email"] for c in COMPANIES if c["key"] == supplier_key)]
        supplier_org = org_ids[supplier_key]

        requirement_id = await requirements_service.create_requirement(
            user_id=buyer_owner, organization_id=buyer_org, name=requirement_name,
        )
        event_id = await sourcing_service.create_event(
            user_id=buyer_owner,
            organization_id=buyer_org,
            requirement_id=requirement_id,
            name=event_name,
            event_type="RFQ",
            bid_mode="SEALED",
            currency_code="CLP",
            requires_nda=False,
        )
        item_id = await sourcing_service.add_item(
            user_id=buyer_owner,
            organization_id=buyer_org,
            event_id=event_id,
            description=item_description,
            quantity=item_quantity,
            taxonomy_node_id=node_id,
        )
        # Deadline en el futuro para que el proveedor pueda cotizar — recién
        # se mueve al pasado más abajo, justo antes de open_bids, imitando
        # que el plazo real ya venció (mismo patrón de dos fases que el
        # recorrido de fase 7 original).
        await sourcing_service.upsert_stage(
            user_id=buyer_owner, organization_id=buyer_org, event_id=event_id,
            stage_type="BID_DEADLINE",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await sourcing_service.publish_event(
            user_id=buyer_owner, organization_id=buyer_org, event_id=event_id,
        )
        invitation_id = await invitations_service.invite_supplier(
            user_id=buyer_owner, organization_id=buyer_org,
            sourcing_event_id=event_id, supplier_organization_id=supplier_org,
        )
        await invitations_service.get_invitation_detail(
            user_id=supplier_owner, organization_id=supplier_org, invitation_id=invitation_id,
        )

        if outcome == "decline":
            await invitations_service.decline(
                user_id=supplier_owner, organization_id=supplier_org,
                invitation_id=invitation_id, reason_code="NO_CAPACITY",
            )
            print(f"    · {event_name}: {supplier_key} declinó la invitación")
            return {"event_id": event_id}

        await invitations_service.express_interest(
            user_id=supplier_owner, organization_id=supplier_org, invitation_id=invitation_id,
        )
        await invitations_service.confirm_participation(
            user_id=supplier_owner, organization_id=supplier_org, invitation_id=invitation_id,
        )
        total_amount = round(item_quantity * unit_price)
        await quotations_service.submit_revision(
            user_id=supplier_owner, organization_id=supplier_org,
            sourcing_event_id=event_id, currency_code="CLP",
            valid_until=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
            subtotal=total_amount, tax_amount=round(total_amount * 0.19),
            total_amount=round(total_amount * 1.19),
            payment_terms="30 días fin de mes", delivery_days=15,
            warranty_terms=None, exclusions=None, notes=None,
            items=[{"sourcing_event_item_id": item_id, "quantity": item_quantity, "unit_price": unit_price}],
        )

        if outcome == "open":
            print(f"    · {event_name}: {supplier_key} cotizó, proceso queda EN EVALUACIÓN (sin adjudicar)")
            return {"event_id": event_id}

        # Ahora sí, mover el plazo al pasado para poder abrir los sobres.
        await sourcing_service.upsert_stage(
            user_id=buyer_owner, organization_id=buyer_org, event_id=event_id,
            stage_type="BID_DEADLINE",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        await quotations_service.open_bids(
            user_id=buyer_owner, organization_id=buyer_org, sourcing_event_id=event_id,
        )
        quotations = await quotations_service.list_quotations(
            user_id=buyer_owner, organization_id=buyer_org, sourcing_event_id=event_id,
        )
        quotation = next(q for q in quotations if q["supplier_organization_id"] == supplier_org)
        revision_id = quotation["current_revision_id"]

        if outcome == "negotiate_award":
            round_id = await negotiations_service.open_round(
                user_id=buyer_owner, organization_id=buyer_org, sourcing_event_id=event_id,
                round_type="COUNTER", participant_supplier_organization_ids=[supplier_org],
                deadline=datetime.now(timezone.utc) + timedelta(days=3),
                target_reduction_pct=5,
                instructions="Buscamos un 5% de ajuste sobre el precio ofertado.",
            )
            counter_unit_price = round(unit_price * 0.96)
            counter_total = round(item_quantity * counter_unit_price)
            revision_id = await negotiations_service.submit_counter(
                user_id=supplier_owner, organization_id=supplier_org,
                sourcing_event_id=event_id, negotiation_round_id=round_id,
                currency_code="CLP",
                valid_until=(datetime.now(timezone.utc) + timedelta(days=30)).date(),
                subtotal=counter_total, tax_amount=round(counter_total * 0.19),
                total_amount=round(counter_total * 1.19),
                payment_terms="30 días fin de mes", delivery_days=15,
                warranty_terms=None, exclusions=None,
                notes="Contraoferta con 4% de descuento sobre el precio original.",
                items=[{"sourcing_event_item_id": item_id, "quantity": item_quantity, "unit_price": counter_unit_price}],
            )
            await negotiations_service.close_round(
                user_id=buyer_owner, organization_id=buyer_org,
                sourcing_event_id=event_id, negotiation_round_id=round_id,
            )
            print(f"    · {event_name}: ronda de negociación COUNTER — {supplier_key} bajó el precio 4%")

        award_id = await awards_service.propose_award(
            user_id=buyer_owner, organization_id=buyer_org, sourcing_event_id=event_id,
            awarded_organization_id=supplier_org, quotation_revision_id=revision_id,
            justification="Mejor propuesta técnica y comercial recibida.",
            items=[{"sourcing_event_item_id": item_id, "quantity": item_quantity, "unit_price": unit_price}],
        )
        await awards_service.publish_award(
            user_id=buyer_owner, organization_id=buyer_org,
            sourcing_event_id=event_id, award_id=award_id,
        )
        print(f"    · {event_name}: adjudicado a {supplier_key} y cerrado")
        return {"event_id": event_id, "award_id": award_id}

    await run_rfq(
        buyer_key="cordillera", supplier_key="safetypro",
        requirement_name="EPP para turno 2026",
        event_name="RFQ Cascos y protección respiratoria — turno 2026",
        item_description="Cascos certificados + kit protección respiratoria, dotación completa",
        item_quantity=200, node_id=NODE_EPP, unit_price=28_000, outcome="award",
    )
    await run_rfq(
        buyer_key="cordillera", supplier_key="cumbre",
        requirement_name="Transporte de personal a faena — turno 2026",
        event_name="RFQ Transporte de personal — turno 2026",
        item_description="Traslado de personal, 40 pasajeros/día, turno diurno y nocturno",
        item_quantity=40, node_id=NODE_TRANSPORTE_PERSONAS, unit_price=212_500,
        outcome="negotiate_award",
    )
    await run_rfq(
        buyer_key="cordillera", supplier_key="capacitamineria",
        requirement_name="Capacitación DS-132 trabajo en altura",
        event_name="RFQ Capacitación trabajo en altura física",
        item_description="Curso DS-132 para 30 trabajadores de faena",
        item_quantity=30, node_id=NODE_CAPACITACION, unit_price=78_000, outcome="open",
    )
    await run_rfq(
        buyer_key="cordillera", supplier_key="clinicaocupacional",
        requirement_name="Exámenes ocupacionales ingreso 2026",
        event_name="RFQ Batería de exámenes ocupacionales",
        item_description="Exámenes preocupacionales y de altura geográfica, 150 trabajadores",
        item_quantity=150, node_id=node_by_key["clinicaocupacional"], unit_price=33_500,
        outcome="award",
    )
    await run_rfq(
        buyer_key="andes", supplier_key="campamentos",
        requirement_name="Campamento para obra 2026",
        event_name="RFQ Arriendo de campamento modular",
        item_description="Arriendo mensual de campamento modular, 100 camas",
        item_quantity=6, node_id=NODE_CAMPAMENTOS, unit_price=340_000, outcome="award",
    )
    await run_rfq(
        buyer_key="andes", supplier_key="ofinorte",
        requirement_name="Útiles de oficina obra Santiago",
        event_name="RFQ Útiles de oficina — reposición mensual",
        item_description="Pack mensual de útiles de oficina para oficina de obra",
        item_quantity=6, node_id=node_by_key["ofinorte"], unit_price=890_000, outcome="decline",
    )
    await run_rfq(
        buyer_key="andes", supplier_key="aseototal",
        requirement_name="Aseo industrial obra 2026",
        event_name="RFQ Servicio de aseo industrial",
        item_description="Servicio de aseo full-time, contrato de 6 meses",
        item_quantity=6, node_id=NODE_ASEO, unit_price=2_450_000, outcome="award",
    )
    await run_rfq(
        buyer_key="andes", supplier_key="cargaexpress",
        requirement_name="Transporte de carga a obra",
        event_name="RFQ Transporte de carga general",
        item_description="Transporte de carga general, 20 viajes/mes",
        item_quantity=20, node_id=NODE_TRANSPORTE_CARGA, unit_price=420_000, outcome="award",
    )

    # ─── Vendor List ──────────────────────────────────────────────────────────
    print("\nActualizando Vendor List de Minera Cordillera...")
    await vendor_list_service.set_relationship_status(
        user_id=accounts["patricia@mineracordillera.cl"], organization_id=org_ids["cordillera"],
        supplier_organization_id=org_ids["safetypro"], status="APPROVED",
    )
    await vendor_list_service.set_relationship_status(
        user_id=accounts["patricia@mineracordillera.cl"], organization_id=org_ids["cordillera"],
        supplier_organization_id=org_ids["cumbre"], status="APPROVED",
    )
    await vendor_list_service.set_relationship_status(
        user_id=accounts["patricia@mineracordillera.cl"], organization_id=org_ids["cordillera"],
        supplier_organization_id=org_ids["capacitamineria"], status="POTENTIAL",
    )
    print("  ✓ SafetyPro y Cumbre APPROVED, Capacita Minería POTENTIAL")

    # ─── Mensajes directos (no todo pasa por un RFQ) ─────────────────────────
    print("\nGenerando mensajería directa entre empresas...")

    async def send_dm(from_key: str, to_key: str, messages: list[str]) -> None:
        from_owner = accounts[next(c["owner_email"] for c in COMPANIES if c["key"] == from_key)]
        from_org = org_ids[from_key]
        to_org = org_ids[to_key]
        conversation_id = await messaging_service.get_or_create_conversation(
            user_id=from_owner, organization_id=from_org,
            context_type="ORGANIZATION", context_id=to_org,
            participant_organization_ids=[to_org],
        )
        to_owner = accounts[next(c["owner_email"] for c in COMPANIES if c["key"] == to_key)]
        senders = [from_owner, to_owner]
        for i, body in enumerate(messages):
            sender_id = senders[i % 2]
            sender_org = from_org if sender_id == from_owner else to_org
            await messaging_service.send_message(
                user_id=sender_id, organization_id=sender_org,
                conversation_id=conversation_id, body=body,
            )

    await send_dm(
        "cordillera", "factoring",
        [
            "Hola, tenemos facturas aprobadas con OC de proveedores que quieren adelantar pago. "
            "¿Trabajan factoring con confirming desde el comprador?",
            "Sí, hacemos confirming — si ustedes confirman la factura nosotros giramos al proveedor "
            "en 48 horas. ¿Cuál sería el volumen mensual aproximado?",
            "Estimamos unos $80.000.000 mensuales entre 4-5 proveedores. Les paso el contacto de "
            "abastecimiento para coordinar.",
        ],
    )
    await send_dm(
        "andes", "safetypro",
        [
            "Vimos su catálogo de EPP — necesitamos cotizar para un proyecto nuevo, "
            "aparte del proceso que ya tenemos con Minera Cordillera. ¿Atienden RM?",
            "Hola Jorge, sí, despachamos a todo Chile. Cuéntenme el volumen y les preparamos "
            "una cotización marco.",
        ],
    )
    await send_dm(
        "cordillera", "cargaexpress",
        [
            "¿Tienen disponibilidad para carga sobredimensionada, no solo carga general?",
            "Sí, contamos con rampla baja para sobredimensionado. Cualquier cotización puntual "
            "la recibimos directo por acá o vía RFQ en la plataforma.",
        ],
    )
    print("  ✓ 3 conversaciones directas creadas (factoring, EPP, carga)")

    print("\n" + "=" * 70)
    print("Listo. Contraseña para todas las cuentas:", PASSWORD)
    print("=" * 70)
    print("\nCompradores:")
    print("  patricia@mineracordillera.cl (dueña) / tomas@mineracordillera.cl (BUYER_MANAGER) — Minera Cordillera")
    print("  jorge@constructoraandes.cl — Constructora Andes")
    print("\nProveedores (uno por rubro):")
    for company in COMPANIES:
        if "SUPPLIER" in company["capabilities"]:
            print(f"  {company['owner_email']} — {company['trade_name']}")
    print(f"\n  {PLATFORM_ADMIN_EMAIL} (backoffice, sin organización)")
    print(f"  {ACCREDITATION_REVIEWER_EMAIL} (backoffice, sin organización)")
    print(
        "\n8 procesos de compra publicados por los dos compradores, cubriendo los "
        "9 rubros (Factoring se resuelve por mensaje directo, no por RFQ — no es "
        "un bien que se licite). 5 adjudicados y cerrados, 1 con ronda de "
        "negociación antes de adjudicar, 1 abierto en evaluación (Capacitación, "
        "sin adjudicar a propósito) y 1 declinado por el proveedor (Útiles de "
        "oficina). SafetyPro, Transportes Cumbre y Clínica Ocupacional Norte "
        "quedaron ACREDITADAS en ACREDITACION_BASE; el resto no, para que el "
        "badge de acreditación en la ficha pública muestre ambos estados."
    )


if __name__ == "__main__":
    asyncio.run(main())
