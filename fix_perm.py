from pathlib import Path

APP = Path(r"C:\Users\james\OneDrive\Area de Trabalho\CURSOR\app.py")

# Tenta encontrar o arquivo
if not APP.exists():
    APP = Path("app.py")

src = APP.read_text(encoding="utf-8")

count = 0

# Protecao 1: Alterar OF
old1 = '                        with st.expander("\u270f\ufe0f Alterar dados desta OF", expanded=False):'
new1 = (
    '                        if not tem_permissao("relatorios_alterar_of"):\n'
    '                            st.info("Sem permissao para alterar OFs.")\n'
    '                        else:\n'
    '                            with st.expander("\u270f\ufe0f Alterar dados desta OF", expanded=False):'
)
if old1 in src:
    src = src.replace(old1, new1, 1)
    count += 1
    print("OK: Alterar OF protegido.")
else:
    print("AVISO: Texto 'Alterar OF' nao encontrado.")

# Protecao 2: Alterar Corrida
old2 = '                    with st.expander("\u270f\ufe0f Alterar dados desta corrida", expanded=False):'
new2 = (
    '                    if not tem_permissao("relatorios_alterar_corrida"):\n'
    '                        st.info("Sem permissao para alterar corridas.")\n'
    '                    else:\n'
    '                        with st.expander("\u270f\ufe0f Alterar dados desta corrida", expanded=False):'
)
if old2 in src:
    src = src.replace(old2, new2, 1)
    count += 1
    print("OK: Alterar Corrida protegido.")
else:
    print("AVISO: Texto 'Alterar Corrida' nao encontrado.")

# Protecao 3: Configuracoes tab4
old3 = '    with tab4:\n        st.subheader'
new3 = (
    '    with tab4:\n'
    '        if not tem_permissao("configuracoes"):\n'
    '            st.warning("Sem permissao para acessar Configuracoes.")\n'
    '            st.stop()\n'
    '        st.subheader'
)
if old3 in src:
    src = src.replace(old3, new3, 1)
    count += 1
    print("OK: Configuracoes protegidas.")
else:
    print("AVISO: Texto 'tab4' nao encontrado.")

APP.write_text(src, encoding="utf-8")
print(f"\nTotal: {count} protecoes adicionadas!")
