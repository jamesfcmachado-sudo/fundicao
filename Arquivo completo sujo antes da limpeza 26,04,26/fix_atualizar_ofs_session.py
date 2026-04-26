from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''    st.info(f"Previa — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    if not st.button("Confirmar atualizacao de OFs", key="btn_confirmar_atualizar_ofs"):
        return

    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()'''

NEW = '''    st.info(f"Prévia — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    # Salva df no session_state para nao perder apos rerun
    st.session_state["_df_atualizar_ofs"] = df

    if not st.button("✅ Confirmar atualização de OFs", key="btn_confirmar_atualizar_ofs",
                     type="primary"):
        return

    # Recupera df do session_state
    df = st.session_state.get("_df_atualizar_ofs", df)

    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando...")
    total_linhas = max(len(df), 1)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Session_state adicionado.")
else:
    print("AVISO: Bloco nao encontrado.")

# Adiciona progress bar no loop
OLD_LOOP = '''        try:
            with db_session() as db:
                of_existente = db.scalar(
                    select(OrdemFabricacao).where(OrdemFabricacao.numero_of == numero_of)
                )'''

NEW_LOOP = '''        barra.progress(min((_ + 1) / total_linhas, 1.0),
                       text=f"Processando {_ + 1}/{total_linhas}...")
        try:
            with db_session() as db:
                of_existente = db.scalar(
                    select(OrdemFabricacao).where(OrdemFabricacao.numero_of == numero_of)
                )'''

if OLD_LOOP in src:
    src = src.replace(OLD_LOOP, NEW_LOOP, 1)
    print("OK: Progress bar adicionada.")

# Adiciona barra no fim
OLD_FIM = '''    if erros:
        st.warning(f"{len(erros)} erro(s) encontrados.")
        with st.expander("Ver erros"):
            for e in erros[:20]:
                st.text(e)
    st.success(f"✅ OFs atualizadas: **{atualizados}** | Novas inseridas: **{inseridos}**")'''

NEW_FIM = '''    barra.progress(1.0, text="Concluído!")
    if erros:
        st.warning(f"{len(erros)} erro(s) encontrados.")
        with st.expander("Ver erros"):
            for e in erros[:20]:
                st.text(e)
    st.success(f"✅ OFs atualizadas: **{atualizados}** | Novas inseridas: **{inseridos}**")
    st.session_state.pop("_df_atualizar_ofs", None)'''

if OLD_FIM in src:
    src = src.replace(OLD_FIM, NEW_FIM, 1)
    print("OK: Fim com barra e limpeza.")
else:
    print("AVISO: Fim nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix atualizar OFs session_state' && git push")
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
