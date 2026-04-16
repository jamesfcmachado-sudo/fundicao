from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''    # ── Carregar dados do banco via SQL direto ──────────────────────────────
    try:
        import sqlite3 as _sq
        from fundicao_db import DB_PATH as _FP
        cx = _sq.connect(str(_FP))
        cx.row_factory = _sq.Row

        # Verificar quais colunas extras existem
        _cols = {r[1] for r in cx.execute("PRAGMA table_info(ordem_entrega)").fetchall()}

        # Montar SELECT com colunas condicionais
        col_extras = []
        for c in ["numero_oe_seq","nome_cliente","num_pedido","num_of_ref","referencia",
                  "liga","corrida","certificado","cod_peca","descricao",
                  "peso_unit","serie","preco_unit","preco_total","data_emissao",
                  "transportadora","nota_fiscal"]:
            col_extras.append(f"oe.{c}" if c in _cols else f"'' AS {c}")

        sql = f"""
            SELECT
                oe.numero_oe,
                oe.qtd_pecas,
                oe.observacao,
                REPLACE(oe.criado_em, 'uman', '') AS criado_em,
                of.numero_of,
                of.nome_cliente  AS of_cliente,
                of.numero_pedido AS of_pedido,
                of.liga          AS of_liga,
                {', '.join(col_extras)}
            FROM ordem_entrega oe
            JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
            ORDER BY oe.numero_oe_seq DESC NULLS LAST, oe.criado_em DESC
        """
        rows = cx.execute(sql).fetchall()
        cx.close()

        if not rows:
            st.info("Nenhuma Ordem de Entrega encontrada no banco.")
            return

        # Converter para DataFrame
        df_raw = pd.DataFrame([dict(r) for r in rows])

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return'''

NEW = '''    # ── Carregar dados do banco via SQLAlchemy (PostgreSQL) ─────────────────
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text

        _sql = """
            SELECT
                oe.numero_oe,
                oe.qtd_pecas,
                oe.observacao,
                oe.criado_em,
                of.numero_of,
                of.nome_cliente  AS of_cliente,
                of.numero_pedido AS of_pedido,
                of.liga          AS of_liga,
                '' AS numero_oe_seq,
                '' AS nome_cliente,
                '' AS num_pedido,
                '' AS num_of_ref,
                '' AS referencia,
                '' AS liga,
                '' AS corrida,
                '' AS certificado,
                '' AS cod_peca,
                '' AS descricao,
                0  AS peso_unit,
                '' AS serie,
                0  AS preco_unit,
                0  AS preco_total,
                oe.data_prevista AS data_emissao,
                '' AS transportadora,
                '' AS nota_fiscal
            FROM ordem_entrega oe
            JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
            ORDER BY oe.criado_em DESC
        """

        with _eng.connect() as _conn:
            rows = _conn.execute(_text(_sql)).fetchall()

        if not rows:
            st.info("Nenhuma Ordem de Entrega encontrada no banco.")
            return

        # Converter para DataFrame
        df_raw = pd.DataFrame(rows, columns=[
            'numero_oe','qtd_pecas','observacao','criado_em',
            'numero_of','of_cliente','of_pedido','of_liga',
            'numero_oe_seq','nome_cliente','num_pedido','num_of_ref',
            'referencia','liga','corrida','certificado','cod_peca',
            'descricao','peso_unit','serie','preco_unit','preco_total',
            'data_emissao','transportadora','nota_fiscal'
        ])

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Consulta de OEs corrigida para PostgreSQL.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Corrige consulta OEs PostgreSQL' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
