"""taxonomy_nodes e industries: los dos ejes ortogonales de clasificación de
oferta (qué se vende / a quién se le vende). Ver docs/01-ARQUITECTURA.md §D.2.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import FetchedValue, ForeignKey, Integer, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

TaxonomyNodeTypeEnum = ENUM(
    "CATEGORY",
    "SUBCATEGORY",
    "SPECIALTY",
    "SERVICE",
    "PRODUCT",
    name="taxonomy_node_type",
    schema="app",
    create_type=False,
)
RiskLevelEnum = ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="risk_level",
    schema="app",
    create_type=False,
)


class TaxonomyNode(Base):
    __tablename__ = "taxonomy_nodes"
    # eager_defaults=False: `path`/`level` no se cargan automáticamente vía
    # RETURNING tras el INSERT — el repositorio ya hace un session.refresh()
    # explícito para traerlos con un SELECT aparte. No es estrictamente
    # necesario (el problema real que motivó esto era otro, ver
    # backend/alembic/sql/0012_admin_divisions.sql), pero es más predecible
    # no depender de RETURNING para columnas que un trigger calcula.
    __mapper_args__ = {"eager_defaults": False}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT")
    )

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    # server_default=FetchedValue(): level y path los calcula
    # app.maintain_hierarchy_path() (trigger BEFORE INSERT), nunca la
    # aplicación. Sin este marcador, SQLAlchemy manda NULL explícito tipado
    # ::VARCHAR/::SMALLINT para cualquier columna sin tocar en el objeto
    # Python — y Postgres rechaza ese bind en el PREPARE por mismatch de tipo
    # contra la columna real, antes de que el trigger llegue a
    # sobreescribirlo. Con FetchedValue(), SQLAlchemy omite la columna del
    # INSERT por completo.
    level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=FetchedValue()
    )
    node_type: Mapped[str] = mapped_column(TaxonomyNodeTypeEnum, nullable=False)
    # ltree como texto plano — ver el codec en app/db/session.py. El trigger
    # que la calcula usa extensions.ltree calificado explícitamente, no
    # ltree a secas — ver el porqué en 0012_admin_divisions.sql.
    path: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=FetchedValue()
    )

    is_leaf: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    risk_level: Mapped[str | None] = mapped_column(RiskLevelEnum)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class TaxonomyNodeTranslation(Base):
    __tablename__ = "taxonomy_node_translations"

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    language_code: Mapped[str] = mapped_column(
        Text, ForeignKey("languages.code"), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class TaxonomyNodeSynonym(Base):
    __tablename__ = "taxonomy_node_synonyms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    synonym: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(
        Text, ForeignKey("languages.code"), nullable=False, server_default="es-CL"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class TaxonomyExternalMapping(Base):
    __tablename__ = "taxonomy_external_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    standard: Mapped[str] = mapped_column(Text, nullable=False)
    external_code: Mapped[str] = mapped_column(Text, nullable=False)
    external_label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class Industry(Base):
    __tablename__ = "industries"
    # eager_defaults=False: ver el comentario extenso en TaxonomyNode.
    __mapper_args__ = {"eager_defaults": False}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("industries.id", ondelete="RESTRICT")
    )

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    # server_default=FetchedValue(): ver el comentario en TaxonomyNode.level.
    level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=FetchedValue()
    )
    path: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=FetchedValue()
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    name: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class IndustryTranslation(Base):
    __tablename__ = "industry_translations"

    industry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    language_code: Mapped[str] = mapped_column(
        Text, ForeignKey("languages.code"), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
