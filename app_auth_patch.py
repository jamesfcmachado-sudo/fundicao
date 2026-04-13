"""
app_auth_patch.py
=================
Integra o sistema de login/permissões no app.py existente.
Execute UMA VEZ na pasta do projeto:
    python app_auth_patch.py
"""

from pathlib import Path

APP = Path("app.py")
BAK = Path("app_auth_backup.py")

src = APP.read_text(encoding="utf-8")

if "tela_login" in src:
    print("⚠️  app.py já parece ter autenticação. Nenhuma alteração feita.")
    exit(0)

BAK.write_text(src, encoding="utf-8")
print(f"✅  Backup salvo em: {BAK}")

# 1) Adicionar import do auth no topo do arquivo
OLD_IMPORT = "from fundicao_db import SessionLocal, init_db, ping_database"
NEW_IMPORT = """from fundicao_db import SessionLocal, init_db, ping_database
from auth import (
    init_auth_db, tela_login, tela_admin_usuarios,
    tem_permissao, usuario_logado, fazer_logout, PERMISSOES,
)"""

src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)

# 2) Adicionar init_auth_db() logo após init_db()
OLD_INIT = "    init_db()\n    _migrar_banco_of_status()"
NEW_INIT = """    init_db()
    init_auth_db()
    _migrar_banco_of_status()"""

src = src.replace(OLD_INIT, NEW_INIT, 1)

# 3) Adicionar verificação de login logo após init_auth_db
OLD_AFTER_INIT = "    if 'mostrar_importador' not in st.session_state:"
NEW_AFTER_INIT = """    # ── Verificação de login ──────────────────────────────────────────────
    if not tela_login():
        st.stop()

    # ── Logout na sidebar ─────────────────────────────────────────────────
    u = usuario_logado()

    if 'mostrar_importador' not in st.session_state:"""

src = src.replace(OLD_AFTER_INIT, NEW_AFTER_INIT, 1)

# 4) Adicionar botão de logout e info do usuário na sidebar
OLD_SIDEBAR_HEADER = '        st.header("Sistema de Controle de Fundição")'
NEW_SIDEBAR_HEADER = '''        st.header("Sistema de Controle de Fundição")
        # Info do usuário logado + logout
        _u = usuario_logado()
        if _u:
            st.caption(f"👤 **{_u['nome']}**")
            if st.button("🚪 Sair", key="btn_logout"):
                fazer_logout()
                st.rerun()'''

src = src.replace(OLD_SIDEBAR_HEADER, NEW_SIDEBAR_HEADER, 1)

# 5) Adicionar Admin Usuários no menu de navegação e controle de permissões
OLD_RADIO = '''        pagina = st.radio(
            "Navegação",
            (
                "Dashboard",
                "Nova Ordem de Fabricação",
                "Nova Ordem de Entrega",
                "Consulta de OEs",
                "Lançar Corrida",
                "Consulta de Rastreabilidade",
                "Consulta de Corridas",
                "Relatórios",
            ),
            label_visibility="collapsed",
        )'''

NEW_RADIO = '''        # Monta menu de acordo com permissões do usuário
        _opcoes_nav = []
        if tem_permissao("dashboard"):          _opcoes_nav.append("Dashboard")
        if tem_permissao("nova_of"):            _opcoes_nav.append("Nova Ordem de Fabricação")
        if tem_permissao("nova_oe"):            _opcoes_nav.append("Nova Ordem de Entrega")
        if tem_permissao("consulta_oes"):       _opcoes_nav.append("Consulta de OEs")
        if tem_permissao("lancar_corrida"):     _opcoes_nav.append("Lançar Corrida")
        if tem_permissao("consulta_rastreab"):  _opcoes_nav.append("Consulta de Rastreabilidade")
        if tem_permissao("consulta_corridas"):  _opcoes_nav.append("Consulta de Corridas")
        if tem_permissao("relatorios"):         _opcoes_nav.append("Relatórios")
        if tem_permissao("admin"):              _opcoes_nav.append("⚙️ Administração")

        if not _opcoes_nav:
            st.warning("Você não tem acesso a nenhum módulo.")
            st.stop()

        pagina = st.radio(
            "Navegação",
            _opcoes_nav,
            label_visibility="collapsed",
        )'''

src = src.replace(OLD_RADIO, NEW_RADIO, 1)

# 6) Adicionar botão importar planilha apenas se tiver permissão
OLD_IMPORTAR = '        if st.button("📥 Importar Planilha Excel"):'
NEW_IMPORTAR = '        if tem_permissao("importar_excel") and st.button("📥 Importar Planilha Excel"):'

src = src.replace(OLD_IMPORTAR, NEW_IMPORTAR, 1)

# 7) Adicionar rota para Administração no bloco de páginas
OLD_ELSE_RELATORIOS = "    else:\n        pagina_relatorios()"
NEW_ELSE_RELATORIOS = """    elif pagina == "⚙️ Administração":
        tela_admin_usuarios()
    else:
        pagina_relatorios()"""

src = src.replace(OLD_ELSE_RELATORIOS, NEW_ELSE_RELATORIOS, 1)

APP.write_text(src, encoding="utf-8")
print("✅  app.py atualizado com sistema de autenticação!")
print("   Alterações:")
print("     • Tela de login adicionada")
print("     • Menu dinâmico por permissão")
print("     • Botão logout na sidebar")
print("     • Tela de administração de usuários")
print("     • Importar Excel protegido por permissão")
print("\n⚠️  Não esqueça de adicionar no Streamlit Cloud secrets:")
print('   ADMIN_SENHA = "sua_senha_master_aqui"')
