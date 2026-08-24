"""Configuración de la aplicación.

Se valida al arrancar. Un fallo de configuración debe reventar en el boot con
un mensaje claro, no en la primera petición con un error opaco.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta, no ".env" relativo. pydantic-settings resuelve env_file contra
# el directorio de trabajo del PROCESO, no contra la ubicación de este
# archivo. Eso funciona cuando se arranca con `cd backend && uvicorn ...`,
# pero se rompe con `uvicorn --app-dir backend` (que ajusta sys.path, no el
# cwd) o con cualquier otro lanzador que invoque desde la raíz del repo —
# exactamente el caso real que lo reveló.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "directorio-empresas"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    sql_echo: bool = False

    # ── Base de datos ────────────────────────────────────────────────────────
    #
    # Dos conexiones distintas y no intercambiables:
    #
    #   database_url  → Transaction Pooler (6543), rol app_user, sujeto a RLS.
    #                   Es la que usa la aplicación.
    #
    #   migration_url → Session Pooler (5432), rol postgres.
    #                   Solo Alembic. El modo transaction no soporta el DDL
    #                   con advisory locks que Alembic necesita.
    database_url: str
    migration_url: str | None = None

    # ── Autenticación ────────────────────────────────────────────────────────
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    bcrypt_rounds: int = 12

    # ── Aplicación ───────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Base pública para URLs canónicas y sitemap del HTML indexable.
    public_base_url: str = "http://localhost:8000"

    # ── Storage (Supabase Storage) ──────────────────────────────────────────
    #
    # El backend es el único que habla con la API de Storage — mismo criterio
    # que con la base de datos: el cliente nunca ve la service_role key, sube
    # el archivo vía multipart a un endpoint de FastAPI, y el backend hace la
    # llamada server-to-server después de validar el permiso correspondiente
    # (organization.update / offering.write). Ver app/core/storage.py.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    @field_validator("database_url", "migration_url")
    @classmethod
    def _validate_dsn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        # asyncpg necesita el esquema postgresql+asyncpg; Supabase entrega
        # postgresql://. Se normaliza aquí para no depender de que quien
        # configure el entorno se acuerde.
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("jwt_secret")
    @classmethod
    def _reject_placeholder_secret(cls, value: str) -> str:
        weak = {"changeme", "secret", "supersecret", "your-secret-key"}
        if value.lower() in weak:
            raise ValueError(
                "JWT_SECRET tiene un valor de marcador. Genera uno real: "
                "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        return value

    @property
    def alembic_url(self) -> str:
        """DSN síncrono para Alembic (psycopg2)."""
        url = self.migration_url or self.database_url
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()


# El PostgresDsn de Pydantic se importa para documentar la intención aunque la
# validación real se haga arriba: Supabase incluye parámetros de query que el
# validador estricto rechaza.
__all__ = ["Settings", "get_settings", "settings", "PostgresDsn"]
