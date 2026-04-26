from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

fixes = [
    # Atualizar Corridas
    (
        '''    if not st.button("Confirmar atualizacao de Corridas", key="btn_confirmar_atualizar_corridas"):
        return

    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()''',
        '''    st.session_state["_df_atualizar_corridas"] = df
    if not st.button("✅ Confirmar atualização de Corridas", key="btn_confirmar_atualizar_corridas",
                     type="primary"):
        return
    df = st.session_state.get("_df_atualizar_corridas", df)
    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando...")
    total_linhas = max(len(df), 1)'''
    ),
    # Importar OFs
    (
        '''    if not st.button("Confirmar importacao de OFs", key="btn_confirmar_ofs"):
        return

    inseridos = 0
    erros = []
    now = datetime.now().astimezone()''',
        '''    st.session_state["_df_importar_ofs"] = df
    if not st.button("✅ Confirmar importação de OFs", key="btn_confirmar_ofs",
                     type="primary"):
        return
    df = st.session_state.get("_df_importar_ofs", df)
    inseridos = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando...")
    total_linhas = max(len(df), 1)'''
    ),
    # Importar Corridas
    (
        '''    if not st.button("Confirmar importacao de Corridas", key="btn_confirmar_corridas"):
        return

    inseridos = 0
    erros = []
    now = datetime.now().astimezone()''',
        '''    st.session_state["_df_importar_corridas"] = df
    if not st.button("✅ Confirmar importação de Corridas", key="btn_confirmar_corridas",
                     type="primary"):
        return
    df = st.session_state.get("_df_importar_corridas", df)
    inseridos = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando...")
    total_linhas = max(len(df), 1)'''
    ),
]

for old, new in fixes:
    if old in src:
        src = src.replace(old, new, 1)
        print(f"OK: Fix aplicado.")
    else:
        print(f"AVISO: Bloco nao encontrado.")

# Fix para OEs e Certificados no mesmo arquivo
for key, label in [
    ("btn_confirmar_oes", "OEs"),
    ("btn_atualizar_oes", "atualização de OEs"),
    ("btn_confirmar_certs", "Certificados"),
    ("btn_atualizar_certs", "atualização de Certificados"),
]:
    old = f'    if not st.button("✅ Confirmar importação de {label.split()[-1]}", key="{key}"):\n        return'
    # Busca qualquer botao sem session_state
    idx = src.find(f'key="{key}"')
    if idx > 0:
        # Verifica se ja tem session_state antes
        trecho = src[max(0,idx-300):idx]
        if "session_state" not in trecho:
            print(f"AVISO: {key} pode precisar de session_state - verificar manualmente.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix session_state todos importadores' && git push")
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
