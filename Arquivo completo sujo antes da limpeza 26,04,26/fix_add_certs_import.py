from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona import de certificados apos 'import streamlit as st'
OLD = 'import streamlit as st\nfrom sqlalchemy import and_, select'
NEW = '''import streamlit as st

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

from sqlalchemy import and_, select'''

if OLD in src and "_CERTS_OK" not in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Import de certificados adicionado.")
elif "_CERTS_OK" in src:
    print("INFO: _CERTS_OK ja existe.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix import certificados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
