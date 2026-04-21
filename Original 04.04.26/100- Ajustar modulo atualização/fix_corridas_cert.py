from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Substitui toda a secao de corridas
OLD = '''    # ── Corridas e Composição Química ─────────────────────────────────────────
    with st.container(border=True):
        st.subheader("I - Composição Química (Corridas)")
        st.caption("Informe as corridas — a composição química será buscada automaticamente do banco.")

        n_corridas = st.number_input("Número de corridas", min_value=1, max_value=15,
                                      value=1, key="cert_n_corridas")
        corridas = []
        for i in range(int(n_corridas)):
            with st.container(border=True):
                st.caption(f"Corrida {i+1}")
                cc1, cc2 = st.columns(2)
                with cc1:
                    nof_corr = st.text_input("OF", key=f"cert_of_{i}")
                with cc2:
                    num_corr = st.text_input("Nº Corrida", key=f"cert_corr_{i}")

                # Botao para buscar composicao
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
                        st.success(f"✅ Composição carregada para corrida {num_corr.strip()}")
                else:
                    comp = {}

                # Exibe composição química
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
                        )

                corridas.append({
                    "num_of": nof_corr.strip(),
                    "num_corrida": num_corr.strip(),
                    "comp": comp_editada
                })'''

NEW = '''    # ── Corridas e Composição Química ─────────────────────────────────────────
    with st.container(border=True):
        st.subheader("I - Composição Química (Corridas)")
        st.caption("Informe OF e Corrida, depois clique em 🔍 para buscar a composição.")

        n_corridas = st.number_input("Número de corridas", min_value=1, max_value=15,
                                      value=1, key="cert_n_corridas")
        corridas = []
        ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","CE"]

        for i in range(int(n_corridas)):
            with st.container(border=True):
                st.caption(f"Corrida {i+1}")
                cc1, cc2, cc3 = st.columns([2, 2, 1])
                with cc1:
                    nof_corr = st.text_input("OF", key=f"cert_of_{i}")
                with cc2:
                    num_corr = st.text_input("Nº Corrida", key=f"cert_corr_{i}")
                with cc3:
                    st.write("")
                    st.write("")
                    _btn_buscar = st.button("🔍 Buscar",
                                            key=f"btn_comp_{i}",
                                            help="Busca composição química desta corrida")

                # Chave unica por corrida
                _key_comp = f"_cert_comp_corrida_{i}"

                if _btn_buscar and num_corr.strip():
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
                                # Seta os campos no session_state
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

                # Campos de composição
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
                        )

                corridas.append({
                    "num_of": nof_corr.strip(),
                    "num_corrida": num_corr.strip(),
                    "comp": comp_editada
                })'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Secao de corridas reescrita.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix corridas certificado robusto' && git push")
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
