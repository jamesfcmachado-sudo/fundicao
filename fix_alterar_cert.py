from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Adiciona seção antes do fim da função tela_novo_certificado
OLD = '''        except Exception as e:
            st.error(f"Erro ao salvar: {e}")


# ── Tela Consulta de Certificados ─────────────────────────────────────────────
def tela_consulta_certificados():'''

NEW = '''        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    with st.expander("🔧 Alterar ou Excluir Certificado Existente"):
        st.caption("Busque um certificado pelo número para editar ou excluir.")

        _num_alt = st.text_input("Nº do Certificado",
                                  placeholder="Ex: 2034/26",
                                  key="alt_cert_num")

        if _num_alt.strip():
            try:
                with engine.connect() as _conn_alt:
                    _cert_alt = _conn_alt.execute(text("""
                        SELECT id, numero_cert, cliente, norma, liga,
                               data_emissao, nota_fiscal, observacoes,
                               outros_ensaios, tipo_template
                        FROM certificado_qualidade
                        WHERE numero_cert = :nc
                        LIMIT 1
                    """), {"nc": _num_alt.strip()}).fetchone()
            except Exception as _e:
                st.error(f"Erro ao buscar: {_e}")
                _cert_alt = None

            if _cert_alt:
                _cm_alt = _cert_alt._mapping
                st.success(f"✅ Certificado encontrado: {_cm_alt['numero_cert']} — {_cm_alt['cliente']}")

                _col1, _col2 = st.columns(2)
                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        st.session_state["_editar_cert_id"]   = str(_cm_alt["id"])
                        st.session_state["_editar_cert_num"]  = _cm_alt["numero_cert"]
                        st.info("Recurso de edição em desenvolvimento. "
                                "Por enquanto, exclua e recrie o certificado.")

                with _col2:
                    if st.button("🗑️ Excluir este certificado",
                                 key="btn_excluir_cert",
                                 type="secondary"):
                        st.session_state["_confirmar_excluir_cert"] = str(_cm_alt["id"])
                        st.session_state["_confirmar_excluir_num"]  = _cm_alt["numero_cert"]

                # Confirmacao de exclusao
                if st.session_state.get("_confirmar_excluir_cert") == str(_cm_alt["id"]):
                    st.warning(f"⚠️ Tem certeza que deseja excluir o certificado "
                               f"**{_cm_alt['numero_cert']}**? Esta ação não pode ser desfeita!")
                    _cc1, _cc2 = st.columns(2)
                    with _cc1:
                        if st.button("✅ Sim, excluir", key="btn_confirmar_excluir",
                                     type="primary"):
                            try:
                                with engine.begin() as _conn_del:
                                    _cert_id_del = str(_cm_alt["id"])
                                    # Exclui registros filhos primeiro
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_item WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_corrida WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM ensaio_mecanico WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_qualidade WHERE id = :id"
                                    ), {"id": _cert_id_del})
                                st.success(f"✅ Certificado {_cm_alt['numero_cert']} excluído!")
                                st.session_state.pop("_confirmar_excluir_cert", None)
                                st.session_state.pop("_confirmar_excluir_num", None)
                                st.rerun()
                            except Exception as _e:
                                st.error(f"Erro ao excluir: {_e}")
                    with _cc2:
                        if st.button("❌ Cancelar", key="btn_cancelar_excluir"):
                            st.session_state.pop("_confirmar_excluir_cert", None)
                            st.session_state.pop("_confirmar_excluir_num", None)
                            st.rerun()
            else:
                st.warning(f"Certificado '{_num_alt.strip()}' não encontrado.")


# ── Tela Consulta de Certificados ─────────────────────────────────────────────
def tela_consulta_certificados():'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Secao alterar/excluir adicionada.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Alterar excluir certificado' && git push")
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
