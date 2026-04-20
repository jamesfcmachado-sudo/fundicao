from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Remove o botao de visualizacao e volta para 2 colunas
OLD = '''                        _dc1, _dc2, _dc3 = st.columns(3)
                        with _dc1:
                            st.download_button(
                                f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                                data=_pdf_bytes,
                                file_name=f"OE_{_noe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{_noe}",
                                type="primary",
                            )
                        with _dc2:
                            st.download_button(
                                f"\U0001f4ca Baixar OE {_noe} em Excel",
                                data=_excel_bytes,
                                file_name=f"OE_{_noe}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_xlsx_{_noe}",
                            )
                        with _dc3:
                            if st.button(f"\U0001f441\ufe0f Visualizar PDF na tela",
                                         key=f"btn_view_{_noe}"):
                                import base64 as _b64save
                                st.session_state[f"_pdf_cache_{_noe}"] = (
                                    _b64save.b64encode(_pdf_bytes).decode()
                                )'''

NEW = '''                        _dc1, _dc2 = st.columns(2)
                        with _dc1:
                            st.download_button(
                                f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                                data=_pdf_bytes,
                                file_name=f"OE_{_noe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{_noe}",
                                type="primary",
                            )
                        with _dc2:
                            st.download_button(
                                f"\U0001f4ca Baixar OE {_noe} em Excel",
                                data=_excel_bytes,
                                file_name=f"OE_{_noe}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_xlsx_{_noe}",
                            )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botao visualizar removido.")
else:
    print("AVISO: Bloco nao encontrado.")

# Remove o bloco de exibicao do PDF
OLD_SHOW = '''                        # Exibe PDF inline se solicitado
                        _b64_cached = st.session_state.get(f"_pdf_cache_{_noe}", "")
                        if _b64_cached:
                            # Usa embed/object que funciona no Streamlit Cloud
                            _html_pdf = (
                                '<object data="data:application/pdf;base64,'
                                + _b64_cached +
                                '" type="application/pdf" width="100%" height="750px"'
                                ' style="border:1px solid #444;border-radius:8px;margin-top:8px;">'
                                '<p>Seu navegador não suporta visualização de PDF. '
                                '<a href="data:application/pdf;base64,' + _b64_cached + '">Clique aqui para baixar.</a>'
                                '</p></object>'
                            )
                            st.markdown(_html_pdf, unsafe_allow_html=True)'''

if OLD_SHOW in src:
    src = src.replace(OLD_SHOW, '', 1)
    print("OK: Bloco de visualizacao removido.")
else:
    print("AVISO: Bloco visualizacao nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove botao visualizar PDF' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
