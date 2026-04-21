from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    # ── Itens (Pedido/Modelo/Descrição/Séries/Qtd) ────────────────────────────
    with st.container(border=True):
        st.subheader("III - Outros Dados (Itens)")
        n_itens = st.number_input("Número de itens", min_value=1, max_value=20,
                                   value=1, key="cert_n_itens")
        itens_cert = []
        for i in range(int(n_itens)):
            ic1, ic2, ic3, ic4, ic5 = st.columns([2, 2, 3, 2, 1])
            with ic1:
                pedido = st.text_input("Pedido/Item", key=f"cert_ped_{i}")
            with ic2:
                modelo = st.text_input("Modelo", key=f"cert_mod_{i}")
            with ic3:
                descricao = st.text_input("Descrição", key=f"cert_desc_{i}")
            with ic4:
                series = st.text_input("Séries", key=f"cert_serie_{i}")
            with ic5:
                qtd = st.number_input("Qtd", min_value=0, value=0,
                                       key=f"cert_qtd_{i}")
            itens_cert.append({
                "pedido": pedido, "modelo": modelo,
                "descricao": descricao, "series": series, "quantidade": qtd
            })'''

NEW = '''    # ── Busca dados da OF para preencher itens ───────────────────────────────
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
            pass

    # Busca ultima serie emitida para esta OF nos certificados anteriores
    def _proxima_serie(of_num, qtd_nova):
        """Retorna (inicio, fim, serie_str) para a proxima serie."""
        if not of_num:
            return 1, qtd_nova, f"1 A {qtd_nova}" if qtd_nova > 1 else "1"
        try:
            with engine.connect() as _conn_s:
                # Busca o maior numero de serie ja emitido para esta OF
                _rows_s = _conn_s.execute(text("""
                    SELECT ci.series, ci.quantidade
                    FROM certificado_item ci
                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                    WHERE cc.numero_of = :of
                    AND ci.series IS NOT NULL AND ci.series != ''
                    ORDER BY cq.criado_em DESC
                """), {"of": of_num}).fetchall()

                ultimo = 0
                for _rs in _rows_s:
                    serie_str = str(_rs[0] or "")
                    # Extrai o ultimo numero da serie (ex: "1 A 20" -> 20)
                    import re as _re
                    nums = _re.findall(r'\d+', serie_str)
                    if nums:
                        ultimo = max(ultimo, max(int(n) for n in nums))

                inicio = ultimo + 1
                fim = ultimo + qtd_nova
                serie_str = f"{inicio} A {fim}" if qtd_nova > 1 else str(inicio)
                return inicio, fim, serie_str
        except Exception:
            return 1, qtd_nova, f"1 A {qtd_nova}" if qtd_nova > 1 else "1"

    # ── Itens (Pedido/Modelo/Descrição/Qtd/Séries) ────────────────────────────
    with st.container(border=True):
        st.subheader("III - Outros Dados (Itens)")
        n_itens = st.number_input("Número de itens", min_value=1, max_value=20,
                                   value=1, key="cert_n_itens")
        itens_cert = []
        _serie_acumulada = 0  # acumula series dentro do mesmo certificado

        for i in range(int(n_itens)):
            with st.container(border=True):
                st.caption(f"Item {i+1}")
                ir1, ir2, ir3 = st.columns([2, 2, 3])
                with ir1:
                    pedido = st.text_input("Pedido/Item",
                        value=_pedido_auto, key=f"cert_ped_{i}")
                with ir2:
                    modelo = st.text_input("Modelo",
                        value=_modelo_auto, key=f"cert_mod_{i}")
                with ir3:
                    descricao = st.text_input("Descrição",
                        value=_descricao_auto, key=f"cert_desc_{i}")

                ir4, ir5 = st.columns([1, 2])
                with ir4:
                    qtd = st.number_input("Quantidade", min_value=0, value=0,
                                           key=f"cert_qtd_{i}")
                with ir5:
                    # Calcula serie automaticamente
                    if qtd > 0:
                        _of_para_serie = _of_cert.strip() if _of_cert.strip() else ""
                        # Calcula inicio considerando acumulado no certificado atual
                        try:
                            with engine.connect() as _conn_s2:
                                _rows_s2 = _conn_s2.execute(text("""
                                    SELECT ci.series
                                    FROM certificado_item ci
                                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                                    WHERE cc.numero_of = :of
                                    AND ci.series IS NOT NULL AND ci.series != ''
                                    ORDER BY cq.criado_em DESC
                                """), {"of": _of_para_serie}).fetchall()
                                import re as _re2
                                _ultimo = 0
                                for _rs2 in _rows_s2:
                                    nums2 = _re2.findall(r'\d+', str(_rs2[0] or ""))
                                    if nums2:
                                        _ultimo = max(_ultimo, max(int(n) for n in nums2))
                                _inicio = _ultimo + _serie_acumulada + 1
                                _fim = _inicio + qtd - 1
                                _serie_auto = f"{_inicio} A {_fim}" if qtd > 1 else str(_inicio)
                        except Exception:
                            _inicio = _serie_acumulada + 1
                            _fim = _serie_acumulada + qtd
                            _serie_auto = f"{_inicio} A {_fim}" if qtd > 1 else str(_inicio)
                    else:
                        _serie_auto = ""

                    series = st.text_input("Série",
                        value=_serie_auto,
                        key=f"cert_serie_{i}",
                        help="Preenchido automaticamente. Edite se necessário.")

                if qtd > 0:
                    _serie_acumulada += qtd

            itens_cert.append({
                "pedido": pedido, "modelo": modelo,
                "descricao": descricao, "series": series, "quantidade": qtd
            })'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Secao de itens melhorada.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Itens cert auto pedido modelo descricao serie' && git push")
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
