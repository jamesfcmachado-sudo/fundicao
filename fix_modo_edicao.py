from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix 1: Ao clicar Editar, seta session_state do formulario principal e faz rerun
OLD_BTN_EDITAR = '''                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        # Carrega dados completos para edicao
                        try:
                            with engine.connect() as _conn_ed:
                                _corridas_ed = _conn_ed.execute(text("""
                                    SELECT numero_of, numero_corrida,
                                           c, si, mn, p, s, cr, ni, mo
                                    FROM certificado_corrida
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                                _itens_ed = _conn_ed.execute(text("""
                                    SELECT pedido, modelo, descricao,
                                           series, quantidade
                                    FROM certificado_item
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                            st.session_state["_editar_cert_id"]      = str(_cm_alt["id"])
                            st.session_state["_editar_cert_num"]     = _cm_alt["numero_cert"]
                            st.session_state["_editar_cert_data"]    = dict(_cm_alt)
                            st.session_state["_editar_cert_corridas"] = [dict(r._mapping) for r in _corridas_ed]
                            st.session_state["_editar_cert_itens"]   = [dict(r._mapping) for r in _itens_ed]
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erro ao carregar dados: {_e}")'''

NEW_BTN_EDITAR = '''                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        try:
                            with engine.connect() as _conn_ed:
                                _corridas_ed = _conn_ed.execute(text("""
                                    SELECT numero_of, numero_corrida,
                                           c, si, mn, p, s, cr, ni, mo
                                    FROM certificado_corrida
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                                _itens_ed = _conn_ed.execute(text("""
                                    SELECT pedido, modelo, descricao,
                                           series, quantidade
                                    FROM certificado_item
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()

                            # Seta flag de edicao
                            st.session_state["_modo_edicao_cert_id"]  = str(_cm_alt["id"])
                            st.session_state["_modo_edicao_cert_num"] = _cm_alt["numero_cert"]

                            # Preenche campos do formulario principal
                            st.session_state["cert_numero_edit"] = _cm_alt["numero_cert"]
                            st.session_state["cert_norma"]       = str(_cm_alt.get("norma","") or "")
                            st.session_state["cert_liga"]        = str(_cm_alt.get("liga","") or "")
                            st.session_state["cert_projeto"]     = str(_cm_alt.get("projeto","") or "")
                            st.session_state["cert_nf"]          = str(_cm_alt.get("nota_fiscal","") or "")
                            st.session_state["cert_obs"]         = str(_cm_alt.get("observacoes","") or "")
                            st.session_state["cert_outros"]      = str(_cm_alt.get("outros_ensaios","") or "")
                            st.session_state["cert_cliente_manual"] = str(_cm_alt.get("cliente","") or "")

                            # Corridas
                            _lista_corr = [dict(r._mapping) for r in _corridas_ed]
                            st.session_state["cert_n_corridas"] = len(_lista_corr)
                            for _ci, _cr in enumerate(_lista_corr):
                                st.session_state[f"cert_of_{_ci}"]   = str(_cr.get("numero_of","") or "")
                                st.session_state[f"cert_corr_{_ci}"] = str(_cr.get("numero_corrida","") or "")
                                _key_comp = f"_cert_comp_corrida_{_ci}"
                                _comp_dict = {
                                    el.upper(): float(_cr.get(el.lower(), 0) or 0)
                                    for el in ["C","Si","Mn","P","S","Cr","Ni","Mo"]
                                }
                                st.session_state[_key_comp] = _comp_dict
                                for _el in ["C","Si","Mn","P","S","Cr","Ni","Mo"]:
                                    st.session_state[f"cert_comp_{_ci}_{_el}"] = float(_cr.get(_el.lower(), 0) or 0)

                            # Itens
                            _lista_itens = [dict(r._mapping) for r in _itens_ed]
                            st.session_state["cert_n_itens"] = len(_lista_itens)
                            for _ii, _it in enumerate(_lista_itens):
                                st.session_state[f"cert_ped_{_ii}"]   = str(_it.get("pedido","") or "")
                                st.session_state[f"cert_mod_{_ii}"]   = str(_it.get("modelo","") or "")
                                st.session_state[f"cert_desc_{_ii}"]  = str(_it.get("descricao","") or "")
                                st.session_state[f"cert_serie_{_ii}"] = str(_it.get("series","") or "")
                                st.session_state[f"cert_qtd_{_ii}"]   = int(_it.get("quantidade",0) or 0)

                            st.success(f"✅ Dados carregados! Role para cima para editar.")
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erro ao carregar dados: {_e}")'''

if OLD_BTN_EDITAR in src:
    src = src.replace(OLD_BTN_EDITAR, NEW_BTN_EDITAR, 1)
    print("OK: Botao editar preenchido.")
else:
    print("AVISO: Botao editar nao encontrado.")

# Fix 2: No topo do formulario, mostra aviso de modo edicao
OLD_TITULO = '''    st.title("🏅 Novo Certificado de Qualidade")'''
NEW_TITULO = '''    # Verifica modo edicao
    _modo_ed = st.session_state.get("_modo_edicao_cert_id", "")
    _modo_ed_num = st.session_state.get("_modo_edicao_cert_num", "")

    if _modo_ed:
        st.title(f"✏️ Editando Certificado {_modo_ed_num}")
        st.warning(f"⚠️ Você está editando o certificado **{_modo_ed_num}**. "
                   f"Ao salvar, os dados serão atualizados no banco.")
        if st.button("❌ Cancelar edição e criar novo", key="btn_cancelar_modo_ed"):
            for _k in list(st.session_state.keys()):
                if _k.startswith("cert_") or _k.startswith("_modo_edicao") or _k.startswith("_cert_"):
                    st.session_state.pop(_k, None)
            st.rerun()
    else:
        st.title("🏅 Novo Certificado de Qualidade")'''

if OLD_TITULO in src:
    src = src.replace(OLD_TITULO, NEW_TITULO, 1)
    print("OK: Titulo com modo edicao.")
else:
    print("AVISO: Titulo nao encontrado.")

# Fix 3: No salvar, verifica se e edicao ou novo
OLD_SALVAR = '''    if st.button("💾 Salvar Certificado", type="primary", key="btn_salvar_cert"):
        if not cliente.strip():
            st.error("Informe o cliente.")
            return
        try:
            import uuid as _uuid
            now = datetime.now().astimezone()
            cert_id = str(_uuid.uuid4())'''

NEW_SALVAR = '''    if st.button("💾 Salvar Certificado", type="primary", key="btn_salvar_cert"):
        if not cliente.strip():
            st.error("Informe o cliente.")
            return
        try:
            import uuid as _uuid
            now = datetime.now().astimezone()
            _cert_id_edicao = st.session_state.get("_modo_edicao_cert_id", "")
            cert_id = _cert_id_edicao if _cert_id_edicao else str(_uuid.uuid4())
            _eh_edicao = bool(_cert_id_edicao)'''

if OLD_SALVAR in src:
    src = src.replace(OLD_SALVAR, NEW_SALVAR, 1)
    print("OK: Salvar com modo edicao.")
else:
    print("AVISO: Salvar nao encontrado.")

# Fix 4: Muda INSERT para UPDATE quando for edicao
OLD_INSERT = '''                # Insere certificado
                conn.execute(text("""
                    INSERT INTO certificado_qualidade (
                        id, numero_cert, ano, seq, cliente, norma, liga,'''

NEW_INSERT = '''                # Insere ou atualiza certificado
                if _eh_edicao:
                    conn.execute(text("""
                        UPDATE certificado_qualidade SET
                            cliente=:cliente, norma=:norma, liga=:liga,
                            nota_fiscal=:nota_fiscal, observacoes=:observacoes,
                            outros_ensaios=:outros_ensaios,
                            tipo_template=:tipo,
                            atualizado_em=:now
                        WHERE id=:id
                    """), {"cliente": cliente, "norma": norma, "liga": liga,
                           "nota_fiscal": nf, "observacoes": obs,
                           "outros_ensaios": outros, "tipo": tipo,
                           "now": now, "id": cert_id})
                    # Remove corridas e itens antigos
                    conn.execute(text("DELETE FROM certificado_corrida WHERE certificado_id=:id"), {"id": cert_id})
                    conn.execute(text("DELETE FROM certificado_item WHERE certificado_id=:id"), {"id": cert_id})
                    conn.execute(text("DELETE FROM ensaio_mecanico WHERE certificado_id=:id"), {"id": cert_id})
                else:
                    conn.execute(text("""
                    INSERT INTO certificado_qualidade (
                        id, numero_cert, ano, seq, cliente, norma, liga,'''

if OLD_INSERT in src:
    src = src.replace(OLD_INSERT, NEW_INSERT, 1)
    print("OK: INSERT/UPDATE adicionado.")
else:
    print("AVISO: INSERT nao encontrado.")

# Fix 5: Fecha o else do INSERT
OLD_CLOSE = '''                # Insere corridas'''
NEW_CLOSE = '''                # Insere corridas (comum para INSERT e UPDATE)'''

if OLD_CLOSE in src:
    # Precisamos fechar o else antes de inserir corridas
    # Primeiro acha o fechamento do INSERT original
    idx_insert = src.find("INSERT INTO certificado_qualidade")
    idx_corridas = src.find("                # Insere corridas (comum", idx_insert)
    # Verifica se precisa fechar
    bloco = src[idx_insert:idx_corridas]
    if bloco.count("if _eh_edicao") > 0 and bloco.count("else:") > 0:
        # Conta a indentacao do insert values para achar o fechamento
        idx_values_end = src.rfind(")\n\n", idx_insert, idx_corridas)
        if idx_values_end > 0:
            # Adiciona fechamento do else
            src = src[:idx_values_end+2] + "                # fim do else INSERT\n" + src[idx_values_end+2:]
            print("OK: Fechamento else adicionado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os, re
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Modo edicao certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-3), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
