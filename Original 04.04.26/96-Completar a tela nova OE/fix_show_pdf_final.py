from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD_SHOW = '''                        # Exibe PDF inline se solicitado
                        if st.session_state.get(f"_show_pdf_{_noe}", False) and "_pdf_bytes" in dir():
                            try:
                                import base64 as _b64v
                                _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()
                                _html_pdf = (
                                    \'<iframe src="data:application/pdf;base64,\'
                                    + _b64_pdf +
                                    \'" width="100%" height="750px"\'
                                    \' style="border:1px solid #444;border-radius:8px;">\'
                                    \'</iframe>\'
                                )
                                st.markdown(_html_pdf, unsafe_allow_html=True)
                            except Exception:
                                pass'''

NEW_SHOW = '''                        # Exibe PDF inline se solicitado
                        _b64_cached = st.session_state.get(f"_pdf_cache_{_noe}", "")
                        if _b64_cached:
                            _html_pdf = (
                                '<iframe src="data:application/pdf;base64,'
                                + _b64_cached +
                                '" width="100%" height="750px"'
                                ' style="border:1px solid #444;border-radius:8px;margin-top:8px;">'
                                '</iframe>'
                            )
                            st.markdown(_html_pdf, unsafe_allow_html=True)'''

if OLD_SHOW in src:
    src = src.replace(OLD_SHOW, NEW_SHOW, 1)
    print("OK: Bloco de exibicao corrigido.")
else:
    print("AVISO: Nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix visualizar PDF' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
