from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''    # ── Carregar dados do banco via SQLAlchemy (PostgreSQL) ─────────────────
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

NEW = '''    # ── Carregar dados do banco via SQLAlchemy (PostgreSQL) ─────────────────
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text

        # Tenta buscar da tabela oe_item (dados historicos detalhados)
        # Se nao existir, busca da ordem_entrega
        with _eng.connect() as _conn:
            # Verifica se tabela oe_item existe
            _tbl_check = _conn.execute(_text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'oe_item'
            """)).scalar()

            if _tbl_check and _tbl_check > 0:
                # Busca da tabela oe_item (itens detalhados)
                _sql_item = """
                    SELECT
                        i.numero_oe,
                        COALESCE(i.qtd, 0)          AS qtd_pecas,
                        COALESCE(i.observacoes, '')  AS observacao,
                        i.criado_em,
                        COALESCE(i.num_of, '')       AS numero_of,
                        COALESCE(i.nome_cliente, '') AS of_cliente,
                        COALESCE(i.num_pedido, '')   AS of_pedido,
                        COALESCE(of.liga, '')        AS of_liga,
                        COALESCE(i.num_oe_seq::TEXT, '') AS numero_oe_seq,
                        COALESCE(i.nome_cliente, '') AS nome_cliente,
                        COALESCE(i.num_pedido, '')   AS num_pedido,
                        COALESCE(i.num_of, '')       AS num_of_ref,
                        COALESCE(i.referencia, '')   AS referencia,
                        COALESCE(i.liga, '')         AS liga,
                        COALESCE(i.corrida, '')      AS corrida,
                        COALESCE(i.certificado, '')  AS certificado,
                        COALESCE(i.cod_peca, '')     AS cod_peca,
                        COALESCE(i.descricao, '')    AS descricao,
                        COALESCE(i.peso_unit, 0)     AS peso_unit,
                        COALESCE(i.serie, '')        AS serie,
                        COALESCE(i.preco_unit, 0)    AS preco_unit,
                        COALESCE(i.preco_total, 0)   AS preco_total,
                        i.criado_em                  AS data_emissao,
                        ''                           AS transportadora,
                        ''                           AS nota_fiscal
                    FROM oe_item i
                    LEFT JOIN ordem_fabricacao of ON of.numero_of = i.num_of
                    ORDER BY i.numero_oe DESC, i.criado_em DESC
                """
                rows = _conn.execute(_text(_sql_item)).fetchall()
            else:
                # Fallback: busca da ordem_entrega
                _sql_oe = """
                    SELECT
                        oe.numero_oe,
                        oe.qtd_pecas,
                        COALESCE(oe.observacao, '') AS observacao,
                        oe.criado_em,
                        of.numero_of,
                        of.nome_cliente  AS of_cliente,
                        COALESCE(of.numero_pedido, '') AS of_pedido,
                        COALESCE(of.liga, '') AS of_liga,
                        '' AS numero_oe_seq, '' AS nome_cliente,
                        '' AS num_pedido, '' AS num_of_ref,
                        '' AS referencia, '' AS liga, '' AS corrida,
                        '' AS certificado, '' AS cod_peca, '' AS descricao,
                        0 AS peso_unit, '' AS serie, 0 AS preco_unit,
                        0 AS preco_total, oe.data_prevista AS data_emissao,
                        '' AS transportadora, '' AS nota_fiscal
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY oe.criado_em DESC
                """
                rows = _conn.execute(_text(_sql_oe)).fetchall()

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
    print("OK: Consulta de OEs atualizada para usar oe_item.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Consulta OEs usa tabela oe_item' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
