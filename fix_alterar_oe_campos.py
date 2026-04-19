from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''        # ── Alterar OE ────────────────────────────────────────────────────
        with st.expander(f"✏️ Alterar OE {num_oe_sel}", expanded=False):
            _edit_obs = st.text_area("Observações",
                value=obs_val, key="edit_obs_cons")
            if st.button("💾 Salvar alterações", key="btn_salvar_oe_cons",
                         type="primary"):
                try:
                    from fundicao_db import engine as _eng_upd
                    from sqlalchemy import text as _text_upd
                    with _eng_upd.begin() as _conn_upd:
                        _conn_upd.execute(_text_upd(
                            "UPDATE ordem_entrega SET observacao=:obs WHERE numero_oe=:noe"
                        ), {"obs": _edit_obs, "noe": num_oe_sel})
                        _conn_upd.execute(_text_upd(
                            "UPDATE oe_item SET observacoes=:obs WHERE numero_oe=:noe"
                        ), {"obs": _edit_obs, "noe": num_oe_sel})
                    st.success(f"✅ OE {num_oe_sel} atualizada!")
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erro: {_e}")'''

NEW = '''        # ── Alterar OE ────────────────────────────────────────────────────
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
                    with _eng_upd.begin() as _conn_upd:
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
                        ), {"qtd": _total_qtd, "obs": _edit_obs, "noe": num_oe_sel})

                    st.success(f"✅ OE {num_oe_sel} atualizada com sucesso!")
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erro ao salvar: {_e}")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Alterar OE com campos completos.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Alterar OE com qtd serie corrida certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
