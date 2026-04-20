from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona import logo apos 'import streamlit as st'
IMPORT_CERT = '''
# Modulo de certificados
try:
    from certificados import (
        init_certificados_db, tela_novo_certificado,
        tela_consulta_certificados, tela_ensaios_mecanicos,
        gerar_certificado_pdf
    )
    _CERTS_OK = True
except Exception as _e_cert:
    _CERTS_OK = False
'''

# Insere apos a linha 'import streamlit as st'
idx = src.find('import streamlit as st')
if idx > 0:
    fim_linha = src.find('\n', idx) + 1
    src = src[:fim_linha] + IMPORT_CERT + src[fim_linha:]
    print("OK: Import de certificados adicionado.")
else:
    print("AVISO: 'import streamlit as st' nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix import certificados definitivo' && git push")
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
