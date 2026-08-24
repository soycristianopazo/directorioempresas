"""Validación de RUT chileno.

Espejo exacto de `app.is_valid_rut()` / `app.normalize_rut()` en la base
(backend/alembic/sql/0001_foundation.sql). Se valida en dos lugares a
propósito: aquí para dar feedback inmediato en el request, y en la base como
CHECK constraint — la validación de frontend/API nunca es la única barrera.
"""

from __future__ import annotations

import re

_CLEAN_RE = re.compile(r"[^0-9kK]")


def _clean(rut: str) -> str:
    return _CLEAN_RE.sub("", rut).upper()


def is_valid_rut(rut: str) -> bool:
    clean = _clean(rut)
    if len(clean) < 2 or len(clean) > 9:
        return False

    body, dv = clean[:-1], clean[-1]
    if not body.isdigit():
        return False

    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1

    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)

    return dv == expected


def format_rut(rut: str) -> str:
    """Formato canónico: 76086428-5. Asume que ya pasó is_valid_rut."""
    clean = _clean(rut)
    return f"{clean[:-1]}-{clean[-1]}"
