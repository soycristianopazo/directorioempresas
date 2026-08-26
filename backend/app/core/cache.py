"""Caché de lectura en memoria, por proceso.

Sin Redis a propósito (decisión explícita, no un atajo): evita provisionar
infraestructura nueva solo para esto. La contrapartida, real y aceptada: en
un despliegue con más de un worker/proceso, cada uno tiene su propio caché
—no se comparten—, así que el hit rate es menor que con un caché
compartido. TTL corto (segundos, no minutos) a propósito: una invalidación
que se nos escape se autocorrige rápido en vez de servir datos viejos por
mucho tiempo.

Nunca cachear una lectura protegida solo por RLS sin que un chequeo de
permiso EXPLÍCITO y SIN cachear siga corriendo en cada llamada — si no, un
usuario sin acceso puede terminar leyendo del caché algo que otro usuario
autorizado dejó ahí. Ver el uso en app/services/team.py::list_team
(el has_permission corre siempre, fresco) vs
app/services/organizations.py::get_organization_detail (sin gate propio,
por eso la clave de caché incluye el user_id).
"""

from __future__ import annotations

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() >= expires_at:
        _store.pop(key, None)
        return None
    return value


def set(key: str, value: Any, *, ttl_seconds: float) -> None:
    _store[key] = (time.monotonic() + ttl_seconds, value)


def invalidate(key: str) -> None:
    _store.pop(key, None)


def invalidate_prefix(prefix: str) -> None:
    for key in [k for k in _store if k.startswith(prefix)]:
        _store.pop(key, None)
