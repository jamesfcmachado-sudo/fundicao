from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                if _btn_buscar and num_corr.strip():
                    try:
                        with engine.connect() as _conn_comp:
                            _rc = _conn_comp.execute(text("""
                                SELECT composicao_quimica_pct
                                FROM corrida
                                WHERE numero_corrida = :nc
                                AND composicao_quimica_pct IS NOT NULL
                                AND composicao_quimica_pct::text != '{}'
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if _rc and _rc[0]:
                                raw = _rc[0]
                                _comp_found = raw if isinstance(raw, dict) else json.loads(raw)
                                st.session_state[_key_comp] = _comp_found
                                for el in ELEM:
                                    val = _comp_found.get(el, 0.0) or 0.0
                                    st.session_state[f"cert_comp_{i}_{el}"] = float(val)
                                st.success(f"✅ Composição da corrida {num_corr.strip()} carregada!")
                                st.rerun()
                            else:
                                st.warning(f"Corrida {num_corr.strip()} sem composição.")
                    except Exception as _e:
                        st.warning(f"Erro: {_e}")

                if _key_comp in st.session_state:
                    st.success(f"✅ Composição carregada")

                _comp_loaded = st.session_state.get(_key_comp, {})
                cols_elem = st.columns(7)
                comp_editada = {}
                for j, el in enumerate(ELEM):
                    with cols_elem[j % 7]:
                        val = float(st.session_state.get(f"cert_comp_{i}_{el}",
                              _comp_loaded.get(el, 0.0) or 0.0))
                        comp_editada[el] = st.number_input(
                            el, value=val, format="%.4f",
                            key=f"cert_comp_{i}_{el}", min_value=0.0
                        )'''

NEW = '''                if _btn_buscar and num_corr.strip():
                    try:
                        with engine.connect() as _conn_comp:
                            _rc = _conn_comp.execute(text("""
                                SELECT composicao_quimica_pct
                                FROM corrida
                                WHERE numero_corrida = :nc
                                AND composicao_quimica_pct IS NOT NULL
                                AND composicao_quimica_pct::text != '{}'
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if _rc and _rc[0]:
                                raw = _rc[0]
                                _comp_found = raw if isinstance(raw, dict) else json.loads(raw)
                                st.session_state[_key_comp] = _comp_found
                                st.success(f"✅ Composição da corrida {num_corr.strip()} carregada!")
                            else:
                                st.warning(f"Corrida {num_corr.strip()} sem composição.")
                    except Exception as _e:
                        st.warning(f"Erro: {_e}")
                elif _key_comp in st.session_state:
                    st.success(f"✅ Composição carregada — {num_corr.strip()}")

                # Campos de composição — usa session_state se disponivel
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

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Corridas sem rerun.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix corridas sem rerun' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
