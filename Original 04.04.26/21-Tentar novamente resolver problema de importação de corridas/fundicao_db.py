"""
Conexão SQLite local — arquivo fundicao.db na raiz do projeto.
Usado pelo Streamlit (app.py) para OFs, OE, certificados e corridas.
"""

from __future__ import annotations

import sqlite3
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


def _migrar_corrida() -> None:
    """
    Remove o UNIQUE constraint (numero_corrida, data_fusao) da tabela corrida.
    Regra de negócio: a mesma corrida pode ter várias OFs e séries diferentes.
    A unicidade é garantida apenas pela PRIMARY KEY (id = UUID).
    Usa sqlite3 puro com o caminho absoluto de DB_PATH — sem depender do ORM.
    Idempotente: verifica antes de alterar.
    """
    if not DB_PATH.exists():
        return
    try:
        con = sqlite3.connect(str(DB_PATH))
        sql = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='corrida'"
        ).fetchone()
        if not sql or "UNIQUE (numero_corrida, data_fusao)" not in sql[0]:
            con.close()
            return  # já está correto

        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("ALTER TABLE corrida RENAME TO _corrida_bak")
        con.execute("""
            CREATE TABLE corrida (
                id VARCHAR(36) NOT NULL,
                data_fusao DATE NOT NULL,
                numero_corrida VARCHAR(50) NOT NULL,
                nome_cliente VARCHAR(200) NOT NULL,
                ordem_fabricacao_id VARCHAR(36),
                numero_ordem_fabricacao VARCHAR(50),
                qtd_pecas_fundidas INTEGER NOT NULL,
                serie_pecas_fundidas VARCHAR(500),
                liga VARCHAR(120),
                norma VARCHAR(120),
                composicao_quimica_pct JSON NOT NULL,
                criado_em DATETIME NOT NULL,
                atualizado_em DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(ordem_fabricacao_id)
                    REFERENCES ordem_fabricacao (id) ON DELETE SET NULL
            )
        """)
        con.execute("INSERT INTO corrida SELECT * FROM _corrida_bak")
        con.execute("DROP TABLE _corrida_bak")
        con.execute("PRAGMA foreign_keys = ON")
        con.commit()
        con.close()
    except Exception:
        pass


def init_db() -> None:
    _migrar_corrida()          # remove UNIQUE antes de criar/atualizar tabelas
    Base.metadata.create_all(bind=engine)


def ping_database() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"SQLite: `{DB_PATH.name}`"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
