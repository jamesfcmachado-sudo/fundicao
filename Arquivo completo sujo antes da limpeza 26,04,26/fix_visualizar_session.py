from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Substitui o botao de visualizacao e o bloco de exibicao
OLD_BTN = '''                        with _dc3:
                            if st.button(f"👁️ Visualizar PDF na tela",
                                         key=f"btn_view_{_noe}"):
                                st.session_state[f"_show_pdf_{_noe}"] = \\
                                    not st.session_state.get(f"_show_pdf_{_noe}", False)'''

NEW_BTN = '''                        with _dc3:
                            if st.button(f"👁️ Visualizar PDF na tela",
                                         key=f"btn_view_{_noe}"):
                                import base64 as _b64save
                                st.session_state[f"_pdf_cache_{_noe}"] = (
                                    _b64save.b64encode(_pdf_bytes).decode()
                                )'''

if OLD_BTN in src:
    src = src.replace(OLD_BTN, NEW_BTN, 1)
    print("OK: Botao visualizar atualizado.")
else:
    print("AVISO: Botao nao encontrado.")

# Substitui o bloco de exibicao
OLD_SHOW = '''                        # Exibe PDF inline se solicitado
                        if st.session_state.get(f"_show_pdf_{_noe}", False):
                            try:
                                import base64 as _b64v
                                _pdf_to_show = st.session_state.get(f"_pdf_cache_{_noe}", b"")
                                if _pdf_to_show:
                                    _b64_pdf = _b64v.b64encode(_pdf_to_show).decode()
                                _html_pdf = (
                                    '<iframe src="data:application/pdf;base64,'
                                    + _b64_pdf +
                                    '" width="100%" height="750px"'
                                    ' style="border:1px solid #444;border-radius:8px;">'
                                    '</iframe>'
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
    print("OK: Bloco de exibicao atualizado.")
else:
    print("AVISO: Bloco de exibicao nao encontrado.")
    # Tenta localizar
    idx = src.find('Exibe PDF inline se solicitado')
    if idx > 0:
        print(repr(src[idx:idx+400]))

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix visualizar PDF session_state' && git push")
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
