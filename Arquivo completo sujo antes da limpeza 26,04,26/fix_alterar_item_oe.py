from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Substitui o bloco de alterar OE por versao que edita linha por linha
OLD = '''        # ── Alterar OE ────────────────────────────────────────────────────
        with st.expander(f"✏️ Alterar OE {num_oe_sel}", expanded=False):
            st.caption("Altere os campos desejados e clique em Salvar.")

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

            # Campo de texto com sugestoes para buscar OF
            _edit_of_texto = st.text_input(
                "Ordem de Fabricação (OF) — Digite o número",
                value=_of_atual,
                key="edit_of_texto",
                placeholder="Ex: 015B6"
            )
            # Filtra sugestoes com base no que foi digitado
            if _edit_of_texto:
                _sugestoes = [o for o in _ofs_lista
                              if _edit_of_texto.upper() in o.upper()][:10]
                if _sugestoes and _edit_of_texto not in _ofs_lista:
                    st.caption(f"Sugestões: {', '.join(_sugestoes)}")
            _edit_of = _edit_of_texto.strip() if _edit_of_texto.strip() in _ofs_lista else _of_atual
            if _edit_of_texto.strip() and _edit_of_texto.strip() not in _ofs_lista:
                st.warning(f"OF '{_edit_of_texto}' não encontrada. Usando OF atual: {_of_atual}")

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
                value=obs_val, key="edit_obs_cons")

            st.divider()

            # Itens editaveis
            _itens_editados = []
            if _itens_alt:
                st.markdown("**Itens da OE:**")
                for _ii, _item in enumerate(_itens_alt):
                    _item_d = dict(_item._mapping)
                    with st.container(border=True):
                        st.caption(f"Item {_ii+1} — {_item_d.get('referencia','')} | {_item_d.get('descricao','')}")
                        _ac1, _ac2, _ac3, _ac4 = st.columns(4)
                        with _ac1:
                            _new_qtd = st.number_input(
                                "Quantidade",
                                value=int(_item_d.get("qtd", 0) or 0),
                                min_value=0,
                                key=f"alt_qtd_{_ii}"
                            )
                        with _ac2:
                            _new_serie = st.text_input(
                                "Série",
                                value=str(_item_d.get("serie", "") or ""),
                                key=f"alt_serie_{_ii}"
                            )
                        with _ac3:
                            _new_corr = st.text_input(
                                "Corrida",
                                value=str(_item_d.get("corrida", "") or ""),
                                key=f"alt_corr_{_ii}"
                            )
                        with _ac4:
                            _new_cert = st.text_input(
                                "Certificado",
                                value=str(_item_d.get("certificado", "") or ""),
                                key=f"alt_cert_{_ii}"
                            )
                        _itens_editados.append({
                            "id":          _item_d["id"],
                            "qtd":         _new_qtd,
                            "serie":       _new_serie,
                            "corrida":     _new_corr,
                            "certificado": _new_cert,
                            "preco_unit":  float(_item_d.get("preco_unit", 0) or 0),
                        })

            if st.button("💾 Salvar alterações", key="btn_salvar_oe_cons",
                         type="primary"):
                try:
                    from fundicao_db import engine as _eng_upd
                    from sqlalchemy import text as _text_upd
                    # Busca dados da OF selecionada
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
                        ), {"qtd": _total_qtd, "noe": num_oe_sel})

                    st.success(f"✅ OE {num_oe_sel} atualizada com sucesso!")
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erro ao salvar: {_e}")'''

NEW = '''        # ── Alterar OE ────────────────────────────────────────────────────
        with st.expander(f"✏️ Alterar OE {num_oe_sel}", expanded=False):
            st.caption("Selecione o item a alterar, modifique os campos e clique em Salvar.")

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
                    _ofs_disp = _conn_alt.execute(_text_alt(
                        "SELECT numero_of FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
            except Exception as _e:
                _itens_alt = []
                _ofs_disp = []
                st.error(f"Erro ao carregar itens: {_e}")

            _ofs_lista = [r[0] for r in _ofs_disp]

            # Observacoes gerais
            _edit_obs = st.text_area("Observações gerais",
                value=obs_val, key="edit_obs_cons")

            st.divider()
            st.markdown("**Selecione o item a alterar:**")

            # Lista itens para selecionar qual alterar
            if _itens_alt:
                _opcoes_itens = {
                    f"Item {i+1}: OF {dict(it._mapping).get('num_of','')} | {dict(it._mapping).get('referencia','')}": i
                    for i, it in enumerate(_itens_alt)
                }
                _item_sel_label = st.selectbox(
                    "Item",
                    options=list(_opcoes_itens.keys()),
                    key="sel_item_alterar"
                )
                _item_sel_idx = _opcoes_itens[_item_sel_label]
                _item_d = dict(_itens_alt[_item_sel_idx]._mapping)

                st.markdown(f"**Editando:** {_item_d.get('referencia','')} — {_item_d.get('descricao','')}")
                _of_atual_item = str(_item_d.get("num_of",""))

                _bc1, _bc2 = st.columns(2)
                with _bc1:
                    # OF digitavel
                    _edit_of_item = st.text_input(
                        "OF",
                        value=_of_atual_item,
                        key="edit_of_item"
                    )
                    if _edit_of_item.strip() and _edit_of_item.strip() not in _ofs_lista:
                        st.warning(f"OF '{_edit_of_item}' não encontrada.")
                    _edit_qtd = st.number_input(
                        "Quantidade",
                        value=int(_item_d.get("qtd", 0) or 0),
                        min_value=0,
                        key="edit_qtd_item"
                    )
                with _bc2:
                    _edit_serie = st.text_input(
                        "Série",
                        value=str(_item_d.get("serie", "") or ""),
                        key="edit_serie_item"
                    )
                    _edit_corr = st.text_input(
                        "Corrida",
                        value=str(_item_d.get("corrida", "") or ""),
                        key="edit_corr_item"
                    )
                    _edit_cert = st.text_input(
                        "Certificado",
                        value=str(_item_d.get("certificado", "") or ""),
                        key="edit_cert_item"
                    )

                if st.button("💾 Salvar alterações deste item", key="btn_salvar_oe_cons",
                             type="primary"):
                    try:
                        from fundicao_db import engine as _eng_upd
                        from sqlalchemy import text as _text_upd
                        _of_edit = _edit_of_item.strip()

                        with _eng_upd.begin() as _conn_upd:
                            # Atualiza observacao geral
                            _conn_upd.execute(_text_upd(
                                "UPDATE ordem_entrega SET observacao=:obs WHERE numero_oe=:noe"
                            ), {"obs": _edit_obs, "noe": num_oe_sel})

                            # Monta campos para atualizar o item
                            _upd = {
                                "id":      _item_d["id"],
                                "num_of":  _of_edit,
                                "qtd":     _edit_qtd,
                                "serie":   _edit_serie,
                                "corrida": _edit_corr,
                                "cert":    _edit_cert,
                                "pt":      _edit_qtd * float(_item_d.get("preco_unit", 0) or 0),
                            }

                            # Se OF mudou, busca dados da nova OF
                            if _of_edit != _of_atual_item and _of_edit in _ofs_lista:
                                _of_novo = _conn_upd.execute(_text_upd("""
                                    SELECT nome_cliente, numero_pedido, liga,
                                           descricao_peca, numero_modelo,
                                           peso_liquido_kg, valor_unitario
                                    FROM ordem_fabricacao WHERE numero_of=:of
                                """), {"of": _of_edit}).fetchone()
                                if _of_novo:
                                    _conn_upd.execute(_text_upd("""
                                        UPDATE oe_item SET
                                            num_of=:num_of, qtd=:qtd, serie=:serie,
                                            corrida=:corrida, certificado=:cert,
                                            preco_total=:pt,
                                            nome_cliente=:cli, num_pedido=:ped,
                                            liga=:liga
                                        WHERE id=:id
                                    """), {**_upd,
                                           "cli":  _of_novo[0] or "",
                                           "ped":  _of_novo[1] or "",
                                           "liga": _of_novo[2] or ""})
                            else:
                                _conn_upd.execute(_text_upd("""
                                    UPDATE oe_item SET
                                        num_of=:num_of, qtd=:qtd, serie=:serie,
                                        corrida=:corrida, certificado=:cert,
                                        preco_total=:pt
                                    WHERE id=:id
                                """), _upd)

                        st.success(f"✅ Item atualizado com sucesso!")
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Erro ao salvar: {_e}")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Alterar OE por item individual.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Alterar OE por item individual' && git push")
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
