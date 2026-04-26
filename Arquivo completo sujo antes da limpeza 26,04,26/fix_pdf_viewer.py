from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''                        # Exibe PDF inline se solicitado
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

NEW = '''                        # Exibe PDF inline se solicitado
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

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Usando object em vez de iframe.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'PDF viewer com object tag' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
