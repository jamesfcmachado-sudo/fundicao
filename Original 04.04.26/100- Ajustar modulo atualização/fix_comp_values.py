from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                # Exibe composição química
                ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","CE"]
                cols_elem = st.columns(7)
                comp_editada = {}
                for j, el in enumerate(ELEM):
                    with cols_elem[j % 7]:
                        val = comp.get(el, comp.get(el.lower(), 0.0)) or 0.0
                        comp_editada[el] = st.number_input(
                            el, value=float(val), format="%.4f",
                            key=f"cert_comp_{i}_{el}", min_value=0.0
                        )'''

NEW = '''                # Exibe composição química
                ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","CE"]
                cols_elem = st.columns(7)
                comp_editada = {}
                _key_comp = f"_comp_{i}_{num_corr.strip()}"
                _comp_loaded = st.session_state.get(_key_comp, comp)
                for j, el in enumerate(ELEM):
                    with cols_elem[j % 7]:
                        val = _comp_loaded.get(el, _comp_loaded.get(el.lower(), 0.0)) or 0.0
                        comp_editada[el] = st.number_input(
                            el, value=float(val), format="%.4f",
                            key=f"cert_comp_{i}_{el}_{num_corr.strip()}", min_value=0.0
                        )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Campos composicao usando session_state.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix composicao usa session_state' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
