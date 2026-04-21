from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix 1: Cliente preenchido automaticamente quando OF é informada
OLD_DADOS = '''    # ── Dados principais ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Dados Gerais")

        # Busca clientes para autocomplete
        try:
            with engine.connect() as _conn_cli:
                _clientes_ac = _conn_cli.execute(text(
                    "SELECT DISTINCT nome_cliente FROM ordem_fabricacao "
                    "WHERE nome_cliente IS NOT NULL ORDER BY nome_cliente"
                )).fetchall()
                _clientes_lista = [r[0] for r in _clientes_ac]
        except Exception:
            _clientes_lista = []'''

NEW_DADOS = '''    # ── Dados principais ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Dados Gerais")

        # Busca clientes para autocomplete
        try:
            with engine.connect() as _conn_cli:
                _clientes_ac = _conn_cli.execute(text(
                    "SELECT DISTINCT nome_cliente FROM ordem_fabricacao "
                    "WHERE nome_cliente IS NOT NULL ORDER BY nome_cliente"
                )).fetchall()
                _clientes_lista = [r[0] for r in _clientes_ac]
        except Exception:
            _clientes_lista = []

        # Preenche automaticamente a partir da OF
        _cliente_auto = _of_data.get("cliente", "")
        _norma_auto   = _of_data.get("norma", "")
        _liga_auto    = _of_data.get("liga", "")'''

if OLD_DADOS in src:
    src = src.replace(OLD_DADOS, NEW_DADOS, 1)
    print("OK: Variaveis auto adicionadas.")
else:
    print("AVISO: Bloco dados nao encontrado.")

# Fix 2: Usa valores automaticos nos campos de cliente, norma e liga
OLD_FIELDS = '''        c1, c2, c3 = st.columns(3)
        with c1:
            cliente = st.text_input("Cliente *", key="cert_cliente")
        with c2:
            norma = st.text_input("Norma da Liga", placeholder="Ex: ASTM-A351 (CF8)",
                                   key="cert_norma")
        with c3:
            liga = st.text_input("Liga", placeholder="Ex: CF8", key="cert_liga")'''

NEW_FIELDS = '''        c1, c2, c3 = st.columns(3)
        with c1:
            cliente = st.text_input("Cliente *", value=_cliente_auto,
                                     key="cert_cliente")
        with c2:
            norma = st.text_input("Norma da Liga", value=_norma_auto,
                                   placeholder="Ex: ASTM-A351 (CF8)",
                                   key="cert_norma")
        with c3:
            liga = st.text_input("Liga", value=_liga_auto,
                                  placeholder="Ex: CF8", key="cert_liga")'''

if OLD_FIELDS in src:
    src = src.replace(OLD_FIELDS, NEW_FIELDS, 1)
    print("OK: Campos preenchidos automaticamente com dados da OF.")
else:
    print("AVISO: Campos nao encontrados.")

# Fix 3: Composição química busca nas colunas individuais do banco
OLD_COMP = '''                if num_corr.strip():
                    try:
                        with engine.connect() as conn:
                            row_corr = conn.execute(text("""
                                SELECT composicao_quimica_pct
                                FROM corrida
                                WHERE numero_corrida = :nc
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if row_corr and row_corr[0]:
                                comp = row_corr[0] if isinstance(row_corr[0], dict) else json.loads(row_corr[0])
                                st.success(f"Composição encontrada para corrida {num_corr}")
                    except Exception as e:
                        pass'''

NEW_COMP = '''                if num_corr.strip():
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

if OLD_COMP in src:
    src = src.replace(OLD_COMP, NEW_COMP, 1)
    print("OK: Composição química corrigida.")
else:
    print("AVISO: Bloco composição nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix cliente auto e composicao quimica' && git push")
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
