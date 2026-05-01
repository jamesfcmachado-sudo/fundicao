"""
Conexão SQLAlchemy com o PostgreSQL do Supabase.
Otimizado com cache de engine e session para performance máxima.
"""

from __future__ import annotations

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

from sqlite_models import Base


def _get_database_url() -> str:
    try:
        import streamlit as st
        url = st.secrets["DATABASE_URL"]
        if url:
            return url
    except Exception:
        pass

    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url

    raise RuntimeError(
        "DATABASE_URL não encontrada. "
        "Configure em .streamlit/secrets.toml ou variável de ambiente."
    )


def _build_engine():
    """Cria o engine com configurações otimizadas para Supabase."""
    DATABASE_URL = _get_database_url()

    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

    if "sslmode" not in DATABASE_URL:
        sep = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,          # mais conexões simultâneas
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=300,      # recicla conexões a cada 5 min
        echo=False,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    )


# Tenta usar cache do Streamlit para manter o engine entre reruns
try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _get_cached_engine():
        return _build_engine()

    engine = _get_cached_engine()

except Exception:
    engine = _build_engine()


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def ping_database() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "PostgreSQL (Supabase) conectado ✅"
    except Exception as exc:
        return False, str(exc)
