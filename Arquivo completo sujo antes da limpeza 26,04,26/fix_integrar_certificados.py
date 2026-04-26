from pathlib import Path

if not Path("certificados.py").exists():
    print("ERRO: certificados.py nao encontrado na pasta CURSOR!")
    exit(1)
print("OK: certificados.py encontrado.")

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD_IMPORT = "# redeploy-mover-alterar"
NEW_IMPORT = """# redeploy-mover-alterar
try:
    from certificados import (
        init_certificados_db, tela_novo_certificado,
        tela_consulta_certificados, tela_ensaios_mecanicos,
        gerar_certificado_pdf
    )
    _CERTS_OK = True
except Exception as _e_cert:
    _CERTS_OK = False"""

if OLD_IMPORT in src and "_CERTS_OK" not in src:
    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("OK: Import adicionado.")

OLD_INIT = "    _migrar_banco_oe()"
NEW_INIT = """    _migrar_banco_oe()
    if _CERTS_OK:
        try:
            init_certificados_db()
        except Exception:
            pass"""

if OLD_INIT in src and "init_certificados_db" not in src:
    src = src.replace(OLD_INIT, NEW_INIT, 1)
    print("OK: init_certificados_db adicionado.")

OLD_MENU = '"Nova Ordem de Entrega",'
NEW_MENU = '''"Nova Ordem de Entrega",
                "Novo Certificado",
                "Consulta de Certificados",
                "Ensaios Mecânicos",'''

if OLD_MENU in src and "Novo Certificado" not in src:
    src = src.replace(OLD_MENU, NEW_MENU, 1)
    print("OK: Menus adicionados.")

OLD_ROUTE = '    elif pagina == "Nova Ordem de Entrega":\n        pagina_nova_oe()'
NEW_ROUTE = '''    elif pagina == "Nova Ordem de Entrega":
        pagina_nova_oe()
    elif pagina == "Novo Certificado":
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

if OLD_ROUTE in src and "Novo Certificado" not in src:
    src = src.replace(OLD_ROUTE, NEW_ROUTE, 1)
    print("OK: Roteamento adicionado.")

AUTH = Path("auth.py")
if AUTH.exists():
    auth_src = AUTH.read_text(encoding="utf-8")
    if "Novo Certificado" not in auth_src:
        OLD_PERM = '"Nova Ordem de Entrega": True,'
        NEW_PERM = '''"Nova Ordem de Entrega": True,
            "Novo Certificado": True,
            "Consulta de Certificados": True,
            "Ensaios Mecanicos": True,'''
        if OLD_PERM in auth_src:
            auth_src = auth_src.replace(OLD_PERM, NEW_PERM, 1)
            AUTH.write_text(auth_src, encoding="utf-8")
            print("OK: Permissoes adicionadas.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
for nome in ["app.py", "certificados.py"]:
    codigo = Path(nome).read_text(encoding="utf-8")
    tmp = tempfile.mktemp(suffix='.py')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(codigo)
    try:
        py_compile.compile(tmp, doraise=True)
        print(f"SINTAXE {nome} OK!")
    except py_compile.PyCompileError as e:
        print(f"ERRO {nome}: {e}")
    finally:
        os.unlink(tmp)

print("\nRode: git add . && git commit -m 'Modulo certificados completo' && git push")
