from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Remove o bloco de import do inicio
OLD = '''# redeploy-mover-alterar
try:
    from certificados import (
        init_certificados_db, tela_novo_certificado,
        tela_consulta_certificados, tela_ensaios_mecanicos,
        gerar_certificado_pdf
    )
    _CERTS_OK = True
except Exception as _e_cert:
    _CERTS_OK = False
# deploy: PDF fiel ao template v2
"""
Sistema de Controle de Fundição — interface Streamlit + SQLAlchemy (SQLite fundicao.db).

Na raiz do projeto:
    streamlit run app.py
"""'''

NEW = '''# redeploy-mover-alterar
# deploy: PDF fiel ao template v2
"""
Sistema de Controle de Fundição — interface Streamlit + SQLAlchemy (SQLite fundicao.db).

Na raiz do projeto:
    streamlit run app.py
"""'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Docstring restaurado ao inicio.")
else:
    print("AVISO: Bloco nao encontrado.")

# Adiciona o import depois dos imports principais
OLD_IMPORT = 'import streamlit as st'
NEW_IMPORT = '''import streamlit as st

# Modulo de certificados
try:
    from certificados import (
        init_certificados_db, tela_novo_certificado,
        tela_consulta_certificados, tela_ensaios_mecanicos,
        gerar_certificado_pdf
    )
    _CERTS_OK = True
except Exception as _e_cert:
    _CERTS_OK = False'''

if OLD_IMPORT in src and "_CERTS_OK" not in src:
    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("OK: Import movido para apos imports principais.")
elif "_CERTS_OK" in src:
    print("INFO: Import ja existe.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix docstring certificados' && git push")
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
