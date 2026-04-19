from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")
lines = src.split('\n')

# ── Fix 1: Remove historico da Nova OE (linha 3343 em diante) ────────────────
# Encontra inicio e fim do bloco do historico
inicio_hist = None
fim_hist = None
for i, line in enumerate(lines):
    if '# ── Histórico de OEs emitidas' in line and inicio_hist is None:
        inicio_hist = i
    if inicio_hist and i > inicio_hist:
        # Fim do bloco = linha vazia seguida de comentario de modulo ou def
        if ('# ══' in line or line.startswith('def ') or
            line.startswith('# ══')):
            fim_hist = i
            break

if inicio_hist and fim_hist:
    # Substitui o bloco pelo comentario
    new_lines = (lines[:inicio_hist] +
                 ['    # Historico removido - use a aba Consulta de OEs', ''] +
                 lines[fim_hist:])
    lines = new_lines
    print(f"OK: Historico removido (linhas {inicio_hist+1} a {fim_hist}).")
else:
    print(f"AVISO: inicio={inicio_hist}, fim={fim_hist}")

# ── Fix 2: Substitui botao PDF antigo na Consulta de OEs ────────────────────
src2 = '\n'.join(lines)

OLD_BTN = '''            if st.button("📄 Gerar PDF desta OE", key="btn_pdf_cons"):
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

NEW_BTN = '''            # ── Alterar OE ────────────────────────────────────────────────
            with st.expander("✏️ Alterar esta OE", expanded=False):
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
                                "DELETE FROM oe_item WHERE numero_oe=:noe"),
                                {"noe": num_oe_sel})
                            _conn_del.execute(_text_del(
                                "DELETE FROM ordem_entrega WHERE numero_oe=:noe"),
                                {"noe": num_oe_sel})
                        st.success(f"✅ OE {num_oe_sel} excluída!")
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Erro: {_e}")'''

if OLD_BTN in src2:
    src2 = src2.replace(OLD_BTN, NEW_BTN, 1)
    print("OK: Alterar/Excluir adicionado na Consulta de OEs.")
else:
    print("AVISO: Botao PDF nao encontrado.")

APP.write_text(src2, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src2)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove hist Nova OE e add alterar excluir' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
