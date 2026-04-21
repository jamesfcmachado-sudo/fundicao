from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    # Número automático
    seq, ano, num_cert = _proximo_numero_cert()
    st.info(f"Próximo número: **{num_cert}**")

    # ── Dados principais ──────────────────────────────────────────────────────
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
            _of_data = {"cliente": "", "norma": "", "liga": ""}'''

NEW = '''    # ── Número do certificado editável ──────────────────────────────────────
    seq, ano, num_cert_sug = _proximo_numero_cert()

    with st.container(border=True):
        st.subheader("Identificação")
        _id1, _id2 = st.columns(2)
        with _id1:
            num_cert = st.text_input(
                "🔢 Nº do Certificado *",
                value=num_cert_sug,
                help=f"Último gerado: {num_cert_sug}. Edite se necessário.",
                key="cert_numero_edit"
            )
        with _id2:
            # Busca OFs do banco
            try:
                with engine.connect() as _conn_ac:
                    _ofs_ac = _conn_ac.execute(text(
                        "SELECT numero_of, nome_cliente, norma, liga "
                        "FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
                    _ofs_dict = {r[0]: {"cliente": r[1] or "", "norma": r[2] or "", "liga": r[3] or ""}
                                 for r in _ofs_ac}
                    _ofs_lista = list(_ofs_dict.keys())
            except Exception:
                _ofs_dict = {}
                _ofs_lista = []

            _of_cert = st.text_input(
                "📋 Nº da OF *",
                placeholder="Ex: 015B6",
                help="Informe a OF para buscar cliente, norma e liga automaticamente.",
                key="cert_of_ref"
            )
            # Sugestoes de OF
            if _of_cert.strip():
                _sugestoes_of = [o for o in _ofs_lista if _of_cert.strip().upper() in o.upper()][:5]
                if _sugestoes_of and _of_cert.strip() not in _ofs_dict:
                    st.caption(f"Sugestões: {', '.join(_sugestoes_of)}")

        if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
            _of_data = _ofs_dict[_of_cert.strip()]
            st.success(f"✅ OF {_of_cert.strip()} — Cliente: {_of_data['cliente']}")
        else:
            _of_data = {"cliente": "", "norma": "", "liga": ""}

    # ── Dados principais ──────────────────────────────────────────────────────
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

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Campos reorganizados.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Numero cert editavel OF primeiro campo' && git push")
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
