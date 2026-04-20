from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona chamada de init_certificados_db no inicio da funcao tela_novo_certificado
# Mas como é importado localmente, precisamos chamar dentro do try
OLD_CERT_ROUTE = '''    elif pagina == "Novo Certificado":
        try:
            from certificados import tela_novo_certificado as _tnc
            _tnc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")'''

NEW_CERT_ROUTE = '''    elif pagina == "Novo Certificado":
        try:
            from certificados import init_certificados_db as _icd, tela_novo_certificado as _tnc
            _icd()
            _tnc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")'''

if OLD_CERT_ROUTE in src:
    src = src.replace(OLD_CERT_ROUTE, NEW_CERT_ROUTE, 1)
    print("OK: init_certificados_db adicionado no Novo Certificado.")
else:
    print("AVISO: Bloco nao encontrado.")

OLD_CONS_ROUTE = '''    elif pagina == "Consulta de Certificados":
        try:
            from certificados import tela_consulta_certificados as _tcc
            _tcc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")'''

NEW_CONS_ROUTE = '''    elif pagina == "Consulta de Certificados":
        try:
            from certificados import init_certificados_db as _icd2, tela_consulta_certificados as _tcc
            _icd2()
            _tcc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")'''

if OLD_CONS_ROUTE in src:
    src = src.replace(OLD_CONS_ROUTE, NEW_CONS_ROUTE, 1)
    print("OK: init_certificados_db adicionado na Consulta.")

OLD_ENS_ROUTE = '''    elif pagina == "Ensaios Mecânicos":
        try:
            from certificados import tela_ensaios_mecanicos as _tem
            _tem()
        except Exception as _ec:
            st.error(f"Erro ao carregar ensaios: {_ec}")'''

NEW_ENS_ROUTE = '''    elif pagina == "Ensaios Mecânicos":
        try:
            from certificados import init_certificados_db as _icd3, tela_ensaios_mecanicos as _tem
            _icd3()
            _tem()
        except Exception as _ec:
            st.error(f"Erro ao carregar ensaios: {_ec}")'''

if OLD_ENS_ROUTE in src:
    src = src.replace(OLD_ENS_ROUTE, NEW_ENS_ROUTE, 1)
    print("OK: init_certificados_db adicionado nos Ensaios.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Init tabelas certificados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
