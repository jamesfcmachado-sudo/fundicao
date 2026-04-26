from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''            st.caption("Altere os campos desejados e clique em Salvar.")

            # Carrega todos os itens da OE do banco
            try:
                from fundicao_db import engine as _eng_alt
                from sqlalchemy import text as _text_alt
                with _eng_alt.connect() as _conn_alt:
                    _itens_alt = _conn_alt.execute(_text_alt("""
                        SELECT id, num_of, referencia, liga, corrida,
                               certificado, cod_peca, descricao,
                               peso_unit, qtd, serie, preco_unit, preco_total
                        FROM oe_item
                        WHERE numero_oe = :noe
                        ORDER BY id
                    """), {"noe": num_oe_sel}).fetchall()
            except Exception as _e:
                _itens_alt = []
                st.error(f"Erro ao carregar itens: {_e}")

            # Observacoes gerais
            _edit_obs = st.text_area("Observações gerais",
                value=obs_val, key="edit_obs_cons")'''

NEW = '''            st.caption("Altere os campos desejados e clique em Salvar.")

            # Carrega todos os itens da OE do banco
            try:
                from fundicao_db import engine as _eng_alt
                from sqlalchemy import text as _text_alt
                with _eng_alt.connect() as _conn_alt:
                    _itens_alt = _conn_alt.execute(_text_alt("""
                        SELECT id, num_of, referencia, liga, corrida,
                               certificado, cod_peca, descricao,
                               peso_unit, qtd, serie, preco_unit, preco_total,
                               nome_cliente, num_pedido
                        FROM oe_item
                        WHERE numero_oe = :noe
                        ORDER BY id
                    """), {"noe": num_oe_sel}).fetchall()
                    # Busca todas as OFs para o selectbox
                    _ofs_disp = _conn_alt.execute(_text_alt(
                        "SELECT numero_of, nome_cliente FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
            except Exception as _e:
                _itens_alt = []
                _ofs_disp = []
                st.error(f"Erro ao carregar itens: {_e}")

            # OF atual
            _of_atual = str(_itens_alt[0]._mapping.get("num_of","")) if _itens_alt else num_of_sel
            _ofs_lista = [r[0] for r in _ofs_disp]
            _of_idx = _ofs_lista.index(_of_atual) if _of_atual in _ofs_lista else 0

            _edit_of = st.selectbox(
                "Ordem de Fabricação (OF)",
                options=_ofs_lista,
                index=_of_idx,
                key="edit_of_cons"
            )

            # Se OF mudou, carrega dados da nova OF
            _of_changed = _edit_of != _of_atual
            if _of_changed:
                try:
                    with _eng_alt.connect() as _conn_of:
                        _of_dados = _conn_of.execute(_text_alt("""
                            SELECT numero_of, nome_cliente, numero_pedido,
                                   liga, descricao_peca, numero_modelo,
                                   peso_liquido_kg, valor_unitario, numero_desenho
                            FROM ordem_fabricacao WHERE numero_of = :of
                        """), {"of": _edit_of}).fetchone()
                except Exception:
                    _of_dados = None
                if _of_dados:
                    st.info(f"✅ OF {_edit_of} selecionada — Cliente: {_of_dados[1]}")
            else:
                _of_dados = None

            # Observacoes gerais
            _edit_obs = st.text_area("Observações gerais",
                value=obs_val, key="edit_obs_cons")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Campo OF adicionado no alterar.")
else:
    print("AVISO: Bloco nao encontrado.")

# Fix 2: Atualiza o salvar para incluir OF e dados da nova OF
OLD_SAVE = '''                    with _eng_upd.begin() as _conn_upd:
                        # Atualiza observacoes na OE
                        _conn_upd.execute(_text_upd(
                            "UPDATE ordem_entrega SET observacao=:obs WHERE numero_oe=:noe"
                        ), {"obs": _edit_obs, "noe": num_oe_sel})

                        # Atualiza cada item
                        _total_qtd = 0
                        for _it_ed in _itens_editados:
                            _pt = _it_ed["qtd"] * _it_ed["preco_unit"]
                            _conn_upd.execute(_text_upd("""
                                UPDATE oe_item SET
                                    qtd          = :qtd,
                                    serie        = :serie,
                                    corrida      = :corrida,
                                    certificado  = :cert,
                                    preco_total  = :pt,
                                    observacoes  = :obs
                                WHERE id = :id
                            """), {
                                "qtd":     _it_ed["qtd"],
                                "serie":   _it_ed["serie"],
                                "corrida": _it_ed["corrida"],
                                "cert":    _it_ed["certificado"],
                                "pt":      _pt,
                                "obs":     _edit_obs,
                                "id":      _it_ed["id"],
                            })
                            _total_qtd += _it_ed["qtd"]

                        # Atualiza total na ordem_entrega
                        _conn_upd.execute(_text_upd(
                            "UPDATE ordem_entrega SET qtd_pecas=:qtd, observacao=:obs WHERE numero_oe=:noe"
                        ), {"qtd": _total_qtd, "obs": _edit_obs, "noe": num_oe_sel})'''

NEW_SAVE = '''                    # Busca dados da OF selecionada
                    with _eng_upd.connect() as _c_of:
                        _of_upd = _c_of.execute(
                            _text_upd("""
                                SELECT numero_of, nome_cliente, numero_pedido,
                                       liga, descricao_peca, numero_modelo,
                                       peso_liquido_kg, valor_unitario, numero_desenho,
                                       id
                                FROM ordem_fabricacao WHERE numero_of = :of
                            """), {"of": _edit_of}
                        ).fetchone()

                    with _eng_upd.begin() as _conn_upd:
                        # Atualiza OF vinculada na ordem_entrega
                        if _of_upd:
                            _conn_upd.execute(_text_upd("""
                                UPDATE ordem_entrega
                                SET observacao=:obs,
                                    ordem_fabricacao_id=:of_id
                                WHERE numero_oe=:noe
                            """), {"obs": _edit_obs,
                                   "of_id": str(_of_upd[9]),
                                   "noe": num_oe_sel})

                        # Atualiza cada item
                        _total_qtd = 0
                        for _it_ed in _itens_editados:
                            _pt = _it_ed["qtd"] * _it_ed["preco_unit"]
                            # Se OF mudou, atualiza dados da OF no item
                            _upd_fields = {
                                "qtd":     _it_ed["qtd"],
                                "serie":   _it_ed["serie"],
                                "corrida": _it_ed["corrida"],
                                "cert":    _it_ed["certificado"],
                                "pt":      _pt,
                                "obs":     _edit_obs,
                                "id":      _it_ed["id"],
                                "num_of":  _edit_of,
                            }
                            if _of_upd:
                                _upd_fields.update({
                                    "cliente":  _of_upd[1] or "",
                                    "pedido":   _of_upd[2] or "",
                                    "liga":     _of_upd[3] or "",
                                    "descricao": _of_upd[4] or "",
                                    "cod_peca": _of_upd[5] or "",
                                    "peso":     float(_of_upd[6] or 0),
                                    "pu":       float(_of_upd[7] or 0),
                                })
                                _conn_upd.execute(_text_upd("""
                                    UPDATE oe_item SET
                                        num_of       = :num_of,
                                        nome_cliente = :cliente,
                                        num_pedido   = :pedido,
                                        liga         = :liga,
                                        descricao    = :descricao,
                                        cod_peca     = :cod_peca,
                                        peso_unit    = :peso,
                                        preco_unit   = :pu,
                                        qtd          = :qtd,
                                        serie        = :serie,
                                        corrida      = :corrida,
                                        certificado  = :cert,
                                        preco_total  = :pt,
                                        observacoes  = :obs
                                    WHERE id = :id
                                """), _upd_fields)
                            else:
                                _conn_upd.execute(_text_upd("""
                                    UPDATE oe_item SET
                                        num_of      = :num_of,
                                        qtd         = :qtd,
                                        serie       = :serie,
                                        corrida     = :corrida,
                                        certificado = :cert,
                                        preco_total = :pt,
                                        observacoes = :obs
                                    WHERE id = :id
                                """), _upd_fields)
                            _total_qtd += _it_ed["qtd"]

                        # Atualiza total na ordem_entrega
                        _conn_upd.execute(_text_upd(
                            "UPDATE ordem_entrega SET qtd_pecas=:qtd WHERE numero_oe=:noe"
                        ), {"qtd": _total_qtd, "noe": num_oe_sel})'''

if OLD_SAVE in src:
    src = src.replace(OLD_SAVE, NEW_SAVE, 1)
    print("OK: Salvar com OF atualizado.")
else:
    print("AVISO: Bloco salvar nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Alterar OF na OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-5), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
