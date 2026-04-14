"""
Motor de base de datos SQLAlchemy.
Define el engine, la sesión y la función para crear tablas.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# Asegurar que el directorio de la DB existe
db_path = settings.database_url.replace("sqlite:///", "")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Engine SQLite — check_same_thread=False necesario para FastAPI (multi-hilo)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,  # Cambiar a True para ver SQL en logs (útil para debug)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""

    pass


def get_db():
    """
    Dependencia FastAPI: provee una sesión de DB por request.
    Se usa con Depends(get_db) en los endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea todas las tablas definidas si no existen."""
    from app.db import models  # noqa: F401 — necesario para registrar modelos

    Base.metadata.create_all(bind=engine)
