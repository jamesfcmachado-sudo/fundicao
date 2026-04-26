from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# ── Fix 1: Remove historico da Nova OE ───────────────────────────────────────
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

NEW_HIST = '''    # Historico removido - use a aba Consulta de OEs'''

if OLD_HIST in src:
    src = src.replace(OLD_HIST, NEW_HIST, 1)
    print("OK: Historico removido da Nova OE.")
else:
    print("AVISO: Historico nao encontrado na Nova OE.")

# ── Fix 2: Adiciona alterar/excluir na Consulta de OEs ──────────────────────
OLD_CONS = '''            # Gerar PDF da OE selecionada
            st.divider()
            if st.button("📄 Gerar PDF desta OE", key="btn_pdf_cons"):
                try:
                    with db_session() as db:
                        of_obj = db.scalar(
                            select(OrdemFabricacao).where(OrdemFabricacao.numero_of == num_of_sel)
                        )
                    if of_obj:
                        oe_data = {
                            "numero_oe":    num_oe_sel,
                            "data_emissao": str(oe_row.get("data_emissao", "") or
                                                pd.to_datetime(oe_row["criado_em"], errors="coerce").strftime("%Y-%m-%d")),
                            "transportadora": str(oe_row.get("transportadora", "") or ""),
                            "placa_veiculo":  str(oe_row.get("placa_veiculo", "") or ""),
                            "nota_fiscal":    str(oe_row.get("nota_fiscal", "") or ""),
                            "observacoes":    obs_val,
                            "itens": [{
                                "pedido":      str(oe_row.get("num_pedido", "") or of_obj.numero_pedido or ""),
                                "of":          num_of_sel,
                                "referencia":  str(oe_row.get("referencia", "") or ""),
                                "liga":        str(oe_row.get("liga", "") or of_obj.liga or ""),
                                "corrida":     str(oe_row.get("corrida", "") or ""),
                                "certificado": str(oe_row.get("certificado", "") or ""),
                                "codigo_peca": str(oe_row.get("cod_peca", "") or ""),
                                "descricao":   str(oe_row.get("descricao", "") or of_obj.descricao_peca or ""),
                                "peso_unit":   float(oe_row.get("peso_unit", 0) or 0),
                                "qtd":         int(oe_row.get("qtd_pecas", 0) or 0),
                                "serie":       str(oe_row.get("serie", "") or ""),
                                "preco_unit":  float(oe_row.get("preco_unit", 0) or 0),
                                "preco_total": float(oe_row.get("preco_total", 0) or 0),
                            }],
                        }
                        pdf_bytes = _gerar_pdf_oe(oe_data, of_obj)
                        st.download_button(
                            "⬇️ Baixar PDF",
                            data=pdf_bytes,
                            file_name=f"OE_{num_oe_sel}_OF_{num_of_sel}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error(f"OF {num_of_sel} não encontrada no banco.")
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")'''

NEW_CONS = '''            # ── Alterar OE ────────────────────────────────────────────────
            st.divider()
            with st.expander("✏️ Alterar esta OE", expanded=False):
                _edit_obs = st.text_area("Observações",
                    value=obs_val, key="edit_obs_cons")
                if st.button("💾 Salvar alterações", key="btn_salvar_oe_cons",
                             type="primary"):
                    try:
                        from fundicao_db import engine as _eng_upd
                        from sqlalchemy import text as _text_upd
                        with _eng_upd.begin() as _conn_upd:
                            _conn_upd.execute(_text_upd("""
                                UPDATE ordem_entrega
                                SET observacao = :obs
                                WHERE numero_oe = :noe
                            """), {"obs": _edit_obs, "noe": num_oe_sel})
                            _conn_upd.execute(_text_upd("""
                                UPDATE oe_item
                                SET observacoes = :obs
                                WHERE numero_oe = :noe
                            """), {"obs": _edit_obs, "noe": num_oe_sel})
                        st.success(f"✅ OE {num_oe_sel} atualizada!")
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Erro: {_e}")

            # ── Excluir OE ────────────────────────────────────────────────────
            with st.expander("🗑️ Excluir esta OE", expanded=False):
                st.warning(f"⚠️ Excluir a OE **{num_oe_sel}** removerá todos os seus itens. Esta ação não pode ser desfeita.")
                if st.button("🗑️ Confirmar exclusão", key="btn_excluir_oe_cons",
                             type="primary"):
                    try:
                        from fundicao_db import engine as _eng_del
                        from sqlalchemy import text as _text_del
                        with _eng_del.begin() as _conn_del:
                            _conn_del.execute(_text_del(
                                "DELETE FROM oe_item WHERE numero_oe = :noe"),
                                {"noe": num_oe_sel})
                            _conn_del.execute(_text_del(
                                "DELETE FROM ordem_entrega WHERE numero_oe = :noe"),
                                {"noe": num_oe_sel})
                        st.success(f"✅ OE {num_oe_sel} excluída com sucesso!")
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Erro: {_e}")'''

if OLD_CONS in src:
    src = src.replace(OLD_CONS, NEW_CONS, 1)
    print("OK: Alterar/Excluir adicionado na Consulta de OEs.")
else:
    print("AVISO: Bloco consulta nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove hist Nova OE e add alterar excluir Consulta OEs' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
