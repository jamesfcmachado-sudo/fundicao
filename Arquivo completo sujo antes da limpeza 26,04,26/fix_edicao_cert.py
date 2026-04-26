from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        st.session_state["_editar_cert_id"]   = str(_cm_alt["id"])
                        st.session_state["_editar_cert_num"]  = _cm_alt["numero_cert"]
                        st.info("Recurso de edição em desenvolvimento. "
                                "Por enquanto, exclua e recrie o certificado.")'''

NEW = '''                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        # Carrega dados completos para edicao
                        try:
                            with engine.connect() as _conn_ed:
                                _corridas_ed = _conn_ed.execute(text("""
                                    SELECT numero_of, numero_corrida,
                                           c, si, mn, p, s, cr, ni, mo
                                    FROM certificado_corrida
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                                _itens_ed = _conn_ed.execute(text("""
                                    SELECT pedido, modelo, descricao,
                                           series, quantidade
                                    FROM certificado_item
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                            st.session_state["_editar_cert_id"]      = str(_cm_alt["id"])
                            st.session_state["_editar_cert_num"]     = _cm_alt["numero_cert"]
                            st.session_state["_editar_cert_data"]    = dict(_cm_alt)
                            st.session_state["_editar_cert_corridas"] = [dict(r._mapping) for r in _corridas_ed]
                            st.session_state["_editar_cert_itens"]   = [dict(r._mapping) for r in _itens_ed]
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erro ao carregar dados: {_e}")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botao editar carrega dados.")
else:
    print("AVISO: Bloco nao encontrado.")

# Adiciona formulario de edicao antes do expander
OLD_TITULO = '''    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    st.subheader("🔧 Alterar ou Excluir Certificado Existente")
    with st.expander("Clique para buscar um certificado", expanded=False):'''

NEW_TITULO = '''    # ── Formulario de Edicao ──────────────────────────────────────────────────
    if st.session_state.get("_editar_cert_id"):
        _ed_data     = st.session_state.get("_editar_cert_data", {})
        _ed_corridas = st.session_state.get("_editar_cert_corridas", [])
        _ed_itens    = st.session_state.get("_editar_cert_itens", [])
        _ed_num      = st.session_state.get("_editar_cert_num", "")

        st.divider()
        st.subheader(f"✏️ Editando Certificado {_ed_num}")

        with st.container(border=True):
            st.markdown("**Dados Gerais**")
            _ec1, _ec2 = st.columns(2)
            with _ec1:
                _ed_cliente = st.text_input("Cliente", value=_ed_data.get("cliente",""), key="ed_cliente")
                _ed_norma   = st.text_input("Norma", value=_ed_data.get("norma",""), key="ed_norma")
            with _ec2:
                _ed_liga    = st.text_input("Liga", value=_ed_data.get("liga",""), key="ed_liga")
                _ed_nf      = st.text_input("Nota Fiscal", value=str(_ed_data.get("nota_fiscal","") or ""), key="ed_nf")
            _ed_obs    = st.text_area("Observações", value=str(_ed_data.get("observacoes","") or ""), key="ed_obs", height=60)
            _ed_outros = st.text_area("Outros Ensaios", value=str(_ed_data.get("outros_ensaios","") or ""), key="ed_outros", height=60)

        # Corridas
        with st.container(border=True):
            st.markdown("**Composição Química (Corridas)**")
            ELEM_ED = ["c","si","mn","p","s","cr","ni","mo"]
            _ed_corridas_novo = []
            for _eci, _ec in enumerate(_ed_corridas):
                st.caption(f"Corrida {_eci+1}")
                _ecc1, _ecc2 = st.columns(2)
                with _ecc1:
                    _ec_nof  = st.text_input("OF", value=_ec.get("numero_of",""), key=f"ed_nof_{_eci}")
                with _ecc2:
                    _ec_ncorr = st.text_input("Nº Corrida", value=_ec.get("numero_corrida",""), key=f"ed_ncorr_{_eci}")
                _ec_cols = st.columns(8)
                _ec_comp = {}
                for _ej, _ek in enumerate(ELEM_ED):
                    with _ec_cols[_ej]:
                        _ec_comp[_ek] = st.number_input(
                            _ek.upper(),
                            value=float(_ec.get(_ek, 0) or 0),
                            format="%.4f",
                            key=f"ed_comp_{_eci}_{_ek}",
                            min_value=0.0
                        )
                _ed_corridas_novo.append({
                    "numero_of": _ec_nof, "numero_corrida": _ec_ncorr,
                    **_ec_comp
                })

        # Itens
        with st.container(border=True):
            st.markdown("**Itens**")
            _ed_itens_novo = []
            for _eii, _ei in enumerate(_ed_itens):
                _ei1, _ei2, _ei3, _ei4, _ei5 = st.columns([2,2,3,2,1])
                with _ei1:
                    _ei_ped = st.text_input("Pedido", value=_ei.get("pedido",""), key=f"ed_ped_{_eii}")
                with _ei2:
                    _ei_mod = st.text_input("Modelo", value=_ei.get("modelo",""), key=f"ed_mod_{_eii}")
                with _ei3:
                    _ei_desc = st.text_input("Descrição", value=_ei.get("descricao",""), key=f"ed_desc_{_eii}")
                with _ei4:
                    _ei_ser = st.text_input("Série", value=str(_ei.get("series","") or ""), key=f"ed_ser_{_eii}")
                with _ei5:
                    _ei_qtd = st.number_input("Qtd", value=int(_ei.get("quantidade",0) or 0), min_value=0, key=f"ed_qtd_{_eii}")
                _ed_itens_novo.append({
                    "pedido": _ei_ped, "modelo": _ei_mod,
                    "descricao": _ei_desc, "series": _ei_ser, "quantidade": _ei_qtd
                })

        _ebtn1, _ebtn2 = st.columns(2)
        with _ebtn1:
            if st.button("💾 Salvar Alterações", key="btn_salvar_edicao", type="primary"):
                try:
                    _cert_id_ed = st.session_state["_editar_cert_id"]
                    with engine.begin() as _conn_save:
                        # Atualiza dados gerais
                        _conn_save.execute(text("""
                            UPDATE certificado_qualidade
                            SET cliente=:cli, norma=:nor, liga=:lig,
                                nota_fiscal=:nf, observacoes=:obs,
                                outros_ensaios=:out
                            WHERE id=:id
                        """), {"cli": _ed_cliente, "nor": _ed_norma,
                               "lig": _ed_liga, "nf": _ed_nf,
                               "obs": _ed_obs, "out": _ed_outros,
                               "id": _cert_id_ed})

                        # Deleta e reinicia corridas
                        _conn_save.execute(text(
                            "DELETE FROM certificado_corrida WHERE certificado_id=:id"
                        ), {"id": _cert_id_ed})
                        for _nc in _ed_corridas_novo:
                            if _nc["numero_corrida"]:
                                _conn_save.execute(text("""
                                    INSERT INTO certificado_corrida
                                    (certificado_id, numero_of, numero_corrida,
                                     c, si, mn, p, s, cr, ni, mo)
                                    VALUES (:cid, :nof, :nc,
                                     :c, :si, :mn, :p, :s, :cr, :ni, :mo)
                                """), {"cid": _cert_id_ed,
                                       "nof": _nc["numero_of"],
                                       "nc":  _nc["numero_corrida"],
                                       "c":   _nc["c"],  "si": _nc["si"],
                                       "mn":  _nc["mn"], "p":  _nc["p"],
                                       "s":   _nc["s"],  "cr": _nc["cr"],
                                       "ni":  _nc["ni"], "mo": _nc["mo"]})

                        # Deleta e reinicia itens
                        _conn_save.execute(text(
                            "DELETE FROM certificado_item WHERE certificado_id=:id"
                        ), {"id": _cert_id_ed})
                        for _ni in _ed_itens_novo:
                            if _ni["pedido"] or _ni["descricao"]:
                                _conn_save.execute(text("""
                                    INSERT INTO certificado_item
                                    (certificado_id, pedido, modelo,
                                     descricao, series, quantidade)
                                    VALUES (:cid, :ped, :mod, :desc, :ser, :qtd)
                                """), {"cid": _cert_id_ed,
                                       "ped": _ni["pedido"],
                                       "mod": _ni["modelo"],
                                       "desc": _ni["descricao"],
                                       "ser": _ni["series"],
                                       "qtd": _ni["quantidade"]})

                    st.success(f"✅ Certificado {_ed_num} atualizado com sucesso!")
                    # Limpa session_state
                    for _k in ["_editar_cert_id","_editar_cert_num",
                               "_editar_cert_data","_editar_cert_corridas",
                               "_editar_cert_itens"]:
                        st.session_state.pop(_k, None)
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erro ao salvar: {_e}")

        with _ebtn2:
            if st.button("❌ Cancelar Edição", key="btn_cancelar_edicao"):
                for _k in ["_editar_cert_id","_editar_cert_num",
                           "_editar_cert_data","_editar_cert_corridas",
                           "_editar_cert_itens"]:
                    st.session_state.pop(_k, None)
                st.rerun()

    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    st.subheader("🔧 Alterar ou Excluir Certificado Existente")
    with st.expander("Clique para buscar um certificado", expanded=False):'''

if OLD_TITULO in src:
    src = src.replace(OLD_TITULO, NEW_TITULO, 1)
    print("OK: Formulario de edicao adicionado.")
else:
    print("AVISO: Titulo nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Edicao completa certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-3), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
