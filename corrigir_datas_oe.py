import sqlite3, re
from pathlib import Path

DB_PATH = Path(__file__).parent / "fundicao.db"
cx = sqlite3.connect(str(DB_PATH))

rows = cx.execute("SELECT id, criado_em FROM ordem_entrega WHERE criado_em LIKE '%uman%'").fetchall()
print(f"Registros com data corrompida: {len(rows)}")

for row_id, criado_em in rows:
    corrigido = re.sub(r'(\d{2})uman', r'\1', criado_em)
    cx.execute("UPDATE ordem_entrega SET criado_em = ? WHERE id = ?", (corrigido, row_id))

cx.commit()
cx.close()
print("✅  Datas corrigidas com sucesso!")
