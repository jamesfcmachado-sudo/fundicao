from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                            data=_pdf_bytes,
                            file_name=f"OE_{_noe}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{_noe}",
                            type="primary",
                        )'''

NEW = '''                        _vc1, _vc2 = st.columns(2)
                        with _vc1:
                            st.download_button(
                                f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                                data=_pdf_bytes,
                                file_name=f"OE_{_noe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{_noe}",
                                type="primary",
                            )
                        with _vc2:
                            if st.button(f"\U0001f441\ufe0f Visualizar OE {_noe} na tela",
                                         key=f"btn_view_{_noe}"):
                                st.session_state[f"_show_pdf_{_noe}"] = not st.session_state.get(f"_show_pdf_{_noe}", False)

                        # Exibe PDF na tela se solicitado
                        if st.session_state.get(f"_show_pdf_{_noe}", False):
                            import base64 as _b64v
                            _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()
                            _pdf_html = f"""
                                <iframe
                                    src="data:application/pdf;base64,{_b64_pdf}"
                                    width="100%"
                                    height="700px"
                                    style="border: 1px solid #444; border-radius: 8px;"
                                ></iframe>
                            """
                            st.markdown(_pdf_html, unsafe_allow_html=True)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Visualizacao PDF na tela adicionada.")
else:
    print("AVISO: Botao download nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Visualizar PDF OE na tela' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
