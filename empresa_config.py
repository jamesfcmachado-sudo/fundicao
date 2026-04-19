"""
empresa_config.py
=================
Gerencia as configurações da empresa no banco PostgreSQL.
Tabela: empresa_config (chave-valor por empresa)
"""

from __future__ import annotations
import json
import base64
from datetime import datetime
from sqlalchemy import text
import streamlit as st


def _get_engine():
    from fundicao_db import engine
    return engine


# ── Inicializa tabela no banco ────────────────────────────────────────────────
def init_config_db() -> None:
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS empresa_config (
                chave        VARCHAR(100) PRIMARY KEY,
                valor        TEXT,
                atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
    _garantir_defaults()


def _garantir_defaults() -> None:
    """Insere valores padrão se não existirem."""
    defaults = {
        "nome_empresa":        "Metalpoli Fundição de Precisão",
        "cnpj":                "",
        "endereco":            "",
        "bairro":              "",
        "contato":             "",
        "cidade":              "Guarulhos",
        "estado":              "SP",
        "cep":                 "",
        "telefone":            "(11) 2954-9908",
        "email":               "comercial@metalpoli.com.br",
        "site":                "",
        "formato_of":          r"^\d{3}[A-L]\d$",
        "exemplo_of":          "001A6",
        "descricao_formato_of": "3 dígitos + letra A–L + 1 dígito",
        "formato_corrida":     r"^\d{3}[A-L]\d$",
        "exemplo_corrida":     "001A6",
        "descricao_formato_corrida": "3 dígitos + letra A–L + 1 dígito",
        "nome_campo_of":       "Ordem de Fabricação",
        "sigla_campo_of":      "OF",
        "nome_campo_corrida":  "Corrida",
        "nome_campo_oe":       "Ordem de Entrega",
        "sigla_campo_oe":      "OE",
        "logo1_base64":        "",
        "logo1_nome":          "",
        "logo2_base64":        "",
        "logo2_nome":          "",
        "logo_ativo":          "logo1",
        "rodape_relatorio":    "Metalpoli Fundição de Precisão — Guarulhos/SP",
        "rodape_pdf":          "Metalpoli Fundição de Precisão | (11) 2954-9908 | comercial@metalpoli.com.br",
    }
    engine = _get_engine()
    with engine.begin() as conn:
        for chave, valor in defaults.items():
            conn.execute(text("""
                INSERT INTO empresa_config (chave, valor, atualizado_em)
                VALUES (:chave, :valor, NOW())
                ON CONFLICT (chave) DO NOTHING
            """), {"chave": chave, "valor": valor})


# ── Leitura e escrita ─────────────────────────────────────────────────────────
def get_config(chave: str, default: str = "") -> str:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT valor FROM empresa_config WHERE chave = :c"),
                {"c": chave}
            ).fetchone()
            return row[0] if row and row[0] is not None else default
    except Exception:
        return default


def set_config(chave: str, valor: str) -> None:
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO empresa_config (chave, valor, atualizado_em)
            VALUES (:c, :v, NOW())
            ON CONFLICT (chave) DO UPDATE SET valor = :v, atualizado_em = NOW()
        """), {"c": chave, "v": valor})


def get_logo_ativo_bytes() -> bytes | None:
    """Retorna os bytes do logotipo ativo (base64 decodificado)."""
    logo_ativo = get_config("logo_ativo", "logo1")
    b64 = get_config(f"{logo_ativo}_base64", "")
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception:
            return None
    return None


def get_logo_bytes(num: int) -> bytes | None:
    """Retorna bytes do logo 1 ou 2."""
    b64 = get_config(f"logo{num}_base64", "")
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception:
            return None
    return None


# ── Tela de configurações ─────────────────────────────────────────────────────
def tela_configuracoes_empresa() -> None:
    """Tela completa de configurações da empresa."""
    st.title("🏭 Configurações da Empresa")
    st.caption("Personalize as informações da empresa que aparecerão nos relatórios, PDFs e templates.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏢 Dados da Empresa",
        "🖼️ Logotipos",
        "🔢 Numeração e Siglas",
        "📄 Relatórios e PDFs",
        "📋 Templates",
    ])

    # ── ABA 1: Dados da empresa ───────────────────────────────────────────────
    with tab1:
        st.subheader("Dados cadastrais da empresa")

        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome da empresa *",
                value=get_config("nome_empresa"))
            cnpj = st.text_input("CNPJ",
                value=get_config("cnpj"),
                placeholder="00.000.000/0000-00")
            telefone = st.text_input("Telefone",
                value=get_config("telefone"))
            email = st.text_input("E-mail",
                value=get_config("email"))
            site = st.text_input("Site",
                value=get_config("site"))
        with c2:
            endereco = st.text_input("Endereço",
                value=get_config("endereco"))
            bairro = st.text_input("Bairro",
                value=get_config("bairro"))
            contato = st.text_input("Contato / Responsável",
                value=get_config("contato"))
            cidade = st.text_input("Cidade",
                value=get_config("cidade"))
            estado = st.text_input("Estado (UF)",
                value=get_config("estado"),
                max_chars=2)
            cep = st.text_input("CEP",
                value=get_config("cep"))

        if st.button("💾 Salvar dados da empresa", type="primary", key="btn_salvar_dados"):
            set_config("nome_empresa", nome)
            set_config("cnpj", cnpj)
            set_config("telefone", telefone)
            set_config("email", email)
            set_config("site", site)
            set_config("endereco", endereco)
            set_config("bairro", bairro)
            set_config("contato", contato)
            set_config("cidade", cidade)
            set_config("estado", estado.upper())
            set_config("cep", cep)
            st.success("✅ Dados da empresa salvos!")

    # ── ABA 2: Logotipos ──────────────────────────────────────────────────────
    with tab2:
        st.subheader("Logotipos da empresa")
        st.caption("Você pode cadastrar até 2 logotipos e escolher qual será usado nos documentos.")

        logo_ativo = get_config("logo_ativo", "logo1")

        col1, col2 = st.columns(2)

        for num, col in [(1, col1), (2, col2)]:
            with col:
                st.markdown(f"**Logotipo {num}**")
                logo_bytes = get_logo_bytes(num)
                if logo_bytes:
                    st.image(logo_bytes, width=200)
                    st.caption(f"✅ Logo {num} cadastrado: {get_config(f'logo{num}_nome')}")
                else:
                    st.info(f"Nenhum logo {num} cadastrado.")

                upload = st.file_uploader(
                    f"Carregar logotipo {num} (PNG, JPG)",
                    type=["png", "jpg", "jpeg"],
                    key=f"upload_logo{num}"
                )
                if upload:
                    b64 = base64.b64encode(upload.read()).decode()
                    set_config(f"logo{num}_base64", b64)
                    set_config(f"logo{num}_nome", upload.name)
                    st.success(f"✅ Logo {num} salvo!")
                    st.rerun()

                if logo_bytes:
                    if st.button(f"🗑️ Remover logo {num}", key=f"btn_rm_logo{num}"):
                        set_config(f"logo{num}_base64", "")
                        set_config(f"logo{num}_nome", "")
                        st.success(f"Logo {num} removido.")
                        st.rerun()

        st.divider()
        st.subheader("Logo ativo nos documentos")
        novo_ativo = st.radio(
            "Qual logotipo usar nos PDFs e relatórios?",
            options=["logo1", "logo2"],
            format_func=lambda x: f"Logotipo {x[-1]}",
            index=0 if logo_ativo == "logo1" else 1,
            horizontal=True,
            key="radio_logo_ativo"
        )
        if st.button("💾 Salvar escolha do logotipo", key="btn_salvar_logo"):
            set_config("logo_ativo", novo_ativo)
            st.success(f"✅ Logotipo {novo_ativo[-1]} definido como ativo!")

    # ── ABA 3: Numeração e Siglas ─────────────────────────────────────────────
    with tab3:
        st.subheader("Formatos de numeração e siglas")
        st.caption("Configure como os números de OF, Corrida e OE são formatados nesta empresa.")

        st.markdown("##### Ordem de Fabricação (OF)")
        c1, c2 = st.columns(2)
        with c1:
            nome_of = st.text_input("Nome do campo",
                value=get_config("nome_campo_of"),
                key="nome_of")
            sigla_of = st.text_input("Sigla",
                value=get_config("sigla_campo_of"),
                key="sigla_of",
                max_chars=10)
        with c2:
            exemplo_of = st.text_input("Exemplo de número válido",
                value=get_config("exemplo_of"),
                key="ex_of")
            desc_of = st.text_input("Descrição do formato",
                value=get_config("descricao_formato_of"),
                key="desc_of")
            formato_of = st.text_input("Expressão regular (Regex)",
                value=get_config("formato_of"),
                key="fmt_of",
                help="Padrão regex para validar o número. Ex: ^\\d{3}[A-L]\\d$")

        st.divider()
        st.markdown("##### Corrida")
        c3, c4 = st.columns(2)
        with c3:
            nome_corrida = st.text_input("Nome do campo",
                value=get_config("nome_campo_corrida"),
                key="nome_corrida")
        with c4:
            exemplo_corrida = st.text_input("Exemplo de número válido",
                value=get_config("exemplo_corrida"),
                key="ex_corrida")
            desc_corrida = st.text_input("Descrição do formato",
                value=get_config("descricao_formato_corrida"),
                key="desc_corrida")
            formato_corrida = st.text_input("Expressão regular (Regex)",
                value=get_config("formato_corrida"),
                key="fmt_corrida")

        st.divider()
        st.markdown("##### Ordem de Entrega (OE)")
        c5, c6 = st.columns(2)
        with c5:
            nome_oe = st.text_input("Nome do campo",
                value=get_config("nome_campo_oe"),
                key="nome_oe")
        with c6:
            sigla_oe = st.text_input("Sigla",
                value=get_config("sigla_campo_oe"),
                key="sigla_oe",
                max_chars=10)

        if st.button("💾 Salvar numeração e siglas", type="primary", key="btn_salvar_num"):
            set_config("nome_campo_of", nome_of)
            set_config("sigla_campo_of", sigla_of)
            set_config("exemplo_of", exemplo_of)
            set_config("descricao_formato_of", desc_of)
            set_config("formato_of", formato_of)
            set_config("nome_campo_corrida", nome_corrida)
            set_config("exemplo_corrida", exemplo_corrida)
            set_config("descricao_formato_corrida", desc_corrida)
            set_config("formato_corrida", formato_corrida)
            set_config("nome_campo_oe", nome_oe)
            set_config("sigla_campo_oe", sigla_oe)
            st.success("✅ Numeração e siglas salvas!")
            st.info("⚠️ O novo formato de numeração será aplicado nos próximos lançamentos.")


    # ── ABA 5: Templates ──────────────────────────────────────────────────────
    with tab5:
        st.subheader("Templates de documentos")
        st.caption("Faça upload dos templates Excel para geração automática de documentos.")

        st.markdown("##### Template — Ordem de Entrega (OE)")
        _resp_oe = st.text_input(
            "Responsável pela OE (aparece no campo Contato do documento)",
            value=get_config("template_oe_responsavel", get_config("contato")),
            key="resp_oe_input"
        )
        if st.button("💾 Salvar responsável OE", key="btn_resp_oe"):
            set_config("template_oe_responsavel", _resp_oe)
            st.success(f"✅ Responsável OE salvo: {_resp_oe}")

        _oe_tmpl = get_config("template_oe_base64", "")
        if _oe_tmpl:
            st.success(f"Template OE cadastrado: {get_config('template_oe_nome')}")
            if st.button("🗑️ Remover template OE", key="btn_rm_tmpl_oe"):
                set_config("template_oe_base64", "")
                set_config("template_oe_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de OE cadastrado.")

        _orient_oe = st.radio(
            "Orientação da página",
            options=["Retrato", "Paisagem"],
            index=0 if get_config("template_oe_orientacao", "Paisagem") == "Retrato" else 1,
            horizontal=True,
            key="orient_oe"
        )
        if st.button("💾 Salvar orientação OE", key="btn_orient_oe"):
            set_config("template_oe_orientacao", _orient_oe)
            st.success(f"✅ Orientação OE salva: {_orient_oe}")

        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_oe"
        )
        if _up_oe:
            import base64
            _b64 = base64.b64encode(_up_oe.read()).decode()
            set_config("template_oe_base64", _b64)
            set_config("template_oe_nome", _up_oe.name)
            st.success(f"✅ Template OE salvo: {_up_oe.name}")
            st.rerun()

        st.divider()

        st.markdown("##### Template — Certificado de Qualidade")
        _resp_cert = st.text_input(
            "Responsável pelo Certificado (aparece no documento)",
            value=get_config("template_cert_responsavel", get_config("contato")),
            key="resp_cert_input"
        )
        if st.button("💾 Salvar responsável Certificado", key="btn_resp_cert"):
            set_config("template_cert_responsavel", _resp_cert)
            st.success(f"✅ Responsável Certificado salvo: {_resp_cert}")

        _cert_tmpl = get_config("template_cert_base64", "")
        if _cert_tmpl:
            st.success(f"Template Certificado cadastrado: {get_config('template_cert_nome')}")
            if st.button("🗑️ Remover template Certificado", key="btn_rm_tmpl_cert"):
                set_config("template_cert_base64", "")
                set_config("template_cert_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de Certificado cadastrado.")

        _orient_cert = st.radio(
            "Orientação da página",
            options=["Retrato", "Paisagem"],
            index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
            horizontal=True,
            key="orient_cert"
        )
        if st.button("💾 Salvar orientação Certificado", key="btn_orient_cert"):
            set_config("template_cert_orientacao", _orient_cert)
            st.success(f"✅ Orientação Certificado salva: {_orient_cert}")

        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_cert"
        )
        if _up_cert:
            import base64
            _b64 = base64.b64encode(_up_cert.read()).decode()
            set_config("template_cert_base64", _b64)
            set_config("template_cert_nome", _up_cert.name)
            st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
            st.rerun()

    # ── ABA 4: Relatórios e PDFs ──────────────────────────────────────────────
    with tab4:
        st.subheader("Textos em relatórios e PDFs")

        rodape_rel = st.text_input(
            "Rodapé dos relatórios",
            value=get_config("rodape_relatorio"),
            help="Aparece no rodapé das tabelas e relatórios impressos."
        )
        rodape_pdf = st.text_area(
            "Rodapé dos PDFs (OE, Certificados)",
            value=get_config("rodape_pdf"),
            height=80,
            help="Aparece no rodapé dos PDFs gerados pelo sistema."
        )

        st.divider()
        st.subheader("Prévia do cabeçalho dos PDFs")
        logo_bytes = get_logo_ativo_bytes()
        prev_c1, prev_c2 = st.columns([1, 3])
        with prev_c1:
            if logo_bytes:
                st.image(logo_bytes, width=120)
            else:
                st.info("Sem logo")
        with prev_c2:
            st.markdown(f"**{get_config('nome_empresa')}**")
            st.caption(f"{get_config('endereco')} — {get_config('cidade')}/{get_config('estado')}")
            st.caption(f"Tel: {get_config('telefone')} | {get_config('email')}")

        if st.button("💾 Salvar configurações de PDF", type="primary", key="btn_salvar_pdf"):
            set_config("rodape_relatorio", rodape_rel)
            set_config("rodape_pdf", rodape_pdf)
            st.success("✅ Configurações de PDF salvas!")
