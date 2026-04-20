from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona menus de certificados apos Nova OE
OLD_MENU = '''        if tem_permissao("nova_oe"):            _opcoes_nav.append("Nova Ordem de Entrega")
        if tem_permissao("consulta_oes"):       _opcoes_nav.append("Consulta de OEs")'''

NEW_MENU = '''        if tem_permissao("nova_oe"):            _opcoes_nav.append("Nova Ordem de Entrega")
        if tem_permissao("consulta_oes"):       _opcoes_nav.append("Consulta de OEs")
        if tem_permissao("novo_certificado"):   _opcoes_nav.append("Novo Certificado")
        if tem_permissao("consulta_certs"):     _opcoes_nav.append("Consulta de Certificados")
        if tem_permissao("ensaios_mec"):        _opcoes_nav.append("Ensaios Mecânicos")'''

if OLD_MENU in src:
    src = src.replace(OLD_MENU, NEW_MENU, 1)
    print("OK: Menus de certificados adicionados.")
else:
    print("AVISO: Menu nao encontrado.")

APP.write_text(src, encoding="utf-8")

# Adiciona permissoes no auth.py
AUTH = Path("auth.py")
if AUTH.exists():
    auth_src = AUTH.read_text(encoding="utf-8")

    # Adiciona permissoes nos defaults
    OLD_PERM = '"nova_oe":          True,'
    NEW_PERM = '''"nova_oe":          True,
            "novo_certificado": True,
            "consulta_certs":   True,
            "ensaios_mec":      True,'''
    if OLD_PERM in auth_src and "novo_certificado" not in auth_src:
        auth_src = auth_src.replace(OLD_PERM, NEW_PERM, 1)
        AUTH.write_text(auth_src, encoding="utf-8")
        print("OK: Permissoes adicionadas no auth.py.")
    else:
        print("INFO: Permissoes ja existem.")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Menus certificados no lateral' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
