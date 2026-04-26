from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Substitui as referencias a _CERTS_OK no roteamento
# para nao depender de variavel global
OLD_CERT = '''    elif pagina == "Novo Certificado":
        if _CERTS_OK:
            tela_novo_certificado()
        else:
            st.error("Modulo de certificados nao disponivel.")
    elif pagina == "Consulta de Certificados":
        if _CERTS_OK:
            tela_consulta_certificados()
        else:
            st.error("Modulo de certificados nao disponivel.")
    elif pagina == "Ensaios Mecanicos":
        if _CERTS_OK:
            tela_ensaios_mecanicos()
        else:
            st.error("Modulo de certificados nao disponivel.")'''

NEW_CERT = '''    elif pagina == "Novo Certificado":
        try:
            from certificados import tela_novo_certificado as _tnc
            _tnc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")
    elif pagina == "Consulta de Certificados":
        try:
            from certificados import tela_consulta_certificados as _tcc
            _tcc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")
    elif pagina == "Ensaios Mecânicos":
        try:
            from certificados import tela_ensaios_mecanicos as _tem
            _tem()
        except Exception as _ec:
            st.error(f"Erro ao carregar ensaios: {_ec}")'''

if OLD_CERT in src:
    src = src.replace(OLD_CERT, NEW_CERT, 1)
    print("OK: Roteamento corrigido com import local.")
else:
    # Tenta variacao com acento
    OLD_CERT2 = '''    elif pagina == "Ensaios Mecânicos":
        if _CERTS_OK:
            tela_ensaios_mecanicos()
        else:
            st.error("Modulo de certificados nao disponivel.")'''
    if OLD_CERT2 in src:
        src = src.replace(OLD_CERT2,
            '''    elif pagina == "Ensaios Mecânicos":
        try:
            from certificados import tela_ensaios_mecanicos as _tem
            _tem()
        except Exception as _ec:
            st.error(f"Erro: {_ec}")''', 1)
        print("OK: Ensaios Mecanicos corrigido.")

    # Corrige Novo Certificado
    for old, new in [
        ('        if _CERTS_OK:\n            tela_novo_certificado()\n        else:\n            st.error("Modulo de certificados nao disponivel.")',
         '        try:\n            from certificados import tela_novo_certificado as _tnc\n            _tnc()\n        except Exception as _ec:\n            st.error(f"Erro: {_ec}")'),
        ('        if _CERTS_OK:\n            tela_consulta_certificados()\n        else:\n            st.error("Modulo de certificados nao disponivel.")',
         '        try:\n            from certificados import tela_consulta_certificados as _tcc\n            _tcc()\n        except Exception as _ec:\n            st.error(f"Erro: {_ec}")'),
    ]:
        if old in src:
            src = src.replace(old, new, 1)
            print(f"OK: Bloco corrigido.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix escopo CERTS_OK' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
