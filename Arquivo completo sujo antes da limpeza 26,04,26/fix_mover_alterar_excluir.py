from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# ── Fix 1: Remove alterar/excluir da Consulta de OEs ─────────────────────────
OLD_CONS = '''        # ── Alterar OE ────────────────────────────────────────────────────
        with st.expander(f"✏️ Alterar OE {num_oe_sel}", expanded=False):'''

# Encontra o bloco completo ate o fim do excluir
idx_inicio = src.find('        # ── Alterar OE ────────────────────────────────────────────────────\n        with st.expander(f"✏️ Alterar OE {num_oe_sel}"')
idx_excluir_fim = src.find('                    st.rerun()\n                except Exception as _e:\n                    st.error(f"Erro: {_e}")', idx_inicio)
# Encontra o fechamento do bloco excluir
idx_fim = src.find('\n\n    # ── Exportar CSV', idx_excluir_fim)

if idx_inicio > 0 and idx_fim > 0:
    bloco_alterar_excluir = src[idx_inicio:idx_fim]
    src = src[:idx_inicio] + src[idx_fim:]
    print(f"OK: Alterar/Excluir removido da Consulta de OEs ({len(bloco_alterar_excluir)} chars).")
else:
    bloco_alterar_excluir = ""
    print(f"AVISO: Bloco nao encontrado. inicio={idx_inicio}, fim={idx_fim}")

# ── Fix 2: Adiciona alterar/excluir na Nova OE ───────────────────────────────
NOVO_BLOCO = '''
    # ── Gerenciar OE existente ─────────────────────────────────────────────────
    st.divider()
    with st.expander("🔧 Alterar ou Excluir uma OE existente", expanded=False):
        st.caption("Busque uma OE pelo número para alterar ou excluir.")

        _oe_num_ger = st.text_input("Nº da OE", placeholder="Ex: 1626",
                                     key="ger_oe_num")
        if _oe_num_ger.strip():
            try:
                from fundicao_db import engine as _eng_ger
                from sqlalchemy import text as _text_ger
                with _eng_ger.connect() as _conn_ger:
                    _itens_ger = _conn_ger.execute(_text_ger("""
                        SELECT id, num_of, referencia, liga, corrida,
                               certificado, cod_peca, descricao,
                               peso_unit, qtd, serie, preco_unit, preco_total,
                               nome_cliente, num_pedido
                        FROM oe_item
                        WHERE numero_oe = :noe
                        ORDER BY id
                    """), {"noe": _oe_num_ger.strip()}).fetchall()
                    _ofs_ger = _conn_ger.execute(_text_ger(
                        "SELECT numero_of FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
                    _obs_ger = _conn_ger.execute(_text_ger(
                        "SELECT observacao FROM ordem_entrega WHERE numero_oe=:noe",
                    ), {"noe": _oe_num_ger.strip()}).scalar()

                _ofs_lista_ger = [r[0] for r in _ofs_ger]

                if not _itens_ger:
                    st.warning(f"OE {_oe_num_ger} não encontrada.")
                else:
                    st.success(f"OE {_oe_num_ger} encontrada — {len(_itens_ger)} item(ns)")

                    # ── Alterar ──────────────────────────────────────────────
                    with st.expander(f"✏️ Alterar OE {_oe_num_ger}", expanded=False):
                        st.caption("Selecione o item a alterar, modifique os campos e clique em Salvar.")

                        _edit_obs_ger = st.text_area("Observações gerais",
                            value=_obs_ger or "", key="edit_obs_ger")

                        st.divider()
                        st.markdown("**Selecione o item a alterar:**")

                        _opcoes_ger = {
                            f"Item {i+1}: OF {dict(it._mapping).get('num_of','')} | {dict(it._mapping).get('referencia','')}": i
                            for i, it in enumerate(_itens_ger)
                        }
                        _item_sel_ger = st.selectbox("Item", options=list(_opcoes_ger.keys()),
                                                      key="sel_item_ger")
                        _item_idx_ger = _opcoes_ger[_item_sel_ger]
                        _item_d_ger = dict(_itens_ger[_item_idx_ger]._mapping)
                        _of_atual_ger = str(_item_d_ger.get("num_of",""))

                        st.markdown(f"**Editando:** {_item_d_ger.get('referencia','')} — {_item_d_ger.get('descricao','')}")

                        _gc1, _gc2 = st.columns(2)
                        with _gc1:
                            _edit_of_ger = st.text_input("OF", value=_of_atual_ger, key="edit_of_ger")
                            if _edit_of_ger.strip() and _edit_of_ger.strip() not in _ofs_lista_ger:
                                st.warning(f"OF '{_edit_of_ger}' não encontrada.")
                            _edit_qtd_ger = st.number_input("Quantidade",
                                value=int(_item_d_ger.get("qtd",0) or 0),
                                min_value=0, key="edit_qtd_ger")
                        with _gc2:
                            _edit_serie_ger  = st.text_input("Série",
                                value=str(_item_d_ger.get("serie","") or ""), key="edit_serie_ger")
                            _edit_corr_ger   = st.text_input("Corrida",
                                value=str(_item_d_ger.get("corrida","") or ""), key="edit_corr_ger")
                            _edit_cert_ger   = st.text_input("Certificado",
                                value=str(_item_d_ger.get("certificado","") or ""), key="edit_cert_ger")

                        if st.button("💾 Salvar alterações deste item", key="btn_salvar_ger",
                                     type="primary"):
                            try:
                                from fundicao_db import engine as _eng_upd_g
                                from sqlalchemy import text as _text_upd_g
                                _of_edit_g = _edit_of_ger.strip()
                                with _eng_upd_g.begin() as _conn_upd_g:
                                    _conn_upd_g.execute(_text_upd_g(
                                        "UPDATE ordem_entrega SET observacao=:obs WHERE numero_oe=:noe"
                                    ), {"obs": _edit_obs_ger, "noe": _oe_num_ger.strip()})

                                    _upd_g = {
                                        "id":      _item_d_ger["id"],
                                        "num_of":  _of_edit_g,
                                        "qtd":     _edit_qtd_ger,
                                        "serie":   _edit_serie_ger,
                                        "corrida": _edit_corr_ger,
                                        "cert":    _edit_cert_ger,
                                        "pt":      _edit_qtd_ger * float(_item_d_ger.get("preco_unit",0) or 0),
                                    }
                                    if _of_edit_g in _ofs_lista_ger:
                                        _of_novo_g = _conn_upd_g.execute(_text_upd_g("""
                                            SELECT nome_cliente, numero_pedido, liga,
                                                   descricao_peca, numero_modelo,
                                                   peso_liquido_kg, valor_unitario
                                            FROM ordem_fabricacao WHERE numero_of=:of
                                        """), {"of": _of_edit_g}).fetchone()
                                        if _of_novo_g:
                                            _novo_pu_g = float(_of_novo_g[6] or 0)
                                            _conn_upd_g.execute(_text_upd_g("""
                                                UPDATE oe_item SET
                                                    num_of=:num_of, qtd=:qtd, serie=:serie,
                                                    corrida=:corrida, certificado=:cert,
                                                    preco_total=:pt, nome_cliente=:cli,
                                                    num_pedido=:ped, liga=:liga,
                                                    descricao=:descricao, cod_peca=:cod_peca,
                                                    peso_unit=:peso, preco_unit=:pu
                                                WHERE id=:id
                                            """), {**_upd_g,
                                                   "cli":      _of_novo_g[0] or "",
                                                   "ped":      _of_novo_g[1] or "",
                                                   "liga":     _of_novo_g[2] or "",
                                                   "descricao": _of_novo_g[3] or "",
                                                   "cod_peca": _of_novo_g[4] or "",
                                                   "peso":     float(_of_novo_g[5] or 0),
                                                   "pu":       _novo_pu_g,
                                                   "pt":       _edit_qtd_ger * _novo_pu_g})
                                    else:
                                        _conn_upd_g.execute(_text_upd_g("""
                                            UPDATE oe_item SET
                                                num_of=:num_of, qtd=:qtd, serie=:serie,
                                                corrida=:corrida, certificado=:cert,
                                                preco_total=:pt
                                            WHERE id=:id
                                        """), _upd_g)
                                st.success(f"✅ Item atualizado com sucesso!")
                                st.rerun()
                            except Exception as _e_g:
                                st.error(f"Erro: {_e_g}")

                    # ── Excluir ───────────────────────────────────────────────
                    with st.expander(f"🗑️ Excluir OE {_oe_num_ger}", expanded=False):
                        st.warning(f"⚠️ Excluir a OE **{_oe_num_ger}** removerá todos os seus itens. Esta ação não pode ser desfeita.")
                        if st.button("🗑️ Confirmar exclusão", key="btn_excluir_ger", type="primary"):
                            try:
                                from fundicao_db import engine as _eng_del_g
                                from sqlalchemy import text as _text_del_g
                                with _eng_del_g.begin() as _conn_del_g:
                                    _conn_del_g.execute(_text_del_g(
                                        "DELETE FROM oe_item WHERE numero_oe=:noe"),
                                        {"noe": _oe_num_ger.strip()})
                                    _conn_del_g.execute(_text_del_g(
                                        "DELETE FROM ordem_entrega WHERE numero_oe=:noe"),
                                        {"noe": _oe_num_ger.strip()})
                                st.success(f"✅ OE {_oe_num_ger} excluída!")
                                st.rerun()
                            except Exception as _e_g:
                                st.error(f"Erro: {_e_g}")

            except Exception as _e_ger:
                st.error(f"Erro ao buscar OE: {_e_ger}")

'''

# Adiciona o bloco na Nova OE - apos o comentario "Historico removido"
OLD_HIST_COMMENT = '    # Historico removido - use a aba Consulta de OEs'
if OLD_HIST_COMMENT in src:
    src = src.replace(OLD_HIST_COMMENT,
                      OLD_HIST_COMMENT + NOVO_BLOCO, 1)
    print("OK: Alterar/Excluir adicionado na Nova OE.")
else:
    print("AVISO: Comentario historico nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Move alterar excluir para Nova OE' && git push")
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
