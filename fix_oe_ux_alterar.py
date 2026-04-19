from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# 1) Adiciona instrucao acima da tabela
OLD_TABLE = '''    # Selecionar linha para ver detalhes
    evento = st.dataframe('''

NEW_TABLE = '''    # Selecionar linha para ver detalhes
    st.caption("💡 **Clique em uma linha** da tabela abaixo para ver os detalhes, gerar PDF/Excel, alterar ou excluir a OE.")
    evento = st.dataframe('''

if OLD_TABLE in src:
    src = src.replace(OLD_TABLE, NEW_TABLE, 1)
    print("OK: Instrucao adicionada acima da tabela.")
else:
    print("AVISO: Tabela nao encontrada.")

# 2) Move alterar/excluir para FORA do expander de detalhes
# Atualmente esta dentro do expander - precisa estar fora
OLD_EXPANDER = '''        with st.expander(f"📋 Detalhes da OE {num_oe_sel} — OF {num_of_sel}", expanded=True):'''

NEW_EXPANDER = '''        with st.expander(f"📋 Detalhes da OE {num_oe_sel} — OF {num_of_sel}", expanded=True):
            st.caption("👆 Role para baixo para ver as opções de Alterar e Excluir.")'''

if OLD_EXPANDER in src:
    src = src.replace(OLD_EXPANDER, NEW_EXPANDER, 1)
    print("OK: Dica adicionada no expander.")
else:
    print("AVISO: Expander nao encontrado.")

# 3) Move alterar/excluir para fora do expander (apos o with st.expander)
# Localiza o bloco de alterar que esta dentro do expander e move para fora
OLD_ALT = '''            # ── Alterar OE ────────────────────────────────────────────────
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

NEW_ALT = '''        # ── Alterar OE ────────────────────────────────────────────────────
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
                    st.error(f"Erro: {_e}")

        # ── Excluir OE ────────────────────────────────────────────────────────
        with st.expander(f"🗑️ Excluir OE {num_oe_sel}", expanded=False):
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

if OLD_ALT in src:
    src = src.replace(OLD_ALT, NEW_ALT, 1)
    print("OK: Alterar/Excluir movidos para fora do expander de detalhes.")
else:
    print("AVISO: Bloco alterar/excluir nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Melhora UX alterar excluir OE' && git push")
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
