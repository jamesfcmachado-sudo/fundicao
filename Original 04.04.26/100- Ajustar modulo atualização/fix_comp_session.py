from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Substitui o bloco de composicao para usar session_state
OLD = '''                if num_corr.strip():
                    try:
                        with engine.connect() as conn:
                            # Busca corrida com composição quimica preenchida
                            row_corr = conn.execute(text("""
                                SELECT composicao_quimica_pct, liga, norma
                                FROM corrida
                                WHERE numero_corrida = :nc
                                AND composicao_quimica_pct IS NOT NULL
                                AND composicao_quimica_pct::text != '{}'
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if row_corr:
                                raw = row_corr[0]
                                comp = raw if isinstance(raw, dict) else json.loads(raw)
                                if comp:
                                    st.success(f"✅ Composição encontrada para corrida {num_corr.strip()}")
                                else:
                                    st.warning(f"Corrida {num_corr.strip()} sem composição química.")
                            else:
                                st.warning(f"Corrida {num_corr.strip()} não encontrada ou sem composição.")
                    except Exception as e:
                        st.warning(f"Erro ao buscar corrida: {e}")'''

NEW = '''                # Botao para buscar composicao
                if num_corr.strip():
                    _key_comp = f"_comp_{i}_{num_corr.strip()}"
                    if st.button(f"🔍 Buscar composição da corrida {num_corr.strip()}",
                                 key=f"btn_comp_{i}"):
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
                                    st.success(f"✅ Composição encontrada!")
                                    st.rerun()
                                else:
                                    st.warning(f"Corrida {num_corr.strip()} sem composição.")
                        except Exception as _e:
                            st.warning(f"Erro: {_e}")

                    # Carrega do session_state se disponivel
                    if _key_comp in st.session_state:
                        comp = st.session_state[_key_comp]
                        st.success(f"✅ Composição carregada para corrida {num_corr.strip()}")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botao de busca composicao adicionado.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Botao buscar composicao corrida' && git push")
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
