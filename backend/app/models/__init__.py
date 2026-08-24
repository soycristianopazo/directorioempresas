"""Registra TODOS los modelos contra `Base.metadata` con solo importar este
paquete — necesario porque SQLAlchemy resuelve las FK entre módulos (p.ej.
`accreditation_programs.applies_to_industry_id → industries.id`) por nombre
de tabla contra el metadata compartido, no por el import de Python que
originó la clase. Cualquier entry point que dispare un `flush()`/`commit()`
sin haber importado (aunque sea transitivamente) el módulo dueño de la tabla
referenciada revienta con `NoReferencedTableError` en el primer flush que la
toque, no al importar — el error llega tarde y lejos de la causa real.

En la app real (`app.main`) esto "funciona" porque cada router importa su
servicio, que importa su repositorio, que importa su modelo, y montar TODOS
los routers en `main.py` termina importando todos los modelos de rebote. Ese
encadenamiento es accidental, no una garantía — cualquier script o test que
solo importe una porción del árbol (p.ej. `backend/tests/`, que solo toca
acreditación) puede quedar corto. Importar `app.models` explícitamente hace
la garantía real en vez de accidental.
"""

from __future__ import annotations

from app.models import (  # noqa: F401
    accreditation,
    admin_division,
    attribute,
    badge,
    credentials,
    documents,
    matching,
    offering,
    offering_attribute,
    organization,
    organization_profile,
    rbac,
    reference,
    requirements,
    search,
    sourcing,
    supplier_list,
    taxonomy,
    user,
)
