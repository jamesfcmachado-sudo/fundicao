from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                if num_corr.strip():
                    try:
                        with engine.connect() as conn:
                            row_corr = conn.execute(text("""
                                SELECT "C","Si","Mn","P","S","Cr","Ni","Mo",
                                       "Cu","W","Nb","V","Fe","N","Mg","B",
                                       composicao_quimica_pct
                                FROM corrida
                                WHERE numero_corrida = :nc
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if row_corr:
                                _rm = row_corr._mapping
                                # Tenta colunas individuais primeiro
                                comp_cols = {}
                                for el in ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","N","Mg","B"]:
                                    v = _rm.get(el)
                                    if v is not None:
                                        try:
                                            comp_cols[el] = float(v)
                                        except Exception:
                                            pass
                                if any(v > 0 for v in comp_cols.values()):
                                    comp = comp_cols
                                    st.success(f"✅ Composição encontrada para corrida {num_corr.strip()}")
                                elif _rm.get("composicao_quimica_pct"):
                                    raw = _rm["composicao_quimica_pct"]
                                    comp = raw if isinstance(raw, dict) else json.loads(raw)
                                    st.success(f"✅ Composição encontrada para corrida {num_corr.strip()}")
                                else:
                                    st.warning(f"Corrida {num_corr.strip()} sem composição química.")
                    except Exception as e:
                        st.warning(f"Corrida não encontrada: {e}")'''

NEW = '''                if num_corr.strip():
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

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Query composição corrigida.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix composicao quimica certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
