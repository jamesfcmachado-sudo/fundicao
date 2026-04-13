"""
Execute este script UMA VEZ para adicionar a coluna status_of à tabela ordem_fabricacao.

Como rodar:
    python migrar_status_of.py

Coloque este script na mesma pasta do fundicao.db e do app.py.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "fundicao.db"

if not DB_PATH.exists():
    print(f"ERRO: fundicao.db não encontrado em {DB_PATH}")
    input("\nPressione Enter para fechar...")
    exit(1)

print(f"Banco encontrado: {DB_PATH}")

con = sqlite3.connect(str(DB_PATH))

cols = [r[1] for r in con.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]

if "status_of" in cols:
    print("✅ Coluna status_of já existe — nenhuma alteração necessária.")
    con.close()
    input("\nPressione Enter para fechar...")
    exit(0)

print("Adicionando coluna status_of...")

try:
    con.execute("ALTER TABLE ordem_fabricacao ADD COLUMN status_of VARCHAR(20) DEFAULT 'Ativa'")
    con.commit()

    cols2 = [r[1] for r in con.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]
    count = con.execute("SELECT COUNT(*) FROM ordem_fabricacao").fetchone()[0]

    if "status_of" in cols2:
        print(f"✅ Coluna adicionada com sucesso! {count} registros preservados.")
        print("\nAgora você pode:")
        print("  - Reiniciar o Streamlit")
        print("  - Ir em Relatórios → Ordens de Fabricação")
        print("  - Selecionar uma OF → Alterar → Cancelar OF ou Finalizar OF")
    else:
        print("❌ Algo deu errado.")

except Exception as e:
    print(f"❌ Erro: {e}")

con.close()
input("\nPressione Enter para fechar...")
