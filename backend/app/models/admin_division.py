"""admin_divisions — jerarquía territorial genérica multi-país."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import FetchedValue, ForeignKey, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import CHAR, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AdminDivision(Base):
    __tablename__ = "admin_divisions"
    # eager_defaults=False: ver el comentario extenso en TaxonomyNode
    # (app/models/taxonomy.py) — mismo problema real de asyncpg decodificando
    # ltree dentro de un RETURNING de INSERT/UPDATE.
    __mapper_args__ = {"eager_defaults": False}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    country_code: Mapped[str] = mapped_column(
        CHAR(2), ForeignKey("countries.code"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_divisions.id", ondelete="RESTRICT")
    )

    # server_default=FetchedValue(): level y path los calcula
    # app.maintain_hierarchy_path() (trigger BEFORE INSERT). Sin este
    # marcador, SQLAlchemy manda un NULL explícito tipado ::SMALLINT/::VARCHAR
    # para cualquier columna sin tocar, y Postgres lo rechaza en el PREPARE
    # por mismatch de tipo contra la columna real (ltree en particular no
    # tiene cast implícito desde varchar) — antes de que el trigger llegue a
    # sobreescribirlo. Con FetchedValue() la columna se omite del INSERT.
    level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=FetchedValue()
    )
    level_name: Mapped[str] = mapped_column(Text, nullable=False)

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    # ltree, mapeado como texto plano — ver el codec registrado en
    # app/db/session.py. La aplicación nunca construye ni compara valores
    # ltree en Python, solo los lee.
    path: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=FetchedValue()
    )
    official_code: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
