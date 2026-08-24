"""Punto de entrada para el proceso gestionado por supervisor.

Supervisor arranca `uvicorn server:app` desde /app/backend. La aplicación real
vive en app.main; aquí solo se reexporta para respetar esa convención sin
duplicar configuración.
"""

from app.main import app

__all__ = ["app"]
