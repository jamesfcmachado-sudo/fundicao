"""
Conexão SQLAlchemy com o PostgreSQL do sistema de fundição.

Um único banco (`fundicao`, via DATABASE_URL) concentra:
  - esquema **fabricacao** — ordens de fabricação (OFs), OE, certificados;
  - esquema **corridas** — corridas de fusão e composição química.

Use `SessionLocal` para abrir sessões (Streamlit, scripts, jobs).
A API FastAPI reutiliza estes objetos através de `app.database.get_db`.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

__all__ = [
    "engine",
    "SessionLocal",
    "ping_database",
    "set_audit_user_on_session",
]


def _make_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=False,
    )


engine = _make_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def ping_database() -> tuple[bool, str]:
    """Testa se o PostgreSQL responde (mesma URL usada para OFs e corridas)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Conectado ao banco"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def set_audit_user_on_session(db: Session, login: str | None) -> None:
    """Define app.usuario no PostgreSQL para triggers em fabricacao.* e corridas.*."""
    if not login:
        return
    db.execute(text("SELECT set_config('app.usuario', :login, false)"), {"login": login})
