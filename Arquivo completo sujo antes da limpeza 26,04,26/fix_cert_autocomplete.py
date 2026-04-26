from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    # ── Dados principais ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Dados Gerais")
        c1, c2, c3 = st.columns(3)
        with c1:
            cliente = st.text_input("Cliente *", key="cert_cliente")
        with c2:
            norma = st.text_input("Norma da Liga", placeholder="Ex: ASTM-A351 (CF8)",
                                   key="cert_norma")
        with c3:
            liga = st.text_input("Liga", placeholder="Ex: CF8", key="cert_liga")

        c4, c5, c6 = st.columns(3)
        with c4:
            projeto = st.text_input("Projeto", key="cert_projeto")
        with c5:
            data_emissao = st.date_input("Data de Emissão", value=date.today(),
                                          format="DD/MM/YYYY", key="cert_data")
        with c6:
            nota_fiscal = st.text_input("Nota Fiscal", key="cert_nf")'''

NEW = '''    # ── Dados principais ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Dados Gerais")

        # Busca clientes e OFs do banco para autocomplete
        try:
            with engine.connect() as _conn_ac:
                _clientes_ac = _conn_ac.execute(text(
                    "SELECT DISTINCT nome_cliente FROM ordem_fabricacao "
                    "WHERE nome_cliente IS NOT NULL ORDER BY nome_cliente"
                )).fetchall()
                _clientes_lista = [r[0] for r in _clientes_ac]

                _ofs_ac = _conn_ac.execute(text(
                    "SELECT numero_of, nome_cliente, norma, liga "
                    "FROM ordem_fabricacao ORDER BY numero_of"
                )).fetchall()
                _ofs_dict = {r[0]: {"cliente": r[1], "norma": r[2] or "", "liga": r[3] or ""}
                             for r in _ofs_ac}
        except Exception:
            _clientes_lista = []
            _ofs_dict = {}

        # Campo OF para buscar dados automaticamente
        _of_cert = st.text_input(
            "OF (opcional) — preenche Cliente, Norma e Liga automaticamente",
            placeholder="Ex: 015B6", key="cert_of_ref"
        )
        if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
            _of_data = _ofs_dict[_of_cert.strip()]
            st.success(f"OF encontrada: Cliente {_of_data['cliente']}")
        else:
            _of_data = {"cliente": "", "norma": "", "liga": ""}

        c1, c2, c3 = st.columns(3)
        with c1:
            # Cliente com autocomplete
            _cliente_default = _of_data["cliente"] or ""
            cliente = st.selectbox(
                "Cliente *",
                options=[""] + _clientes_lista,
                index=(_clientes_lista.index(_cliente_default) + 1)
                      if _cliente_default in _clientes_lista else 0,
                key="cert_cliente"
            )
            if not cliente:
                cliente = st.text_input("Ou digite o cliente", key="cert_cliente_manual")
        with c2:
            norma = st.text_input("Norma da Liga",
                value=_of_data["norma"],
                placeholder="Ex: ASTM-A351 (CF8)",
                key="cert_norma")
        with c3:
            liga = st.text_input("Liga",
                value=_of_data["liga"],
                placeholder="Ex: CF8", key="cert_liga")

        c4, c5, c6 = st.columns(3)
        with c4:
            projeto = st.text_input("Projeto", key="cert_projeto")
        with c5:
            data_emissao = st.date_input("Data de Emissão", value=date.today(),
                                          format="DD/MM/YYYY", key="cert_data")
        with c6:
            nota_fiscal = st.text_input("Nota Fiscal", key="cert_nf")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Autocomplete adicionado.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Autocomplete cliente norma liga certificado' && git push")
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
