"""
auth.py — Sistema de autenticação e controle de acesso.
Tabela `usuario` no banco PostgreSQL (criada automaticamente).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime

import streamlit as st
from sqlalchemy import text

# ── Permissões disponíveis no sistema ────────────────────────────────────────
PERMISSOES = {
    "dashboard":              "Dashboard",
    "importar_excel":         "Importar Planilha Excel",
    "nova_of":                "Nova Ordem de Fabricação",
    "nova_oe":                "Nova Ordem de Entrega",
    "consulta_oes":           "Consulta de OEs",
    "lancar_corrida":         "Lançar Corrida",
    "consulta_rastreab":      "Consulta de Rastreabilidade",
    "consulta_corridas":      "Consulta de Corridas",
    "relatorios":             "Relatórios (visualizar)",
    "relatorios_alterar_of":  "Relatórios → Alterar OF",
    "relatorios_excluir_of":  "Relatórios → Excluir OF",
    "relatorios_excluir_of":  "Relatórios → Excluir OF",
    "relatorios_alterar_corrida": "Relatórios → Alterar Corridas",
    "relatorios_excluir_corrida": "Relatórios → Excluir Corridas",
    "configuracoes":          "Configurações",
    "admin":                  "Administrador (acesso total)",
}

# Senha do admin master via environment/secrets
ADMIN_MASTER_LOGIN = "admin"


def _get_engine():
    from fundicao_db import engine
    return engine


def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


# ── Criação da tabela de usuários ─────────────────────────────────────────────
def init_auth_db() -> None:
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                login VARCHAR(80) NOT NULL UNIQUE,
                nome VARCHAR(200) NOT NULL,
                senha_hash VARCHAR(64) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                permissoes TEXT NOT NULL DEFAULT '',
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

    # Garante que o admin master existe
    _garantir_admin_master()


def _garantir_admin_master() -> None:
    """Cria o usuário admin master se não existir."""
    engine = _get_engine()
    senha_master = os.environ.get("ADMIN_SENHA", "")
    if not senha_master:
        try:
            import streamlit as st
            senha_master = st.secrets.get("ADMIN_SENHA", "admin123")
        except Exception:
            senha_master = "admin123"

    with engine.begin() as conn:
        existe = conn.execute(
            text("SELECT id FROM usuario WHERE login = :login"),
            {"login": ADMIN_MASTER_LOGIN}
        ).fetchone()

        if not existe:
            conn.execute(text("""
                INSERT INTO usuario (login, nome, senha_hash, ativo, permissoes)
                VALUES (:login, :nome, :senha_hash, TRUE, :permissoes)
            """), {
                "login": ADMIN_MASTER_LOGIN,
                "nome": "Administrador Master",
                "senha_hash": _hash_senha(senha_master),
                "permissoes": "admin",
            })


# ── Autenticação ──────────────────────────────────────────────────────────────
def autenticar(login: str, senha: str) -> dict | None:
    """Retorna dict do usuário se credenciais válidas, None caso contrário."""
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM usuario WHERE login = :login AND ativo = TRUE"),
            {"login": login.strip().lower()}
        ).fetchone()

    if not row:
        return None

    if row.senha_hash != _hash_senha(senha):
        return None

    return dict(row._mapping)


def tem_permissao(permissao: str) -> bool:
    """Verifica se o usuário logado tem uma permissão específica."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        return False
    perms = [p.strip() for p in usuario.get("permissoes", "").split(",")]
    return "admin" in perms or permissao in perms


def usuario_logado() -> dict | None:
    return st.session_state.get("usuario_logado")


def fazer_logout() -> None:
    st.session_state.pop("usuario_logado", None)


# ── Tela de Login ─────────────────────────────────────────────────────────────
def tela_login() -> bool:
    """
    Exibe a tela de login. Retorna True se o usuário está autenticado.
    """
    if st.session_state.get("usuario_logado"):
        return True

    # CSS customizado para a tela de login
    st.markdown("""
    <style>
    .login-box {
        max-width: 400px;
        margin: 80px auto;
        padding: 40px;
        background: #f8f9fa;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    .login-title {
        text-align: center;
        color: #1a3a5c;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .login-sub {
        text-align: center;
        color: #666;
        margin-bottom: 32px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-title">🏭 Controle de Fundição</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Faça login para continuar</div>', unsafe_allow_html=True)
        st.divider()

        login = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_input")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha", key="senha_input")

        if st.button("Entrar", use_container_width=True, type="primary"):
            if not login or not senha:
                st.error("Preencha usuário e senha.")
            else:
                usuario = autenticar(login, senha)
                if usuario:
                    st.session_state["usuario_logado"] = usuario
                    st.success(f"Bem-vindo, {usuario['nome']}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos, ou acesso bloqueado.")

    return False


# ── Tela de Administração de Usuários ─────────────────────────────────────────
def tela_admin_usuarios() -> None:
    """Tela completa de gerenciamento de usuários (apenas admin)."""
    if not tem_permissao("admin"):
        st.error("⛔ Acesso negado. Apenas administradores podem acessar esta tela.")
        return

    st.title("⚙️ Administração de Usuários")
    st.caption("Gerencie os usuários e suas permissões de acesso ao sistema.")

    engine = _get_engine()

    aba1, aba2 = st.tabs(["👥 Usuários cadastrados", "➕ Novo usuário"])

    # ── ABA 1: Listar e editar usuários ──────────────────────────────────────
    with aba1:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM usuario ORDER BY nome")
            ).fetchall()

        if not rows:
            st.info("Nenhum usuário cadastrado.")
        else:
            for row in rows:
                u = dict(row._mapping)
                is_master = u["login"] == ADMIN_MASTER_LOGIN
                perms_atuais = [p.strip() for p in u["permissoes"].split(",") if p.strip()]

                with st.expander(
                    f"{'🔑' if 'admin' in perms_atuais else '👤'} "
                    f"{u['nome']} ({u['login']}) "
                    f"{'✅ Ativo' if u['ativo'] else '🔴 Bloqueado'}",
                    expanded=False
                ):
                    if is_master:
                        st.info("Este é o administrador master — não pode ser editado aqui.")
                        continue

                    c1, c2 = st.columns(2)
                    with c1:
                        novo_nome = st.text_input("Nome", value=u["nome"], key=f"nome_{u['id']}")
                    with c2:
                        nova_senha = st.text_input(
                            "Nova senha (deixe em branco para manter)",
                            type="password", key=f"senha_{u['id']}"
                        )

                    ativo = st.checkbox("Usuário ativo", value=u["ativo"], key=f"ativo_{u['id']}")

                    st.markdown("**Permissões:**")
                    novas_perms = []
                    
                    # Checkbox admin primeiro
                    is_admin = st.checkbox(
                        "🔑 " + PERMISSOES["admin"],
                        value="admin" in perms_atuais,
                        key=f"perm_admin_{u['id']}"
                    )
                    if is_admin:
                        novas_perms = ["admin"]
                        st.info("Administrador tem acesso a tudo automaticamente.")
                    else:
                        cols = st.columns(2)
                        perm_keys = [k for k in PERMISSOES if k != "admin"]
                        for i, perm_key in enumerate(perm_keys):
                            with cols[i % 2]:
                                if st.checkbox(
                                    PERMISSOES[perm_key],
                                    value=perm_key in perms_atuais,
                                    key=f"perm_{perm_key}_{u['id']}"
                                ):
                                    novas_perms.append(perm_key)

                    col_salvar, col_excluir = st.columns(2)
                    with col_salvar:
                        if st.button("💾 Salvar alterações", key=f"salvar_{u['id']}"):
                            updates = {
                                "id": u["id"],
                                "nome": novo_nome,
                                "ativo": ativo,
                                "permissoes": ",".join(novas_perms),
                                "atualizado_em": datetime.now(),
                            }
                            if nova_senha:
                                updates["senha_hash"] = _hash_senha(nova_senha)
                                sql = text("""
                                    UPDATE usuario SET nome=:nome, senha_hash=:senha_hash,
                                    ativo=:ativo, permissoes=:permissoes, atualizado_em=:atualizado_em
                                    WHERE id=:id
                                """)
                            else:
                                sql = text("""
                                    UPDATE usuario SET nome=:nome,
                                    ativo=:ativo, permissoes=:permissoes, atualizado_em=:atualizado_em
                                    WHERE id=:id
                                """)
                            with engine.begin() as conn:
                                conn.execute(sql, updates)
                            st.success("✅ Usuário atualizado!")
                            st.rerun()

                    with col_excluir:
                        if st.button("🗑️ Excluir usuário", key=f"excluir_{u['id']}",
                                     type="secondary"):
                            with engine.begin() as conn:
                                conn.execute(
                                    text("DELETE FROM usuario WHERE id = :id"),
                                    {"id": u["id"]}
                                )
                            st.success("Usuário excluído.")
                            st.rerun()

    # ── ABA 2: Novo usuário ───────────────────────────────────────────────────
    with aba2:
        st.subheader("Cadastrar novo usuário")

        c1, c2 = st.columns(2)
        with c1:
            novo_login = st.text_input("Login *", placeholder="ex: joao.silva")
        with c2:
            novo_nome = st.text_input("Nome completo *", placeholder="ex: João Silva")

        c3, c4 = st.columns(2)
        with c3:
            nova_senha1 = st.text_input("Senha *", type="password")
        with c4:
            nova_senha2 = st.text_input("Confirmar senha *", type="password")

        st.markdown("**Permissões:**")
        novas_perms_novo = []

        is_admin_novo = st.checkbox("🔑 " + PERMISSOES["admin"], key="novo_admin")
        if is_admin_novo:
            novas_perms_novo = ["admin"]
            st.info("Administrador tem acesso a tudo automaticamente.")
        else:
            cols2 = st.columns(2)
            perm_keys2 = [k for k in PERMISSOES if k != "admin"]
            for i, perm_key in enumerate(perm_keys2):
                with cols2[i % 2]:
                    if st.checkbox(PERMISSOES[perm_key], key=f"novo_perm_{perm_key}"):
                        novas_perms_novo.append(perm_key)

        if st.button("➕ Cadastrar usuário", type="primary"):
            if not novo_login or not novo_nome or not nova_senha1:
                st.error("Preencha todos os campos obrigatórios.")
            elif nova_senha1 != nova_senha2:
                st.error("As senhas não coincidem.")
            elif len(nova_senha1) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO usuario (login, nome, senha_hash, ativo, permissoes)
                            VALUES (:login, :nome, :senha_hash, TRUE, :permissoes)
                        """), {
                            "login": novo_login.strip().lower(),
                            "nome": novo_nome.strip(),
                            "senha_hash": _hash_senha(nova_senha1),
                            "permissoes": ",".join(novas_perms_novo),
                        })
                    st.success(f"✅ Usuário **{novo_nome}** cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error(f"Login '{novo_login}' já existe. Escolha outro.")
                    else:
                        st.error(f"Erro ao cadastrar: {e}")
