"""Cliente de Supabase Storage.

El backend conecta a la base de datos de Supabase pero NO usa su capa de
Auth/PostgREST — auth propio, SQL directo (ver app/db/session.py). Storage es
un servicio HTTP aparte (no una tabla que se pueda tocar con SQLAlchemy), así
que necesita su propio cliente.

Autenticación verificada contra la API real: la service_role key de este
proyecto usa el formato nuevo de Supabase (`sb_secret_...`, no un JWT), y la
API de Storage la exige en DOS headers a la vez — `Authorization: Bearer` Y
`apikey`. Mandar solo uno de los dos falla con "Invalid Compact JWS" (el
mensaje que da la API cuando intenta parsear el string como JWT y no lo es) —
un error que no menciona en ningún lado que falta el segundo header. Ambos
headers llevan el mismo valor.

Todas las llamadas usan la service_role key: quien puede invocar estas
funciones ya pasó el chequeo de permiso de la aplicación (organization.update
u offering.write) antes de llegar aquí — Storage nunca ve al usuario final.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class StorageError(Exception):
    pass


def _headers(*, content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def upload_object(
    *, bucket: str, path: str, content: bytes, content_type: str
) -> None:
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={**_headers(content_type=content_type), "x-upsert": "true"},
            content=content,
        )
    if response.status_code >= 400:
        raise StorageError(
            f"No se pudo subir el archivo ({response.status_code}): {response.text}"
        )


async def delete_object(*, bucket: str, path: str) -> None:
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(url, headers=_headers())
    # 404 es aceptable acá: borrar algo que ya no está no debe tumbar el flujo
    # (ej. reintentos, o el registro en Postgres se borró pero el archivo ya
    # no existía).
    if response.status_code >= 400 and response.status_code != 404:
        raise StorageError(
            f"No se pudo borrar el archivo ({response.status_code}): {response.text}"
        )


def public_url(*, bucket: str, path: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{path}"


async def create_signed_url(*, bucket: str, path: str, expires_in: int = 3600) -> str:
    url = f"{settings.supabase_url}/storage/v1/object/sign/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            url,
            headers=_headers(content_type="application/json"),
            json={"expiresIn": expires_in},
        )
    if response.status_code >= 400:
        raise StorageError(
            f"No se pudo firmar la URL ({response.status_code}): {response.text}"
        )
    signed_path = response.json()["signedURL"]
    return f"{settings.supabase_url}/storage/v1{signed_path}"
