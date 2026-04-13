"""
Conexão SQLite local — arquivo fundicao.db na raiz do projeto.
Usado pelo Streamlit (app.py) para OFs, OE, certificados e corridas.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.sqlite_models import Base

DB_PATH = Path(__file__).resolve().parent / "fundicao.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
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
    Base.metadata.create_all(bind=engine)


def ping_database() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"SQLite: `{DB_PATH.name}`"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
