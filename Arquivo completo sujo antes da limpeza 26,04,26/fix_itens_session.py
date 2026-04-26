from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    # ── Busca dados da OF para preencher itens ───────────────────────────────
    _of_ref = st.session_state.get("_cert_of_data", {})
    _pedido_auto  = ""
    _modelo_auto  = ""
    _descricao_auto = ""
    if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
        try:
            with engine.connect() as _conn_of_item:
                _of_item = _conn_of_item.execute(text("""
                    SELECT numero_pedido, numero_modelo, descricao_peca, numero_desenho
                    FROM ordem_fabricacao WHERE numero_of = :of
                """), {"of": _of_cert.strip()}).fetchone()
                if _of_item:
                    _pedido_auto   = str(_of_item[0] or "")
                    _modelo_auto   = str(_of_item[1] or "")
                    _descricao_auto = str(_of_item[2] or _of_item[3] or "")
        except Exception:
            pass'''

NEW = '''    # ── Busca dados da OF para preencher itens ───────────────────────────────
    _pedido_auto  = ""
    _modelo_auto  = ""
    _descricao_auto = ""
    _of_key = f"_cert_of_item_{_of_cert.strip()}"

    if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
        # Verifica se ja tem no session_state
        if _of_key not in st.session_state:
            try:
                with engine.connect() as _conn_of_item:
                    _of_item = _conn_of_item.execute(text("""
                        SELECT numero_pedido, numero_modelo,
                               descricao_peca, numero_desenho
                        FROM ordem_fabricacao WHERE numero_of = :of
                    """), {"of": _of_cert.strip()}).fetchone()
                    if _of_item:
                        st.session_state[_of_key] = {
                            "pedido":   str(_of_item[0] or ""),
                            "modelo":   str(_of_item[1] or ""),
                            "descricao": str(_of_item[2] or _of_item[3] or ""),
                        }
            except Exception:
                pass

        _of_item_data = st.session_state.get(_of_key, {})
        _pedido_auto   = _of_item_data.get("pedido", "")
        _modelo_auto   = _of_item_data.get("modelo", "")
        _descricao_auto = _of_item_data.get("descricao", "")

        # Seta no session_state para os campos renderizados
        n_itens_atual = int(st.session_state.get("cert_n_itens", 1))
        for _ii in range(n_itens_atual):
            if f"cert_ped_{_ii}" not in st.session_state or not st.session_state.get(f"cert_ped_{_ii}"):
                st.session_state[f"cert_ped_{_ii}"] = _pedido_auto
            if f"cert_mod_{_ii}" not in st.session_state or not st.session_state.get(f"cert_mod_{_ii}"):
                st.session_state[f"cert_mod_{_ii}"] = _modelo_auto
            if f"cert_desc_{_ii}" not in st.session_state or not st.session_state.get(f"cert_desc_{_ii}"):
                st.session_state[f"cert_desc_{_ii}"] = _descricao_auto'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Session_state para itens da OF adicionado.")
else:
    print("AVISO: Bloco nao encontrado.")

# Fix serie: tambem seta no session_state antes de renderizar
OLD_SERIE = '''                with ir5:
                    # Calcula serie automaticamente
                    if qtd > 0:'''

NEW_SERIE = '''                with ir5:
                    # Calcula e seta serie no session_state
                    _qtd_atual = st.session_state.get(f"cert_qtd_{i}", 0)
                    if _qtd_atual > 0 and not st.session_state.get(f"cert_serie_{i}"):
                        try:
                            import re as _re3
                            with engine.connect() as _conn_s3:
                                _rows_s3 = _conn_s3.execute(text("""
                                    SELECT ci.series
                                    FROM certificado_item ci
                                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                                    WHERE cc.numero_of = :of
                                    AND ci.series IS NOT NULL AND ci.series != ''
                                    ORDER BY cq.criado_em DESC
                                """), {"of": _of_cert.strip() or ""}).fetchall()
                                _ult = 0
                                for _rs3 in _rows_s3:
                                    _ns = _re3.findall(r'\d+', str(_rs3[0] or ""))
                                    if _ns:
                                        _ult = max(_ult, max(int(n) for n in _ns))
                                _ini = _ult + _serie_acumulada + 1
                                _fim2 = _ini + _qtd_atual - 1
                                _sa = f"{_ini} A {_fim2}" if _qtd_atual > 1 else str(_ini)
                                st.session_state[f"cert_serie_{i}"] = _sa
                        except Exception:
                            pass

                    # Calcula serie automaticamente
                    if qtd > 0:'''

if OLD_SERIE in src:
    src = src.replace(OLD_SERIE, NEW_SERIE, 1)
    print("OK: Serie calculada no session_state.")
else:
    print("AVISO: Bloco serie nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix session_state itens OF e serie' && git push")
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
