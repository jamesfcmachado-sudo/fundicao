from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Corrige o bloco que ficou mal formado
OLD = '''                        if st.session_state.get(f"_show_pdf_{_noe}", False):
                            import base64 as _b64v
                            _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()
                            st.markdown(
                                f\'\'\'<iframe src="data:application/pdf;base64,{_b64_pdf}"
                                    width="100%" height="750px"
                                    style="border:1px solid #444;border-radius:8px;margin-top:8px;">
                                </iframe>\'\'\',
                                unsafe_allow_html=True
                            )
                        st.success(f"OE {_noe} gerada com {len(_itens_lista)} item(ns)!")
                    except Exception as _ex:'''

NEW = '''                        if st.session_state.get(f"_show_pdf_{_noe}", False):
                            import base64 as _b64v
                            _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()
                            _pdf_html = (
                                '<iframe src="data:application/pdf;base64,' + _b64_pdf + '"'
                                ' width="100%" height="750px"'
                                ' style="border:1px solid #444;border-radius:8px;margin-top:8px;">'
                                '</iframe>'
                            )
                            st.markdown(_pdf_html, unsafe_allow_html=True)
                        st.success(f"OE {_noe} gerada com {len(_itens_lista)} item(ns)!")
                    except Exception as _ex:'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Sintaxe corrigida.")
else:
    print("AVISO: Bloco nao encontrado.")

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
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-5), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
