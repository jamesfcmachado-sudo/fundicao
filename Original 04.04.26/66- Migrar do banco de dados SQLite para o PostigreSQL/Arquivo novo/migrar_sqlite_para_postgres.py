"""
migrar_sqlite_para_postgres.py
===============================
Copia todos os dados do fundicao.db (SQLite local) para o PostgreSQL do Supabase.
Execute UMA VEZ na sua máquina local antes de subir o app para a nuvem.

Pré-requisitos:
    pip install sqlalchemy psycopg2-binary python-dotenv

Como rodar:
    1. Coloque este arquivo na mesma pasta do fundicao.db
    2. Crie um arquivo .env com:
           DATABASE_URL=postgresql+psycopg2://postgres:SUA_SENHA@db.sltqmvzgiwwgszdmhwus.supabase.co:5432/postgres?sslmode=require
    3. Execute:
           python migrar_sqlite_para_postgres.py
"""

import os, sqlite3, json, sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

SQLITE_PATH  = Path(__file__).parent / "fundicao.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("❌  DATABASE_URL não encontrada no .env")
    sys.exit(1)

if not SQLITE_PATH.exists():
    print(f"❌  fundicao.db não encontrado em {SQLITE_PATH}")
    sys.exit(1)

print(f"📂  SQLite: {SQLITE_PATH}")
print(f"🌐  PostgreSQL: {DATABASE_URL[:50]}...")

# ── Conexões ──────────────────────────────────────────────────────────────────
sq = sqlite3.connect(str(SQLITE_PATH))
sq.row_factory = sqlite3.Row

pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def agora_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Helpers ───────────────────────────────────────────────────────────────────
def tabela_existe_sq(nome):
    r = sq.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (nome,)
    ).fetchone()
    return r is not None

def coluna_existe_sq(tabela, coluna):
    cols = [r[1] for r in sq.execute(f"PRAGMA table_info({tabela})").fetchall()]
    return coluna in cols


# ── Criar tabelas no PostgreSQL (via SQLAlchemy models) ───────────────────────
print("\n⚙️   Criando tabelas no PostgreSQL…")
from sqlite_models import Base
Base.metadata.create_all(bind=pg_engine)
print("✅  Tabelas criadas (ou já existem).")


# ── Criar tabela oe_item no PostgreSQL (não está nos models SQLAlchemy) ───────
DDL_OE_ITEM = """
CREATE TABLE IF NOT EXISTS oe_item (
    id            VARCHAR(36) PRIMARY KEY,
    numero_oe     TEXT NOT NULL,
    num_oe_seq    INTEGER,
    nome_cliente  TEXT,
    num_pedido    TEXT,
    num_of        TEXT,
    referencia    TEXT,
    liga          TEXT,
    corrida       TEXT,
    certificado   TEXT,
    cod_peca      TEXT,
    descricao     TEXT,
    peso_unit     REAL,
    qtd           INTEGER,
    serie         TEXT,
    preco_unit    REAL,
    preco_total   REAL,
    observacoes   TEXT,
    criado_em     TEXT
)
"""
with pg_engine.begin() as conn:
    conn.execute(text(DDL_OE_ITEM))
print("✅  Tabela oe_item verificada.")


# ── Migrar ordem_fabricacao ───────────────────────────────────────────────────
print("\n📋  Migrando ordem_fabricacao…")
rows_of = sq.execute("SELECT * FROM ordem_fabricacao").fetchall()
ok_of = 0
with pg_engine.begin() as conn:
    # Limpa destino para reimportar com segurança
    conn.execute(text("DELETE FROM ordem_fabricacao"))
    for r in rows_of:
        d = dict(r)
        # status_of pode não existir em bancos antigos
        d.setdefault("status_of", "Ativa")
        conn.execute(text("""
            INSERT INTO ordem_fabricacao (
                id, numero_of, numero_nn, nome_cliente,
                data_abertura_pedido, prazo_entrega_pedido,
                numero_pedido, numero_modelo, descricao_peca, numero_desenho,
                peso_liquido_kg, peso_bruto_kg, liga, norma,
                qtd_pecas_pedido, qtd_fundida, qtd_expedida,
                valor_unitario, valor_total, condicao_modelo,
                observacoes, status_of, criado_em, atualizado_em
            ) VALUES (
                :id, :numero_of, :numero_nn, :nome_cliente,
                :data_abertura_pedido, :prazo_entrega_pedido,
                :numero_pedido, :numero_modelo, :descricao_peca, :numero_desenho,
                :peso_liquido_kg, :peso_bruto_kg, :liga, :norma,
                :qtd_pecas_pedido, :qtd_fundida, :qtd_expedida,
                :valor_unitario, :valor_total, :condicao_modelo,
                :observacoes, :status_of, :criado_em, :atualizado_em
            ) ON CONFLICT (id) DO NOTHING
        """), d)
        ok_of += 1
print(f"   ✅  {ok_of} ordens de fabricação migradas.")


# ── Migrar ordem_entrega ──────────────────────────────────────────────────────
print("📦  Migrando ordem_entrega…")

# Amplia a coluna numero_oe para TEXT no PostgreSQL (alguns valores são muito longos)
with pg_engine.begin() as conn:
    conn.execute(text("ALTER TABLE ordem_entrega ALTER COLUMN numero_oe TYPE TEXT"))
print("   ✅  Coluna numero_oe ampliada para TEXT.")

rows_oe = sq.execute("SELECT * FROM ordem_entrega").fetchall()
ok_oe = 0
with pg_engine.begin() as conn:
    conn.execute(text("DELETE FROM ordem_entrega"))
    for r in rows_oe:
        d = dict(r)
        conn.execute(text("""
            INSERT INTO ordem_entrega (
                id, ordem_fabricacao_id, numero_oe, qtd_pecas,
                data_prevista, observacao, criado_em
            ) VALUES (
                :id, :ordem_fabricacao_id, :numero_oe, :qtd_pecas,
                :data_prevista, :observacao, :criado_em
            ) ON CONFLICT (id) DO NOTHING
        """), d)
        ok_oe += 1
print(f"   ✅  {ok_oe} ordens de entrega migradas.")


# ── Migrar certificado_peca ───────────────────────────────────────────────────
print("📜  Migrando certificado_peca…")

with pg_engine.begin() as conn:
    conn.execute(text("ALTER TABLE certificado_peca ALTER COLUMN numero_certificado TYPE TEXT"))
print("   ✅  Coluna numero_certificado ampliada para TEXT.")

rows_cert = sq.execute("SELECT * FROM certificado_peca").fetchall()
ok_cert = 0
with pg_engine.begin() as conn:
    conn.execute(text("DELETE FROM certificado_peca"))
    for r in rows_cert:
        d = dict(r)
        conn.execute(text("""
            INSERT INTO certificado_peca (
                id, ordem_fabricacao_id, numero_certificado,
                qtd_pecas, data_emissao, observacao, criado_em
            ) VALUES (
                :id, :ordem_fabricacao_id, :numero_certificado,
                :qtd_pecas, :data_emissao, :observacao, :criado_em
            ) ON CONFLICT (id) DO NOTHING
        """), d)
        ok_cert += 1
print(f"   ✅  {ok_cert} certificados migrados.")


# ── Migrar corrida ────────────────────────────────────────────────────────────
print("🔥  Migrando corridas…")
rows_corrida = sq.execute("SELECT * FROM corrida").fetchall()
ok_corrida = 0
with pg_engine.begin() as conn:
    conn.execute(text("DELETE FROM corrida"))
    for r in rows_corrida:
        d = dict(r)
        # composicao_quimica_pct pode estar como string JSON no SQLite
        comp = d.get("composicao_quimica_pct", "{}")
        if isinstance(comp, str):
            try:
                comp = json.loads(comp)
            except Exception:
                comp = {}
        d["composicao_quimica_pct"] = json.dumps(comp)
        conn.execute(text("""
            INSERT INTO corrida (
                id, data_fusao, numero_corrida, nome_cliente,
                ordem_fabricacao_id, numero_ordem_fabricacao,
                qtd_pecas_fundidas, serie_pecas_fundidas,
                liga, norma, composicao_quimica_pct,
                criado_em, atualizado_em
            ) VALUES (
                :id, :data_fusao, :numero_corrida, :nome_cliente,
                :ordem_fabricacao_id, :numero_ordem_fabricacao,
                :qtd_pecas_fundidas, :serie_pecas_fundidas,
                :liga, :norma, CAST(:composicao_quimica_pct AS jsonb),
                :criado_em, :atualizado_em
            ) ON CONFLICT (id) DO NOTHING
        """), d)
        ok_corrida += 1
print(f"   ✅  {ok_corrida} corridas migradas.")


# ── Migrar oe_item (histórico das planilhas) ──────────────────────────────────
if tabela_existe_sq("oe_item"):
    print("📊  Migrando oe_item (histórico)…")
    rows_item = sq.execute("SELECT * FROM oe_item").fetchall()
    ok_item = 0
    with pg_engine.begin() as conn:
        conn.execute(text("DELETE FROM oe_item"))
        for r in rows_item:
            d = dict(r)
            conn.execute(text("""
                INSERT INTO oe_item (
                    id, numero_oe, num_oe_seq, nome_cliente,
                    num_pedido, num_of, referencia, liga, corrida,
                    certificado, cod_peca, descricao,
                    peso_unit, qtd, serie, preco_unit, preco_total,
                    observacoes, criado_em
                ) VALUES (
                    :id, :numero_oe, :num_oe_seq, :nome_cliente,
                    :num_pedido, :num_of, :referencia, :liga, :corrida,
                    :certificado, :cod_peca, :descricao,
                    :peso_unit, :qtd, :serie, :preco_unit, :preco_total,
                    :observacoes, :criado_em
                ) ON CONFLICT (id) DO NOTHING
            """), d)
            ok_item += 1
    print(f"   ✅  {ok_item} itens de OE históricos migrados.")
else:
    print("⚠️   Tabela oe_item não encontrada no SQLite — pulando.")

sq.close()

print(f"\n{'='*55}")
print("✅  MIGRAÇÃO CONCLUÍDA!")
print(f"   OFs:          {ok_of}")
print(f"   OEs:          {ok_oe}")
print(f"   Certificados: {ok_cert}")
print(f"   Corridas:     {ok_corrida}")
print(f"{'='*55}")
print("\nPróximo passo: faça o deploy no Streamlit Cloud! 🚀")
