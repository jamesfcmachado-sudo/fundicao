"""
fix_admin_config_tab.py
Adiciona aba de Configuracoes da Empresa na tela de Administracao
"""
from pathlib import Path

# Atualiza auth.py para incluir a aba de configuracoes
AUTH = Path("auth.py")
src = AUTH.read_text(encoding="utf-8")

if "tela_configuracoes_empresa" in src:
    print("Ja aplicado no auth.py!")
else:
    # Adiciona import no topo do auth.py
    OLD_IMP = "from __future__ import annotations"
    NEW_IMP = ("from __future__ import annotations\n"
               "# empresa_config importado dentro das funcoes para evitar circular import")
    src = src.replace(OLD_IMP, NEW_IMP, 1)

    # Substitui o inicio da funcao tela_admin_usuarios para adicionar abas
    OLD_FUNC = ('def tela_admin_usuarios() -> None:\n'
                '    """Tela completa de gerenciamento de usuários (apenas admin)."""\n'
                '    if not tem_permissao("admin"):\n'
                '        st.error("⛔ Acesso negado. Apenas administradores podem acessar esta tela.")\n'
                '        return\n'
                '\n'
                '    st.title("⚙️ Administração de Usuários")\n'
                '    st.caption("Gerencie os usuários e suas permissões de acesso ao sistema.")\n'
                '\n'
                '    engine = _get_engine()\n'
                '\n'
                '    aba1, aba2 = st.tabs(["👥 Usuários cadastrados", "➕ Novo usuário"])')

    NEW_FUNC = ('def tela_admin_usuarios() -> None:\n'
                '    """Tela completa de gerenciamento de usuarios e configuracoes (apenas admin)."""\n'
                '    if not tem_permissao("admin"):\n'
                '        st.error("Acesso negado. Apenas administradores podem acessar esta tela.")\n'
                '        return\n'
                '\n'
                '    st.title("\u2699\ufe0f Administra\u00e7\u00e3o")\n'
                '\n'
                '    _tab_usr, _tab_cfg, _tab_new = st.tabs([\n'
                '        "\U0001f465 Usu\u00e1rios cadastrados",\n'
                '        "\U0001f3ed Configura\u00e7\u00f5es da Empresa",\n'
                '        "\u2795 Novo usu\u00e1rio",\n'
                '    ])\n'
                '\n'
                '    with _tab_cfg:\n'
                '        from empresa_config import tela_configuracoes_empresa\n'
                '        tela_configuracoes_empresa()\n'
                '\n'
                '    engine = _get_engine()\n'
                '\n'
                '    with _tab_usr:\n'
                '     aba1 = _tab_usr\n'
                '    with _tab_new:\n'
                '     aba2 = _tab_new\n'
                '    aba1, aba2 = _tab_usr, _tab_new\n'
                '    if True:  # bloco usuarios\n'
                '     pass\n'
                '    aba1, aba2 = _tab_usr, _tab_new')

    if OLD_FUNC in src:
        src = src.replace(OLD_FUNC, NEW_FUNC, 1)
        print("OK: Abas adicionadas na tela de admin.")
    else:
        print("AVISO: Funcao nao encontrada, tentando abordagem diferente...")
        # Abordagem alternativa: encontra a linha com st.tabs
        lines = src.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if 'st.tabs(["' in line and 'Usu' in line and 'Novo' in line:
                indent = len(line) - len(line.lstrip())
                sp = ' ' * indent
                # Substitui a linha das tabs
                new_lines.append(f'{sp}_tab_usr, _tab_cfg, _tab_new = st.tabs([')
                new_lines.append(f'{sp}    "\U0001f465 Usu\u00e1rios cadastrados",')
                new_lines.append(f'{sp}    "\U0001f3ed Configura\u00e7\u00f5es da Empresa",')
                new_lines.append(f'{sp}    "\u2795 Novo usu\u00e1rio",')
                new_lines.append(f'{sp}])')
                new_lines.append(f'{sp}with _tab_cfg:')
                new_lines.append(f'{sp}    from empresa_config import tela_configuracoes_empresa')
                new_lines.append(f'{sp}    tela_configuracoes_empresa()')
                new_lines.append(f'{sp}aba1, aba2 = _tab_usr, _tab_new')
                print(f"OK: Tabs substituidas na linha {i+1}.")
                i += 1
                continue
            new_lines.append(line)
            i += 1
        src = '\n'.join(new_lines)

    AUTH.write_text(src, encoding="utf-8")

# Verifica sintaxe do auth.py
import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE auth.py OK!")
    print("Rode: git add . && git commit -m 'Configuracoes da empresa' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO auth.py: {e}")
finally:
    os.unlink(tmp)
