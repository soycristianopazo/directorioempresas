"""Genera el seed SQL de divisiones administrativas de Chile.

Script de uso único: no se ejecuta en runtime, no requiere conexión a
Postgres. Lee backend/alembic/seed_data/cl_admin_divisions.csv y escribe
backend/alembic/sql/0013_seed_admin_divisions_cl.sql con los tres bloques
`insert into public.admin_divisions (...) values (...)` — regiones,
provincias y comunas, en ese orden (lo exige el trigger de path que arma la
jerarquía a partir del padre ya insertado).

Uso:
    python backend/scripts/gen_admin_divisions_sql.py

Re-ejecutarlo con el mismo CSV produce exactamente el mismo archivo SQL,
byte a byte: los ids son uuid5 deterministas sobre el código único
territorial (CUT), no uuid4 aleatorios.
"""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

# Namespace fijo para esta tabla. Generado una sola vez con uuid.uuid4() y
# congelado aquí — NO regenerar, o los ids dejan de ser estables entre
# corridas.
NAMESPACE_ADMIN_DIVISIONS = uuid.UUID("553c0af4-ef78-44d2-8f8f-7f562faf587e")

COUNTRY_CODE = "CL"

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
CSV_PATH = BACKEND_DIR / "alembic" / "seed_data" / "cl_admin_divisions.csv"
SQL_PATH = BACKEND_DIR / "alembic" / "sql" / "0013_seed_admin_divisions_cl.sql"

EXPECTED_COUNTS = {"1": 16, "2": 56, "3": 346}

HEADER = """\
-- ============================================================================
-- 0013 · Seed de divisiones administrativas de Chile
-- ----------------------------------------------------------------------------
-- 16 regiones + 56 provincias + 346 comunas. Generado desde
-- backend/alembic/seed_data/cl_admin_divisions.csv por
-- backend/scripts/gen_admin_divisions_sql.py — no editar a mano, regenerar
-- desde el CSV si hace falta un cambio.
--
-- UUIDs deterministas (uuid5 sobre el CUT): re-generar este archivo con el
-- mismo CSV produce exactamente el mismo SQL, byte a byte.
--
-- Orden obligatorio: regiones (parent_id NULL) → provincias → comunas. El
-- trigger de path (0012_admin_divisions.sql) necesita que el padre ya exista
-- al insertar el hijo.
-- ============================================================================
"""


def division_id(official_code: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE_ADMIN_DIVISIONS, f"CL:{official_code}")


def sql_string(value: str) -> str:
    """Literal SQL 'texto', escapando comillas simples duplicándolas."""
    return "'" + value.replace("'", "''") + "'"


def sql_number_or_null(value: str) -> str:
    value = value.strip()
    return value if value else "null"


def load_rows() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["level"]] = counts.get(row["level"], 0) + 1

    for level, expected in EXPECTED_COUNTS.items():
        actual = counts.get(level, 0)
        if actual != expected:
            raise ValueError(
                f"nivel {level}: se esperaban {expected} filas, el CSV trae {actual}"
            )

    return rows


def build_values_line(row: dict, parent_id: uuid.UUID | None) -> str:
    row_id = division_id(row["official_code"])
    parent_sql = f"'{parent_id}'" if parent_id is not None else "null"
    return (
        f"  ('{row_id}', '{COUNTRY_CODE}', {parent_sql}, {row['level']}, "
        f"'{row['level_name']}', {sql_string(row['slug'])}, "
        f"{sql_string(row['official_code'])}, {sql_string(row['name'])}, "
        f"{sql_number_or_null(row['lat'])}, {sql_number_or_null(row['lng'])})"
    )


def build_insert_block(rows: list[dict], id_by_code: dict[str, uuid.UUID]) -> str:
    lines = []
    for row in rows:
        parent_code = row["parent_official_code"].strip()
        parent_id = id_by_code[parent_code] if parent_code else None
        lines.append(build_values_line(row, parent_id))

    values_sql = ",\n".join(lines)
    return (
        "insert into public.admin_divisions "
        "(id, country_code, parent_id, level, level_name, slug, official_code, name, lat, lng) values\n"
        f"{values_sql}\n;\n"
    )


def main() -> None:
    rows = load_rows()

    regions = [r for r in rows if r["level"] == "1"]
    provincias = [r for r in rows if r["level"] == "2"]
    comunas = [r for r in rows if r["level"] == "3"]

    # id_by_code se completa progresivamente: las provincias solo necesitan
    # los ids de región ya calculados, las comunas solo los de provincia.
    id_by_code: dict[str, uuid.UUID] = {}
    for row in regions:
        id_by_code[row["official_code"]] = division_id(row["official_code"])
    for row in provincias:
        id_by_code[row["official_code"]] = division_id(row["official_code"])
    for row in comunas:
        id_by_code[row["official_code"]] = division_id(row["official_code"])

    blocks = [
        build_insert_block(regions, id_by_code),
        build_insert_block(provincias, id_by_code),
        build_insert_block(comunas, id_by_code),
    ]

    sql = HEADER + "\n" + "\n".join(blocks)

    SQL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQL_PATH.write_text(sql, encoding="utf-8")

    print(f"OK: {SQL_PATH}")
    print(f"  regiones:   {len(regions)}")
    print(f"  provincias: {len(provincias)}")
    print(f"  comunas:    {len(comunas)}")
    print(f"  total filas: {len(rows)}")


if __name__ == "__main__":
    main()
