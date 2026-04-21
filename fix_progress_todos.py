from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

fixes = [
    # Importar OFs - apos o session_state
    (
        '    df = st.session_state.get("_df_imp_ofs", df)\n    inseridos = 0\n    erros = []\n    now = datetime.now().astimezone()',
        '    df = st.session_state.get("_df_imp_ofs", df)\n    inseridos = 0\n    erros = []\n    now = datetime.now().astimezone()\n    barra = st.progress(0, text="Iniciando importação de OFs...")\n    total_linhas = max(len(df), 1)'
    ),
    # Importar Corridas
    (
        '    df = st.session_state.get("_df_imp_corridas", df)\n    inseridos = 0\n    erros = []\n    now = datetime.now().astimezone()',
        '    df = st.session_state.get("_df_imp_corridas", df)\n    inseridos = 0\n    erros = []\n    now = datetime.now().astimezone()\n    barra = st.progress(0, text="Iniciando importação de Corridas...")\n    total_linhas = max(len(df), 1)'
    ),
    # Atualizar Corridas
    (
        '    df = st.session_state.get("_df_atualizar_corridas", df)\n    inseridos = 0\n    atualizados = 0\n    erros = []\n    now = datetime.now().astimezone()',
        '    df = st.session_state.get("_df_atualizar_corridas", df)\n    inseridos = 0\n    atualizados = 0\n    erros = []\n    now = datetime.now().astimezone()\n    barra = st.progress(0, text="Iniciando atualização de Corridas...")\n    total_linhas = max(len(df), 1)'
    ),
    # Importar OEs
    (
        '    df = st.session_state.get("_df_imp_oes", df)\n    inseridos = erros = 0',
        '    df = st.session_state.get("_df_imp_oes", df)\n    inseridos = erros = 0\n    barra = st.progress(0, text="Iniciando importação de OEs...")\n    total_linhas = max(len(df), 1)'
    ),
    # Atualizar OEs
    (
        '    df = st.session_state.get("_df_atu_oes", df)\n    atualizados = inseridos = erros = 0',
        '    df = st.session_state.get("_df_atu_oes", df)\n    atualizados = inseridos = erros = 0\n    barra = st.progress(0, text="Iniciando atualização de OEs...")\n    total_linhas = max(len(df), 1)'
    ),
    # Importar Certificados
    (
        '    df = st.session_state.get("_df_imp_certs", df)\n    inseridos = erros = 0',
        '    df = st.session_state.get("_df_imp_certs", df)\n    inseridos = erros = 0\n    barra = st.progress(0, text="Iniciando importação de Certificados...")\n    total_linhas = max(len(df), 1)'
    ),
    # Atualizar Certificados
    (
        '    df = st.session_state.get("_df_atu_certs", df)\n    atualizados = inseridos = erros = 0',
        '    df = st.session_state.get("_df_atu_certs", df)\n    atualizados = inseridos = erros = 0\n    barra = st.progress(0, text="Iniciando atualização de Certificados...")\n    total_linhas = max(len(df), 1)'
    ),
]

for old, new in fixes:
    if old in src:
        src = src.replace(old, new, 1)
        print(f"OK: Barra adicionada — {old[:60]}...")
    else:
        print(f"AVISO: Nao encontrado — {old[:60]}...")

# Adiciona atualização da barra nos loops de cada importador
# Para cada loop "for _, row in df.iterrows():"
# precisamos adicionar barra.progress() no inicio do loop

import re

# Encontra loops de importacao e adiciona progresso
# Padrao: for _, row in df.iterrows(): seguido de numero_of ou similar
loops = [
    # importar OFs
    ('_df_imp_ofs', 'numero_of = str(row.get("numero_of"'),
    # importar corridas  
    ('_df_imp_corridas', 'numero_corrida = str(row.get("numero_corrida"'),
    # atualizar corridas
    ('_df_atualizar_corridas', 'numero_corrida_upd'),
    # importar OEs
    ('_df_imp_oes', '"noe":     str(_v("numero_oe"'),
    # atualizar OEs
    ('_df_atu_oes', 'noe = str(_v("numero_oe"'),
    # importar certs
    ('_df_imp_certs', 'numero_certificado=str(_v("numero_certificado"'),
    # atualizar certs
    ('_df_atu_certs', 'num_cert = str(_v("numero_certificado"'),
]

# Adiciona progresso nos loops principais
for _, row_kw in loops:
    # Busca "for _, row in df.iterrows():" antes do row_kw
    idx = src.find(row_kw)
    if idx > 0:
        # Vai atras para encontrar o for loop
        for_idx = src.rfind("    for _, row in df.iterrows():", 0, idx)
        if for_idx > 0:
            old_for = "    for _, row in df.iterrows():\n"
            new_for = "    for _, row in df.iterrows():\n        barra.progress(min((_ + 1) / total_linhas, 1.0), text=f\"Processando {_ + 1}/{total_linhas}...\")\n"
            # Substitui apenas se ainda nao tem barra nesse loop
            check_idx = src.find("barra.progress", for_idx)
            next_for = src.find("    for _, row in df.iterrows():", for_idx + 1)
            if check_idx == -1 or (next_for > 0 and check_idx > next_for):
                src = src[:for_idx] + new_for + src[for_idx + len(old_for):]
                print(f"OK: Progress no loop de {row_kw[:30]}...")
                break

# Adiciona barra.progress(1.0) antes de cada st.success final
success_patterns = [
    'st.success(f"✅ OFs importadas:',
    'st.success(f"✅ OFs atualizadas:',
    'st.success(f"✅ Corridas importadas:',
    'st.success(f"✅ Corridas atualizadas:',
    'st.success(f"OEs importadas:',
    'st.success(f"OEs atualizadas:',
    'st.success(f"Certificados importados:',
    'st.success(f"Certificados atualizados:',
]

for pat in success_patterns:
    idx = src.find(pat)
    if idx > 0:
        # Verifica se ja tem barra.progress antes
        trecho = src[max(0,idx-100):idx]
        if 'barra.progress(1.0' not in trecho:
            src = src[:idx] + 'barra.progress(1.0, text="Concluído!")\n    ' + src[idx:]
            print(f"OK: Barra final adicionada antes de '{pat[:40]}'")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Progress bar todos importadores' && git push")
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
