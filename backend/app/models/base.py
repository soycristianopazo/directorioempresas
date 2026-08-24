"""Base declarativa de SQLAlchemy.

Los modelos aquí son un ESPEJO del esquema que ya existe en
backend/alembic/sql/ — no lo generan. La fuente de verdad del esquema es el
SQL; estos modelos solo le dan a la aplicación una forma tipada de leerlo y
escribirlo. Por eso no llevan `Base.metadata.create_all()` en ningún lado: eso
crearía tablas sin RLS, sin CHECK constraints, sin las policies que son el
punto central de todo el diseño.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
