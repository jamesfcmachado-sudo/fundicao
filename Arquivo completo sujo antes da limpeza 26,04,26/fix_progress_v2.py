from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

fixes = [
    # Atualizar Corridas
    (
        'st.session_state.get("_df_atualizar_corridas", df)\n\n    inseridos = 0\n    atualizados = 0\n    ignorados = 0\n    erros = []\n    now = datetime.now().astimezone()',
        'st.session_state.get("_df_atualizar_corridas", df)\n\n    inseridos = 0\n    atualizados = 0\n    ignorados = 0\n    erros = []\n    now = datetime.now().astimezone()\n    barra = st.progress(0, text="Iniciando atualização de Corridas...")\n    total_linhas = max(len(df), 1)'
    ),
    # Importar OFs - adiciona barra apos o bloco de segurança
    (
        'st.session_state.get("_df_imp_ofs", df)\n\n    # Guarda de segurança extra: força tipos antes do loop (cobre NaN/NaT residuais)',
        'st.session_state.get("_df_imp_ofs", df)\n    barra = st.progress(0, text="Iniciando importação de OFs...")\n    total_linhas = max(len(df), 1)\n\n    # Guarda de segurança extra: força tipos antes do loop (cobre NaN/NaT residuais)'
    ),
    # Importar Corridas
    (
        'st.session_state.get("_df_imp_corridas", df)\n\n    # Guarda de segurança extra para Corridas',
        'st.session_state.get("_df_imp_corridas", df)\n    barra = st.progress(0, text="Iniciando importação de Corridas...")\n    total_linhas = max(len(df), 1)\n\n    # Guarda de segurança extra para Corridas'
    ),
]

for old, new in fixes:
    if old in src:
        src = src.replace(old, new, 1)
        print(f"OK: Barra adicionada.")
    else:
        print(f"AVISO: Nao encontrado — {old[:50]}...")

# Adiciona barra.progress no loop de OFs
OLD_LOOP_OF = '''    for _, row in df.iterrows():
        numero_of = str(row.get("numero_of"'''
NEW_LOOP_OF = '''    for _, row in df.iterrows():
        barra.progress(min((_ + 1) / total_linhas, 1.0), text=f"Processando {_ + 1}/{total_linhas}...")
        numero_of = str(row.get("numero_of"'''

if OLD_LOOP_OF in src:
    src = src.replace(OLD_LOOP_OF, NEW_LOOP_OF, 1)
    print("OK: Progress no loop de OFs.")

# Adiciona barra.progress no loop de Corridas (importar)
OLD_LOOP_CORR = '''    for _, row in df.iterrows():
        numero_corrida = str(row.get("numero_corrida"'''
NEW_LOOP_CORR = '''    for _, row in df.iterrows():
        barra.progress(min((_ + 1) / total_linhas, 1.0), text=f"Processando {_ + 1}/{total_linhas}...")
        numero_corrida = str(row.get("numero_corrida"'''

if OLD_LOOP_CORR in src:
    src = src.replace(OLD_LOOP_CORR, NEW_LOOP_CORR, 1)
    print("OK: Progress no loop de Corridas.")

# Adiciona barra final antes dos st.success
for pat in [
    'st.success(f"✅ OFs importadas:',
    'st.success(f"✅ OFs atualizadas:',
    'st.success(f"✅ Corridas importadas:',
    'st.success(f"✅ Corridas atualizadas:',
]:
    idx = src.find(pat)
    if idx > 0:
        trecho = src[max(0,idx-100):idx]
        if 'barra.progress(1.0' not in trecho:
            src = src[:idx] + 'barra.progress(1.0, text="Concluído!")\n    ' + src[idx:]
            print(f"OK: Barra final antes de '{pat[:40]}'")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Progress bar todos importadores v2' && git push")
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
