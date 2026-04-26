from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''def pagina_nova_oe():
    """Módulo de Nova Ordem de Entrega."""
    _migrar_banco_oe()
    st.title("📦 Nova Ordem de Entrega")

    # ── Carregar próximo número sequencial ─────────────────────────────────
    try:
        import sqlite3 as _sq
        from fundicao_db import DB_PATH as _FP
        _cx = _sq.connect(str(_FP))
        _cols = {r[1] for r in _cx.execute("PRAGMA table_info(ordem_entrega)").fetchall()}
        if 'numero_oe_seq' in _cols:
            row = _cx.execute("SELECT MAX(numero_oe_seq) FROM ordem_entrega").fetchone()
            proximo_num = (row[0] or 1627) + 1
        else:
            proximo_num = 1629
        _cx.close()
    except Exception:
        proximo_num = 1629'''

NEW = '''def pagina_nova_oe():
    """Módulo de Nova Ordem de Entrega."""
    _migrar_banco_oe()
    st.title("📦 Nova Ordem de Entrega")

    # ── Carregar próximo número sequencial via PostgreSQL ───────────────────
    try:
        from fundicao_db import engine as _eng_oe
        from sqlalchemy import text as _text_oe
        with _eng_oe.connect() as _conn_oe:
            _row = _conn_oe.execute(_text_oe(
                "SELECT MAX(CAST(numero_oe AS INTEGER)) FROM ordem_entrega "
                "WHERE numero_oe ~ '^[0-9]+$'"
            )).fetchone()
            proximo_num = (_row[0] or 1628) + 1
    except Exception:
        proximo_num = 1629'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Proximo numero OE via PostgreSQL.")
else:
    print("AVISO: Bloco proximo numero nao encontrado.")

# Fix 2: Corrige o bloco de gravar OE (remove sqlite3/DB_PATH)
OLD_GRAVAR = '''        if gravar:
            try:
                numero_oe_str = str(int(num_oe))
                # Verifica se número já existe
                import sqlite3 as _sq
                from fundicao_db import DB_PATH as _FP
                _cx2 = _sq.connect(str(_FP))
                existing = _cx2.execute(
                    "SELECT COUNT(*) FROM ordem_entrega WHERE numero_oe=? AND ordem_fabricacao_id=(SELECT id FROM ordem_fabricacao WHERE numero_of=?)",
                    (numero_oe_str, of_selecionada)
                ).fetchone()[0]
                _cx2.close()

                with db_session() as db:
                    of_db = db.scalar(select(OrdemFabricacao).where(OrdemFabricacao.numero_of == of_selecionada))
                    if not of_db:
                        st.error("OF não encontrada no banco.")
                    else:
                        oe = OrdemEntrega(
                            numero_oe=numero_oe_str,
                            qtd_pecas=total_qtd_oe,
                            data_prevista=data_emissao,
                            observacao=observacoes,
                            criado_em=datetime.now(),
                        )
                        of_db.ordens_entrega.append(oe)
                        db.flush()
                        # Gravar campos extras via sqlite3 direto
                        import sqlite3 as _sq2
                        from fundicao_db import DB_PATH as _FP2
                        _cx3 = _sq2.connect(str(_FP2))
                        _cx3.execute(
                            "UPDATE ordem_entrega SET numero_oe_seq=?, data_emissao=?, transportadora=?, placa_veiculo=?, nota_fiscal=? WHERE id=?",
                            (int(num_oe), str(data_emissao), transportadora, placa_veiculo, nota_fiscal, oe.id)
                        )
                        _cx3.commit()
                        _cx3.close()
                st.success(f"✅ OE Nº {numero_oe_str} gravada com sucesso para a OF {of_selecionada}!")
                st.session_state['_oe_gravada_dados'] = {
                    'numero_oe': numero_oe_str,
                    'data_emissao': str(data_emissao),
                    'transportadora': transportadora,
                    'placa_veiculo': placa_veiculo,
                    'nota_fiscal': nota_fiscal,
                    'observacoes': observacoes,
                    'itens': itens,
                }
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")

        if gerar_pdf:
            oe_data = st.session_state.get('_oe_gravada_dados', {
                'numero_oe': str(int(num_oe)),
                'data_emissao': str(data_emissao),
                'transportadora': transportadora,
                'placa_veiculo': placa_veiculo,
                'nota_fiscal': nota_fiscal,
                'observacoes': observacoes,
                'itens': itens,
            })
            try:
                pdf_bytes = _gerar_pdf_oe(oe_data, of_obj)
                st.download_button(
                    "⬇️ Baixar PDF da OE",
                    data=pdf_bytes,
                    file_name=f"OE_{oe_data['numero_oe']}_OF_{of_obj.numero_of}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {e}")'''

NEW_GRAVAR = '''        if gravar:
            try:
                numero_oe_str = str(int(num_oe))
                now = datetime.now().astimezone()
                with db_session() as db:
                    of_db = db.scalar(select(OrdemFabricacao).where(
                        OrdemFabricacao.numero_of == of_selecionada))
                    if not of_db:
                        st.error("OF não encontrada no banco.")
                    else:
                        oe = OrdemEntrega(
                            numero_oe=numero_oe_str,
                            qtd_pecas=total_qtd_oe,
                            data_prevista=data_emissao,
                            observacao=observacoes,
                            criado_em=now,
                        )
                        of_db.ordens_entrega.append(oe)

                # Grava itens na tabela oe_item
                import uuid as _uuid
                from fundicao_db import engine as _eng2
                from sqlalchemy import text as _text2
                with _eng2.begin() as _conn2:
                    for it in itens:
                        _conn2.execute(_text2("""
                            INSERT INTO oe_item (
                                id, numero_oe, num_oe_seq, nome_cliente,
                                num_pedido, num_of, referencia, liga, corrida,
                                certificado, cod_peca, descricao,
                                peso_unit, qtd, serie, preco_unit, preco_total,
                                observacoes, criado_em
                            ) VALUES (
                                :id, :noe, :seq, :cliente,
                                :pedido, :of, :ref, :liga, :corr,
                                :cert, :cod, :desc,
                                :peso, :qtd, :serie, :pu, :pt,
                                :obs, NOW()
                            )
                        """), {
                            "id":      str(_uuid.uuid4()),
                            "noe":     numero_oe_str,
                            "seq":     int(num_oe),
                            "cliente": of_obj.nome_cliente or "",
                            "pedido":  it.get("pedido",""),
                            "of":      it.get("of",""),
                            "ref":     it.get("referencia",""),
                            "liga":    it.get("liga",""),
                            "corr":    it.get("corrida",""),
                            "cert":    it.get("certificado",""),
                            "cod":     it.get("codigo_peca",""),
                            "desc":    it.get("descricao",""),
                            "peso":    float(it.get("peso_unit",0) or 0),
                            "qtd":     int(it.get("qtd",0) or 0),
                            "serie":   it.get("serie",""),
                            "pu":      float(it.get("preco_unit",0) or 0),
                            "pt":      float(it.get("preco_total",0) or 0),
                            "obs":     observacoes or "",
                        })

                st.success(f"✅ OE Nº {numero_oe_str} gravada com sucesso!")
                st.session_state['_oe_gravada_itens'] = itens
                st.session_state['_oe_gravada_num'] = numero_oe_str
                st.session_state['_oe_gravada_obs'] = observacoes
                st.session_state['_oe_gravada_cliente'] = of_obj.nome_cliente or ""
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")

        # ── Botoes PDF e Excel apos gravar ────────────────────────────────
        _num_gravado = st.session_state.get('_oe_gravada_num','')
        if _num_gravado and str(int(num_oe)) == _num_gravado:
            _itens_grav = st.session_state.get('_oe_gravada_itens', itens)
            _obs_grav   = st.session_state.get('_oe_gravada_obs', observacoes)
            _cli_grav   = st.session_state.get('_oe_gravada_cliente', of_obj.nome_cliente if of_obj else "")
            _tmpl_b64   = get_config("template_oe_base64","")
            if _tmpl_b64:
                st.divider()
                st.success(f"OE {_num_gravado} gravada! Gere os documentos:")
                _itens_pdf = [{
                    "num_pedido":  it.get("pedido",""),
                    "num_of":      it.get("of",""),
                    "referencia":  it.get("referencia",""),
                    "liga":        it.get("liga",""),
                    "corrida":     it.get("corrida",""),
                    "certificado": it.get("certificado",""),
                    "cod_peca":    it.get("codigo_peca",""),
                    "descricao":   it.get("descricao",""),
                    "peso_unit":   float(it.get("peso_unit",0) or 0),
                    "qtd":         int(it.get("qtd",0) or 0),
                    "serie":       it.get("serie",""),
                    "preco_unit":  float(it.get("preco_unit",0) or 0),
                    "preco_total": float(it.get("preco_total",0) or 0),
                } for it in _itens_grav]
                _cfg_oe = {
                    "nome_empresa": get_config("nome_empresa"),
                    "endereco":     get_config("endereco"),
                    "bairro":       get_config("bairro"),
                    "cidade":       get_config("cidade"),
                    "estado":       get_config("estado"),
                    "telefone":     get_config("telefone"),
                    "email":        get_config("email"),
                    "contato":      get_config("template_oe_responsavel") or get_config("contato"),
                    "rodape_pdf":   get_config("rodape_pdf"),
                    "orientacao":   get_config("template_oe_orientacao","Paisagem"),
                }
                _logo_bts = None
                try:
                    from empresa_config import get_logo_ativo_bytes
                    _logo_bts = get_logo_ativo_bytes()
                except Exception:
                    pass
                import base64 as _b64m
                _tmpl_bts = _b64m.b64decode(_tmpl_b64)
                from gerar_oe_excel import gerar_oe_excel, gerar_oe_pdf, configurar_impressao_excel
                _excel_bts = gerar_oe_excel(_tmpl_bts, _num_gravado, _cli_grav,
                                             _itens_pdf, _obs_grav, _cfg_oe, _logo_bts)
                _excel_bts = configurar_impressao_excel(_excel_bts, _cfg_oe.get("orientacao","Paisagem"))
                _pdf_bts   = gerar_oe_pdf(_num_gravado, _cli_grav, _itens_pdf,
                                           _obs_grav, _cfg_oe, _logo_bts)
                _db1, _db2 = st.columns(2)
                with _db1:
                    st.download_button(
                        f"⬇️ Baixar OE {_num_gravado} em PDF",
                        data=_pdf_bts,
                        file_name=f"OE_{_num_gravado}.pdf",
                        mime="application/pdf",
                        key="dl_nova_oe_pdf",
                        type="primary",
                    )
                with _db2:
                    st.download_button(
                        f"📊 Baixar OE {_num_gravado} em Excel",
                        data=_excel_bts,
                        file_name=f"OE_{_num_gravado}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_nova_oe_xlsx",
                    )'''

if OLD_GRAVAR in src:
    src = src.replace(OLD_GRAVAR, NEW_GRAVAR, 1)
    print("OK: Gravar OE corrigido com PDF/Excel.")
else:
    print("AVISO: Bloco gravar nao encontrado.")

# Fix 3: Corrige historico de OEs (remove DB_PATH)
OLD_HIST = '''    # ── Histórico de OEs emitidas ──────────────────────────────────────────
    st.divider()
    with st.expander("📚 Histórico de Ordens de Entrega emitidas", expanded=False):
        try:
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

NEW_HIST = '''    # ── Histórico de OEs emitidas ──────────────────────────────────────────
    st.divider()
    with st.expander("📚 Histórico de Ordens de Entrega emitidas", expanded=False):
        try:
            from fundicao_db import engine as _eng_h
            from sqlalchemy import text as _text_h
            with _eng_h.connect() as _conn_h:
                _rows_h = _conn_h.execute(_text_h("""
                    SELECT oe.numero_oe, of.numero_of, of.nome_cliente,
                           oe.qtd_pecas, oe.data_prevista, oe.observacao,
                           oe.criado_em, oe.id
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY oe.criado_em DESC
                    LIMIT 200
                """)).fetchall()
            if _rows_h:
                _df_h = pd.DataFrame(_rows_h, columns=[
                    'Nº OE','OF','Cliente','Qtd Peças','Data','Observação','Criado em','id'])
                _df_h = _df_h.drop(columns=['id','Criado em'])
                st.dataframe(_df_h, use_container_width=True, hide_index=True)

                # Alterar / Excluir OE
                st.divider()
                st.markdown("**✏️ Alterar ou excluir uma OE:**")
                _oe_sel_hist = st.selectbox(
                    "Selecione a OE",
                    options=[r[0] for r in _rows_h],
                    index=None,
                    placeholder="Selecione o Nº da OE...",
                    key="sel_oe_hist"
                )
                if _oe_sel_hist:
                    _row_sel = next((r for r in _rows_h if r[0] == _oe_sel_hist), None)
                    if _row_sel:
                        _hc1, _hc2 = st.columns(2)
                        with _hc1:
                            _nova_obs = st.text_area("Observações",
                                value=_row_sel[5] or "", key="edit_obs_hist")
                        with _hc2:
                            _nova_qtd = st.number_input("Qtd Peças",
                                value=int(_row_sel[3] or 0), min_value=0,
                                key="edit_qtd_hist")
                        _ha1, _ha2 = st.columns(2)
                        with _ha1:
                            if st.button("💾 Salvar alterações", key="btn_salvar_oe_hist",
                                         type="primary"):
                                try:
                                    from fundicao_db import engine as _eng_upd
                                    from sqlalchemy import text as _text_upd
                                    with _eng_upd.begin() as _conn_upd:
                                        _conn_upd.execute(_text_upd("""
                                            UPDATE ordem_entrega
                                            SET observacao=:obs, qtd_pecas=:qtd
                                            WHERE numero_oe=:noe
                                        """), {"obs": _nova_obs,
                                               "qtd": _nova_qtd,
                                               "noe": _oe_sel_hist})
                                    st.success(f"✅ OE {_oe_sel_hist} atualizada!")
                                    st.rerun()
                                except Exception as _e:
                                    st.error(f"Erro: {_e}")
                        with _ha2:
                            if st.button("🗑️ Excluir esta OE", key="btn_excluir_oe_hist"):
                                st.session_state['_confirmar_excluir_oe'] = _oe_sel_hist

                        if st.session_state.get('_confirmar_excluir_oe') == _oe_sel_hist:
                            st.warning(f"⚠️ Confirma exclusão da OE **{_oe_sel_hist}**? Esta ação não pode ser desfeita.")
                            _ex1, _ex2 = st.columns(2)
                            with _ex1:
                                if st.button("✅ Sim, excluir", key="btn_conf_excluir_oe",
                                             type="primary"):
                                    try:
                                        from fundicao_db import engine as _eng_del
                                        from sqlalchemy import text as _text_del
                                        with _eng_del.begin() as _conn_del:
                                            _conn_del.execute(_text_del(
                                                "DELETE FROM oe_item WHERE numero_oe=:noe"),
                                                {"noe": _oe_sel_hist})
                                            _conn_del.execute(_text_del(
                                                "DELETE FROM ordem_entrega WHERE numero_oe=:noe"),
                                                {"noe": _oe_sel_hist})
                                        st.success(f"✅ OE {_oe_sel_hist} excluída!")
                                        st.session_state.pop('_confirmar_excluir_oe', None)
                                        st.rerun()
                                    except Exception as _e:
                                        st.error(f"Erro: {_e}")
                            with _ex2:
                                if st.button("❌ Cancelar", key="btn_canc_excluir_oe"):
                                    st.session_state.pop('_confirmar_excluir_oe', None)
                                    st.rerun()
            else:
                st.info("Nenhuma OE registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")'''

if OLD_HIST in src:
    src = src.replace(OLD_HIST, NEW_HIST, 1)
    print("OK: Historico com alterar/excluir adicionado.")
else:
    print("AVISO: Bloco historico nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Nova OE completa com PDF Excel alterar excluir' && git push")
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
