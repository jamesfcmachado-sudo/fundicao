from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

changes = 0

# ── Fix 1: Historico de OEs na tela Nova OE ──────────────────────────────────
OLD1 = '''        try:
            import sqlite3 as _sq
            from fundicao_db import DB_PATH as _FP
            _cx = _sq.connect(str(_FP))
            cols = {r[1] for r in _cx.execute("PRAGMA table_info(ordem_entrega)").fetchall()}
            if 'numero_oe_seq' in cols:
                rows = _cx.execute("""
                    SELECT oe.numero_oe, oe.numero_oe_seq, of.numero_of, of.nome_cliente,
                           oe.qtd_pecas, oe.data_prevista, oe.observacao
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY oe.numero_oe_seq DESC NULLS LAST, oe.criado_em DESC
                    LIMIT 200
                """).fetchall()
                _cx.close()
                if rows:
                    df_hist = pd.DataFrame(rows, columns=['Nº OE', 'Seq', 'OF', 'Cliente', 'Qtd Peças', 'Data', 'Observação'])
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma OE registrada ainda.")
            else:
                rows = _cx.execute("""
                    SELECT oe.numero_oe, of.numero_of, of.nome_cliente, oe.qtd_pecas, oe.data_prevista
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY oe.criado_em DESC LIMIT 200
                """).fetchall()
                _cx.close()
                if rows:
                    df_hist = pd.DataFrame(rows, columns=['Nº OE', 'OF', 'Cliente', 'Qtd Peças', 'Data'])
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma OE registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")'''

NEW1 = '''        try:
            from fundicao_db import engine as _eng
            from sqlalchemy import text as _text
            with _eng.connect() as _conn:
                rows = _conn.execute(_text("""
                    SELECT oe.numero_oe, of.numero_of, of.nome_cliente,
                           oe.qtd_pecas, oe.data_prevista, oe.observacao
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY oe.criado_em DESC
                    LIMIT 200
                """)).fetchall()
            if rows:
                df_hist = pd.DataFrame(rows, columns=['Nº OE', 'OF', 'Cliente', 'Qtd Peças', 'Data', 'Observação'])
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma OE registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")'''

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes += 1
    print("OK: Historico de OEs corrigido.")
else:
    print("AVISO: Historico de OEs nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print(f"SINTAXE OK! {changes} correcoes feitas.")
    print("Rode: git add . && git commit -m 'Corrige historico OEs PostgreSQL' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
