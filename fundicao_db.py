"""
Conexão SQLAlchemy com o PostgreSQL do Supabase.
Substitui o fundicao_db.py original (SQLite) — mantém a mesma interface
para que o app.py funcione sem alterações de lógica.
"""

from __future__ import annotations

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from sqlite_models import Base

# ── Lê DATABASE_URL do ambiente (Streamlit Secrets ou variável de ambiente) ──
def _get_database_url() -> str:
    # 1) Tenta Streamlit secrets (produção no Streamlit Cloud)
    try:
        import streamlit as st
        url = st.secrets["DATABASE_URL"]
        if url:
            return url
    except Exception:
        pass

    # 2) Tenta variável de ambiente (local com .env)
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url

    raise RuntimeError(
        "DATABASE_URL não encontrada. "
        "Configure em .streamlit/secrets.toml ou variável de ambiente."
    )


DATABASE_URL = _get_database_url()

# Garante o driver correto para SQLAlchemy
# Supabase retorna postgresql:// — SQLAlchemy 2.x precisa de postgresql+psycopg2://
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# Adiciona sslmode=require se não estiver presente
if "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def init_db() -> None:
    """Cria as tabelas se não existirem (idempotente)."""
    Base.metadata.create_all(bind=engine)


def ping_database() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "PostgreSQL (Supabase) conectado ✅"
    except Exception as exc:
        return False, str(exc)
