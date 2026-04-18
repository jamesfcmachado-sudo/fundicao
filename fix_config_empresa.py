"""
fix_config_empresa.py
Integra o modulo de configuracoes da empresa no app.py
"""
from pathlib import Path

print("OK: empresa_config.py ja esta na pasta.")

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "empresa_config" in src:
    print("Patch ja aplicado!")
    exit(0)

# 1) Adiciona import do modulo
OLD_IMPORT = "from auth import ("
NEW_IMPORT = ("from empresa_config import (\n"
              "    init_config_db, tela_configuracoes_empresa,\n"
              "    get_config, get_logo_ativo_bytes,\n"
              ")\n"
              "from auth import (")

if OLD_IMPORT in src:
    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("OK: Import adicionado.")
else:
    print("AVISO: Import nao encontrado.")

# 2) Inicializa o banco de configuracoes junto com init_db
OLD_INIT = ("    init_db()\n"
            "    init_auth_db()")
NEW_INIT = ("    init_db()\n"
            "    init_auth_db()\n"
            "    init_config_db()")

if OLD_INIT in src:
    src = src.replace(OLD_INIT, NEW_INIT, 1)
    print("OK: init_config_db() adicionado.")
else:
    print("AVISO: init_db nao encontrado.")

# 3) Adiciona aba Configuracoes da Empresa na tela de Administracao
OLD_ADMIN = "def tela_admin_usuarios() -> None:"
NEW_ADMIN = ("def tela_admin_empresa() -> None:\n"
             "    \"\"\"Redireciona para tela de configuracoes da empresa.\"\"\"\n"
             "    tela_configuracoes_empresa()\n"
             "\n\n"
             "def tela_admin_usuarios() -> None:")

if OLD_ADMIN in src:
    src = src.replace(OLD_ADMIN, NEW_ADMIN, 1)
    print("OK: tela_admin_empresa() adicionada.")
else:
    print("AVISO: tela_admin_usuarios nao encontrado.")

# 4) Atualiza a tela de administracao para incluir aba de configuracoes
OLD_ADMIN_TELA = ('    st.title("\u2699\ufe0f Administra\u00e7\u00e3o de Usu\u00e1rios")\n'
                  '    st.caption("Gerencie os usu\u00e1rios e suas permiss\u00f5es de acesso ao sistema.")\n'
                  '\n'
                  '    engine = _get_engine()\n'
                  '\n'
                  '    aba1, aba2 = st.tabs(["👥 Usuários cadastrados", "➕ Novo usuário"])')

NEW_ADMIN_TELA = ('    st.title("\u2699\ufe0f Administra\u00e7\u00e3o")\n'
                  '\n'
                  '    _admin_tab1, _admin_tab2, _admin_tab3 = st.tabs([\n'
                  '        "\U0001f465 Usu\u00e1rios",\n'
                  '        "\U0001f3ed Configura\u00e7\u00f5es da Empresa",\n'
                  '        "\U0001f512 Permiss\u00f5es",\n'
                  '    ])\n'
                  '\n'
                  '    with _admin_tab2:\n'
                  '        tela_configuracoes_empresa()\n'
                  '        return\n'
                  '\n'
                  '    with _admin_tab3:\n'
                  '        st.info("Use a aba Usu\u00e1rios para gerenciar permiss\u00f5es.")\n'
                  '        return\n'
                  '\n'
                  '    with _admin_tab1:\n'
                  '     st.caption("Gerencie os usu\u00e1rios e suas permiss\u00f5es de acesso ao sistema.")\n'
                  '\n'
                  '     engine = _get_engine()\n'
                  '\n'
                  '     aba1, aba2 = st.tabs(["\U0001f465 Usu\u00e1rios cadastrados", "\u2795 Novo usu\u00e1rio"])')

if OLD_ADMIN_TELA in src:
    src = src.replace(OLD_ADMIN_TELA, NEW_ADMIN_TELA, 1)
    print("OK: Abas de administracao atualizadas.")
else:
    print("AVISO: Tela de admin nao encontrada - adicionando aba separada.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK!")
    print("Rode: git add . && git commit -m 'Configuracoes da empresa' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
