from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                # Campos de composição — usa session_state se disponivel
                _comp_loaded = st.session_state.get(_key_comp, {})
                cols_elem = st.columns(7)
                comp_editada = {}
                for j, el in enumerate(ELEM):
                    with cols_elem[j % 7]:
                        # Valor: session_state tem prioridade, depois comp_loaded
                        _vk = f"cert_comp_{i}_{el}"
                        if _btn_buscar and _key_comp in st.session_state:
                            # Acabou de buscar - usa valor do banco
                            val = float(_comp_loaded.get(el, 0.0) or 0.0)
                        else:
                            # Usa o que ja estava no campo
                            val = float(st.session_state.get(_vk,
                                  _comp_loaded.get(el, 0.0) or 0.0))
                        comp_editada[el] = st.number_input(
                            el, value=val, format="%.4f",
                            key=_vk, min_value=0.0
                        )'''

NEW = '''                # Tabela editável de composição química
                _comp_loaded = st.session_state.get(_key_comp, {})
                if _comp_loaded:
                    import pandas as _pd_comp
                    _comp_df = _pd_comp.DataFrame([{
                        el: float(_comp_loaded.get(el, 0.0) or 0.0)
                        for el in ELEM
                    }])
                    _comp_edited = st.data_editor(
                        _comp_df,
                        key=f"cert_comp_table_{i}",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            el: st.column_config.NumberColumn(
                                el, format="%.4f", min_value=0.0
                            ) for el in ELEM
                        }
                    )
                    comp_editada = {el: float(_comp_edited.iloc[0][el] or 0.0)
                                    for el in ELEM}
                else:
                    st.caption("Digite o número da corrida e clique 🔍 Buscar")
                    comp_editada = {el: 0.0 for el in ELEM}'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Composição com data_editor.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix composicao data_editor' && git push")
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
