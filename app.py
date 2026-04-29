# redeploy-1777157152
# deploy: PDF fiel ao template v2
"""
Sistema de Controle de Fundição — interface Streamlit + SQLAlchemy (SQLite fundicao.db).

Na raiz do projeto:
    streamlit run app.py
"""


import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

import pandas as pd
import streamlit as st

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
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.sqlite_models import CertificadoPeca, Corrida, OrdemEntrega, OrdemFabricacao
from fundicao_db import SessionLocal, init_db, ping_database
from gerar_oe_excel import gerar_oe_excel
from empresa_config import (
    init_config_db, tela_configuracoes_empresa,
    get_config, get_logo_ativo_bytes,
)
from auth import (
    init_auth_db, tela_login, tela_admin_usuarios,
    tem_permissao, usuario_logado, fazer_logout, PERMISSOES,
)

# sqlite3 removido — agora usa PostgreSQL via SQLAlchemy


def formatar_datas_br(df):
    try:
        if df is not None and not df.empty:
            cols = ['data', 'data_fusao', 'data_entrega', 'Data fusão']
            for col in cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y')
    except Exception:
        pass
    return df


FORMATO_DATA_BR = "%d/%m/%Y"
FORMATO_DATE_INPUT_BR = "DD/MM/YYYY"


def _exibir_data_br(val) -> str:
    """Converte date/datetime/Timestamp para DD/MM/YYYY (somente data); vazio se None."""
    if val is None:
        return ""
    if isinstance(val, pd.Timestamp):
        val = val.to_pydatetime()
    if isinstance(val, datetime):
        if val.tzinfo:
            val = val.astimezone().replace(tzinfo=None)
        return val.date().strftime(FORMATO_DATA_BR)
    if isinstance(val, date):
        return val.strftime(FORMATO_DATA_BR)
    return str(val)


RE_NUMERO_OP_OU_CORRIDA = re.compile(r"^\d{3}[A-L]\d$")

MSG_ERRO_FORMATO_OP_CORRIDA = (
    "Formato inválido. O campo deve seguir **000A0**: exatamente 3 dígitos, "
    "1 letra maiúscula de **A** a **L** e 1 dígito no final (exemplo: **001A6**)."
)


def codigo_op_ou_corrida_valido(valor: str) -> bool:
    """True se o valor (após strip) casa com 000A0 via regex."""
    if not valor or not str(valor).strip():
        return False
    return RE_NUMERO_OP_OU_CORRIDA.fullmatch(valor.strip()) is not None


ELEMENTOS_QUIMICOS = [
    "C", "Si", "Mn", "P", "S", "Cr", "Ni", "Mo", "Cu",
    "W", "Nb", "B", "CE", "V", "Co", "Fe", "N", "Mg",
]


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ler_status_of_banco(numero_of: str) -> str:
    """Lê status_of diretamente do banco via SQLAlchemy (PostgreSQL compatível)."""
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text
        with _eng.connect() as _conn:
            _r = _conn.execute(
                _text("SELECT status_of FROM ordem_fabricacao WHERE numero_of = :n"),
                {"n": numero_of},
            ).fetchone()
            return (_r[0] or "Ativa") if _r else "Ativa"
    except Exception:
        pass
    return "Ativa"


def _status_of(of: OrdemFabricacao) -> str:
    # Lê via SQL direto para garantir valor correto
    _st = _ler_status_of_banco(of.numero_of)
    if _st == "Finalizada":
        return "Encerrada"
    if _st == "Cancelada":
        return "Cancelada"
    meta = of.qtd_pecas_pedido or 0
    exp = of.qtd_expedida or 0
    if meta <= 0:
        return "Sem qtd. pedido"
    if exp >= meta:
        return "Encerrada"
    if exp > 0:
        return "Expedição parcial"
    return "Aberta"




# Sequência e títulos amigáveis das colunas de OF para exibição
_OF_DISPLAY_COLS = [
    ("numero_of",            "Nº OF"),
    ("numero_nn",            "NN°"),
    ("nome_cliente",         "Cliente"),
    ("data_abertura_pedido", "Abertura"),
    ("prazo_entrega_pedido", "Prazo Entrega"),
    ("numero_pedido",        "Nº Pedido"),
    ("numero_modelo",        "Modelo"),
    ("descricao_peca",       "Descrição Peça"),
    ("numero_desenho",       "Nº Desenho"),
    ("peso_liquido_kg",      "Peso Líq. (kg)"),
    ("peso_bruto_kg",        "Peso Bruto (kg)"),
    ("liga",                 "Liga"),
    ("norma",                "Norma"),
    ("qtd_pecas_pedido",     "Qtd Pedido"),
    ("qtd_fundida",          "Qtd Fundida"),
    ("qtd_expedida",         "Qtd Expedida"),
    ("valor_unitario",       "Vlr Unit. (R$)"),
    ("valor_total",          "Vlr Total (R$)"),
    ("cond_modelo",          "Cond. Modelo"),
    ("observacoes",          "Observações"),
    ("numero_oe",            "Nº OE"),
    ("numero_certificado",   "Nº Certificado"),
    ("status_of",            "Status"),
]

def _montar_linhas_of(ofs_list) -> list[dict]:
    """
    Monta UMA linha por OF com TODAS as colunas na sequência exigida.
    OEs e certificados são consolidados em uma única célula cada.
    Lê status_of diretamente via SQL para garantir leitura correta,
    independente do mapeamento ORM.
    """
    # Usa função cacheada — evita abrir nova conexão a cada chamada
    _status_map: dict[str, str] = _carregar_status_map()

    rows = []
    for of in ofs_list:
        oes   = list(of.ordens_entrega or [])
        certs = list(of.certificados   or [])
        oes_str   = ", ".join(o.numero_oe          for o in oes   if o.numero_oe)
        certs_str = ", ".join(c.numero_certificado for c in certs if c.numero_certificado)

        # Usa mapa SQL como fonte primária
        _of_status = _status_map.get(of.numero_of, "Ativa")

        rows.append({
            "_id":                  of.id,
            "numero_of":            of.numero_of or "",
            "numero_nn":            of.numero_nn or "",
            "nome_cliente":         of.nome_cliente or "",
            "data_abertura_pedido": _exibir_data_br(of.data_abertura_pedido),
            "prazo_entrega_pedido": _exibir_data_br(of.prazo_entrega_pedido) or "",
            "numero_pedido":        of.numero_pedido or "",
            "numero_modelo":        of.numero_modelo or "",
            "descricao_peca":       of.descricao_peca or "",
            "numero_desenho":       of.numero_desenho or "",
            "peso_liquido_kg":      float(of.peso_liquido_kg) if of.peso_liquido_kg is not None else None,
            "peso_bruto_kg":        float(of.peso_bruto_kg)   if of.peso_bruto_kg   is not None else None,
            "liga":                 of.liga  or "",
            "norma":                of.norma or "",
            "qtd_pecas_pedido":     of.qtd_pecas_pedido  or 0,
            "qtd_fundida":          of.qtd_fundida        or 0,
            "qtd_expedida":         of.qtd_expedida       or 0,
            "valor_unitario":       float(of.valor_unitario) if of.valor_unitario is not None else None,
            "valor_total":          float(of.valor_total)    if of.valor_total    is not None else None,
            "cond_modelo":          of.condicao_modelo or "",
            "observacoes":          of.observacoes or "",
            "numero_oe":            oes_str,
            "numero_certificado":   certs_str,
            "status_of":            _of_status,
        })

    return rows


def _df_of_formatado(rows: list[dict]) -> "pd.DataFrame":
    """Converte lista de dicts em DataFrame com títulos amigáveis na ordem certa."""
    df = pd.DataFrame(rows, columns=[k for k, _ in _OF_DISPLAY_COLS])
    df = df.rename(columns={k: v for k, v in _OF_DISPLAY_COLS})
    # Preserva _id para seleção por linha
    if rows and "_id" in rows[0]:
        df["_id"] = [r["_id"] for r in rows]
    return df



def _gerar_pdf_ofs(df: "pd.DataFrame") -> bytes:
    """Gera PDF da tabela de OFs abertas usando reportlab. Retorna bytes."""
    from io import BytesIO
    from datetime import datetime as _dt
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=5*mm, rightMargin=5*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("titulo", parent=styles["Title"],
                                  fontSize=13, alignment=TA_CENTER, spaceAfter=4)
    sub_style   = ParagraphStyle("sub", parent=styles["Normal"],
                                  fontSize=8, alignment=TA_CENTER, spaceAfter=8,
                                  textColor=colors.grey)
    cell_style  = ParagraphStyle("cell", parent=styles["Normal"], fontSize=6.5, leading=8)
    head_style  = ParagraphStyle("head", parent=styles["Normal"],
                                  fontSize=7, leading=8, textColor=colors.white)

    story = [
        Paragraph("Sistema de Controle de Fundição", title_style),
        Paragraph(f"OFs Abertas ou em Expedição Parcial — gerado em "
                  f"{_dt.now().strftime('%d/%m/%Y %H:%M')}", sub_style),
        Spacer(1, 4*mm),
    ]

    # Largura útil A4 paisagem com margens 5mm cada lado = 287mm
    # Colunas proporcionalmente ajustadas para caber exatamente na página
    _COLS = [
        ("Nº OF",          13.6), ("NN°",           10.2), ("Cliente",        40.8),
        ("Abertura",       15.3), ("Prazo Entrega",  15.3), ("Nº Pedido",      17.0),
        ("Descrição Peça", 34.0), ("Liga",           11.9), ("Norma",          27.2),
        ("Qtd Pedido",     11.9), ("Qtd Fundida",    11.9), ("Qtd Expedida",   11.9),
        ("Vlr Total (R$)", 18.7), ("Nº OE",          18.7), ("Nº Certificado", 18.7),
    ]
    col_names  = [c[0] for c in _COLS]
    col_widths = [c[1]*mm for c in _COLS]

    # Filtra só as colunas que existem no df
    col_names  = [c for c in col_names  if c in df.columns]
    col_widths = [col_widths[i] for i, c in enumerate([c[0] for c in _COLS]) if c in df.columns]

    # Ajusta larguras para preencher exatamente a área útil da página
    _util_mm = 287  # A4 paisagem 297mm - 2x5mm de margem
    _total   = sum(col_widths)
    if _total > 0:
        _fator   = (_util_mm * mm) / _total
        col_widths = [w * _fator for w in col_widths]

    # Cabeçalho
    header = [Paragraph(f"<b>{c}</b>", head_style) for c in col_names]
    rows   = [header]

    for _, row in df[col_names].iterrows():
        rows.append([
            Paragraph(str(row[c]) if pd.notna(row[c]) else "", cell_style)
            for c in col_names
        ])

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Cabeçalho
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),  7),
        ("ALIGN",         (0,0), (-1,0),  "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUND", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1), (-1,-1), 6.5),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#c0c8d0")),
        ("LEFTPADDING",   (0,0), (-1,-1), 2),
        ("RIGHTPADDING",  (0,0), (-1,-1), 2),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(tbl)
    doc.build(story)
    return buf.getvalue()

@st.cache_data(ttl=30, show_spinner=False)
def _carregar_status_map() -> dict:
    """Carrega status_of de todas as OFs em uma única query (PostgreSQL compatível). Cache de 30s."""
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text
        with _eng.connect() as _conn:
            rows = _conn.execute(
                _text("SELECT numero_of, status_of FROM ordem_fabricacao")
            ).fetchall()
            return {r[0]: (r[1] or "Ativa") for r in rows}
    except Exception:
        return {}


def _status_of_rapido(of: "OrdemFabricacao", status_map: dict) -> str:
    """Determina status usando mapa pré-carregado — sem query por OF."""
    _st = status_map.get(of.numero_of, "Ativa")
    if _st == "Finalizada":
        return "Encerrada"
    if _st == "Cancelada":
        return "Cancelada"
    meta = of.qtd_pecas_pedido or 0
    exp  = of.qtd_expedida or 0
    if meta <= 0:
        return "Sem qtd. pedido"
    if exp >= meta:
        return "Encerrada"
    if exp > 0:
        return "Expedição parcial"
    return "Aberta"


def pagina_dashboard():
    st.title("Dashboard da Fundição")

    # ── Uma única query com todos os relacionamentos + status em cache ────
    try:
        with db_session() as db:
            todas_completas = list(
                db.scalars(
                    select(OrdemFabricacao)
                    .options(
                        selectinload(OrdemFabricacao.ordens_entrega),
                        selectinload(OrdemFabricacao.certificados),
                    )
                ).all()
            )
            # Monta linhas dentro da sessão (evita DetachedInstanceError)
            # status_map carregado uma vez e cacheado por 30s
            _smap = _carregar_status_map()
            abertas_list   = [of for of in todas_completas
                              if _status_of_rapido(of, _smap) in
                              ("Aberta", "Expedição parcial", "Sem qtd. pedido", "Cancelada")]
            linhas_abertas = _montar_linhas_of(abertas_list)
            todas          = todas_completas  # alias para métricas
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        todas_completas = []
        todas           = []
        linhas_abertas  = []
        _smap           = {}

    soma_pedido = sum(float(of.qtd_pecas_pedido or 0) for of in todas)
    abertas_ct  = sum(1 for of in todas_completas if _status_of_rapido(of, _smap) == "Aberta")
    parciais_ct = sum(1 for of in todas_completas if _status_of_rapido(of, _smap) == "Expedição parcial")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("OFs cadastradas", len(todas))

    m2.metric("OFs em acompanhamento", abertas_ct + parciais_ct)
    m3.metric("Abertas / parciais", f"{abertas_ct} / {parciais_ct}")
    m4.metric("Peças pedido (total)", soma_pedido)

    st.divider()
    st.subheader("OFs abertas ou em expedição parcial — visão completa")
    if not todas:
        st.info("Nenhuma OF cadastrada. Use **Nova Ordem de Fabricação**.")
    elif not linhas_abertas:
        st.info("Todas as OFs estão encerradas.")
    else:
        _df_dash = _df_of_formatado(linhas_abertas)

        # Ordena crescente — OFs mais antigas primeiro
        if "Nº OF" in _df_dash.columns:
            _df_dash[["_s_ano","_s_mes","_s_seq","_s_cod"]] = pd.DataFrame(
                _df_dash["Nº OF"].fillna("").apply(_chave_of).tolist(),
                index=_df_dash.index
            )
            _df_dash = _df_dash.sort_values(
                by=["_s_ano","_s_mes","_s_seq"],
                ascending=[True, True, True],
                na_position="last"
            ).drop(columns=["_s_ano","_s_mes","_s_seq","_s_cod","_id"], errors="ignore")\
             .reset_index(drop=True)

        # Aplica estilo visual para OFs Canceladas
        def _style_canceladas(row):
            if row.get("Status") == "Cancelada":
                return ["background-color:#ffe0e0; color:#cc0000; "
                        "text-decoration:line-through; font-weight:bold"] * len(row)
            return [""] * len(row)

        _DASH_COL_CFG = {
            "Peso Líq. (kg)":  st.column_config.NumberColumn("Peso Líq. (kg)",  format="%.2f"),
            "Peso Bruto (kg)": st.column_config.NumberColumn("Peso Bruto (kg)", format="%.2f"),
            "Vlr Unit. (R$)":  st.column_config.NumberColumn("Vlr Unit. (R$)",  format="%.2f"),
            "Vlr Total (R$)":  st.column_config.NumberColumn("Vlr Total (R$)",  format="%.2f"),
        }

        _altura_dash = st.slider("Altura da tabela (linhas)", min_value=200, max_value=1200, value=400, step=50, key="altura_dash")
        st.dataframe(
            _df_dash.style.apply(_style_canceladas, axis=1),
            height=_altura_dash,
            use_container_width=True,
            hide_index=True,
            column_config=_DASH_COL_CFG,
        )

        _btn1, _btn2 = st.columns(2)
        with _btn1:
            try:
                _pdf_bytes = _gerar_pdf_ofs(_df_dash)
                st.download_button(
                    "📄 Baixar PDF",
                    data=_pdf_bytes,
                    file_name=f"ofs_abertas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as _pe:
                st.error(f"Erro ao gerar PDF: {_pe}")
        with _btn2:
            # Botão de impressão via HTML/JS
            st.markdown(
                """<button onclick="window.print()" style="
                    width:100%; padding:8px 0; background:#4f8ef7; color:white;
                    border:none; border-radius:5px; font-size:14px; cursor:pointer;">
                    🖨️ Imprimir
                </button>""",
                unsafe_allow_html=True,
            )




def pagina_nova_of() -> None:
    st.title("Nova Ordem de Fabricação")
    st.caption("Dados gravados em **fundicao.db** (tabelas `ordem_fabricacao`, `ordem_entrega`, `certificado_peca`).")

    if st.session_state.get("nova_of_sucesso"):
        st.success(st.session_state["nova_of_sucesso"])
        if st.button("Fechar mensagem", key="btn_fechar_sucesso_of"):
            del st.session_state["nova_of_sucesso"]
            st.rerun()

    # ── Carrega opções de autocomplete do banco ───────────────────────────
    try:
        with db_session() as _db_ac:
            _ofs_ac = list(_db_ac.scalars(select(OrdemFabricacao)).all())
            _opts_cliente  = sorted({o.nome_cliente   for o in _ofs_ac if o.nome_cliente},   key=str.upper)
            _opts_modelo   = sorted({o.numero_modelo  for o in _ofs_ac if o.numero_modelo},  key=str.upper)
            _opts_descr    = sorted({o.descricao_peca for o in _ofs_ac if o.descricao_peca}, key=str.upper)
            _opts_desenho  = sorted({o.numero_desenho for o in _ofs_ac if o.numero_desenho}, key=str.upper)
            _opts_liga     = sorted({o.liga  for o in _ofs_ac if o.liga},  key=str.upper)
            _opts_norma    = sorted({o.norma for o in _ofs_ac if o.norma}, key=str.upper)
    except Exception:
        _opts_cliente = _opts_modelo = _opts_descr = _opts_desenho = _opts_liga = _opts_norma = []

    # Campos de OE e certificados removidos - usar abas especificas
    n_oes = 0
    n_certs = 0

    with st.form("form_nova_of", clear_on_submit=True):
        st.markdown("##### Dados da OF")
        st.caption("💡 Campos com **(▼)** aceitam digitação livre e mostram sugestões dos valores já cadastrados.")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("**Número da OP:** formato `000A0` — 3 dígitos + letra A–L + 1 dígito.")
            numero_of = st.text_input(
                "Número da OP *",
                placeholder="001A6",
                help="Regex: ^\\d{3}[A-L]\\d$ — apenas maiúsculas na letra central.",
            )
            numero_nn = st.text_input("NN°")
            nome_cliente = st.selectbox(
                "Nome do Cliente * (▼)",
                options=[""] + _opts_cliente,
                index=0,
                accept_new_options=True,
                key="form_cliente",
            )
            data_abertura = st.date_input(
                "Data de abertura do pedido *",
                value=date.today(),
                format=FORMATO_DATE_INPUT_BR,
            )
            prazo_entrega = st.date_input(
                "Prazo de entrega do pedido",
                value=None,
                format=FORMATO_DATE_INPUT_BR,
                min_value=date(1900, 1, 1),
                max_value=date(2100, 12, 31),
            )
            numero_pedido = st.text_input("Número do pedido")
            numero_modelo = st.selectbox(
                "Número do modelo (▼)",
                options=[""] + _opts_modelo,
                index=0,
                accept_new_options=True,
                key="form_modelo",
            )
        with c2:
            descricao_peca = st.selectbox(
                "Descrição da peça (▼)",
                options=[""] + _opts_descr,
                index=0,
                accept_new_options=True,
                key="form_descr",
            )
            numero_desenho = st.selectbox(
                "Número do desenho (▼)",
                options=[""] + _opts_desenho,
                index=0,
                accept_new_options=True,
                key="form_desenho",
            )
            peso_liquido = st.number_input("Peso líquido (kg)", min_value=0.0, value=0.0, format="%.4f")
            peso_bruto   = st.number_input("Peso bruto (kg)",   min_value=0.0, value=0.0, format="%.4f")
            liga  = st.selectbox(
                "Liga (▼)",
                options=[""] + _opts_liga,
                index=0,
                accept_new_options=True,
                key="form_liga",
            )
            norma = st.selectbox(
                "Norma (▼)",
                options=[""] + _opts_norma,
                index=0,
                accept_new_options=True,
                key="form_norma",
            )
            qtd_pedido   = st.number_input("Quantidade de peças do pedido *", min_value=0, value=0, step=1)
            qtd_fundida  = st.number_input("Qtde fundida",  min_value=0, value=0, step=1)
            qtd_expedida = st.number_input("Qtde expedida", min_value=0, value=0, step=1)

        valor_unit  = st.number_input("Valor unitário", min_value=0.0, value=0.0, format="%.6f")
        valor_total = st.number_input("Valor total",    min_value=0.0, value=0.0, format="%.2f")
        condicao_modelo = st.text_input("Condição do modelo")
        observacoes     = st.text_area("Observações gerais da OF")

        if n_oes > 0:
            st.divider()
            st.markdown("##### OE — número e quantidade de peças")
            for i in range(int(n_oes)):
                a, b = st.columns(2)
                with a:
                    st.text_input(f"OE {i + 1} — número", key=f"oe_n_{i}")
                with b:
                    st.number_input(f"OE {i + 1} — qtd peças", min_value=0, value=0, step=1, key=f"oe_q_{i}")

        if n_certs > 0:
            st.divider()
            st.markdown("##### Certificado — número e quantidade de peças")
            for i in range(int(n_certs)):
                a, b = st.columns(2)
                with a:
                    st.text_input(f"Certificado {i + 1} — número", key=f"ce_n_{i}")
                with b:
                    st.number_input(
                        f"Certificado {i + 1} — qtd peças",
                        min_value=0, value=0, step=1, key=f"ce_q_{i}",
                    )

        enviar = st.form_submit_button("Salvar no banco de dados")

    if not enviar:
        return

    if not numero_of.strip() or not (nome_cliente or "").strip():
        st.error("Preencha o número da OP e o nome do cliente.")
        return

    if not codigo_op_ou_corrida_valido(numero_of):
        st.error(MSG_ERRO_FORMATO_OP_CORRIDA)
        return

    pares_oe: list[tuple[str, int]] = []
    if n_oes > 0:
        for i in range(int(n_oes)):
            noe = st.session_state.get(f"oe_n_{i}", "")
            q = int(st.session_state.get(f"oe_q_{i}", 0))
            if str(noe).strip():
                if q <= 0:
                    st.error(f"OE {i + 1}: informe quantidade > 0 ou deixe o número em branco.")
                    return
                pares_oe.append((str(noe).strip(), q))
            elif q > 0:
                st.error(f"OE {i + 1}: informe o número da OE.")
                return

    pares_cert: list[tuple[str, int]] = []
    if n_certs > 0:
        for i in range(int(n_certs)):
            nc = st.session_state.get(f"ce_n_{i}", "")
            q = int(st.session_state.get(f"ce_q_{i}", 0))
            if str(nc).strip():
                if q <= 0:
                    st.error(f"Certificado {i + 1}: quantidade deve ser > 0.")
                    return
                pares_cert.append((str(nc).strip(), q))
            elif q > 0:
                st.error(f"Certificado {i + 1}: informe o número do certificado.")
                return

    now = datetime.now().astimezone()
    of = OrdemFabricacao(
        numero_of=numero_of.strip(),
        numero_nn=numero_nn.strip() or None,
        nome_cliente=(nome_cliente or "").strip(),
        data_abertura_pedido=data_abertura,
        prazo_entrega_pedido=prazo_entrega,
        numero_pedido=numero_pedido.strip() or None,
        numero_modelo=(numero_modelo or "").strip() or None,
        descricao_peca=(descricao_peca or "").strip() or None,
        numero_desenho=(numero_desenho or "").strip() or None,
        peso_liquido_kg=Decimal(str(peso_liquido)) if peso_liquido else None,
        peso_bruto_kg=Decimal(str(peso_bruto)) if peso_bruto else None,
        liga=(liga or "").strip() or None,
        norma=(norma or "").strip() or None,
        qtd_pecas_pedido=int(qtd_pedido),
        qtd_fundida=int(qtd_fundida),
        qtd_expedida=int(qtd_expedida),
        valor_unitario=Decimal(str(valor_unit)) if valor_unit else None,
        valor_total=Decimal(str(valor_total)) if valor_total else None,
        condicao_modelo=condicao_modelo.strip() or None,
        observacoes=observacoes.strip() or None,
        criado_em=now,
        atualizado_em=now,
    )
    for noe, q in pares_oe:
        of.ordens_entrega.append(OrdemEntrega(numero_oe=noe, qtd_pecas=q, criado_em=now))
    for nc, q in pares_cert:
        of.certificados.append(CertificadoPeca(numero_certificado=nc, qtd_pecas=q, criado_em=now))

    try:
        with db_session() as db:
            db.add(of)
            db.flush()
            db.refresh(of)
            oid = of.id
            num = of.numero_of
        st.session_state["nova_of_sucesso"] = (
            f"**Salvo com sucesso** em `fundicao.db`: OF **{num}** (id `{oid}`). "
            f"OE: {len(pares_oe)} linha(s); Certificados: {len(pares_cert)} linha(s)."
        )
        if hasattr(st, "toast"):
            st.toast("Ordem de fabricação gravada.", icon="✅")
        st.rerun()
    except IntegrityError as e:
        st.error(f"Não foi possível salvar (OF duplicada ou dado inválido): {e}")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def pagina_lancar_corrida() -> None:
    st.title("Lançar Corrida")
    st.caption("Gravação na tabela **corrida** do arquivo **fundicao.db**.")
    st.caption("**Número da Corrida** e **Número da OF** (se informado): formato `000A0`.")

    # ── Autocomplete da CORRIDA (fora do form para ser reativo) ──────────────
    _numero_corrida_input = st.text_input(
        "Número da corrida *",
        placeholder="001A6",
        help="Ao digitar uma corrida já cadastrada, preenche automaticamente liga, norma e composição.",
        key="lancar_corrida_num_input",
    )
    # Busca corrida existente no banco
    _corr_liga_auto   = ""
    _corr_norma_auto  = ""
    _corr_comp_auto   = {}
    _corr_cliente_auto = ""
    if _numero_corrida_input.strip():
        try:
            with SessionLocal() as _db_corr:
                _corr_found = _db_corr.execute(
                    select(Corrida).where(
                        Corrida.numero_corrida == _numero_corrida_input.strip().upper()
                    ).order_by(Corrida.criado_em.desc())
                ).scalars().first()
            if _corr_found:
                _corr_liga_auto    = _corr_found.liga or ""
                _corr_norma_auto   = _corr_found.norma or ""
                _corr_comp_auto    = _corr_found.composicao_quimica_pct or {}
                _corr_cliente_auto = _corr_found.nome_cliente or ""
                # Verifica se composição mudou para forçar rerender
                _comp_anterior = st.session_state.get("_corr_auto_comp", {})
                if _comp_anterior != _corr_comp_auto:
                    st.session_state["_corr_auto_comp"] = _corr_comp_auto
                    # Limpa chaves chem_ e força rerender
                    for _ek in list(st.session_state.keys()):
                        if _ek.startswith("chem_"):
                            del st.session_state[_ek]
                    st.rerun()
                st.info(f"🔄 Corrida encontrada — liga: **{_corr_liga_auto}** | norma: **{_corr_norma_auto}** | composição preenchida automaticamente.")
        except Exception:
            pass

    # ── Autocomplete da OF (fora do form para ser reativo) ───────────────────
    _numero_of_input = st.text_input(
        "Número da OF",
        placeholder="001A6",
        help="Opcional. Ao digitar, busca cliente, liga e norma automaticamente.",
        key="lancar_corrida_of_input",
    )
    # Busca dados da OF no banco ao digitar
    _of_cliente_auto = _corr_cliente_auto  # usa cliente da corrida se existir
    _of_liga_auto    = _corr_liga_auto
    _of_norma_auto   = _corr_norma_auto
    _of_id_auto      = None
    _serie_auto      = ""  # próxima série calculada automaticamente

    if _numero_of_input.strip():
        try:
            with SessionLocal() as _db_of:
                _of_found = _db_of.execute(
                    select(OrdemFabricacao).where(
                        OrdemFabricacao.numero_of == _numero_of_input.strip().upper()
                    )
                ).scalar_one_or_none()

                # Busca última série cadastrada para esta OF
                _ultima_corrida_of = _db_of.execute(
                    select(Corrida).where(
                        Corrida.numero_ordem_fabricacao == _numero_of_input.strip().upper(),
                        Corrida.serie_pecas_fundidas != None,
                        Corrida.serie_pecas_fundidas != ""
                    ).order_by(Corrida.criado_em.desc())
                ).scalars().first()

            if _of_found:
                _of_cliente_auto = _of_found.nome_cliente or ""
                _of_liga_auto    = _of_found.liga or _corr_liga_auto
                _of_norma_auto   = _of_found.norma or _corr_norma_auto
                _of_id_auto      = _of_found.id
                # Salva no session_state para preencher campos do form
                st.session_state["_of_auto_cliente"] = _of_cliente_auto
                st.session_state["_of_auto_liga"]    = _of_liga_auto
                st.session_state["_of_auto_norma"]   = _of_norma_auto
                st.success(f"✅ OF encontrada: **{_of_found.nome_cliente}**")
            else:
                if len(_numero_of_input.strip()) >= 5:
                    st.warning("⚠️ OF não encontrada no banco.")

            # Calcula próxima série baseada na última série cadastrada
            if _ultima_corrida_of and _ultima_corrida_of.serie_pecas_fundidas:
                _ultima_serie = _ultima_corrida_of.serie_pecas_fundidas.strip().upper()
                import re as _re
                # Busca o maior número final nas séries (formato "X A Y" ou "X E Y")
                _nums = _re.findall(r'\d+', _ultima_serie)
                if _nums:
                    _ultimo_num = max(int(n) for n in _nums)
                    _proximo_inicio = _ultimo_num + 1
                    st.info(f"📋 Última série da OF: **{_ultima_serie}** → próxima série começa em **{_proximo_inicio}**")
                    # Guarda para usar no campo série
                    st.session_state["_serie_proximo_inicio"] = _proximo_inicio
                else:
                    st.session_state.pop("_serie_proximo_inicio", None)
            else:
                st.session_state.pop("_serie_proximo_inicio", None)

        except Exception:
            pass

    # ── Quantidade e série automática (fora do form para ser reativo) ────────
    _qtd_input = st.number_input(
        "Qtd peças fundidas *",
        min_value=0, value=0, step=1,
        key="lancar_corrida_qtd_input",
    )

    # Calcula série automaticamente com base na última série + quantidade
    _prox_inicio = st.session_state.get("_serie_proximo_inicio", 1)  # começa do 1 se não houver série anterior
    _serie_sugerida = ""
    if _qtd_input > 0:
        _proximo_fim = _prox_inicio + int(_qtd_input) - 1
        # Se for só 1 peça, mostra só o número
        if int(_qtd_input) == 1:
            _serie_sugerida = str(_prox_inicio)
        else:
            _serie_sugerida = f"{_prox_inicio} A {_proximo_fim}"
        if _prox_inicio == 1:
            st.info(f"📋 Primeira série da OF: **{_serie_sugerida}**")
        else:
            st.success(f"📋 Série calculada: **{_serie_sugerida}**")

    with st.form("form_corrida", clear_on_submit=False):
        l1c1, l1c2, l1c3, l1c4 = st.columns(4)
        with l1c1:
            data_fusao = st.date_input(
                "Data de fusão *", value=date.today(), format=FORMATO_DATE_INPUT_BR
            )
        with l1c2:
            nome_cliente = st.text_input(
                "Nome do cliente *",
                value=st.session_state.get("_of_auto_cliente", _of_cliente_auto),
            )
        with l1c3:
            st.write(f"**Qtd peças fundidas:** {int(_qtd_input)}")
            qtd_fundidas = _qtd_input
        with l1c4:
            serie = st.text_input(
                "Série das peças",
                value=_serie_sugerida,
                help="Preenchido automaticamente com a continuação da última série da OF.",
            )

        l2c1, l2c2, l2c3, l2c4, l2c5, l2c6 = st.columns(6)
        with l2c1:
            liga = st.text_input("Liga", value=st.session_state.get("_of_auto_liga", _of_liga_auto))
        with l2c2:
            norma = st.text_input("Norma", value=st.session_state.get("_of_auto_norma", _of_norma_auto))
        with l2c3:
            usar_json = st.checkbox("Composição via JSON", value=False)
        with l2c4:
            pass
        with l2c5:
            pass
        with l2c6:
            pass

        st.subheader("Composição química (%)")
        st.caption("Percentuais; apenas valores maiores que zero entram na composição.")

        raw_json = ""
        l3c1, l3c2, l3c3, l3c4, l3c5, l3c6 = st.columns(6)
        if usar_json:
            with l3c1:
                raw_json = st.text_area(
                    'JSON — ex.: {"C": 3.45, "Si": 2.1}',
                    value=json.dumps(_corr_comp_auto) if _corr_comp_auto else "{}",
                    label_visibility="visible",
                )
        else:
            _els = ELEMENTOS_QUIMICOS
            with l3c1:
                st.number_input(_els[0], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[0], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[0]}")
            with l3c2:
                st.number_input(_els[1], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[1], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[1]}")
            with l3c3:
                st.number_input(_els[2], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[2], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[2]}")
            with l3c4:
                st.number_input(_els[3], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[3], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[3]}")
            with l3c5:
                st.number_input(_els[4], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[4], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[4]}")
            with l3c6:
                st.number_input(_els[5], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[5], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[5]}")

        if not usar_json:
            l4c1, l4c2, l4c3, l4c4, l4c5, l4c6 = st.columns(6)
            with l4c1:
                st.number_input(_els[6], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[6], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[6]}")
            with l4c2:
                st.number_input(_els[7], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[7], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[7]}")
            with l4c3:
                st.number_input(_els[8], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[8], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[8]}")
            with l4c4:
                st.number_input(_els[9], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[9], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[9]}")
            with l4c5:
                st.number_input(_els[10], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[10], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[10]}")
            with l4c6:
                st.number_input(_els[11], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[11], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[11]}")

            l5c1, l5c2, l5c3, l5c4, l5c5, l5c6 = st.columns(6)
            with l5c1:
                st.number_input(_els[12], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[12], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[12]}")
            with l5c2:
                st.number_input(_els[13], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[13], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[13]}")
            with l5c3:
                st.number_input(_els[14], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[14], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[14]}")
            with l5c4:
                st.number_input(_els[15], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[15], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[15]}")
            with l5c5:
                st.number_input(_els[16], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[16], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[16]}")
            with l5c6:
                st.number_input(_els[17], min_value=0.0, value=float(st.session_state.get("_corr_auto_comp", _corr_comp_auto).get(_els[17], 0.0)), format="%.4f", step=0.01, key=f"chem_{_els[17]}")

        # Campo invisível para absorver o Enter e evitar submit acidental
        st.text_input(".", value="", label_visibility="collapsed", key="_absorve_enter_corrida")

        enviar = st.form_submit_button("💾 Salvar corrida", type="primary")

    if not enviar:
        return

    if not _numero_corrida_input.strip():
        st.error("Preencha o numero da corrida.")
        return
    if not nome_cliente.strip():
        st.error("Preencha o nome do cliente. Este campo e obrigatorio.")
        return
    if not data_fusao:
        st.error("Preencha a data de fusao.")
        return

    if not codigo_op_ou_corrida_valido(_numero_corrida_input.strip()):
        st.error(f"**Número da corrida:** {MSG_ERRO_FORMATO_OP_CORRIDA}")
        return

    nof_raw = _numero_of_input.strip()
    if nof_raw and not codigo_op_ou_corrida_valido(nof_raw):
        st.error(f"**Número da OF:** {MSG_ERRO_FORMATO_OP_CORRIDA}")
        return

    if usar_json:
        try:
            composicao = json.loads(raw_json) if raw_json.strip() else {}
        except json.JSONDecodeError:
            st.error("JSON inválido.")
            return
        if not isinstance(composicao, dict):
            st.error("O JSON deve ser um objeto.")
            return
    else:
        composicao = {}
        for el in ELEMENTOS_QUIMICOS:
            k = f"chem_{el}"
            if k in st.session_state and float(st.session_state[k]) > 0:
                composicao[el] = float(st.session_state[k])

    of_id = None
    nof = nof_raw
    if nof:
        with db_session() as db:
            row = db.scalar(select(OrdemFabricacao).where(OrdemFabricacao.numero_of == nof))
            if row:
                of_id = row.id

    now = datetime.now().astimezone()
    corrida = Corrida(
        data_fusao=data_fusao,
        numero_corrida=_numero_corrida_input.strip().upper(),
        nome_cliente=nome_cliente.strip(),
        ordem_fabricacao_id=of_id,
        numero_ordem_fabricacao=nof or None,
        qtd_pecas_fundidas=int(qtd_fundidas),
        serie_pecas_fundidas=serie.strip() or None,
        liga=liga.strip() or None,
        norma=norma.strip() or None,
        composicao_quimica_pct=composicao,
        criado_em=now,
        atualizado_em=now,
    )

    try:
        with db_session() as db:
            db.add(corrida)
            db.flush()
            db.refresh(corrida)

            # Atualiza qtd_fundida na OF somando a quantidade da corrida
            if of_id and int(qtd_fundidas) > 0:
                _of_atualizar = db.scalar(
                    select(OrdemFabricacao).where(OrdemFabricacao.id == of_id)
                )
                if _of_atualizar:
                    _qtd_atual = int(_of_atualizar.qtd_fundida or 0)
                    _of_atualizar.qtd_fundida = _qtd_atual + int(qtd_fundidas)

        st.success(f"✅ Corrida **{corrida.numero_corrida}** registrada com sucesso!")
        if of_id and int(qtd_fundidas) > 0:
            st.info(f"✅ OF **{nof}** atualizada: +{int(qtd_fundidas)} peças fundidas.")

        # Limpa todos os campos para novo lançamento
        for _k in list(st.session_state.keys()):
            if any(_k.startswith(p) for p in [
                "lancar_corrida_", "chem_", "_serie_proximo_inicio",
                "_absorve_enter_corrida", "_of_auto_", "_corr_auto_"
            ]):
                del st.session_state[_k]
        st.session_state.pop("_serie_proximo_inicio", None)
        st.rerun()
    except IntegrityError as e:
        st.error(f"Corrida já existe para este número e data, ou vínculo inválido: {e}")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


RASTREABILIDADE_CAMPOS: list[tuple[str, str, str]] = [
    ("Número da OF", "numero_of", "text"),
    ("NN°", "numero_nn", "text"),
    ("Nome do Cliente", "nome_cliente", "text"),
    ("Data de abertura do pedido", "data_abertura_pedido", "date"),
    ("Prazo de Entrega do Pedido", "prazo_entrega_pedido", "date"),
    ("Número do pedido", "numero_pedido", "text"),
    ("Número do Modelo", "numero_modelo", "text"),
    ("Descrição da peça", "descricao_peca", "text"),
    ("Número do Desenho", "numero_desenho", "text"),
    ("Peso líquido", "peso_liquido_kg", "decimal"),
    ("Peso bruto", "peso_bruto_kg", "decimal"),
    ("Liga", "liga", "text"),
    ("Norma", "norma", "text"),
    ("Quantidade de peças do pedido", "qtd_pecas_pedido", "int"),
    ("Qtde fundida", "qtd_fundida", "int"),
    ("Qtde expedida", "qtd_expedida", "int"),
    ("Valor unitário", "valor_unitario", "decimal"),
    ("Valor total", "valor_total", "decimal"),
    ("Condição do Modelo", "condicao_modelo", "text"),
    ("OE (número da Ordem de entrega)", "oe_numero", "join_oe"),
    ("Número do Certificado", "cert_numero", "join_cert"),
]


def _buscar_ofs_rastreabilidade(
    db: Session, attr: str, tipo: str, valor_busca
) -> list[OrdemFabricacao]:
    base_opts = [
        selectinload(OrdemFabricacao.ordens_entrega),
        selectinload(OrdemFabricacao.certificados),
    ]

    if tipo == "join_oe":
        v = str(valor_busca).strip()
        stmt = (
            select(OrdemFabricacao)
            .options(*base_opts)
            .join(OrdemEntrega, OrdemEntrega.ordem_fabricacao_id == OrdemFabricacao.id)
            .where(OrdemEntrega.numero_oe.ilike(f"%{v}%"))
        )
        return list(db.scalars(stmt).unique().all())

    if tipo == "join_cert":
        v = str(valor_busca).strip()
        stmt = (
            select(OrdemFabricacao)
            .options(*base_opts)
            .join(CertificadoPeca, CertificadoPeca.ordem_fabricacao_id == OrdemFabricacao.id)
            .where(CertificadoPeca.numero_certificado.ilike(f"%{v}%"))
        )
        return list(db.scalars(stmt).unique().all())

    col = getattr(OrdemFabricacao, attr)
    stmt = select(OrdemFabricacao).options(*base_opts)

    if tipo == "text":
        v = str(valor_busca).strip()
        stmt = stmt.where(and_(col.isnot(None), col.ilike(f"%{v}%")))
    elif tipo == "date":
        stmt = stmt.where(col == valor_busca)
    elif tipo == "int":
        stmt = stmt.where(col == int(valor_busca))
    elif tipo == "decimal":
        stmt = stmt.where(col == Decimal(str(valor_busca)))
    else:
        return []

    return list(db.scalars(stmt).all())


def _data_oe_para_tabela(oe: OrdemEntrega) -> date | None:
    if oe.data_prevista is not None:
        return oe.data_prevista
    if oe.criado_em is not None:
        return oe.criado_em.date() if hasattr(oe.criado_em, "date") else oe.criado_em
    return None


def _montar_df_rastreabilidade(ofs: list[OrdemFabricacao]) -> pd.DataFrame:
    """Reutiliza _montar_linhas_of e _df_of_formatado para manter
    exibição idêntica à aba Relatórios → Ordens de fabricação."""
    rows = _montar_linhas_of(ofs)
    return _df_of_formatado(rows)


def pagina_consulta_rastreabilidade() -> None:
    st.title("Consulta de Rastreabilidade")
    st.caption("Filtre ordens de fabricação em **fundicao.db** e visualize os dados da OF com **datas e quantidades das OEs**.")

    labels = [t[0] for t in RASTREABILIDADE_CAMPOS]
    mapa = {t[0]: (t[1], t[2]) for t in RASTREABILIDADE_CAMPOS}

    escolha = st.selectbox("Filtrar por campo da Ordem de Fabricação", labels, key="rastreio_campo")
    attr, tipo = mapa[escolha]

    if tipo == "date":
        valor_widget = st.date_input(
            "Valor da busca (data)",
            value=date.today(),
            format=FORMATO_DATE_INPUT_BR,
            key="rastreio_val_date",
        )
    elif tipo == "int":
        valor_widget = st.number_input("Valor da busca (número inteiro)", step=1, value=0, key="rastreio_val_int")
    elif tipo == "decimal":
        valor_widget = st.number_input("Valor da busca (decimal)", value=0.0, format="%.6f", key="rastreio_val_dec")
    else:
        valor_widget = st.text_input("Valor da busca", placeholder="Digite o termo…", key="rastreio_val_text")

    if st.button("Buscar", type="primary", key="rastreio_btn"):
        st.session_state["rastreio_executado"] = True
        if tipo in ("text", "join_oe", "join_cert") and not str(valor_widget).strip():
            st.session_state["rastreio_df"] = None
            st.session_state["rastreio_vazio"] = False
            st.session_state["rastreio_erro"] = "Informe um valor para buscar."
        elif tipo == "date" and valor_widget is None:
            st.session_state["rastreio_df"] = None
            st.session_state["rastreio_vazio"] = False
            st.session_state["rastreio_erro"] = "Informe uma data válida."
        else:
            st.session_state["rastreio_erro"] = None
            try:
                with db_session() as db:
                    ofs = _buscar_ofs_rastreabilidade(db, attr, tipo, valor_widget)
                    # Monta o df DENTRO da sessão — evita lazy load após a sessão fechar
                    if not ofs:
                        _rast_df = None
                    else:
                        _rast_df = _montar_df_rastreabilidade(ofs)
                if _rast_df is None:
                    st.session_state["rastreio_df"] = None
                    st.session_state["rastreio_vazio"] = True
                else:
                    st.session_state["rastreio_df"] = _rast_df
                    st.session_state["rastreio_vazio"] = False
            except Exception as e:
                st.session_state["rastreio_df"] = None
                st.session_state["rastreio_vazio"] = False
                st.session_state["rastreio_erro"] = f"Erro ao consultar o banco: {e}"

    if st.session_state.get("rastreio_erro"):
        st.error(st.session_state["rastreio_erro"])
    elif st.session_state.get("rastreio_executado"):
        if st.session_state.get("rastreio_vazio"):
            st.warning("Nenhuma informação registrada para essa busca")
        elif st.session_state.get("rastreio_df") is not None:
            st.subheader("Resultados")
            _df_rast = st.session_state["rastreio_df"]

            # Mesma ordenação da aba Relatórios: ano de abertura → chave alfanumérica
            if "Nº OF" in _df_rast.columns and "Abertura" in _df_rast.columns:
                _df_rast["_sort_ano"] = pd.to_datetime(
                    _df_rast["Abertura"], format="%d/%m/%Y", errors="coerce"
                ).dt.year.fillna(9999).astype(int)
                _df_rast["_sort_of"] = _df_rast["Nº OF"].fillna("").apply(_chave_of)
                _df_rast = _df_rast.sort_values(
                    by=["_sort_ano", "_sort_of"], ascending=[False, False], na_position="last"
                ).drop(columns=["_sort_ano", "_sort_of"]).reset_index(drop=True)

            # Mesma configuração de colunas do relatório
            _RAST_COL_CFG = {
                "Nº OF":           st.column_config.TextColumn("Nº OF",            width="small"),
                "NN°":             st.column_config.TextColumn("NN°",              width="small"),
                "Cliente":         st.column_config.TextColumn("Cliente",          width="large"),
                "Abertura":        st.column_config.TextColumn("Abertura",         width="small"),
                "Prazo Entrega":   st.column_config.TextColumn("Prazo Entrega",    width="small"),
                "Nº Pedido":       st.column_config.TextColumn("Nº Pedido",        width="small"),
                "Modelo":          st.column_config.TextColumn("Modelo",           width="small"),
                "Descrição Peça":  st.column_config.TextColumn("Descrição Peça",   width="medium"),
                "Nº Desenho":      st.column_config.TextColumn("Nº Desenho",       width="small"),
                "Peso Líq. (kg)":  st.column_config.NumberColumn("Peso Líq. (kg)", width="small", format="%.4f"),
                "Peso Bruto (kg)": st.column_config.NumberColumn("Peso Bruto(kg)", width="small", format="%.4f"),
                "Liga":            st.column_config.TextColumn("Liga",             width="small"),
                "Norma":           st.column_config.TextColumn("Norma",            width="medium"),
                "Qtd Pedido":      st.column_config.NumberColumn("Qtd Pedido",     width="small", format="%d"),
                "Qtd Fundida":     st.column_config.NumberColumn("Qtd Fundida",    width="small", format="%d"),
                "Qtd Expedida":    st.column_config.NumberColumn("Qtd Expedida",   width="small", format="%d"),
                "Vlr Unit. (R$)":  st.column_config.NumberColumn("Vlr Unit.(R$)",  width="small", format="%.2f"),
                "Vlr Total (R$)":  st.column_config.NumberColumn("Vlr Total(R$)",  width="small", format="%.2f"),
                "Cond. Modelo":    st.column_config.TextColumn("Cond. Modelo",     width="medium"),
                "Observações":     st.column_config.TextColumn("Observações",      width="large"),
                "Nº OE":           st.column_config.TextColumn("Nº OE",            width="large"),
                "Nº Certificado":  st.column_config.TextColumn("Nº Certificado",   width="large"),
            }

            st.dataframe(
                _df_rast,
                height=500,
                use_container_width=True,
                hide_index=True,
                column_config=_RAST_COL_CFG,
            )


CORRIDAS_CONSULTA_CAMPOS: list[tuple[str, str, str]] = [
    ("Data de fusão", "data_fusao", "date"),
    ("Número da corrida", "numero_corrida", "text"),
    ("Nome do cliente", "nome_cliente", "text"),
    ("Número da Ordem de fabricação", "numero_ordem_fabricacao", "text"),
    ("Quantidade de peças fundidas", "qtd_pecas_fundidas", "int"),
    ("Série das peças fundidas", "serie_pecas_fundidas", "text"),
    ("Liga", "liga", "text"),
    ("Norma", "norma", "text"),
]

_CORRIDA_TEXT_NULLABLE = frozenset(
    {"numero_ordem_fabricacao", "serie_pecas_fundidas", "liga", "norma"}
)


def _buscar_corridas_filtro(db: Session, attr: str, tipo: str, valor_busca) -> list[Corrida]:
    col = getattr(Corrida, attr)
    stmt = select(Corrida)

    if tipo == "text":
        v = str(valor_busca).strip()
        if attr in _CORRIDA_TEXT_NULLABLE:
            stmt = stmt.where(and_(col.isnot(None), col.ilike(f"%{v}%")))
        else:
            stmt = stmt.where(col.ilike(f"%{v}%"))
    elif tipo == "date":
        stmt = stmt.where(col == valor_busca)
    elif tipo == "int":
        stmt = stmt.where(col == int(valor_busca))
    else:
        return []

    return list(
        db.scalars(stmt.order_by(Corrida.data_fusao.desc(), Corrida.criado_em.desc())).all()
    )


def _montar_df_corridas_completas(corridas: list[Corrida]) -> pd.DataFrame:
    """Monta DataFrame de corridas com mesmo formato da aba Relatórios → Corridas."""
    _ELEM_SEQ = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","B","CE","V","Co","Fe","N","Mg"]
    rows: list[dict] = []
    for c in corridas:
        comp = c.composicao_quimica_pct or {}
        row = {
            "Corrida":     c.numero_corrida or "",
            "Data fusão":  _exibir_data_br(c.data_fusao),
            "Cliente":     c.nome_cliente or "",
            "OF":          c.numero_ordem_fabricacao or "",
            "Qtd fundida": c.qtd_pecas_fundidas,
            "Série":       c.serie_pecas_fundidas or "",
            "Liga":        c.liga or "",
            "Norma":       c.norma or "",
        }
        for elem in _ELEM_SEQ:
            v = comp.get(elem)
            row[elem] = float(v) if v is not None else None
        rows.append(row)
    return pd.DataFrame(rows)


def pagina_consulta_corridas() -> None:
    st.title("Consulta de Corridas")
    st.caption("Filtre registros da tabela **corrida** em **fundicao.db**.")

    labels = [t[0] for t in CORRIDAS_CONSULTA_CAMPOS]
    mapa = {t[0]: (t[1], t[2]) for t in CORRIDAS_CONSULTA_CAMPOS}

    escolha = st.selectbox("Filtrar por campo da Corrida", labels, key="corr_consulta_campo")
    attr, tipo = mapa[escolha]

    if tipo == "date":
        valor_widget = st.date_input(
            "Valor da busca (data)",
            value=date.today(),
            format=FORMATO_DATE_INPUT_BR,
            key="corr_consulta_val_date",
        )
    elif tipo == "int":
        valor_widget = st.number_input(
            "Valor da busca (quantidade)", step=1, value=0, key="corr_consulta_val_int"
        )
    else:
        valor_widget = st.text_input("Valor da busca", placeholder="Digite o termo…", key="corr_consulta_val_text")

    if st.button("Buscar", type="primary", key="corr_consulta_btn"):
        st.session_state["corr_consulta_executado"] = True
        if tipo == "text" and not str(valor_widget).strip():
            st.session_state["corr_consulta_df"] = None
            st.session_state["corr_consulta_vazio"] = False
            st.session_state["corr_consulta_erro"] = "Informe um valor para buscar."
        elif tipo == "date" and valor_widget is None:
            st.session_state["corr_consulta_df"] = None
            st.session_state["corr_consulta_vazio"] = False
            st.session_state["corr_consulta_erro"] = "Informe uma data válida."
        else:
            st.session_state["corr_consulta_erro"] = None
            try:
                with db_session() as db:
                    corridas = _buscar_corridas_filtro(db, attr, tipo, valor_widget)
                if not corridas:
                    st.session_state["corr_consulta_df"] = None
                    st.session_state["corr_consulta_vazio"] = True
                else:
                    st.session_state["corr_consulta_df"] = _montar_df_corridas_completas(corridas)
                    st.session_state["corr_consulta_vazio"] = False
            except Exception as e:
                st.session_state["corr_consulta_df"] = None
                st.session_state["corr_consulta_vazio"] = False
                st.session_state["corr_consulta_erro"] = f"Erro ao consultar o banco: {e}"

    if st.session_state.get("corr_consulta_erro"):
        st.error(st.session_state["corr_consulta_erro"])
    elif st.session_state.get("corr_consulta_executado"):
        if st.session_state.get("corr_consulta_vazio"):
            st.warning("Nenhuma informação registrada para essa busca")
        elif st.session_state.get("corr_consulta_df") is not None:
            st.subheader("Resultados")
            _df_cc = st.session_state["corr_consulta_df"]

            # Mesma ordenação da aba Relatórios → Corridas: data completa → chave alfanumérica
            if "Corrida" in _df_cc.columns and "Data fusão" in _df_cc.columns:
                _df_cc["_sort_data"] = pd.to_datetime(
                    _df_cc["Data fusão"], format="%d/%m/%Y", errors="coerce"
                )
                _df_cc["_sort_c"] = _df_cc["Corrida"].fillna("").apply(_chave_of)
                _df_cc = _df_cc.sort_values(
                    by=["_sort_data", "_sort_c"], ascending=[False, False], na_position="last"
                ).drop(columns=["_sort_data", "_sort_c"]).reset_index(drop=True)

            # Mesma configuração de colunas do relatório de corridas
            _ELEM_SEQ_CC = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","B","CE","V","Co","Fe","N","Mg"]
            _col_cfg_cc = {
                "Corrida":     st.column_config.TextColumn("Corrida",       width="small"),
                "Data fusão":  st.column_config.TextColumn("Data Fusão",    width="small"),
                "Cliente":     st.column_config.TextColumn("Cliente",       width="large"),
                "OF":          st.column_config.TextColumn("Nº OF",         width="small"),
                "Qtd fundida": st.column_config.NumberColumn("Qtd Fundida", width="small", format="%d"),
                "Série":       st.column_config.TextColumn("Série",         width="medium"),
                "Liga":        st.column_config.TextColumn("Liga",          width="small"),
                "Norma":       st.column_config.TextColumn("Norma",         width="medium"),
            }
            for _el in _ELEM_SEQ_CC:
                _col_cfg_cc[_el] = st.column_config.NumberColumn(_el, width="small", format="%.4f")

            st.dataframe(
                _df_cc,
                height=500,
                use_container_width=True,
                hide_index=True,
                column_config=_col_cfg_cc,
            )



def _chave_of(codigo: str) -> tuple:
    """
    Chave de ordenação para códigos no formato 000X0 (ex: 001A6, 002B3).

    Formato: NNN + LETRA + D
      NNN   = sequência no mês (001, 002...)
      LETRA = mês (A=Jan, B=Fev, ... L=Dez)
      D     = dígito do ano

    Regra de década:
      O dígito final representa o último dígito do ano.
      Para evitar ambiguidade (ex: 9 pode ser 2019 ou 2029),
      usamos um ANO_CORTE: dígitos <= ANO_CORTE pertencem à década atual (2020s),
      dígitos > ANO_CORTE pertencem à década anterior (2010s).

      ANO_CORTE = último dígito do ano atual + 1 (com margem de 1 ano à frente).
      Ex: em 2026, ANO_CORTE = 7 → dígitos 0-7 = 2020-2027, dígitos 8-9 = 2018-2019.

      Quando chegarmos em 2028 (ANO_CORTE=9), dígito 9 = 2029 e não haverá ambiguidade.
      Em 2030, o formato provavelmente mudará — mas a lógica se adapta automaticamente.

    Ordena por: ano_real → letra → sequência numérica (crescente)
    Códigos fora do padrão vão para o final.
    """
    import re as _re
    from datetime import date as _date

    if not codigo or not isinstance(codigo, str):
        return (9999, "Z", 9999, codigo or "")

    # Remove "dev" e busca padrão NNN + LETRA + D
    limpo = _re.sub(r"(?i)dev", "", codigo.strip()).strip()
    m = _re.search(r"(\d{1,4})([A-Za-z])(\d)", limpo)
    if not m:
        return (9999, "Z", 9999, codigo)

    num, letra, sfx = m.groups()
    digito = int(sfx)

    # Calcula ano real com regra de corte de década
    ano_atual = _date.today().year          # ex: 2026
    decada_atual = (ano_atual // 10) * 10   # ex: 2020
    ano_corte = (ano_atual % 10) + 1        # ex: 7 (em 2026)

    if digito <= ano_corte:
        ano_real = decada_atual + digito     # ex: 2020 + 6 = 2026
    else:
        ano_real = decada_atual - 10 + digito  # ex: 2010 + 9 = 2019

    return (ano_real, letra.upper(), int(num), codigo)

def pagina_relatorios() -> None:
    st.title("Relatórios")
    pode_alterar_of = tem_permissao("relatorios_alterar_of")
    pode_excluir_of = tem_permissao("relatorios_excluir_of")
    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")
    pode_excluir_corrida = tem_permissao("relatorios_excluir_corrida")
    pode_configuracoes = tem_permissao("configuracoes")
    st.caption("Consultas e exportação a partir de **fundicao.db**.")

    with db_session() as db:
        ofs = list(db.scalars(select(OrdemFabricacao).order_by(OrdemFabricacao.criado_em.desc())).all())
        corridas = list(db.scalars(select(Corrida).order_by(Corrida.data_fusao.desc())).all())

    if pode_configuracoes:
        tab1, tab2, tab3, tab4 = st.tabs(["Ordens de fabricação", "Corridas", "Resumo", "⚙️ Configurações"])
    else:
        _tabs_sem_cfg = st.tabs(["Ordens de fabricação", "Corridas", "Resumo"])
        tab1, tab2, tab3, tab4 = _tabs_sem_cfg[0], _tabs_sem_cfg[1], _tabs_sem_cfg[2], None

    with tab1:
        if not ofs:
            st.info("Nenhuma OF para exibir.")
        else:
            try:
                with db_session() as db:
                    ofs_completas = list(
                        db.scalars(
                            select(OrdemFabricacao)
                            .options(
                                selectinload(OrdemFabricacao.ordens_entrega),
                                selectinload(OrdemFabricacao.certificados),
                            )
                            .order_by(OrdemFabricacao.criado_em.desc())
                        ).all()
                    )
                    # Extrai dentro da sessão antes de fechar
                    rows = _montar_linhas_of(ofs_completas)
            except Exception as e:
                st.error(f"Erro ao carregar OEs/certificados: {e}")
                rows = _montar_linhas_of(ofs)

            df = _df_of_formatado(rows)

            # Ordena pela chave da OF — decrescente (mais recentes primeiro)
            if "Nº OF" in df.columns:
                df[["_s_ano","_s_mes","_s_seq","_s_cod"]] = pd.DataFrame(
                    df["Nº OF"].fillna("").apply(_chave_of).tolist(),
                    index=df.index
                )
                df = df.sort_values(
                    by=["_s_ano","_s_mes","_s_seq"],
                    ascending=[False, False, False],
                    na_position="last",
                ).drop(columns=["_s_ano","_s_mes","_s_seq","_s_cod"], errors="ignore")\
                 .reset_index(drop=True)

            # Rótulos em português e larguras por tipo de campo
            # Últimas colunas com width="large" para garantir visualização completa
            _OF_COL_CFG = {
                "Nº OF":           st.column_config.TextColumn("Nº OF",            width="small"),
                "NN°":             st.column_config.TextColumn("NN°",              width="small"),
                "Cliente":         st.column_config.TextColumn("Cliente",          width="large"),
                "Abertura":        st.column_config.TextColumn("Abertura",         width="small"),
                "Prazo Entrega":   st.column_config.TextColumn("Prazo Entrega",    width="small"),
                "Nº Pedido":       st.column_config.TextColumn("Nº Pedido",        width="small"),
                "Modelo":          st.column_config.TextColumn("Modelo",           width="small"),
                "Descrição Peça":  st.column_config.TextColumn("Descrição Peça",   width="medium"),
                "Nº Desenho":      st.column_config.TextColumn("Nº Desenho",       width="small"),
                "Peso Líq. (kg)":  st.column_config.NumberColumn("Peso Líq. (kg)", width="small", format="%.4f"),
                "Peso Bruto (kg)": st.column_config.NumberColumn("Peso Bruto(kg)", width="small", format="%.4f"),
                "Liga":            st.column_config.TextColumn("Liga",             width="small"),
                "Norma":           st.column_config.TextColumn("Norma",            width="medium"),
                "Qtd Pedido":      st.column_config.NumberColumn("Qtd Pedido",     width="small", format="%d"),
                "Qtd Fundida":     st.column_config.NumberColumn("Qtd Fundida",    width="small", format="%d"),
                "Qtd Expedida":    st.column_config.NumberColumn("Qtd Expedida",   width="small", format="%d"),
                "Vlr Unit. (R$)":  st.column_config.NumberColumn("Vlr Unit.(R$)",  width="small", format="%.2f"),
                "Vlr Total (R$)":  st.column_config.NumberColumn("Vlr Total(R$)",  width="small", format="%.2f"),
                "Cond. Modelo":    st.column_config.TextColumn("Cond. Modelo",     width="medium"),
                "Observações":     st.column_config.TextColumn("Observações",      width="large"),
                "Nº OE":           st.column_config.TextColumn("Nº OE",            width="large"),
                "Nº Certificado":  st.column_config.TextColumn("Nº Certificado",   width="large"),
            }

            # O numero_of é lido diretamente do df já ordenado — garante correspondência exata
            st.caption("Clique no ☐ à esquerda da linha para selecionar uma OF e usar as opções abaixo.")
            _altura_of = st.slider("Altura da tabela (px)", min_value=200, max_value=1400, value=500, step=50, key="altura_of")
            # Guarda _id antes de remover do display
            _df_ids_of = df["_id"].tolist() if "_id" in df.columns else []
            df_display_of = df.drop(columns=["_id"], errors="ignore")
            sel_of = st.dataframe(
                df_display_of,
                height=_altura_of,
                use_container_width=True,
                hide_index=True,
                column_config=_OF_COL_CFG,
                on_select="rerun",
                selection_mode="single-row",
                key="sel_df_ofs",
            )

            buf = StringIO()
            df_display_of.to_csv(buf, index=False)
            st.download_button("⬇️ Baixar CSV — OFs completo", buf.getvalue(), file_name="relatorio_ofs.csv", mime="text/csv")

            # Identifica linha selecionada — usa _df_ids_of para garantir correspondência correta
            _idx_of = (sel_of.selection.rows or [None])[0]
            if _idx_of is not None and _idx_of < len(_df_ids_of):
                _of_id_sel  = _df_ids_of[_idx_of]
                _nof_sel    = df_display_of.iloc[_idx_of]["Nº OF"] if "Nº OF" in df_display_of.columns else ""
                _label_sel  = _nof_sel if _nof_sel else f"(sem número — id: {str(_of_id_sel)[:8]})"
                if _of_id_sel:
                    st.divider()
                    st.subheader(f"OF selecionada: **{_label_sel}**")
                    _col_alt, _col_exc = st.columns(2)

                    # ── Alterar ──────────────────────────────────────────────
                    if pode_alterar_of:
                     with _col_alt:
                      with st.expander("✏️ Alterar dados desta OF", expanded=False):
                            try:
                                with db_session() as _db_ed:
                                    _of_ed = _db_ed.scalar(
                                        select(OrdemFabricacao).where(OrdemFabricacao.numero_of == _nof_sel)
                                    )
                                    if _of_ed:
                                        _of_data = {
                                            "numero_nn":          _of_ed.numero_nn or "",
                                            "nome_cliente":       _of_ed.nome_cliente or "",
                                            "prazo_entrega_pedido": _of_ed.prazo_entrega_pedido,
                                            "numero_pedido":      _of_ed.numero_pedido or "",
                                            "numero_modelo":      _of_ed.numero_modelo or "",
                                            "descricao_peca":     _of_ed.descricao_peca or "",
                                            "numero_desenho":     _of_ed.numero_desenho or "",
                                            "peso_liquido_kg":    float(_of_ed.peso_liquido_kg) if _of_ed.peso_liquido_kg else 0.0,
                                            "peso_bruto_kg":      float(_of_ed.peso_bruto_kg) if _of_ed.peso_bruto_kg else 0.0,
                                            "liga":               _of_ed.liga or "",
                                            "norma":              _of_ed.norma or "",
                                            "qtd_pecas_pedido":   _of_ed.qtd_pecas_pedido or 0,
                                            "qtd_fundida":        _of_ed.qtd_fundida or 0,
                                            "qtd_expedida":       _of_ed.qtd_expedida or 0,
                                            "valor_unitario":     float(_of_ed.valor_unitario) if _of_ed.valor_unitario else 0.0,
                                            "valor_total":        float(_of_ed.valor_total) if _of_ed.valor_total else 0.0,
                                            "data_abertura_pedido": _of_ed.data_abertura_pedido,
                                            "condicao_modelo":    _of_ed.condicao_modelo or "",
                                            "observacoes":        _of_ed.observacoes or "",
                                        }
                            except Exception as _ex:
                                st.error(f"Erro ao carregar OF: {_ex}")
                                _of_data = None

                            if _of_data:
                                with st.form(f"form_alt_of_{_nof_sel}", clear_on_submit=False):
                                    _c1, _c2 = st.columns(2)
                                    with _c1:
                                        _nn       = st.text_input("NN°",          value=_of_data["numero_nn"])
                                        _cliente  = st.text_input("Cliente *",    value=_of_data["nome_cliente"])
                                        _pedido   = st.text_input("Nº Pedido",    value=_of_data["numero_pedido"])
                                        _modelo   = st.text_input("Modelo",       value=_of_data["numero_modelo"])
                                        _descr    = st.text_area("Descrição",     value=_of_data["descricao_peca"])
                                        _desenho  = st.text_input("Nº Desenho",   value=_of_data["numero_desenho"])
                                        _liga     = st.text_input("Liga",         value=_of_data["liga"])
                                        _norma    = st.text_input("Norma",        value=_of_data["norma"])
                                    with _c2:
                                        _abertura = st.date_input("Data abertura *", value=_of_data["data_abertura_pedido"], format="DD/MM/YYYY", min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
                                        _prazo    = st.date_input("Prazo entrega", value=_of_data["prazo_entrega_pedido"] if _of_data["prazo_entrega_pedido"] else None, format="DD/MM/YYYY", min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
                                        _pl       = st.number_input("Peso líq. (kg)",  value=_of_data["peso_liquido_kg"], format="%.4f")
                                        _pb       = st.number_input("Peso bruto (kg)", value=_of_data["peso_bruto_kg"],   format="%.4f")
                                        _qtdp     = st.number_input("Qtd pedido",  value=_of_data["qtd_pecas_pedido"], step=1)
                                        _qtdf     = st.number_input("Qtd fundida", value=_of_data["qtd_fundida"],       step=1)
                                        _qtde     = st.number_input("Qtd expedida",value=_of_data["qtd_expedida"],      step=1)
                                        _vunit    = st.number_input("Vlr unitário",value=_of_data["valor_unitario"],    format="%.2f")
                                        _vtot     = st.number_input("Vlr total",   value=_of_data["valor_total"],       format="%.2f")
                                    _cond     = st.text_input("Cond. Modelo", value=_of_data["condicao_modelo"])
                                    _obs      = st.text_area("Observações",  value=_of_data["observacoes"])

                                    _sb1, _sb2, _sb3 = st.columns(3)
                                    with _sb1:
                                        _salvar = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
                                    with _sb2:
                                        _finalizar = st.form_submit_button("✅ Finalizar OF", use_container_width=True)
                                    with _sb3:
                                        _cancelar = st.form_submit_button("🚫 Cancelar OF", use_container_width=True)

                                    _acao = "salvar" if _salvar else ("finalizar" if _finalizar else ("cancelar" if _cancelar else None))
                                    if _acao:
                                        try:
                                            from decimal import Decimal as _Dec
                                            with db_session() as _db_save:
                                                _of_save = _db_save.scalar(
                                                    select(OrdemFabricacao).where(OrdemFabricacao.numero_of == _nof_sel)
                                                )
                                                if _of_save:
                                                    if _acao in ("salvar", "finalizar", "cancelar"):
                                                        _of_save.numero_nn          = _nn.strip() or None
                                                        _of_save.nome_cliente       = _cliente.strip()
                                                        _of_save.data_abertura_pedido = _abertura
                                                        _of_save.prazo_entrega_pedido = _prazo
                                                        _of_save.numero_pedido      = _pedido.strip() or None
                                                        _of_save.numero_modelo      = _modelo.strip() or None
                                                        _of_save.descricao_peca     = _descr.strip() or None
                                                        _of_save.numero_desenho     = _desenho.strip() or None
                                                        _of_save.peso_liquido_kg    = _Dec(str(_pl)) if _pl else None
                                                        _of_save.peso_bruto_kg      = _Dec(str(_pb)) if _pb else None
                                                        _of_save.liga               = _liga.strip() or None
                                                        _of_save.norma              = _norma.strip() or None
                                                        _of_save.qtd_pecas_pedido   = int(_qtdp)
                                                        _of_save.qtd_fundida        = int(_qtdf)
                                                        _of_save.qtd_expedida       = int(_qtde)
                                                        _of_save.valor_unitario     = _Dec(str(_vunit)) if _vunit else None
                                                        _of_save.valor_total        = _Dec(str(_vtot)) if _vtot else None
                                                        _of_save.condicao_modelo    = _cond.strip() or None
                                                        _of_save.observacoes        = _obs.strip() or None
                                                        _of_save.atualizado_em      = datetime.now().astimezone()

                                                        # Atualiza em cascata nas corridas vinculadas
                                                        _corridas_vinc = _db_save.execute(
                                                            select(Corrida).where(
                                                                (Corrida.numero_ordem_fabricacao == _nof_sel) |
                                                                (Corrida.ordem_fabricacao_id == _of_save.id)
                                                            )
                                                        ).scalars().all()
                                                        for _corr_v in _corridas_vinc:
                                                            if _cliente.strip():
                                                                _corr_v.nome_cliente = _cliente.strip()
                                                            if _liga.strip():
                                                                _corr_v.liga = _liga.strip()
                                                            if _norma.strip():
                                                                _corr_v.norma = _norma.strip()
                                                            _corr_v.atualizado_em = datetime.now().astimezone()
                                                    if _acao == "finalizar":
                                                        _of_save.status_of = "Finalizada"
                                                        # UPDATE direto via SQL para garantir gravação
                                                        _db_save.execute(
                                                            __import__("sqlalchemy").text(
                                                                "UPDATE ordem_fabricacao SET status_of='Finalizada' WHERE numero_of=:nof"
                                                            ),
                                                            {"nof": _nof_sel}
                                                        )
                                                    elif _acao == "cancelar":
                                                        _of_save.status_of = "Cancelada"
                                                        # UPDATE direto via SQL para garantir gravação
                                                        _db_save.execute(
                                                            __import__("sqlalchemy").text(
                                                                "UPDATE ordem_fabricacao SET status_of='Cancelada' WHERE numero_of=:nof"
                                                            ),
                                                            {"nof": _nof_sel}
                                                        )
                                                    else:
                                                        # Salvar simples — mantém status atual
                                                        pass
                                            _msg = {"salvar": f"OF **{_nof_sel}** atualizada com sucesso!",
                                                    "finalizar": f"OF **{_nof_sel}** marcada como **Finalizada** e removida do dashboard.",
                                                    "cancelar":  f"OF **{_nof_sel}** marcada como **Cancelada**. Aparecerá com marca d'água no dashboard."}
                                            st.success(_msg[_acao])
                                            st.session_state.pop("sel_df_ofs", None)
                                            st.rerun()
                                        except Exception as _ex:
                                            st.error(f"Erro ao salvar: {_ex}")

                    # ── Excluir ──────────────────────────────────────────────
                    if pode_excluir_of:
                     with _col_exc:
                      with st.expander("🗑️ Excluir esta OF", expanded=False):
                            st.warning(f"Isso excluirá a OF **{_label_sel}** e todos os seus registros vinculados (OEs, certificados). Esta ação **não pode ser desfeita**.")
                            if st.button(f"⚠️ Confirmar exclusão de {_label_sel}", key=f"btn_exc_of_{_of_id_sel}", type="primary"):
                                try:
                                    with db_session() as _db_del:
                                        _of_del = _db_del.scalar(
                                            select(OrdemFabricacao).where(OrdemFabricacao.id == _of_id_sel)
                                        )
                                        if _of_del:
                                            _db_del.delete(_of_del)
                                    st.success(f"OF **{_label_sel}** excluída com sucesso.")
                                    st.session_state.pop("sel_df_ofs", None)
                                    st.rerun()
                                except Exception as _ex:
                                    st.error(f"Erro ao excluir: {_ex}")

    with tab2:
        if not corridas:
            st.info("Nenhuma corrida para exibir.")
        else:
            # Elementos na mesma sequência da tela "Lançar Corrida"
            _ELEM_SEQ = [
                "C", "Si", "Mn", "P", "S", "Cr", "Ni", "Mo", "Cu",
                "W", "Nb", "B", "CE", "V", "Co", "Fe", "N", "Mg",
            ]
            rows = []
            for c in corridas:
                comp = c.composicao_quimica_pct or {}
                row = {
                    "_id":          c.id,
                    "Corrida":      c.numero_corrida or "",
                    "Data fusão":   _exibir_data_br(c.data_fusao),
                    "Cliente":      c.nome_cliente or "",
                    "OF":           c.numero_ordem_fabricacao or "",
                    "Qtd fundida":  c.qtd_pecas_fundidas,
                    "Série":        c.serie_pecas_fundidas or "",
                    "Liga":         c.liga or "",
                    "Norma":        c.norma or "",
                }
                # Um elemento por coluna, na sequência padrão
                for elem in _ELEM_SEQ:
                    v = comp.get(elem)
                    row[elem] = float(v) if v is not None else None
                rows.append(row)

            df = pd.DataFrame(rows)

            # Configuração de colunas
            col_config = {
                "Corrida":     st.column_config.TextColumn("Corrida",    width="small"),
                "Data fusão":  st.column_config.TextColumn("Data fusão", width="small"),
                "Cliente":     st.column_config.TextColumn("Cliente",    width="medium"),
                "OF":          st.column_config.TextColumn("OF",         width="small"),
                "Qtd fundida": st.column_config.NumberColumn("Qtd fund.", width="small", format="%d"),
                "Série":       st.column_config.TextColumn("Série",      width="medium"),
                "Liga":        st.column_config.TextColumn("Liga",       width="small"),
                "Norma":       st.column_config.TextColumn("Norma",      width="medium"),
            }
            # Colunas dos elementos químicos — formato com 4 decimais
            for elem in _ELEM_SEQ:
                col_config[elem] = st.column_config.NumberColumn(
                    elem, width="small", format="%.4f"
                )

            # Centraliza Qtd fundida convertendo para texto
            if "Qtd fundida" in df.columns:
                df["Qtd fundida"] = df["Qtd fundida"].apply(
                    lambda x: str(int(x)) if pd.notna(x) and x != 0 else ""
                )

            # Ordena: 1º pela data de fusão (mais antiga primeiro), 2º pela chave alfanumérica
            if "Corrida" in df.columns and "Data fusão" in df.columns:
                df["_sort_data"] = pd.to_datetime(
                    df["Data fusão"], format="%d/%m/%Y", errors="coerce"
                )
                df["_sort_corrida"] = df["Corrida"].fillna("").apply(_chave_of)
                df = df.sort_values(
                    by=["_sort_data", "_sort_corrida"],
                    ascending=[False, False],
                    na_position="last",
                ).drop(columns=["_sort_data", "_sort_corrida"]).reset_index(drop=True)

            # Atualiza rótulos do column_config com nomes em português
            col_config.update({
                "Corrida":      st.column_config.TextColumn("Corrida",       width="small"),
                "Data fusão":   st.column_config.TextColumn("Data Fusão",    width="small"),
                "Cliente":      st.column_config.TextColumn("Cliente",       width="large"),
                "OF":           st.column_config.TextColumn("Nº OF",         width="small"),
                "Qtd fundida":  st.column_config.NumberColumn("Qtd Fundida", width="small", format="%d"),
                "Série":        st.column_config.TextColumn("Série",         width="medium"),
                "Liga":         st.column_config.TextColumn("Liga",          width="small"),
                "Norma":        st.column_config.TextColumn("Norma",         width="medium"),
            })

            # IDs ficam no df na mesma ordem — sem necessidade de reordenar separado
            _ids_corr_ord = df["_id"].tolist()

            # Remove coluna _id do display
            df_display = df.drop(columns=["_id"])

            st.caption("Clique no ☐ à esquerda da linha para selecionar uma corrida e usar as opções abaixo.")
            _altura_corr = st.slider("Altura da tabela (px)", min_value=200, max_value=1400, value=400, step=50, key="altura_corr")
            sel_corr = st.dataframe(
                df_display,
                height=_altura_corr,
                use_container_width=True,
                hide_index=True,
                column_config=col_config,
                on_select="rerun",
                selection_mode="single-row",
                key="sel_df_corridas",
            )

            buf = StringIO()
            df_display.to_csv(buf, index=False)
            st.download_button(
                "⬇️ Baixar CSV — corridas", buf.getvalue(),
                file_name="relatorio_corridas.csv", mime="text/csv"
            )

            _idx_corr = (sel_corr.selection.rows or [None])[0]
            if _idx_corr is not None and _idx_corr < len(_ids_corr_ord):
                _id_corr_sel = _ids_corr_ord[_idx_corr]
                st.divider()

                try:
                    with db_session() as _db_cv:
                        _corr_view = _db_cv.scalar(select(Corrida).where(Corrida.id == _id_corr_sel))
                        _corr_label = f"{_corr_view.numero_corrida} / OF {_corr_view.numero_ordem_fabricacao or '—'} / Série {_corr_view.serie_pecas_fundidas or '—'}" if _corr_view else _id_corr_sel
                except Exception:
                    _corr_label = _id_corr_sel

                st.subheader(f"Corrida selecionada: **{_corr_label}**")
                _cc1, _cc2 = st.columns(2)

                # ── Alterar Corrida ───────────────────────────────────────
                if pode_alterar_corrida:
                 with _cc1:
                  with st.expander("✏️ Alterar dados desta corrida", expanded=False):
                        try:
                            with db_session() as _db_ced:
                                _corr_ed = _db_ced.scalar(select(Corrida).where(Corrida.id == _id_corr_sel))
                                if _corr_ed:
                                    _cd = {
                                        "data_fusao":            _corr_ed.data_fusao,
                                        "numero_corrida":        _corr_ed.numero_corrida or "",
                                        "nome_cliente":          _corr_ed.nome_cliente or "",
                                        "numero_ordem_fabricacao": _corr_ed.numero_ordem_fabricacao or "",
                                        "qtd_pecas_fundidas":    _corr_ed.qtd_pecas_fundidas or 0,
                                        "serie_pecas_fundidas":  _corr_ed.serie_pecas_fundidas or "",
                                        "liga":                  _corr_ed.liga or "",
                                        "norma":                 _corr_ed.norma or "",
                                        "composicao":            dict(_corr_ed.composicao_quimica_pct or {}),
                                    }
                        except Exception as _ex:
                            st.error(f"Erro ao carregar corrida: {_ex}")
                            _cd = None

                        if _cd:
                            with st.form(f"form_alt_corr_{_id_corr_sel}", clear_on_submit=False):
                                _cc1a, _cc1b = st.columns(2)
                                with _cc1a:
                                    _c_data   = st.date_input("Data fusão *", value=_cd["data_fusao"], format="DD/MM/YYYY", min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
                                    _c_num    = st.text_input("Nº Corrida *",  value=_cd["numero_corrida"])
                                    _c_cli    = st.text_input("Cliente *",     value=_cd["nome_cliente"])
                                    _c_of     = st.text_input("Nº OF",         value=_cd["numero_ordem_fabricacao"])
                                    _c_qtd    = st.number_input("Qtd fundida", value=_cd["qtd_pecas_fundidas"], step=1)
                                    _c_serie  = st.text_input("Série",         value=_cd["serie_pecas_fundidas"])
                                    _c_liga   = st.text_input("Liga",          value=_cd["liga"])
                                    _c_norma  = st.text_input("Norma",         value=_cd["norma"])
                                with _cc1b:
                                    st.markdown("**Composição química (%)**")
                                    _ELEM_ED = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","B","CE","V","Co","Fe","N","Mg"]
                                    _comp_ed = {}
                                    for _el in _ELEM_ED:
                                        _comp_ed[_el] = st.number_input(_el, value=float(_cd["composicao"].get(_el, 0) or 0), format="%.4f", key=f"ed_chem_{_id_corr_sel}_{_el}")

                                if st.form_submit_button("💾 Salvar alterações", type="primary"):
                                    try:
                                        _comp_save = {k: v for k, v in _comp_ed.items() if v > 0}
                                        with db_session() as _db_cs:
                                            _corr_s = _db_cs.scalar(select(Corrida).where(Corrida.id == _id_corr_sel))
                                            if _corr_s:
                                                _corr_s.data_fusao              = _c_data
                                                _corr_s.numero_corrida          = _c_num.strip()
                                                _corr_s.nome_cliente            = _c_cli.strip()
                                                _corr_s.numero_ordem_fabricacao = _c_of.strip() or None
                                                _corr_s.qtd_pecas_fundidas      = int(_c_qtd)
                                                _corr_s.serie_pecas_fundidas    = _c_serie.strip() or None
                                                _corr_s.liga                    = _c_liga.strip() or None
                                                _corr_s.norma                   = _c_norma.strip() or None
                                                _corr_s.composicao_quimica_pct  = _comp_save
                                                _corr_s.atualizado_em           = datetime.now().astimezone()
                                        st.success("Corrida atualizada com sucesso!")
                                        st.session_state.pop("sel_df_corridas", None)
                                        st.rerun()
                                    except Exception as _ex:
                                        st.error(f"Erro ao salvar: {_ex}")

                # ── Excluir Corrida ───────────────────────────────────────
                if pode_excluir_corrida:
                 with _cc2:
                  with st.expander("🗑️ Excluir esta corrida", expanded=False):
                        st.warning(f"Isso excluirá permanentemente esta corrida. **Esta ação não pode ser desfeita**.")
                        if st.button("⚠️ Confirmar exclusão", key=f"btn_exc_corr_{_id_corr_sel}", type="primary"):
                            try:
                                with db_session() as _db_cd:
                                    _corr_d = _db_cd.scalar(select(Corrida).where(Corrida.id == _id_corr_sel))
                                    if _corr_d:
                                        _db_cd.delete(_corr_d)
                                st.success("Corrida excluída com sucesso.")
                                st.session_state.pop("sel_df_corridas", None)
                                st.rerun()
                            except Exception as _ex:
                                st.error(f"Erro ao excluir: {_ex}")

    with tab3:
        st.metric("Total de OFs", len(ofs))
        st.metric("Total de corridas", len(corridas))
        if ofs:
            por_cliente = (
                pd.DataFrame([{"Cliente": of.nome_cliente, "Qtd pedido": of.qtd_pecas_pedido or 0} for of in ofs])
                .groupby("Cliente", as_index=False)["Qtd pedido"]
                .sum()
                .sort_values("Qtd pedido", ascending=False)
            )
            st.subheader("Peças pedidas por cliente")
            st.dataframe(formatar_datas_br(por_cliente), use_container_width=True, hide_index=True)

    if tab4:
     with tab4:
        st.subheader("\U0001f5c4\ufe0f Limpeza de Dados")
        st.caption("Use com cautela — esta ação **não pode ser desfeita**.")
        st.divider()

        if st.button("\u26a0\ufe0f Limpar Banco de Dados", type="secondary", key="btn_limpar_inicio"):
            st.session_state["limpar_confirmacao_pendente"] = True

        if st.session_state.get("limpar_confirmacao_pendente"):
            st.warning(
                "**Tem certeza? Isso apagará todas as OFs e Corridas!**\n\n"
                "Esta operação é irreversível."
            )
            col_confirma, col_cancela = st.columns(2)
            with col_confirma:
                if st.button("\U0001f5d1\ufe0f Sim, apagar tudo", type="primary", key="btn_limpar_confirmar"):
                    try:
                        from sqlalchemy import text as _text
                        with db_session() as db:
                            db.execute(_text("DELETE FROM certificado_peca"))
                            db.execute(_text("DELETE FROM ordem_entrega"))
                            db.execute(_text("DELETE FROM ordem_fabricacao"))
                            db.execute(_text("DELETE FROM corrida"))
                        st.session_state["limpar_confirmacao_pendente"] = False
                        st.session_state["limpar_sucesso"] = True
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao limpar o banco: {exc}")
            with col_cancela:
                if st.button("\u21a9\ufe0f Cancelar", key="btn_limpar_cancelar"):
                    st.session_state["limpar_confirmacao_pendente"] = False
                    st.rerun()

        if st.session_state.get("limpar_sucesso"):
            st.success("\u2705 Banco de dados resetado com sucesso!")
            if st.button("Fechar", key="btn_limpar_fechar"):
                st.session_state["limpar_sucesso"] = False
                st.rerun()


def tela_consulta_op():
    st.header("🔍 Busca de Rastreabilidade")
    op_para_buscar = st.text_input("Digite o número da OP:")
    if op_para_buscar:
        with sqlite3.connect('fundicao.db') as conn:
            query = f"SELECT * FROM corridas WHERE numero_op = '{op_para_buscar}'"
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                st.success(f"Encontramos {len(df)} registros para a OP {op_para_buscar}")
                st.dataframe(formatar_datas_br(df))
            else:
                st.warning("Nenhuma OP encontrada com este número.")


# ---------------------------------------------------------------------------
# Mapeamentos: coluna da planilha → coluna no banco (schema fundicao_schema.sql)
# ---------------------------------------------------------------------------

# fabricacao.ordem_fabricacao
OF_COLUMN_MAP: dict[str, str] = {
    # Planilha pode usar qualquer um dos aliases abaixo
    "numero_of":              "numero_of",
    "nº of":                  "numero_of",
    "of":                     "numero_of",
    "numero_nn":              "numero_nn",
    "nn":                     "numero_nn",
    "nn°":                    "numero_nn",
    "nome_cliente":           "nome_cliente",
    "cliente":                "nome_cliente",
    "data_abertura_pedido":   "data_abertura_pedido",
    "data abertura":          "data_abertura_pedido",
    "data_abertura":          "data_abertura_pedido",
    "prazo_entrega_pedido":   "prazo_entrega_pedido",
    "prazo entrega":          "prazo_entrega_pedido",
    "prazo_entrega":          "prazo_entrega_pedido",
    "numero_pedido":          "numero_pedido",
    "pedido":                 "numero_pedido",
    "numero_modelo":          "numero_modelo",
    "modelo":                 "numero_modelo",
    "descricao_peca":         "descricao_peca",
    "descrição":              "descricao_peca",
    "descricao":              "descricao_peca",
    "numero_desenho":         "numero_desenho",
    "desenho":                "numero_desenho",
    "peso_liquido_kg":        "peso_liquido_kg",
    "peso liquido":           "peso_liquido_kg",
    "peso líquido":           "peso_liquido_kg",
    "peso_bruto_kg":          "peso_bruto_kg",
    "peso bruto":             "peso_bruto_kg",
    "liga":                   "liga",
    "norma":                  "norma",
    "qtd_pecas_pedido":       "qtd_pecas_pedido",
    "qtd pedido":             "qtd_pecas_pedido",
    "qtd_pedido":             "qtd_pecas_pedido",
    "qtd_fundida":            "qtd_fundida",
    "qtd fundida":            "qtd_fundida",
    "qtd_expedida":           "qtd_expedida",
    "qtd expedida":           "qtd_expedida",
    "valor_unitario":         "valor_unitario",
    "valor unitario":         "valor_unitario",
    "valor unitário":         "valor_unitario",
    "valor_total":            "valor_total",
    "valor total":            "valor_total",
    "condicao_modelo":        "condicao_modelo",
    "condição modelo":        "condicao_modelo",
    "condicao modelo":        "condicao_modelo",
    "observacoes":            "observacoes",
    "observações":            "observacoes",
    # OE — número da ordem de entrega (pode ter múltiplas colunas: oe1, oe2...)
    "numero_oe":              "numero_oe",
    "nº oe":                  "numero_oe",
    "oe":                     "numero_oe",
    "ordem de entrega":       "numero_oe",
    "ordem_entrega":          "numero_oe",
    # Certificado
    "numero_certificado":     "numero_certificado",
    "nº certificado":         "numero_certificado",
    "certificado":            "numero_certificado",
    "cert":                   "numero_certificado",
}

# Colunas obrigatórias na tabela ordem_fabricacao
OF_REQUIRED = {"numero_of", "nome_cliente", "data_abertura_pedido"}

# corridas.corrida
CORRIDA_COLUMN_MAP: dict[str, str] = {
    "data_fusao":                   "data_fusao",
    "data fusão":                   "data_fusao",
    "data fusao":                   "data_fusao",
    "data":                         "data_fusao",
    "numero_corrida":               "numero_corrida",
    "corrida":                      "numero_corrida",
    "nº corrida":                   "numero_corrida",
    "nome_cliente":                 "nome_cliente",
    "cliente":                      "nome_cliente",
    "numero_ordem_fabricacao":      "numero_ordem_fabricacao",
    "numero of":                    "numero_ordem_fabricacao",
    "nº of":                        "numero_ordem_fabricacao",
    "of":                           "numero_ordem_fabricacao",
    # coluna da planilha de corridas exportada do sistema
    "ordem_fabricacao_id":          "numero_ordem_fabricacao",
    "nº da of":                     "numero_ordem_fabricacao",
    "numero da of":                 "numero_ordem_fabricacao",
    "qtd_pecas_fundidas":           "qtd_pecas_fundidas",
    "qtd fundidas":                 "qtd_pecas_fundidas",
    "qtd_fundidas":                 "qtd_pecas_fundidas",
    "qtd peças fundidas":           "qtd_pecas_fundidas",
    "serie_pecas_fundidas":         "serie_pecas_fundidas",
    "série":                        "serie_pecas_fundidas",
    "serie":                        "serie_pecas_fundidas",
    "liga":                         "liga",
    "norma":                        "norma",
    # Elementos químicos — aceitos como colunas individuais na planilha
    "c":   "C",   "si":  "Si",  "mn":  "Mn",  "p":   "P",
    "s":   "S",   "cr":  "Cr",  "ni":  "Ni",  "mo":  "Mo",
    "cu":  "Cu",  "w":   "W",   "nb":  "Nb",  "b":   "B",
    "ce":  "CE",  "v":   "V",   "co":  "Co",  "fe":  "Fe",
    "n":   "N",   "mg":  "Mg",
}

CORRIDA_REQUIRED = {"data_fusao", "numero_corrida", "nome_cliente"}

ELEMENTOS_QUIMICOS_SET = frozenset([
    "C", "Si", "Mn", "P", "S", "Cr", "Ni", "Mo",
    "Cu", "W", "Nb", "B", "CE", "V", "Co", "Fe", "N", "Mg",
])


def _normalizar_colunas(df: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    """Renomeia colunas do DataFrame usando o mapa (case-insensitive).
    Faz strip() nos nomes das colunas antes de comparar — cobre colunas
    com espaços extras como 'serie_pecas_fundidas ' ou 'numero_of '.
    """
    # Primeiro normaliza os próprios nomes das colunas (remove espaços)
    df = df.rename(columns=lambda c: c.strip())
    rename = {}
    for col in df.columns:
        chave = col.strip().lower()
        if chave in mapa:
            rename[col] = mapa[chave]
    return df.rename(columns=rename)



# ---------------------------------------------------------------------------
# Limpeza defensiva de DataFrame antes da importação
# ---------------------------------------------------------------------------

# Colunas numéricas inteiras das OFs
_OF_COLS_INT   = ["qtd_pecas_pedido", "qtd_fundida", "qtd_expedida"]
# Colunas numéricas decimais das OFs
_OF_COLS_FLOAT = ["peso_liquido_kg", "peso_bruto_kg", "valor_unitario", "valor_total"]
# Colunas de texto das OFs (recebem fillna(""))
_OF_COLS_TEXT  = [
    "numero_of", "numero_nn", "nome_cliente", "numero_pedido", "numero_modelo",
    "descricao_peca", "numero_desenho", "liga", "norma", "condicao_modelo", "observacoes",
    "numero_oe", "numero_certificado",
]

# Colunas numéricas inteiras das Corridas
_CORRIDA_COLS_INT   = ["qtd_pecas_fundidas"]
# Colunas decimais das Corridas (elementos químicos incluídos dinamicamente)
_CORRIDA_COLS_FLOAT = list(ELEMENTOS_QUIMICOS_SET)
# Colunas de texto das Corridas
_CORRIDA_COLS_TEXT  = [
    "numero_corrida", "nome_cliente", "numero_ordem_fabricacao",
    "serie_pecas_fundidas", "liga", "norma",
]

_RE_CANCELADO = re.compile(r"^\s*cancelado\s*$", re.IGNORECASE)


def _limpar_df(
    df: pd.DataFrame,
    cols_int: list[str],
    cols_float: list[str],
    cols_text: list[str],
) -> pd.DataFrame:
    """
    Limpeza defensiva compatível com pandas 3.x / Python 3.14.

    Passo 1 — Colunas numéricas: converte tudo para float64 primeiro
              (neutraliza Arrow-backed strings e tipos incompatíveis),
              substitui "cancelado" por NaN, depois preenche com 0.
    Passo 2 — Colunas de texto: converte para object dtype antes do fillna
              (evita TypeError ao atribuir string em coluna Arrow string).
    Passo 3 — Conversão final: int → Int64, float → float64.
    """
    df = df.copy()

    # Passo 1 — colunas numéricas: normaliza dtype para float64 antes de qualquer operação
    for col in cols_int + cols_float:
        if col not in df.columns:
            continue
        # Converte para string, detecta "cancelado", depois força numérico
        ser = df[col].astype(str)
        mask = ser.str.match(_RE_CANCELADO)
        # Zera os "cancelado" substituindo por NaN na série numérica
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[mask, col] = float("nan")

    # Passo 2 — preenche NaN
    for col in cols_text:
        if col in df.columns:
            # Força object dtype antes do fillna para evitar Arrow string TypeError
            df[col] = df[col].astype(object).fillna("")
    for col in cols_int + cols_float:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Passo 3 — conversão explícita de tipos
    for col in cols_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round(0).astype("Int64")
    for col in cols_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    return df


def _importar_ofs(arquivo) -> None:
    """Lê a planilha de OFs e insere em fabricacao.ordem_fabricacao via SQLAlchemy."""
    df = pd.read_excel(arquivo)
    df = _normalizar_colunas(df, OF_COLUMN_MAP)
    df = _limpar_df(df, _OF_COLS_INT, _OF_COLS_FLOAT, _OF_COLS_TEXT)

    # Normalização de datas logo após a leitura:
    # - gravação: dt.date (Python date puro, sem 00:00:00)
    # - exibição: strftime DD/MM/AAAA em coluna auxiliar
    _COLS_DATA_OF = ["data_abertura_pedido", "prazo_entrega_pedido"]
    for _col in _COLS_DATA_OF:
        if _col in df.columns:
            _parsed = pd.to_datetime(df[_col], errors="coerce")
            df[_col] = _parsed.dt.date                          # gravação limpa
            df[f"{_col}__exib"] = _parsed.dt.strftime("%d/%m/%Y")  # só para preview

    faltando = OF_REQUIRED - set(df.columns)
    if faltando:
        st.error(
            f"Colunas obrigatórias não encontradas na planilha: **{', '.join(sorted(faltando))}**\n\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
        return

    # DataFrame de prévia: substitui datas brutas pelas formatadas e oculta auxiliares
    df_exib = df.drop(columns=[c for c in df.columns if c.endswith("__exib")]).copy()
    for _col in _COLS_DATA_OF:
        if f"{_col}__exib" in df.columns:
            df_exib[_col] = df[f"{_col}__exib"]

    st.info(f"Prévia — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    st.session_state["_df_imp_ofs"] = df
    if not st.button("✅ Confirmar importação de OFs", key="btn_confirmar_ofs", type="primary"):
        return
    df = st.session_state.get("_df_imp_ofs", df)
    barra = st.progress(0, text="Iniciando importação de OFs...")
    total_linhas = max(len(df), 1)

    # Guarda de segurança extra: força tipos antes do loop (cobre NaN/NaT residuais)
    for _c in _OF_COLS_INT:
        if _c in df.columns:
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0).round(0).astype('Int64')
    if 'numero_nn' in df.columns:
        _DASH_SET = frozenset(["-", "—", "–", "nan", "none", "n/a", ""])
        df['numero_nn'] = df['numero_nn'].apply(
            lambda v: None if (pd.isna(v) if not isinstance(v, str) else str(v).strip().lower() in _DASH_SET) else str(v).strip()
        )
    for _c in _OF_COLS_FLOAT:
        if _c in df.columns:
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0.0).astype(float)
    for _c in ['data_abertura_pedido', 'prazo_entrega_pedido']:
        if _c in df.columns:
            df[_c] = df[_c].apply(lambda v: None if (v is None or (isinstance(v, float) and pd.isna(v))) else v)

    now = datetime.now().astimezone()
    inseridos = 0
    erros = []

    for _, row in df.iterrows():
        try:
            def _val(col, default=None):
                v = row.get(col, default)
                # pd.NA (tipo Int64) não é float — pd.isna() cobre todos os casos nulos
                try:
                    if pd.isna(v):
                        return default
                except (TypeError, ValueError):
                    pass
                return v

            def _int(col):
                """int nativo garantido — nunca pd.NA / None / NaN."""
                v = _val(col, 0)
                try:
                    return int(v) if v is not None else 0
                except (ValueError, TypeError):
                    return 0

            def _dec(col):
                """Decimal ou None — nunca pd.NA / NaN."""
                v = _val(col, None)
                if v is None:
                    return None
                try:
                    f = float(v)
                    return Decimal(str(f)) if f else None
                except (ValueError, TypeError):
                    return None

            def _date(col):
                v = _val(col)
                if v is None:
                    return None
                # Após normalização, já chega como Python date; aceita também datetime/Timestamp
                if isinstance(v, date) and not isinstance(v, datetime):
                    return v
                if isinstance(v, datetime):
                    return v.date()
                try:
                    return pd.to_datetime(v).date()
                except Exception:
                    return None

            of = OrdemFabricacao(
                numero_of=str(_val("numero_of", "")).strip(),
                numero_nn=str(_val("numero_nn", "") or "").strip() or None,
                nome_cliente=str(_val("nome_cliente", "")).strip(),
                data_abertura_pedido=_date("data_abertura_pedido") or date.today(),
                prazo_entrega_pedido=_date("prazo_entrega_pedido"),
                numero_pedido=str(_val("numero_pedido", "") or "").strip() or None,
                numero_modelo=str(_val("numero_modelo", "") or "").strip() or None,
                descricao_peca=str(_val("descricao_peca", "") or "").strip() or None,
                numero_desenho=str(_val("numero_desenho", "") or "").strip() or None,
                peso_liquido_kg=_dec("peso_liquido_kg"),
                peso_bruto_kg=_dec("peso_bruto_kg"),
                liga=str(_val("liga", "") or "").strip() or None,
                norma=str(_val("norma", "") or "").strip() or None,
                qtd_pecas_pedido=_int("qtd_pecas_pedido"),
                qtd_fundida=_int("qtd_fundida"),
                qtd_expedida=_int("qtd_expedida"),
                valor_unitario=_dec("valor_unitario"),
                valor_total=_dec("valor_total"),
                condicao_modelo=str(_val("condicao_modelo", "") or "").strip() or None,
                observacoes=str(_val("observacoes", "") or "").strip() or None,
                criado_em=now,
                atualizado_em=now,
            )

            # ── OE e Certificados: células podem ter múltiplos valores ──
            # Ex: "(160-10) (176-28) (183-14)" → 3 registros separados
            _DASH_IMPORT = frozenset(["-", "—", "–", "nan", "none", "n/a", ""])

            def _extrair_multiplos(col):
                """Divide célula com múltiplos valores separados por espaço.
                Ex: '(160-10) (176-28)' → ['(160-10)', '(176-28)']
                Também aceita valores únicos simples.
                """
                v = _val(col)
                if v is None:
                    return []
                s = str(v).strip()
                if not s or s.lower() in _DASH_IMPORT:
                    return []
                import re as _re
                # Divide por espaço mas respeita grupos entre parênteses
                # Padrão: qualquer token não-espaço
                tokens = _re.findall(r'\S+', s)
                # Agrupa tokens que fazem parte do mesmo item entre parênteses
                # Ex: "(160-10)" é um token; "160-10" também
                # Junta tokens se o anterior abre parêntese mas não fecha
                result = []
                buf = ""
                for tok in tokens:
                    buf = (buf + " " + tok).strip() if buf else tok
                    if buf.count("(") == buf.count(")"):
                        result.append(buf)
                        buf = ""
                if buf:
                    result.append(buf)
                return [r for r in result if r.lower() not in _DASH_IMPORT]

            oe_nums   = _extrair_multiplos("numero_oe")
            cert_nums = _extrair_multiplos("numero_certificado")

            # Suporte adicional a colunas oe1, oe2... cert1, cert2...
            for _sfx in range(1, 11):
                for _alias in [f"oe{_sfx}", f"numero_oe{_sfx}"]:
                    for v in _extrair_multiplos(_alias):
                        if v not in oe_nums:
                            oe_nums.append(v)
                for _alias in [f"cert{_sfx}", f"numero_certificado{_sfx}"]:
                    for v in _extrair_multiplos(_alias):
                        if v not in cert_nums:
                            cert_nums.append(v)

            for noe in oe_nums:
                of.ordens_entrega.append(
                    OrdemEntrega(numero_oe=noe, qtd_pecas=1, criado_em=now)
                )
            for ncert in cert_nums:
                of.certificados.append(
                    CertificadoPeca(numero_certificado=ncert, qtd_pecas=1, criado_em=now)
                )

            with db_session() as db:
                db.add(of)
            inseridos += 1
        except IntegrityError:
            erros.append(f"OF duplicada: {row.get('numero_of', '?')}")
        except Exception as exc:
            erros.append(f"Linha {_ + 2}: {exc}")

    if inseridos:
        st.success(f"**{inseridos}** Ordem(ns) de Fabricação importada(s) com sucesso!")
    for e in erros:
        st.warning(e)


def _importar_corridas(arquivo) -> None:
    """Lê a planilha de Corridas e insere em corridas.corrida via SQLAlchemy."""
    df = pd.read_excel(arquivo)
    df = _normalizar_colunas(df, CORRIDA_COLUMN_MAP)
    df = _limpar_df(df, _CORRIDA_COLS_INT, _CORRIDA_COLS_FLOAT, _CORRIDA_COLS_TEXT)

    # Normalização de datas logo após a leitura:
    # - gravação: dt.date (Python date puro, sem 00:00:00)
    # - exibição: strftime DD/MM/AAAA em coluna auxiliar
    _COLS_DATA_CORRIDA = ["data_fusao"]
    for _col in _COLS_DATA_CORRIDA:
        if _col in df.columns:
            _parsed = pd.to_datetime(df[_col], errors="coerce")
            df[_col] = _parsed.dt.date                              # gravação limpa
            df[f"{_col}__exib"] = _parsed.dt.strftime("%d/%m/%Y")  # só para preview

    faltando = CORRIDA_REQUIRED - set(df.columns)
    if faltando:
        st.error(
            f"Colunas obrigatórias não encontradas na planilha: **{', '.join(sorted(faltando))}**\n\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
        return

    # DataFrame de prévia: substitui datas brutas pelas formatadas e oculta auxiliares
    df_exib = df.drop(columns=[c for c in df.columns if c.endswith("__exib")]).copy()
    for _col in _COLS_DATA_CORRIDA:
        if f"{_col}__exib" in df.columns:
            df_exib[_col] = df[f"{_col}__exib"]

    st.info(f"Prévia — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    st.session_state["_df_imp_corridas"] = df
    if not st.button("✅ Confirmar importação de Corridas", key="btn_confirmar_corridas", type="primary"):
        return
    df = st.session_state.get("_df_imp_corridas", df)
    barra = st.progress(0, text="Iniciando importação de Corridas...")
    total_linhas = max(len(df), 1)

    # Guarda de segurança extra para Corridas
    for _c in _CORRIDA_COLS_INT:
        if _c in df.columns:
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0).round(0).astype('Int64')
    for _c in list(ELEMENTOS_QUIMICOS_SET):
        if _c in df.columns:
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0.0).astype(float)
    if 'data_fusao' in df.columns:
        df['data_fusao'] = df['data_fusao'].apply(
            lambda v: None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
        )

    now = datetime.now().astimezone()
    inseridos = 0
    erros = []

    for _, row in df.iterrows():
        try:
            def _val(col, default=None):
                v = row.get(col, default)
                # pd.NA (tipo Int64) não é float — pd.isna() cobre todos os casos nulos
                try:
                    if pd.isna(v):
                        return default
                except (TypeError, ValueError):
                    pass
                return v

            def _int(col):
                """int nativo garantido — nunca pd.NA / None / NaN."""
                v = _val(col, 0)
                try:
                    return int(v) if v is not None else 0
                except (ValueError, TypeError):
                    return 0

            def _dec(col):
                """Decimal ou None — nunca pd.NA / NaN."""
                v = _val(col, None)
                if v is None:
                    return None
                try:
                    f = float(v)
                    return Decimal(str(f)) if f else None
                except (ValueError, TypeError):
                    return None

            def _date(col):
                v = _val(col)
                if v is None:
                    return None
                # Após normalização, já chega como Python date; aceita também datetime/Timestamp
                if isinstance(v, date) and not isinstance(v, datetime):
                    return v
                if isinstance(v, datetime):
                    return v.date()
                try:
                    return pd.to_datetime(v).date()
                except Exception:
                    return None

            # Monta composição química a partir de colunas individuais (se presentes)
            composicao: dict = {}
            for elem in ELEMENTOS_QUIMICOS_SET:
                v = _val(elem)
                if v is not None:
                    try:
                        fv = float(v)
                        if fv > 0:
                            composicao[elem] = fv
                    except (ValueError, TypeError):
                        pass

            # Limpa traços/marcadores de preenchimento que chegam de células vazias
            _DASH_VALS = frozenset(["-", "—", "–", "nan", "none", "n/a", ""])

            def _clean_text(col):
                """Retorna str limpa ou None se for traço/vazio/nulo."""
                v = _val(col)
                if v is None:
                    return None
                s = str(v).strip()
                return None if s.lower() in _DASH_VALS else s

            # nof e serie: None quando célula estava vazia ou continha "—"
            nof = _clean_text("numero_ordem_fabricacao")
            serie = _clean_text("serie_pecas_fundidas")

            of_id = None
            if nof:
                try:
                    with db_session() as db:
                        row_of = db.scalar(
                            select(OrdemFabricacao).where(OrdemFabricacao.numero_of == nof)
                        )
                        if row_of:
                            of_id = row_of.id
                except Exception:
                    pass

            # Chave única real: (corrida, data, OF, série)
            # Permite: mesma corrida com OFs distintas, mesma OF em séries distintas.
            corrida = Corrida(
                data_fusao=_date("data_fusao") or date.today(),
                numero_corrida=str(_val("numero_corrida", "")).strip(),
                nome_cliente=str(_val("nome_cliente", "")).strip(),
                ordem_fabricacao_id=of_id,
                numero_ordem_fabricacao=nof,   # None quando sem OF
                qtd_pecas_fundidas=_int("qtd_pecas_fundidas"),
                serie_pecas_fundidas=serie,    # None quando sem série
                liga=_clean_text("liga"),
                norma=_clean_text("norma"),
                composicao_quimica_pct=composicao,
                criado_em=now,
                atualizado_em=now,
            )
            with db_session() as db:
                db.add(corrida)  # PK = UUID novo → sempre insere linha nova
            inseridos += 1
        except IntegrityError:
            erros.append(
                f"Linha {_ + 2} — corrida \"{row.get('numero_corrida', '?')}\""  
                f" / OF \"{nof or '—'}\" / Série \"{serie or '—'}\": já existe no banco."
            )
        except Exception as exc:
            erros.append(f"Linha {_ + 2}: {exc}")

    if inseridos:
        st.success(f"**{inseridos}** Corrida(s) importada(s) com sucesso!")
    for e in erros:
        st.warning(e)




def _atualizar_ofs(arquivo) -> None:
    """Atualiza OFs existentes e insere novas a partir da planilha."""
    df = pd.read_excel(arquivo)
    df = _normalizar_colunas(df, OF_COLUMN_MAP)
    df = _limpar_df(df, _OF_COLS_INT, _OF_COLS_FLOAT, _OF_COLS_TEXT)

    _COLS_DATA_OF = ["data_abertura_pedido", "prazo_entrega_pedido"]
    for _col in _COLS_DATA_OF:
        if _col in df.columns:
            _parsed = pd.to_datetime(df[_col], errors="coerce")
            df[_col] = _parsed.dt.date
            df[f"{_col}__exib"] = _parsed.dt.strftime("%d/%m/%Y")

    faltando = OF_REQUIRED - set(df.columns)
    if faltando:
        st.error(f"Colunas obrigatorias nao encontradas: **{', '.join(sorted(faltando))}**")
        return

    df_exib = df.drop(columns=[c for c in df.columns if c.endswith("__exib")]).copy()
    for _col in _COLS_DATA_OF:
        if f"{_col}__exib" in df.columns:
            df_exib[_col] = df[f"{_col}__exib"]

    st.info(f"Prévia — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    # Salva df no session_state para nao perder apos rerun
    st.session_state["_df_atualizar_ofs"] = df

    if not st.button("✅ Confirmar atualização de OFs", key="btn_confirmar_atualizar_ofs",
                     type="primary"):
        return

    # Recupera df do session_state
    df = st.session_state.get("_df_atualizar_ofs", df)

    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando...")
    total_linhas = max(len(df), 1)

    for _, row in df.iterrows():
        barra.progress(min((_ + 1) / total_linhas, 1.0), text=f"Processando {_ + 1}/{total_linhas}...")
        numero_of = str(row.get("numero_of", "") or "").strip()
        if not numero_of:
            continue

        def _val(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        def _date(c):
            v = row.get(c)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            if isinstance(v, date):
                return v
            try:
                return pd.to_datetime(v).date()
            except Exception:
                return None

        def _int(c):
            v = row.get(c, 0)
            try:
                return int(float(v)) if v is not None and not (isinstance(v, float) and pd.isna(v)) else 0
            except Exception:
                return 0

        def _float(c):
            v = row.get(c)
            try:
                return float(v) if v is not None and not (isinstance(v, float) and pd.isna(v)) else None
            except Exception:
                return None

        barra.progress(min((_ + 1) / total_linhas, 1.0),
                       text=f"Processando {_ + 1}/{total_linhas}...")
        try:
            with db_session() as db:
                of_existente = db.scalar(
                    select(OrdemFabricacao).where(OrdemFabricacao.numero_of == numero_of)
                )

                if of_existente:
                    # Atualiza todos os campos
                    of_existente.numero_nn = str(_val("numero_nn", "") or "").strip() or None
                    of_existente.nome_cliente = str(_val("nome_cliente", "") or "").strip()
                    of_existente.data_abertura_pedido = _date("data_abertura_pedido") or of_existente.data_abertura_pedido
                    of_existente.prazo_entrega_pedido = _date("prazo_entrega_pedido")
                    of_existente.numero_pedido = str(_val("numero_pedido", "") or "").strip() or None
                    of_existente.numero_modelo = str(_val("numero_modelo", "") or "").strip() or None
                    of_existente.descricao_peca = str(_val("descricao_peca", "") or "").strip() or None
                    of_existente.numero_desenho = str(_val("numero_desenho", "") or "").strip() or None
                    of_existente.peso_liquido_kg = _float("peso_liquido_kg")
                    of_existente.peso_bruto_kg = _float("peso_bruto_kg")
                    of_existente.liga = str(_val("liga", "") or "").strip() or None
                    of_existente.norma = str(_val("norma", "") or "").strip() or None
                    of_existente.qtd_pecas_pedido = _int("qtd_pecas_pedido")
                    of_existente.qtd_fundida = _int("qtd_fundida")
                    of_existente.qtd_expedida = _int("qtd_expedida")
                    of_existente.valor_unitario = _float("valor_unitario")
                    of_existente.valor_total = _float("valor_total")
                    of_existente.condicao_modelo = str(_val("condicao_modelo", "") or "").strip() or None
                    of_existente.observacoes = str(_val("observacoes", "") or "").strip() or None
                    of_existente.atualizado_em = now
                    atualizados += 1
                else:
                    # Insere nova OF
                    nova_of = OrdemFabricacao(
                        numero_of=numero_of,
                        numero_nn=str(_val("numero_nn", "") or "").strip() or None,
                        nome_cliente=str(_val("nome_cliente", "") or "").strip(),
                        data_abertura_pedido=_date("data_abertura_pedido") or date.today(),
                        prazo_entrega_pedido=_date("prazo_entrega_pedido"),
                        numero_pedido=str(_val("numero_pedido", "") or "").strip() or None,
                        numero_modelo=str(_val("numero_modelo", "") or "").strip() or None,
                        descricao_peca=str(_val("descricao_peca", "") or "").strip() or None,
                        numero_desenho=str(_val("numero_desenho", "") or "").strip() or None,
                        peso_liquido_kg=_float("peso_liquido_kg"),
                        peso_bruto_kg=_float("peso_bruto_kg"),
                        liga=str(_val("liga", "") or "").strip() or None,
                        norma=str(_val("norma", "") or "").strip() or None,
                        qtd_pecas_pedido=_int("qtd_pecas_pedido"),
                        qtd_fundida=_int("qtd_fundida"),
                        qtd_expedida=_int("qtd_expedida"),
                        valor_unitario=_float("valor_unitario"),
                        valor_total=_float("valor_total"),
                        condicao_modelo=str(_val("condicao_modelo", "") or "").strip() or None,
                        observacoes=str(_val("observacoes", "") or "").strip() or None,
                        criado_em=now,
                        atualizado_em=now,
                    )
                    db.add(nova_of)
                    inseridos += 1
        except Exception as exc:
            erros.append(f"OF {numero_of}: {exc}")

    st.success(f"OFs atualizadas: **{atualizados}** | Novas inseridas: **{inseridos}**")
    if erros:
        st.warning(f"{len(erros)} erro(s):")
        for e in erros[:10]:
            st.caption(e)


def _atualizar_corridas(arquivo) -> None:
    """Atualiza corridas existentes e insere novas a partir da planilha."""
    df = pd.read_excel(arquivo)
    df = _normalizar_colunas(df, CORRIDA_COLUMN_MAP)
    df = _limpar_df(df, _CORRIDA_COLS_INT, [], _CORRIDA_COLS_TEXT)

    _COLS_DATA_C = ["data_fusao"]
    for _col in _COLS_DATA_C:
        if _col in df.columns:
            _parsed = pd.to_datetime(df[_col], errors="coerce")
            df[_col] = _parsed.dt.date

    faltando = CORRIDA_REQUIRED - set(df.columns)
    if faltando:
        st.error(f"Colunas obrigatorias nao encontradas: **{', '.join(sorted(faltando))}**")
        return

    st.info(f"Previa — {len(df)} linhas encontradas:")
    st.dataframe(df.head(), height=400, use_container_width=True, hide_index=True)

    st.session_state["_df_atualizar_corridas"] = df
    if not st.button("✅ Confirmar atualização de Corridas", key="btn_confirmar_atualizar_corridas", type="primary"):
        return
    df = st.session_state.get("_df_atualizar_corridas", df)

    inseridos = 0
    atualizados = 0
    ignorados = 0
    erros = []
    now = datetime.now().astimezone()
    barra = st.progress(0, text="Iniciando atualização de Corridas...")
    total_linhas = max(len(df), 1)

    ELEMENTOS_Q = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","B","CE","V","Co","Fe","N","Mg"]

    for _, row in df.iterrows():
        def _val(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        def _date(c):
            v = row.get(c)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            if isinstance(v, date):
                return v
            try:
                return pd.to_datetime(v).date()
            except Exception:
                return None

        numero_corrida = str(_val("numero_corrida", "")).strip()
        nome_cliente = str(_val("nome_cliente", "")).strip()
        data_fusao = _date("data_fusao")
        nof = str(_val("numero_ordem_fabricacao", "") or "").strip() or None
        serie = str(_val("serie_pecas_fundidas", "") or "").strip() or None

        if not numero_corrida or not nome_cliente or not data_fusao:
            ignorados += 1
            continue

        # Composicao quimica
        composicao = {}
        for el in ELEMENTOS_Q:
            v = row.get(el)
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                try:
                    fv = float(v)
                    if fv > 0:
                        composicao[el] = fv
                except Exception:
                    pass

        try:
            with db_session() as db:
                # Busca pela chave unica: corrida + data + OF + serie
                from sqlalchemy import and_
                corrida_existente = db.scalar(
                    select(Corrida).where(
                        and_(
                            Corrida.numero_corrida == numero_corrida,
                            Corrida.data_fusao == data_fusao,
                            Corrida.numero_ordem_fabricacao == nof,
                            Corrida.serie_pecas_fundidas == serie,
                        )
                    )
                )

                if corrida_existente:
                    # Atualiza todos os campos
                    corrida_existente.nome_cliente = nome_cliente
                    corrida_existente.liga = str(_val("liga", "") or "").strip() or None
                    corrida_existente.norma = str(_val("norma", "") or "").strip() or None
                    corrida_existente.composicao_quimica_pct = composicao
                    try:
                        corrida_existente.qtd_pecas_fundidas = int(float(_val("qtd_pecas_fundidas", 0)))
                    except Exception:
                        pass
                    corrida_existente.atualizado_em = now
                    atualizados += 1
                else:
                    # Busca OF vinculada
                    of_id = None
                    if nof:
                        try:
                            row_of = db.scalar(
                                select(OrdemFabricacao).where(OrdemFabricacao.numero_of == nof)
                            )
                            if row_of:
                                of_id = row_of.id
                        except Exception:
                            pass

                    nova_corrida = Corrida(
                        data_fusao=data_fusao,
                        numero_corrida=numero_corrida,
                        nome_cliente=nome_cliente,
                        ordem_fabricacao_id=of_id,
                        numero_ordem_fabricacao=nof,
                        qtd_pecas_fundidas=int(float(_val("qtd_pecas_fundidas", 0))),
                        serie_pecas_fundidas=serie,
                        liga=str(_val("liga", "") or "").strip() or None,
                        norma=str(_val("norma", "") or "").strip() or None,
                        composicao_quimica_pct=composicao,
                        criado_em=now,
                        atualizado_em=now,
                    )
                    db.add(nova_corrida)
                    inseridos += 1
        except Exception as exc:
            erros.append(f"Corrida {numero_corrida} / {data_fusao}: {exc}")

    st.success(f"Corridas atualizadas: **{atualizados}** | Novas inseridas: **{inseridos}** | Ignoradas: **{ignorados}**")
    if erros:
        st.warning(f"{len(erros)} erro(s):")
        for e in erros[:10]:
            st.caption(e)



def _importar_oes(arquivo) -> None:
    """Importa OEs de planilha Excel para a tabela oe_item."""
    import uuid as _uuid
    df = pd.read_excel(arquivo)
    df.columns = [c.strip().lower().replace(' ','_') for c in df.columns]

    # Mapeia colunas
    col_map = {
        'numero_oe': ['numero_oe','noe','oe','num_oe'],
        'num_of':    ['num_of','numero_of','of','nof'],
        'nome_cliente': ['nome_cliente','cliente'],
        'num_pedido':['num_pedido','numero_pedido','pedido'],
        'referencia':['referencia','ref'],
        'liga':      ['liga'],
        'corrida':   ['corrida','corr'],
        'certificado':['certificado','cert'],
        'cod_peca':  ['cod_peca','codigo_peca','codigo'],
        'descricao': ['descricao','desc'],
        'peso_unit': ['peso_unit','peso_unitario','peso'],
        'qtd':       ['qtd','quantidade','qtde'],
        'serie':     ['serie'],
        'preco_unit':['preco_unit','preco_unitario','preco_un'],
        'preco_total':['preco_total'],
        'observacoes':['observacoes','obs'],
    }
    for dest, srcs in col_map.items():
        if dest not in df.columns:
            for s in srcs:
                if s in df.columns:
                    df[dest] = df[s]
                    break

    if 'numero_oe' not in df.columns or 'num_of' not in df.columns:
        st.error("Colunas obrigatórias não encontradas: `numero_oe`, `num_of`")
        return

    st.info(f"Prévia — {len(df)} linhas encontradas:")
    st.dataframe(df.head(), use_container_width=True, hide_index=True)

    st.session_state["_df_imp_oes"] = df
    if not st.button("✅ Confirmar importação de OEs", key="btn_confirmar_oes", type="primary"):
        return
    df = st.session_state.get("_df_imp_oes", df)

    inseridos = erros = 0
    now = datetime.now().astimezone()
    from fundicao_db import engine as _eng_oe_imp
    from sqlalchemy import text as _text_oe_imp

    for _, row in df.iterrows():
        def _v(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        try:
            with _eng_oe_imp.begin() as conn:
                conn.execute(_text_oe_imp("""
                    INSERT INTO oe_item (
                        id, numero_oe, num_oe_seq, nome_cliente,
                        num_pedido, num_of, referencia, liga, corrida,
                        certificado, cod_peca, descricao,
                        peso_unit, qtd, serie, preco_unit, preco_total,
                        observacoes, criado_em
                    ) VALUES (
                        :id, :noe, :seq, :cli, :ped, :of, :ref,
                        :liga, :corr, :cert, :cod, :desc,
                        :peso, :qtd, :serie, :pu, :pt, :obs, :now
                    )
                """), {
                    "id":   str(_uuid.uuid4()),
                    "noe":  str(_v("numero_oe","")),
                    "seq":  int(float(_v("numero_oe",0))) if str(_v("numero_oe","")).isdigit() else 0,
                    "cli":  str(_v("nome_cliente","")),
                    "ped":  str(_v("num_pedido","")),
                    "of":   str(_v("num_of","")),
                    "ref":  str(_v("referencia","")),
                    "liga": str(_v("liga","")),
                    "corr": str(_v("corrida","")),
                    "cert": str(_v("certificado","")),
                    "cod":  str(_v("cod_peca","")),
                    "desc": str(_v("descricao","")),
                    "peso": float(_v("peso_unit",0) or 0),
                    "qtd":  int(float(_v("qtd",0) or 0)),
                    "serie":str(_v("serie","")),
                    "pu":   float(_v("preco_unit",0) or 0),
                    "pt":   float(_v("preco_total",0) or 0),
                    "obs":  str(_v("observacoes","")),
                    "now":  now,
                })
            inseridos += 1
        except Exception as e:
            erros += 1

    barra.progress(1.0, text="Concluído!")
    st.success(f"OEs importadas: **{inseridos}** | Erros: **{erros}**")


def _atualizar_oes(arquivo) -> None:
    """Atualiza OEs existentes e insere novas da planilha."""
    import uuid as _uuid
    df = pd.read_excel(arquivo)
    df.columns = [c.strip().lower().replace(' ','_') for c in df.columns]

    col_map = {
        'numero_oe': ['numero_oe','noe','oe'],
        'num_of':    ['num_of','numero_of','of'],
        'nome_cliente': ['nome_cliente','cliente'],
        'qtd':       ['qtd','quantidade','qtde'],
        'serie':     ['serie'],
        'corrida':   ['corrida','corr'],
        'certificado':['certificado','cert'],
        'observacoes':['observacoes','obs'],
    }
    for dest, srcs in col_map.items():
        if dest not in df.columns:
            for s in srcs:
                if s in df.columns:
                    df[dest] = df[s]; break

    if 'numero_oe' not in df.columns or 'num_of' not in df.columns:
        st.error("Colunas obrigatórias: `numero_oe`, `num_of`")
        return

    st.info(f"Prévia — {len(df)} linhas:")
    st.dataframe(df.head(), use_container_width=True, hide_index=True)

    st.session_state["_df_atu_oes"] = df
    if not st.button("✅ Confirmar atualização de OEs", key="btn_atualizar_oes", type="primary"):
        return
    df = st.session_state.get("_df_atu_oes", df)

    atualizados = inseridos = erros = 0
    now = datetime.now().astimezone()
    from fundicao_db import engine as _eng_upd_oe
    from sqlalchemy import text as _text_upd_oe

    for _, row in df.iterrows():
        barra.progress(min((_ + 1) / total_linhas, 1.0), text=f"Processando {_ + 1}/{total_linhas}...")
        def _v(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        noe = str(_v("numero_oe","")).strip()
        nof = str(_v("num_of","")).strip()
        if not noe or not nof:
            continue

        try:
            with _eng_upd_oe.begin() as conn:
                existe = conn.execute(_text_upd_oe(
                    "SELECT id FROM oe_item WHERE numero_oe=:noe AND num_of=:nof LIMIT 1"
                ), {"noe": noe, "nof": nof}).fetchone()

                if existe:
                    conn.execute(_text_upd_oe("""
                        UPDATE oe_item SET
                            qtd=:qtd, serie=:serie, corrida=:corr,
                            certificado=:cert, observacoes=:obs
                        WHERE numero_oe=:noe AND num_of=:nof
                    """), {
                        "noe":  noe, "nof": nof,
                        "qtd":  int(float(_v("qtd",0) or 0)),
                        "serie":str(_v("serie","")),
                        "corr": str(_v("corrida","")),
                        "cert": str(_v("certificado","")),
                        "obs":  str(_v("observacoes","")),
                    })
                    atualizados += 1
                else:
                    import uuid as _uuid2
                    conn.execute(_text_upd_oe("""
                        INSERT INTO oe_item (id, numero_oe, num_of, nome_cliente,
                            qtd, serie, corrida, certificado, observacoes, criado_em)
                        VALUES (:id,:noe,:nof,:cli,:qtd,:serie,:corr,:cert,:obs,:now)
                    """), {
                        "id":   str(_uuid2.uuid4()),
                        "noe":  noe, "nof": nof,
                        "cli":  str(_v("nome_cliente","")),
                        "qtd":  int(float(_v("qtd",0) or 0)),
                        "serie":str(_v("serie","")),
                        "corr": str(_v("corrida","")),
                        "cert": str(_v("certificado","")),
                        "obs":  str(_v("observacoes","")),
                        "now":  now,
                    })
                    inseridos += 1
        except Exception as e:
            erros += 1

    barra.progress(1.0, text="Concluído!")
    st.success(f"OEs atualizadas: **{atualizados}** | Novas: **{inseridos}** | Erros: **{erros}**")


def _importar_certificados(arquivo) -> None:
    """Importa Certificados de planilha Excel."""
    import uuid as _uuid
    df = pd.read_excel(arquivo)
    df.columns = [c.strip().lower().replace(' ','_') for c in df.columns]

    col_map = {
        'numero_certificado': ['numero_certificado','certificado','cert','num_cert'],
        'numero_of':          ['numero_of','num_of','of'],
        'nome_cliente':       ['nome_cliente','cliente'],
        'qtd_pecas':          ['qtd_pecas','qtd','quantidade'],
    }
    for dest, srcs in col_map.items():
        if dest not in df.columns:
            for s in srcs:
                if s in df.columns:
                    df[dest] = df[s]; break

    if 'numero_certificado' not in df.columns:
        st.error("Coluna obrigatória não encontrada: `numero_certificado`")
        return

    st.info(f"Prévia — {len(df)} linhas:")
    st.dataframe(df.head(), use_container_width=True, hide_index=True)

    st.session_state["_df_imp_certs"] = df
    if not st.button("✅ Confirmar importação de Certificados", key="btn_confirmar_certs", type="primary"):
        return
    df = st.session_state.get("_df_imp_certs", df)

    inseridos = erros = 0
    now = datetime.now().astimezone()

    for _, row in df.iterrows():
        def _v(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        try:
            with db_session() as db:
                cert = CertificadoPeca(
                    numero_certificado=str(_v("numero_certificado","")),
                    qtd_pecas=int(float(_v("qtd_pecas",0) or 0)),
                    criado_em=now,
                )
                # Vincula OF se existir
                nof = str(_v("numero_of","")).strip()
                if nof:
                    of_obj = db.scalar(select(OrdemFabricacao).where(
                        OrdemFabricacao.numero_of == nof))
                    if of_obj:
                        of_obj.certificados.append(cert)
                    else:
                        db.add(cert)
                else:
                    db.add(cert)
            inseridos += 1
        except Exception as e:
            erros += 1

    barra.progress(1.0, text="Concluído!")
    st.success(f"Certificados importados: **{inseridos}** | Erros: **{erros}**")


def _atualizar_certificados(arquivo) -> None:
    """Atualiza Certificados existentes e insere novos da planilha."""
    import uuid as _uuid
    df = pd.read_excel(arquivo)
    df.columns = [c.strip().lower().replace(' ','_') for c in df.columns]

    col_map = {
        'numero_certificado': ['numero_certificado','certificado','cert'],
        'numero_of':          ['numero_of','num_of','of'],
        'qtd_pecas':          ['qtd_pecas','qtd','quantidade'],
    }
    for dest, srcs in col_map.items():
        if dest not in df.columns:
            for s in srcs:
                if s in df.columns:
                    df[dest] = df[s]; break

    if 'numero_certificado' not in df.columns:
        st.error("Coluna obrigatória: `numero_certificado`")
        return

    st.info(f"Prévia — {len(df)} linhas:")
    st.dataframe(df.head(), use_container_width=True, hide_index=True)

    st.session_state["_df_atu_certs"] = df
    if not st.button("✅ Confirmar atualização de Certificados", key="btn_atualizar_certs", type="primary"):
        return
    df = st.session_state.get("_df_atu_certs", df)

    atualizados = inseridos = erros = 0
    now = datetime.now().astimezone()

    for _, row in df.iterrows():
        def _v(c, d=""):
            v = row.get(c, d)
            return d if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        num_cert = str(_v("numero_certificado","")).strip()
        if not num_cert:
            continue

        try:
            with db_session() as db:
                cert_existente = db.scalar(select(CertificadoPeca).where(
                    CertificadoPeca.numero_certificado == num_cert))

                if cert_existente:
                    cert_existente.qtd_pecas = int(float(_v("qtd_pecas",0) or 0))
                    atualizados += 1
                else:
                    novo_cert = CertificadoPeca(
                        numero_certificado=num_cert,
                        qtd_pecas=int(float(_v("qtd_pecas",0) or 0)),
                        criado_em=now,
                    )
                    nof = str(_v("numero_of","")).strip()
                    if nof:
                        of_obj = db.scalar(select(OrdemFabricacao).where(
                            OrdemFabricacao.numero_of == nof))
                        if of_obj:
                            of_obj.certificados.append(novo_cert)
                        else:
                            db.add(novo_cert)
                    else:
                        db.add(novo_cert)
                    inseridos += 1
        except Exception as e:
            erros += 1

    barra.progress(1.0, text="Concluído!")
    st.success(f"Certificados atualizados: **{atualizados}** | Novos: **{inseridos}** | Erros: **{erros}**")

def tela_importar_excel():
    st.header("📥 Importar Planilhas")
    st.caption("Importe ou atualize dados via planilhas Excel.")

    # --- 1: Importar OFs ---
    st.subheader("1️⃣ Importar Ordens de Fabricação")
    st.caption(
        "Colunas obrigatórias: `numero_of`, `nome_cliente`, `data_abertura_pedido`. "
        "Demais colunas são opcionais."
    )
    arquivo_of = st.file_uploader(
        "Selecione a planilha de **OFs** (.xlsx)",
        type=["xlsx"], key="uploader_ofs",
    )
    if arquivo_of:
        _importar_ofs(arquivo_of)

    st.divider()

    # --- 2: Atualizar OFs ---
    st.subheader("2️⃣ Atualizar Ordens de Fabricação")
    st.caption(
        "Atualiza OFs já existentes (pelo Nº OP) e insere as novas. Nenhum dado é excluído."
    )
    arquivo_atualizar_of = st.file_uploader(
        "Selecione a planilha de OFs para atualizar (.xlsx)",
        type=["xlsx"], key="uploader_atualizar_ofs",
    )
    if arquivo_atualizar_of:
        _atualizar_ofs(arquivo_atualizar_of)

    st.divider()

    # --- 3: Importar Corridas ---
    st.subheader("3️⃣ Importar Corridas")
    st.caption(
        "Colunas obrigatórias: `data_fusao`, `numero_corrida`, `nome_cliente`."
    )
    arquivo_corrida = st.file_uploader(
        "Selecione a planilha de **Corridas** (.xlsx)",
        type=["xlsx"], key="uploader_corridas",
    )
    if arquivo_corrida:
        _importar_corridas(arquivo_corrida)

    st.divider()

    # --- 4: Atualizar Corridas ---
    st.subheader("4️⃣ Atualizar Corridas")
    st.caption(
        "Atualiza corridas já existentes (pela chave Corrida + Data + OF + Série) "
        "e insere as novas. Nenhum dado é excluído."
    )
    arquivo_atualizar_corrida = st.file_uploader(
        "Selecione a planilha de Corridas para atualizar (.xlsx)",
        type=["xlsx"], key="uploader_atualizar_corridas",
    )
    if arquivo_atualizar_corrida:
        _atualizar_corridas(arquivo_atualizar_corrida)

    st.divider()

    # --- 5: Importar OEs ---
    st.subheader("5️⃣ Importar Ordens de Entrega (OEs)")
    st.caption(
        "Colunas obrigatórias: `numero_oe`, `num_of`, `nome_cliente`. "
        "Insere itens na tabela `oe_item`."
    )
    arquivo_oe = st.file_uploader(
        "Selecione a planilha de **OEs** (.xlsx)",
        type=["xlsx"], key="uploader_oes",
    )
    if arquivo_oe:
        _importar_oes(arquivo_oe)

    st.divider()

    # --- 6: Atualizar OEs ---
    st.subheader("6️⃣ Atualizar Ordens de Entrega (OEs)")
    st.caption(
        "Atualiza OEs já existentes (pelo Nº OE + Nº OF) e insere as novas."
    )
    arquivo_atualizar_oe = st.file_uploader(
        "Selecione a planilha de OEs para atualizar (.xlsx)",
        type=["xlsx"], key="uploader_atualizar_oes",
    )
    if arquivo_atualizar_oe:
        _atualizar_oes(arquivo_atualizar_oe)

    st.divider()

    # --- 7: Importar Certificados ---
    st.subheader("7️⃣ Importar Certificados")
    st.caption(
        "Colunas obrigatórias: `numero_certificado`, `numero_of`, `nome_cliente`."
    )
    arquivo_cert = st.file_uploader(
        "Selecione a planilha de **Certificados** (.xlsx)",
        type=["xlsx"], key="uploader_certs",
    )
    if arquivo_cert:
        _importar_certificados(arquivo_cert)

    st.divider()

    # --- 8: Atualizar Certificados ---
    st.subheader("8️⃣ Atualizar Certificados")
    st.caption(
        "Atualiza certificados já existentes (pelo Nº Certificado) e insere os novos."
    )
    arquivo_atualizar_cert = st.file_uploader(
        "Selecione a planilha de Certificados para atualizar (.xlsx)",
        type=["xlsx"], key="uploader_atualizar_certs",
    )
    if arquivo_atualizar_cert:
        _atualizar_certificados(arquivo_atualizar_cert)


def _migrar_banco_of_status() -> None:
    """Adiciona coluna status_of à tabela ordem_fabricacao se não existir.
    Usa o caminho real do banco via fundicao_db.DB_PATH."""
    try:
        from fundicao_db import DB_PATH as _FDB_PATH
        import sqlite3 as _sq3
        _con3 = _sq3.connect(str(_FDB_PATH))
        _cols3 = [r[1] for r in _con3.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]
        if "status_of" not in _cols3:
            _con3.execute("ALTER TABLE ordem_fabricacao ADD COLUMN status_of VARCHAR(20) DEFAULT 'Ativa'")
            _con3.commit()
            st.toast("Banco atualizado: coluna status_of adicionada.", icon="🔧")
        _con3.close()
    except Exception as _me:
        pass  # silencioso — não bloqueia o app


def _migrar_banco_corridas() -> None:
    """
    Remove TODOS os índices únicos da tabela corrida, independente do nome.

    Regra de negócio:
    - A mesma corrida pode ter várias OFs diferentes
    - A mesma OF pode aparecer em várias corridas diferentes
    - A série (numero_of + sequência) é única por OF, mas pode se repetir em OFs distintas
    - Portanto: a ÚNICA chave de unicidade é a PK (UUID gerado automaticamente)
    - Nenhum índice único composto é necessário ou correto

    Esta função dropa qualquer índice único existente na tabela corrida,
    independente do nome — cobrindo índices criados pelo ORM, por migrations
    anteriores ou manualmente.
    """
    import sqlalchemy

    def _get_engine():
        try:
            return SessionLocal().bind  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            from fundicao_db import engine as _e
            return _e
        except Exception:
            return None

    engine = _get_engine()
    if engine is None:
        return

    dialect = engine.dialect.name

    try:
        with engine.connect() as conn:
            if dialect == "sqlite":
                # Busca TODOS os índices da tabela corrida no SQLite
                rows = conn.execute(sqlalchemy.text(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='corrida' AND sql IS NOT NULL"
                )).fetchall()

                # Dropa qualquer índice que seja UNIQUE (sql contém "UNIQUE")
                dropped = []
                for name, sql in rows:
                    if sql and "UNIQUE" in sql.upper():
                        conn.execute(sqlalchemy.text(f"DROP INDEX IF EXISTS \"{name}\""))
                        dropped.append(name)

                # Também dropa por nomes conhecidos (caso sql seja NULL para índices implícitos)
                known = ["uq_corridas_numero_data", "uq_corridas_numero_data_of",
                         "ix_corrida_numero_corrida", "uq_corrida"]
                all_names = [r[0] for r in conn.execute(sqlalchemy.text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='corrida'"
                )).fetchall()]
                for name in known:
                    if name in all_names and name not in dropped:
                        conn.execute(sqlalchemy.text(f"DROP INDEX IF EXISTS \"{name}\""))
                        dropped.append(name)

                conn.commit()

            elif dialect == "postgresql":
                # Busca todos os índices únicos da tabela corrida no schema corridas
                rows = conn.execute(sqlalchemy.text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname IN ('corridas', 'fabricacao', 'public') "
                    "AND tablename = 'corrida' "
                    "AND indexdef ILIKE '%UNIQUE%' "
                    "AND indexname NOT ILIKE '%pkey%'"
                )).fetchall()

                for (idx_name,) in rows:
                    for schema in ["corridas", "public"]:
                        conn.execute(sqlalchemy.text(
                            f"DROP INDEX IF EXISTS {schema}.\"{idx_name}\""
                        ))
                conn.commit()

    except Exception:
        pass  # Silencioso: banco pode ainda não existir na primeira execução
    

def main() -> None:
    st.set_page_config(
        page_title="Controle de Fundição",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()
    init_auth_db()
    init_config_db()
    _migrar_banco_of_status()   # garante coluna status_of
    _migrar_banco_corridas()     # garante constraint correta em bancos existentes

    # ── Verificação de login ──────────────────────────────────────────────
    if not tela_login():
        st.stop()

    # ── Logout na sidebar ─────────────────────────────────────────────────
    u = usuario_logado()

    if 'mostrar_importador' not in st.session_state:
        st.session_state.mostrar_importador = False

    if st.session_state.mostrar_importador:
        tela_importar_excel()
        if st.button("🏠 Voltar para Lançamentos"):
            st.session_state.mostrar_importador = False
        return

    with st.sidebar:
        st.header("Sistema de Controle de Fundição")
        # Info do usuário logado + logout
        _u = usuario_logado()
        if _u:
            st.caption(f"👤 **{_u['nome']}**")
            if st.button("🚪 Sair", key="btn_logout"):
                fazer_logout()
                st.rerun()
        ok, msg = ping_database()
        if ok:
            st.success(msg)
        else:
            st.error("Falha ao acessar o banco")
            st.caption(msg)
        st.divider()
        if tem_permissao("importar_excel") and st.button("📥 Importar Planilha Excel"):
            st.session_state.mostrar_importador = True
        # Monta menu de acordo com permissões do usuário
        _opcoes_nav = []
        if tem_permissao("dashboard"):          _opcoes_nav.append("Dashboard")
        if tem_permissao("nova_of"):            _opcoes_nav.append("Nova Ordem de Fabricação")
        if tem_permissao("nova_oe"):            _opcoes_nav.append("Nova Ordem de Entrega")
        if tem_permissao("consulta_oes"):       _opcoes_nav.append("Consulta de OEs")
        if tem_permissao("novo_certificado"):   _opcoes_nav.append("Novo Certificado")
        if tem_permissao("consulta_certs"):     _opcoes_nav.append("Consulta de Certificados")
        if tem_permissao("ensaios_mec"):        _opcoes_nav.append("Ensaios Mecânicos")
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
        )

    if pagina == "Dashboard":
        pagina_dashboard()
    elif pagina == "Nova Ordem de Fabricação":
        pagina_nova_of()
    elif pagina == "Nova Ordem de Entrega":
        pagina_nova_oe()
    elif pagina == "Novo Certificado":
        try:
            from certificados import init_certificados_db as _icd, tela_novo_certificado as _tnc
            _icd()
            _tnc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")
    elif pagina == "Consulta de Certificados":
        try:
            from certificados import init_certificados_db as _icd2, tela_consulta_certificados as _tcc
            _icd2()
            _tcc()
        except Exception as _ec:
            st.error(f"Erro ao carregar certificados: {_ec}")
    elif pagina == "Ensaios Mecânicos":
        try:
            from certificados import init_certificados_db as _icd3, tela_ensaios_mecanicos as _tem
            _icd3()
            _tem()
        except Exception as _ec:
            st.error(f"Erro ao carregar ensaios: {_ec}")
    elif pagina == "Consulta de OEs":
        pagina_consulta_oes()
    elif pagina == "Lançar Corrida":
        pagina_lancar_corrida()
    elif pagina == "Consulta de Rastreabilidade":
        pagina_consulta_rastreabilidade()
    elif pagina == "Consulta de Corridas":
        pagina_consulta_corridas()
    elif pagina == "⚙️ Administração":
        tela_admin_usuarios()
    else:
        pagina_relatorios()


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO: ORDEM DE ENTREGA
# ══════════════════════════════════════════════════════════════════════════════

def _migrar_banco_oe():
    """Garante colunas extras na tabela ordem_entrega (migração não-destrutiva)."""
    try:
        import sqlite3 as _sq
        from fundicao_db import DB_PATH as _FP
        _cx = _sq.connect(str(_FP))
        _cols = {r[1] for r in _cx.execute("PRAGMA table_info(ordem_entrega)").fetchall()}
        extras = {
            "numero_oe_seq": "INTEGER",
            "data_emissao": "DATE",
            "transportadora": "TEXT",
            "placa_veiculo": "TEXT",
            "nota_fiscal": "TEXT",
        }
        for col, tipo in extras.items():
            if col not in _cols:
                _cx.execute(f"ALTER TABLE ordem_entrega ADD COLUMN {col} {tipo}")
        _cx.commit()
        _cx.close()
    except Exception as e:
        pass


def _gerar_pdf_oe(oe_data: dict, of: "OrdemFabricacao") -> bytes:
    """Gera PDF da Ordem de Entrega no formato do último impresso Excel."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=8*mm, bottomMargin=8*mm,
        leftMargin=10*mm, rightMargin=10*mm,
    )
    story = []
    styles = getSampleStyleSheet()
    W = (A4[0] - 20*mm)  # largura útil

    def _p(txt, size=8, bold=False, align=TA_LEFT, color=colors.black):
        style = ParagraphStyle('x', fontName='Helvetica-Bold' if bold else 'Helvetica',
                               fontSize=size, leading=size+2, textColor=color, alignment=align)
        return Paragraph(str(txt) if txt else '', style)

    def _oe_bloco(numero_via: int):
        """Retorna a lista de flowables para uma via da OE."""
        bloco = []

        # Cabeçalho título
        titulo_data = [
            [_p('Metalpoli — Fundição de Precisão', 10, True, TA_CENTER),
             _p(f'ORDEM DE ENTREGA   Nº {oe_data["numero_oe"]} / {numero_via}', 11, True, TA_CENTER)],
        ]
        t_titulo = Table(titulo_data, colWidths=[W*0.5, W*0.5])
        t_titulo.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWHEIGHT', (0,0), (-1,-1), 16),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        bloco.append(t_titulo)

        # Dados do fornecedor e cliente
        fornec = [
            ['Fornecedor:', 'Metalpoli - Fundição de Precisão', '', 'Data Emissão:', str(oe_data.get('data_emissao', ''))],
            ['Endereço:', 'Rua Umbuzeirro Nº 74 — Cidade Satélite — Guarulhos/SP', '', 'Nº da OF:', str(of.numero_of)],
            ['Contato:', 'James Machado   Tel.: (11) 2954-9908   e-mail: comercial@metalpoli.com.br', '', '', ''],
            ['Cliente:', str(of.nome_cliente), '', 'Nº Pedido:', str(of.numero_pedido or '')],
        ]
        col_w = [22*mm, W*0.45, 4*mm, 24*mm, W*0.25]
        t_fornec = Table(fornec, colWidths=col_w)
        t_fornec.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (3,0), (3,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('LINEAFTER', (1,0), (1,-1), 0.3, colors.grey),
            ('LINEBELOW', (0,0), (-1,-2), 0.3, colors.grey),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('SPAN', (1,2), (4,2)),
        ]))
        bloco.append(t_fornec)

        # Tabela de itens — cabeçalho
        cab = ['Nº Pedido/OF', 'Referência', 'Liga', 'Corrida', 'Certificado', 'Código da Peça', 'Descrição', 'Peso Unit.(kg)', 'Qtde (pçs)', 'Série', 'Preço Unit.(R$)', 'Preço Total (R$)']






        col_items = [26*mm, 20*mm, 12*mm, 14*mm, 18*mm, 24*mm, W*0.14,
                     13*mm, 11*mm, 14*mm, 16*mm, 16*mm]

        rows = [cab]
        itens = oe_data.get('itens', [])
        for it in itens:
            rows.append([
                f"{it.get('pedido','')} / {it.get('of','')}",
                it.get('referencia', ''),
                it.get('liga', ''),
                it.get('corrida', ''),
                it.get('certificado', ''),
                it.get('codigo_peca', ''),
                it.get('descricao', ''),
                f"{it.get('peso_unit', 0):.3f}" if it.get('peso_unit') else '',
                str(it.get('qtd', '')),
                it.get('serie', ''),
                f"R$ {it.get('preco_unit', 0):,.2f}" if it.get('preco_unit') else '',
                f"R$ {it.get('preco_total', 0):,.2f}" if it.get('preco_total') else '',
            ])

        # Linha de total
        total_qtd = sum(it.get('qtd', 0) for it in itens if isinstance(it.get('qtd'), (int, float)))
        total_val = sum(it.get('preco_total', 0) for it in itens if isinstance(it.get('preco_total'), (int, float)))
        rows.append(['TOTAL', '', '', '', '', '', '', '', str(int(total_qtd)), '', '', f"R$ {total_val:,.2f}"])

        t_items = Table(rows, colWidths=col_items, repeatRows=1)
        ts = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 6.5),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.3, colors.black),
            ('ROWBACKGROUND', (0,1), (-1,-2), [colors.white, colors.HexColor('#f0f4f8')]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e8edf2')),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ])
        t_items.setStyle(ts)
        bloco.append(t_items)

        # Observações
        obs_txt = oe_data.get('observacoes', '') or ''
        obs_data = [['Observações:', _p(obs_txt, 7.5)]]
        t_obs = Table(obs_data, colWidths=[22*mm, W-22*mm])
        t_obs.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        bloco.append(t_obs)

        # Assinaturas
        transp = oe_data.get('transportadora', '') or ''
        placa = oe_data.get('placa_veiculo', '') or ''
        nf = oe_data.get('nota_fiscal', '') or ''
        ass_data = [
            [f'Transportadora: {transp}   Placa: {placa}   NF: {nf}', 'Carregado por: ___________________', 'Liberado por: ___________________'],
            ['', '', ''],
        ]
        t_ass = Table(ass_data, colWidths=[W*0.4, W*0.3, W*0.3], rowHeights=[10, 18])
        t_ass.setStyle(TableStyle([
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('BOX', (0,0), (-1,-1), 0.3, colors.black),
            ('LINEAFTER', (0,0), (1,-1), 0.3, colors.grey),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        bloco.append(t_ass)
        bloco.append(HRFlowable(width=W, thickness=1, color=colors.HexColor('#1a3a5c'), spaceAfter=3))
        return bloco

    # Gera 3 vias: Fornecedor (/0), Transportadora (/1), Cliente (/2)
    for via in range(3):
        story.extend(_oe_bloco(via))
        if via < 2:
            story.append(Spacer(1, 4*mm))

    doc.build(story)
    return buf.getvalue()


def pagina_nova_oe():
    """Módulo de Nova Ordem de Entrega."""
    _migrar_banco_oe()
    st.title("📦 Nova Ordem de Entrega")

    # ── Carregar próximo número sequencial via PostgreSQL ───────────────────
    try:
        from fundicao_db import engine as _eng_oe
        from sqlalchemy import text as _text_oe
        with _eng_oe.connect() as _conn_oe:
            # Busca o maior numero entre ordem_entrega e oe_item
            _row = _conn_oe.execute(_text_oe("""
                SELECT GREATEST(
                    COALESCE((SELECT MAX(CAST(numero_oe AS INTEGER))
                              FROM ordem_entrega
                              WHERE numero_oe ~ '^[0-9]+$'), 0),
                    COALESCE((SELECT MAX(CAST(numero_oe AS INTEGER))
                              FROM oe_item
                              WHERE numero_oe ~ '^[0-9]+$'), 0)
                )
            """)).fetchone()
            proximo_num = (_row[0] or 1628) + 1
    except Exception:
        proximo_num = 1629

    # ── Formulário de identificação ─────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Identificação da OE")
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            num_oe = st.number_input("Nº da OE", min_value=1, value=proximo_num, step=1)
        with col2:
            # Busca todas as OFs disponíveis para autocomplete
            try:
                with db_session() as db:
                    ofs_disponiveis = db.execute(
                        select(OrdemFabricacao.numero_of, OrdemFabricacao.nome_cliente)
                        .order_by(OrdemFabricacao.numero_of)
                    ).fetchall()
            except Exception:
                ofs_disponiveis = []

            opcoes_of = [r[0] for r in ofs_disponiveis]
            of_selecionada = st.selectbox("Nº da Ordem de Fabricação (OF)", options=opcoes_of,
                                          index=None, placeholder="Selecione ou busque a OF...")
        with col3:
            data_emissao = st.date_input("Data de Emissão", value=date.today(),
                                          min_value=date(2000,1,1), max_value=date(2100,12,31),
                                          format="DD/MM/YYYY")

    # ── Carregar dados da OF automaticamente ───────────────────────────────
    of_obj = None
    if of_selecionada:
        try:
            with db_session() as db:
                of_obj = db.scalar(
                    select(OrdemFabricacao)
                    .options(
                        selectinload(OrdemFabricacao.ordens_entrega),
                        selectinload(OrdemFabricacao.certificados),
                    )
                    .where(OrdemFabricacao.numero_of == of_selecionada)
                )
        except Exception as e:
            st.error(f"Erro ao carregar OF: {e}")

    if of_obj:
        with st.container(border=True):
            st.subheader("📋 Dados da OF — preenchidos automaticamente")
            c1, c2, c3 = st.columns(3)
            c1.text_input("Cliente", value=of_obj.nome_cliente, disabled=True)
            c2.text_input("Nº Pedido do Cliente", value=of_obj.numero_pedido or '', disabled=True)
            c3.text_input("Liga", value=of_obj.liga or '', disabled=True)
            c4, c5, c6 = st.columns(3)
            c4.text_input("Descrição da Peça", value=of_obj.descricao_peca or '', disabled=True)
            c5.text_input("Norma", value=of_obj.norma or '', disabled=True)
            c6.text_input("Modelo / Desenho", value=f"{of_obj.numero_modelo or ''} / {of_obj.numero_desenho or ''}", disabled=True)
            c7, c8, c9 = st.columns(3)
            c7.text_input("Peso Líquido (kg)", value=str(of_obj.peso_liquido_kg or ''), disabled=True)
            c8.text_input("Preço Unit. (R$)", value=str(of_obj.valor_unitario or ''), disabled=True)
            oes_existentes = ', '.join(oe.numero_oe for oe in (of_obj.ordens_entrega or []))
            c9.text_input("OEs já emitidas", value=oes_existentes or 'Nenhuma', disabled=True)

        # ── Formulário de dados da OE ──────────────────────────────────────
        st.divider()
        with st.container(border=True):
            st.subheader("Dados da Expedição")
            ca, cb, cc = st.columns(3)
            with ca:
                transportadora = st.text_input("Transportadora")
            with cb:
                placa_veiculo = st.text_input("Placa do Veículo")
            with cc:
                nota_fiscal = st.text_input("Nota Fiscal")
            observacoes = st.text_area("Observações", placeholder="Ex.: PEÇAS PRONTAS PARA RETIRAR EM 30/03/26.")

        # ── Itens da OE ────────────────────────────────────────────────────
        st.divider()
        st.subheader("Itens desta Ordem de Entrega")

        # Corr. e certificados disponíveis
        certs = [c.numero_certificado for c in (of_obj.certificados or [])]
        certs_str = ', '.join(certs) if certs else '—'

        n_linhas = st.number_input("Número de linhas de itens", min_value=1, max_value=20, value=1)
        itens = []
        for i in range(int(n_linhas)):
            with st.container(border=True):
                st.caption(f"Item {i+1}")
                r1c1, r1c2, r1c3, r1c4 = st.columns([2, 1.5, 1.5, 2])
                with r1c1:
                    referencia = st.text_input("Referência", key=f"ref_{i}",
                                               value=of_obj.numero_desenho or '')
                with r1c2:
                    liga = st.text_input("Liga", key=f"liga_{i}", value=of_obj.liga or '')
                with r1c3:
                    corrida = st.text_input("Corrida", key=f"corr_{i}")
                with r1c4:
                    certificado = st.text_input(f"Certificado (disponíveis: {certs_str})",
                                                key=f"cert_{i}", value=certs[0] if certs else '')
                r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns([2, 2, 1, 1, 1.5, 1.5])
                with r2c1:
                    codigo_peca = st.text_input("Código da Peça", key=f"cod_{i}",
                                                value=of_obj.numero_modelo or '')
                with r2c2:
                    descricao = st.text_input("Descrição", key=f"desc_{i}",
                                              value=of_obj.descricao_peca or '')
                with r2c3:
                    peso_unit = st.number_input("Peso Unit. (kg)", key=f"peso_{i}",
                                                value=float(of_obj.peso_liquido_kg or 0), min_value=0.0, format="%.3f")
                with r2c4:
                    qtd = st.number_input("Qtde (pçs)", key=f"qtd_{i}", min_value=0, value=0)
                with r2c5:
                    serie = st.text_input("Série", key=f"serie_{i}")
                with r2c6:
                    preco_unit = st.number_input("Preço Unit. (R$)", key=f"preco_{i}",
                                                 value=float(of_obj.valor_unitario or 0), min_value=0.0, format="%.4f")
                preco_total = qtd * preco_unit
                st.caption(f"💰 Preço Total: R$ {preco_total:,.2f}")
                itens.append({
                    'pedido': of_obj.numero_pedido or '',
                    'of': of_obj.numero_of,
                    'referencia': referencia,
                    'liga': liga,
                    'corrida': corrida,
                    'certificado': certificado,
                    'codigo_peca': codigo_peca,
                    'descricao': descricao,
                    'peso_unit': peso_unit,
                    'qtd': qtd,
                    'serie': serie,
                    'preco_unit': preco_unit,
                    'preco_total': preco_total,
                })

        total_qtd_oe = sum(it.get('qtd', 0) for it in itens)
        total_val_oe = sum(it.get('preco_total', 0) for it in itens)
        st.info(f"**Total da OE:** {total_qtd_oe} peças  |  R$ {total_val_oe:,.2f}")

        # ── Ações ────────────────────────────────────────────────────────────
        st.divider()
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        with col_btn1:
            gravar = st.button("💾 Gravar OE", type="primary", use_container_width=True)
        with col_btn2:
            gerar_pdf = st.button("📄 Gerar PDF", use_container_width=True)

        if gravar:
            try:
                numero_oe_str = str(int(num_oe))
                now = datetime.now().astimezone()
                with db_session() as db:
                    of_db = db.scalar(select(OrdemFabricacao).where(
                        OrdemFabricacao.numero_of == of_selecionada))
                    if not of_db:
                        st.error("OF não encontrada no banco.")
                    else:
                        oe = OrdemEntrega(
                            numero_oe=numero_oe_str,
                            qtd_pecas=total_qtd_oe,
                            data_prevista=data_emissao,
                            observacao=observacoes,
                            criado_em=now,
                        )
                        of_db.ordens_entrega.append(oe)

                # Grava itens na tabela oe_item
                import uuid as _uuid
                from fundicao_db import engine as _eng2
                from sqlalchemy import text as _text2
                with _eng2.begin() as _conn2:
                    for it in itens:
                        _conn2.execute(_text2("""
                            INSERT INTO oe_item (
                                id, numero_oe, num_oe_seq, nome_cliente,
                                num_pedido, num_of, referencia, liga, corrida,
                                certificado, cod_peca, descricao,
                                peso_unit, qtd, serie, preco_unit, preco_total,
                                observacoes, criado_em
                            ) VALUES (
                                :id, :noe, :seq, :cliente,
                                :pedido, :of, :ref, :liga, :corr,
                                :cert, :cod, :desc,
                                :peso, :qtd, :serie, :pu, :pt,
                                :obs, NOW()
                            )
                        """), {
                            "id":      str(_uuid.uuid4()),
                            "noe":     numero_oe_str,
                            "seq":     int(num_oe),
                            "cliente": of_obj.nome_cliente or "",
                            "pedido":  it.get("pedido",""),
                            "of":      it.get("of",""),
                            "ref":     it.get("referencia",""),
                            "liga":    it.get("liga",""),
                            "corr":    it.get("corrida",""),
                            "cert":    it.get("certificado",""),
                            "cod":     it.get("codigo_peca",""),
                            "desc":    it.get("descricao",""),
                            "peso":    float(it.get("peso_unit",0) or 0),
                            "qtd":     int(it.get("qtd",0) or 0),
                            "serie":   it.get("serie",""),
                            "pu":      float(it.get("preco_unit",0) or 0),
                            "pt":      float(it.get("preco_total",0) or 0),
                            "obs":     observacoes or "",
                        })

                st.success(f"✅ OE Nº {numero_oe_str} gravada com sucesso!")

                # Atualiza qtd_expedida nas OFs somando qtd de cada item
                try:
                    with db_session() as _db_exp:
                        # Agrupa qtd por OF
                        _qtd_por_of = {}
                        for it in itens:
                            _nof = it.get("of", "").strip()
                            _qtd = int(it.get("qtd", 0) or 0)
                            if _nof and _qtd > 0:
                                _qtd_por_of[_nof] = _qtd_por_of.get(_nof, 0) + _qtd

                        for _nof, _qtd in _qtd_por_of.items():
                            _of_exp = _db_exp.scalar(
                                select(OrdemFabricacao).where(OrdemFabricacao.numero_of == _nof)
                            )
                            if _of_exp:
                                _of_exp.qtd_expedida = int(_of_exp.qtd_expedida or 0) + _qtd
                                st.info(f"✅ OF **{_nof}** atualizada: +{_qtd} peças expedidas.")
                except Exception as _ex_exp:
                    st.warning(f"OE gravada mas erro ao atualizar qtd_expedida: {_ex_exp}")
                st.session_state['_oe_gravada_itens'] = itens
                st.session_state['_oe_gravada_num'] = numero_oe_str
                st.session_state['_oe_gravada_obs'] = observacoes
                st.session_state['_oe_gravada_cliente'] = of_obj.nome_cliente or ""
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")

        # ── Botoes PDF e Excel apos gravar ────────────────────────────────
        _num_gravado = st.session_state.get('_oe_gravada_num','')
        if _num_gravado and str(int(num_oe)) == _num_gravado:
            _itens_grav = st.session_state.get('_oe_gravada_itens', itens)
            _obs_grav   = st.session_state.get('_oe_gravada_obs', observacoes)
            _cli_grav   = st.session_state.get('_oe_gravada_cliente', of_obj.nome_cliente if of_obj else "")
            _tmpl_b64   = get_config("template_oe_base64","")
            if _tmpl_b64:
                st.divider()
                st.success(f"OE {_num_gravado} gravada! Gere os documentos:")
                _itens_pdf = [{
                    "num_pedido":  it.get("pedido",""),
                    "num_of":      it.get("of",""),
                    "referencia":  it.get("referencia",""),
                    "liga":        it.get("liga",""),
                    "corrida":     it.get("corrida",""),
                    "certificado": it.get("certificado",""),
                    "cod_peca":    it.get("codigo_peca",""),
                    "descricao":   it.get("descricao",""),
                    "peso_unit":   float(it.get("peso_unit",0) or 0),
                    "qtd":         int(it.get("qtd",0) or 0),
                    "serie":       it.get("serie",""),
                    "preco_unit":  float(it.get("preco_unit",0) or 0),
                    "preco_total": float(it.get("preco_total",0) or 0),
                } for it in _itens_grav]
                _cfg_oe = {
                    "nome_empresa": get_config("nome_empresa"),
                    "endereco":     get_config("endereco"),
                    "bairro":       get_config("bairro"),
                    "cidade":       get_config("cidade"),
                    "estado":       get_config("estado"),
                    "telefone":     get_config("telefone"),
                    "email":        get_config("email"),
                    "contato":      get_config("template_oe_responsavel") or get_config("contato"),
                    "rodape_pdf":   get_config("rodape_pdf"),
                    "orientacao":   get_config("template_oe_orientacao","Paisagem"),
                }
                _logo_bts = None
                try:
                    from empresa_config import get_logo_ativo_bytes
                    _logo_bts = get_logo_ativo_bytes()
                except Exception:
                    pass
                import base64 as _b64m
                _tmpl_bts = _b64m.b64decode(_tmpl_b64)
                from gerar_oe_excel import gerar_oe_excel, gerar_oe_pdf, configurar_impressao_excel
                _excel_bts = gerar_oe_excel(_tmpl_bts, _num_gravado, _cli_grav,
                                             _itens_pdf, _obs_grav, _cfg_oe, _logo_bts)
                _excel_bts = configurar_impressao_excel(_excel_bts, _cfg_oe.get("orientacao","Paisagem"))
                _pdf_bts   = gerar_oe_pdf(_num_gravado, _cli_grav, _itens_pdf,
                                           _obs_grav, _cfg_oe, _logo_bts)
                _db1, _db2 = st.columns(2)
                with _db1:
                    st.download_button(
                        f"⬇️ Baixar OE {_num_gravado} em PDF",
                        data=_pdf_bts,
                        file_name=f"OE_{_num_gravado}.pdf",
                        mime="application/pdf",
                        key="dl_nova_oe_pdf",
                        type="primary",
                    )
                with _db2:
                    st.download_button(
                        f"📊 Baixar OE {_num_gravado} em Excel",
                        data=_excel_bts,
                        file_name=f"OE_{_num_gravado}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_nova_oe_xlsx",
                    )

    elif of_selecionada is not None and not of_obj:
        st.warning("OF não encontrada no banco de dados.")
    else:
        st.info("👆 Selecione uma Ordem de Fabricação para preencher os dados automaticamente.")

    # Historico removido - use a aba Consulta de OEs
    # ── Gerenciar OE existente ─────────────────────────────────────────────────
    st.divider()
    with st.expander("🔧 Alterar ou Excluir uma OE existente", expanded=False):
        st.caption("Busque uma OE pelo número para alterar ou excluir.")

        _oe_num_ger = st.text_input("Nº da OE", placeholder="Ex: 1626",
                                     key="ger_oe_num")
        if _oe_num_ger.strip():
            try:
                from fundicao_db import engine as _eng_ger
                from sqlalchemy import text as _text_ger
                with _eng_ger.connect() as _conn_ger:
                    _itens_ger = _conn_ger.execute(_text_ger("""
                        SELECT id, num_of, referencia, liga, corrida,
                               certificado, cod_peca, descricao,
                               peso_unit, qtd, serie, preco_unit, preco_total,
                               nome_cliente, num_pedido
                        FROM oe_item
                        WHERE numero_oe = :noe
                        ORDER BY id
                    """), {"noe": _oe_num_ger.strip()}).fetchall()
                    _ofs_ger = _conn_ger.execute(_text_ger(
                        "SELECT numero_of FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
                    _obs_ger = _conn_ger.execute(_text_ger(
                        "SELECT observacao FROM ordem_entrega WHERE numero_oe=:noe",
                    ), {"noe": _oe_num_ger.strip()}).scalar()

                _ofs_lista_ger = [r[0] for r in _ofs_ger]

                if not _itens_ger:
                    st.warning(f"OE {_oe_num_ger} não encontrada.")
                else:
                    st.success(f"OE {_oe_num_ger} encontrada — {len(_itens_ger)} item(ns)")

                    # ── Alterar ──────────────────────────────────────────────
                    with st.expander(f"✏️ Alterar OE {_oe_num_ger}", expanded=False):
                        st.caption("Selecione o item a alterar, modifique os campos e clique em Salvar.")

                        _edit_obs_ger = st.text_area("Observações gerais",
                            value=_obs_ger or "", key="edit_obs_ger")

                        st.divider()
                        st.markdown("**Selecione o item a alterar:**")

                        _opcoes_ger = {
                            f"Item {i+1}: OF {dict(it._mapping).get('num_of','')} | {dict(it._mapping).get('referencia','')}": i
                            for i, it in enumerate(_itens_ger)
                        }
                        _item_sel_ger = st.selectbox("Item", options=list(_opcoes_ger.keys()),
                                                      key="sel_item_ger")
                        _item_idx_ger = _opcoes_ger[_item_sel_ger]
                        _item_d_ger = dict(_itens_ger[_item_idx_ger]._mapping)
                        _of_atual_ger = str(_item_d_ger.get("num_of",""))

                        st.markdown(f"**Editando:** {_item_d_ger.get('referencia','')} — {_item_d_ger.get('descricao','')}")

                        _gc1, _gc2 = st.columns(2)
                        with _gc1:
                            _edit_of_ger = st.text_input("OF", value=_of_atual_ger, key="edit_of_ger")
                            if _edit_of_ger.strip() and _edit_of_ger.strip() not in _ofs_lista_ger:
                                st.warning(f"OF '{_edit_of_ger}' não encontrada.")
                            _edit_qtd_ger = st.number_input("Quantidade",
                                value=int(_item_d_ger.get("qtd",0) or 0),
                                min_value=0, key="edit_qtd_ger")
                        with _gc2:
                            _edit_serie_ger  = st.text_input("Série",
                                value=str(_item_d_ger.get("serie","") or ""), key="edit_serie_ger")
                            _edit_corr_ger   = st.text_input("Corrida",
                                value=str(_item_d_ger.get("corrida","") or ""), key="edit_corr_ger")
                            _edit_cert_ger   = st.text_input("Certificado",
                                value=str(_item_d_ger.get("certificado","") or ""), key="edit_cert_ger")

                        if st.button("💾 Salvar alterações deste item", key="btn_salvar_ger",
                                     type="primary"):
                            try:
                                from fundicao_db import engine as _eng_upd_g
                                from sqlalchemy import text as _text_upd_g
                                _of_edit_g = _edit_of_ger.strip()
                                with _eng_upd_g.begin() as _conn_upd_g:
                                    _conn_upd_g.execute(_text_upd_g(
                                        "UPDATE ordem_entrega SET observacao=:obs WHERE numero_oe=:noe"
                                    ), {"obs": _edit_obs_ger, "noe": _oe_num_ger.strip()})

                                    _upd_g = {
                                        "id":      _item_d_ger["id"],
                                        "num_of":  _of_edit_g,
                                        "qtd":     _edit_qtd_ger,
                                        "serie":   _edit_serie_ger,
                                        "corrida": _edit_corr_ger,
                                        "cert":    _edit_cert_ger,
                                        "pt":      _edit_qtd_ger * float(_item_d_ger.get("preco_unit",0) or 0),
                                    }
                                    if _of_edit_g in _ofs_lista_ger:
                                        _of_novo_g = _conn_upd_g.execute(_text_upd_g("""
                                            SELECT nome_cliente, numero_pedido, liga,
                                                   descricao_peca, numero_modelo,
                                                   peso_liquido_kg, valor_unitario
                                            FROM ordem_fabricacao WHERE numero_of=:of
                                        """), {"of": _of_edit_g}).fetchone()
                                        if _of_novo_g:
                                            _novo_pu_g = float(_of_novo_g[6] or 0)
                                            _conn_upd_g.execute(_text_upd_g("""
                                                UPDATE oe_item SET
                                                    num_of=:num_of, qtd=:qtd, serie=:serie,
                                                    corrida=:corrida, certificado=:cert,
                                                    preco_total=:pt, nome_cliente=:cli,
                                                    num_pedido=:ped, liga=:liga,
                                                    descricao=:descricao, cod_peca=:cod_peca,
                                                    peso_unit=:peso, preco_unit=:pu
                                                WHERE id=:id
                                            """), {**_upd_g,
                                                   "cli":      _of_novo_g[0] or "",
                                                   "ped":      _of_novo_g[1] or "",
                                                   "liga":     _of_novo_g[2] or "",
                                                   "descricao": _of_novo_g[3] or "",
                                                   "cod_peca": _of_novo_g[4] or "",
                                                   "peso":     float(_of_novo_g[5] or 0),
                                                   "pu":       _novo_pu_g,
                                                   "pt":       _edit_qtd_ger * _novo_pu_g})
                                    else:
                                        _conn_upd_g.execute(_text_upd_g("""
                                            UPDATE oe_item SET
                                                num_of=:num_of, qtd=:qtd, serie=:serie,
                                                corrida=:corrida, certificado=:cert,
                                                preco_total=:pt
                                            WHERE id=:id
                                        """), _upd_g)
                                st.success(f"✅ Item atualizado com sucesso!")
                                st.rerun()
                            except Exception as _e_g:
                                st.error(f"Erro: {_e_g}")

                    # ── Excluir ───────────────────────────────────────────────
                    with st.expander(f"🗑️ Excluir OE {_oe_num_ger}", expanded=False):
                        st.warning(f"⚠️ Excluir a OE **{_oe_num_ger}** removerá todos os seus itens. Esta ação não pode ser desfeita.")
                        if st.button("🗑️ Confirmar exclusão", key="btn_excluir_ger", type="primary"):
                            try:
                                from fundicao_db import engine as _eng_del_g
                                from sqlalchemy import text as _text_del_g
                                with _eng_del_g.begin() as _conn_del_g:
                                    _conn_del_g.execute(_text_del_g(
                                        "DELETE FROM oe_item WHERE numero_oe=:noe"),
                                        {"noe": _oe_num_ger.strip()})
                                    _conn_del_g.execute(_text_del_g(
                                        "DELETE FROM ordem_entrega WHERE numero_oe=:noe"),
                                        {"noe": _oe_num_ger.strip()})
                                st.success(f"✅ OE {_oe_num_ger} excluída!")
                                st.rerun()
                            except Exception as _e_g:
                                st.error(f"Erro: {_e_g}")

            except Exception as _e_ger:
                st.error(f"Erro ao buscar OE: {_e_ger}")



# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO: CONSULTA DE ORDENS DE ENTREGA
# ══════════════════════════════════════════════════════════════════════════════

def pagina_consulta_oes():
    """Consulta, filtros e relatório de Ordens de Entrega."""
    _migrar_banco_oe()
    st.title("🔍 Consulta de Ordens de Entrega")

    # ── Carregar dados do banco via SQLAlchemy (PostgreSQL) ─────────────────
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text

        # Tenta buscar da tabela oe_item (dados historicos detalhados)
        # Se nao existir, busca da ordem_entrega
        with _eng.connect() as _conn:
            # Verifica se tabela oe_item existe
            _tbl_check = _conn.execute(_text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'oe_item'
            """)).scalar()

            if _tbl_check and _tbl_check > 0:
                # Busca da tabela oe_item (itens detalhados)
                _sql_item = """
                    SELECT
                        i.numero_oe,
                        COALESCE(i.qtd, 0)          AS qtd_pecas,
                        COALESCE(i.observacoes, '')  AS observacao,
                        i.criado_em,
                        COALESCE(i.num_of, '')       AS numero_of,
                        COALESCE(i.nome_cliente, '') AS of_cliente,
                        COALESCE(i.num_pedido, '')   AS of_pedido,
                        COALESCE(of.liga, '')        AS of_liga,
                        COALESCE(i.num_oe_seq::TEXT, '') AS numero_oe_seq,
                        COALESCE(i.nome_cliente, '') AS nome_cliente,
                        COALESCE(i.num_pedido, '')   AS num_pedido,
                        COALESCE(i.num_of, '')       AS num_of_ref,
                        COALESCE(i.referencia, '')   AS referencia,
                        COALESCE(i.liga, '')         AS liga,
                        COALESCE(i.corrida, '')      AS corrida,
                        COALESCE(i.certificado, '')  AS certificado,
                        COALESCE(i.cod_peca, '')     AS cod_peca,
                        COALESCE(i.descricao, '')    AS descricao,
                        COALESCE(i.peso_unit, 0)     AS peso_unit,
                        COALESCE(i.serie, '')        AS serie,
                        COALESCE(i.preco_unit, 0)    AS preco_unit,
                        COALESCE(i.preco_total, 0)   AS preco_total,
                        i.criado_em                  AS data_emissao,
                        ''                           AS transportadora,
                        ''                           AS nota_fiscal
                    FROM oe_item i
                    LEFT JOIN ordem_fabricacao of ON of.numero_of = i.num_of
                    ORDER BY CAST(REGEXP_REPLACE(i.numero_oe, '[^0-9]', '', 'g') AS INTEGER) DESC NULLS LAST, i.criado_em DESC
                """
                rows = _conn.execute(_text(_sql_item)).fetchall()
            else:
                # Fallback: busca da ordem_entrega
                _sql_oe = """
                    SELECT
                        oe.numero_oe,
                        oe.qtd_pecas,
                        COALESCE(oe.observacao, '') AS observacao,
                        oe.criado_em,
                        of.numero_of,
                        of.nome_cliente  AS of_cliente,
                        COALESCE(of.numero_pedido, '') AS of_pedido,
                        COALESCE(of.liga, '') AS of_liga,
                        '' AS numero_oe_seq, '' AS nome_cliente,
                        '' AS num_pedido, '' AS num_of_ref,
                        '' AS referencia, '' AS liga, '' AS corrida,
                        '' AS certificado, '' AS cod_peca, '' AS descricao,
                        0 AS peso_unit, '' AS serie, 0 AS preco_unit,
                        0 AS preco_total, oe.data_prevista AS data_emissao,
                        '' AS transportadora, '' AS nota_fiscal
                    FROM ordem_entrega oe
                    JOIN ordem_fabricacao of ON of.id = oe.ordem_fabricacao_id
                    ORDER BY CAST(REGEXP_REPLACE(oe.numero_oe, '[^0-9]', '', 'g') AS INTEGER) DESC NULLS LAST, oe.criado_em DESC
                """
                rows = _conn.execute(_text(_sql_oe)).fetchall()

        if not rows:
            st.info("Nenhuma Ordem de Entrega encontrada no banco.")
            return

        # Converter para DataFrame
        df_raw = pd.DataFrame(rows, columns=[
            'numero_oe','qtd_pecas','observacao','criado_em',
            'numero_of','of_cliente','of_pedido','of_liga',
            'numero_oe_seq','nome_cliente','num_pedido','num_of_ref',
            'referencia','liga','corrida','certificado','cod_peca',
            'descricao','peso_unit','serie','preco_unit','preco_total',
            'data_emissao','transportadora','nota_fiscal'
        ])

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # ── Filtros ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Filtros")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_oe = st.text_input("Nº da OE", placeholder="Ex: 1628")
        with fc2:
            f_of = st.text_input("Nº da OF", placeholder="Ex: 015B6")
        with fc3:
            # Clientes únicos para selectbox
            clientes = ["Todos"] + sorted(
                df_raw["nome_cliente"].dropna().unique().tolist()
                if "nome_cliente" in df_raw.columns and df_raw["nome_cliente"].notna().any()
                else df_raw["of_cliente"].dropna().unique().tolist()
            )
            f_cliente = st.selectbox("Cliente", options=clientes)

        fc4, fc5, fc6 = st.columns(3)
        with fc4:
            f_ref = st.text_input("Referência / Código Peça", placeholder="Ex: FLACAMINC")
        with fc5:
            f_liga = st.text_input("Liga", placeholder="Ex: CF8")
        with fc6:
            f_cert = st.text_input("Certificado", placeholder="Ex: 2034/26")

        fc7, fc8 = st.columns(2)
        with fc7:
            f_data_ini = st.date_input("Data de (criação)", value=None,
                                        min_value=date(2000,1,1), max_value=date(2100,12,31),
                                        format="DD/MM/YYYY")
        with fc8:
            f_data_fim = st.date_input("Data até", value=None,
                                        min_value=date(2000,1,1), max_value=date(2100,12,31),
                                        format="DD/MM/YYYY")

    # ── Aplicar filtros ─────────────────────────────────────────────────────
    df = df_raw.copy()

    if f_oe.strip():
        df = df[df["numero_oe"].astype(str).str.contains(f_oe.strip(), case=False, na=False)]
    if f_of.strip():
        mask = df["numero_of"].astype(str).str.contains(f_of.strip(), case=False, na=False)
        if "num_of_ref" in df.columns:
            mask = mask | df["num_of_ref"].astype(str).str.contains(f_of.strip(), case=False, na=False)
        df = df[mask]
    if f_cliente != "Todos":
        col_cli = "nome_cliente" if ("nome_cliente" in df.columns and df["nome_cliente"].notna().any()) else "of_cliente"
        df = df[df[col_cli].astype(str).str.contains(f_cliente, case=False, na=False)]
    if f_ref.strip():
        mask = pd.Series([False]*len(df), index=df.index)
        for c in ["referencia","cod_peca","descricao"]:
            if c in df.columns:
                mask = mask | df[c].astype(str).str.contains(f_ref.strip(), case=False, na=False)
        df = df[mask]
    if f_liga.strip():
        col_l = "liga" if "liga" in df.columns else "of_liga"
        df = df[df[col_l].astype(str).str.contains(f_liga.strip(), case=False, na=False)]
    if f_cert.strip() and "certificado" in df.columns:
        df = df[df["certificado"].astype(str).str.contains(f_cert.strip(), case=False, na=False)]
    if f_data_ini:
        df = df[pd.to_datetime(df["criado_em"], errors="coerce").dt.date >= f_data_ini]
    if f_data_fim:
        df = df[pd.to_datetime(df["criado_em"], errors="coerce").dt.date <= f_data_fim]

    # ── Métricas do resultado filtrado ──────────────────────────────────────
    total_oes   = len(df)
    total_pecas = df["qtd_pecas"].fillna(0).astype(int).sum()
    col_val = "preco_total" if "preco_total" in df.columns else None
    total_valor = df[col_val].fillna(0).astype(float).sum() if col_val else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("OEs encontradas", total_oes)
    m2.metric("Total de peças", f"{total_pecas:,}".replace(",", "."))
    m3.metric("Valor total (R$)", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    if df.empty:
        st.warning("Nenhum resultado para os filtros aplicados.")
        return

    # ── Botao gerar OE com template (aparece quando filtra por numero de OE) ─
    _oes_unicas = df["numero_oe"].unique().tolist()
    if len(_oes_unicas) == 1 or (f_oe.strip() and len(_oes_unicas) <= 3):
        _tmpl_b64 = get_config("template_oe_base64", "")
        if _tmpl_b64:
            st.divider()
            for _noe in _oes_unicas:
                _df_oe = df[df["numero_oe"] == _noe]
                _cliente_oe = str(
                    _df_oe["nome_cliente"].iloc[0]
                    if "nome_cliente" in _df_oe.columns and _df_oe["nome_cliente"].iloc[0]
                    else _df_oe["of_cliente"].iloc[0]
                    if "of_cliente" in _df_oe.columns
                    else ""
                )
                _obs_oe = str(_df_oe["observacao"].iloc[0] if "observacao" in _df_oe.columns else "")

                if st.button(f"📊 Gerar OE {_noe} com Template Excel",
                             key=f"btn_tmpl_{_noe}", type="primary"):
                    try:
                        import base64 as _b64mod
                        from fundicao_db import engine as _eng
                        from sqlalchemy import text as _text
                        from gerar_oe_excel import gerar_oe_excel

                        # Busca TODOS os itens da OE no banco
                        with _eng.connect() as _conn:
                            _itens_oe = _conn.execute(_text("""
                                SELECT num_pedido, num_of, referencia, liga, corrida,
                                       certificado, cod_peca, descricao,
                                       peso_unit, qtd, serie, preco_unit, preco_total,
                                       observacoes
                                FROM oe_item
                                WHERE numero_oe = :oe
                                ORDER BY id
                            """), {"oe": str(_noe)}).fetchall()

                        if not _itens_oe:
                            # Usa dados do DataFrame como fallback
                            _itens_lista = [{
                                "num_pedido":  str(r.get("num_pedido", "") or r.get("of_pedido", "")),
                                "num_of":      str(r.get("numero_of", "")),
                                "referencia":  str(r.get("referencia", "")),
                                "liga":        str(r.get("liga", "") or r.get("of_liga", "")),
                                "corrida":     str(r.get("corrida", "")),
                                "certificado": str(r.get("certificado", "")),
                                "cod_peca":    str(r.get("cod_peca", "")),
                                "descricao":   str(r.get("descricao", "")),
                                "peso_unit":   float(r.get("peso_unit", 0) or 0),
                                "qtd":         int(r.get("qtd_pecas", 0) or 0),
                                "serie":       str(r.get("serie", "")),
                                "preco_unit":  float(r.get("preco_unit", 0) or 0),
                                "preco_total": float(r.get("preco_total", 0) or 0),
                            } for _, r in _df_oe.iterrows()]
                        else:
                            _itens_lista = [dict(r._mapping) for r in _itens_oe]

                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        get_config("bairro"),
                            "cidade":        get_config("cidade"),
                            "estado":        get_config("estado"),
                            "telefone":      get_config("telefone"),
                            "email":         get_config("email"),
                            "contato":       get_config("template_oe_responsavel") or get_config("contato"),
                            "rodape_pdf":    get_config("rodape_pdf"),
                            "orientacao":    get_config("template_oe_orientacao", "Paisagem"),
                        }
                        # Busca logo ativo
                        _logo_bytes = None
                        try:
                            from empresa_config import get_logo_ativo_bytes
                            _logo_bytes = get_logo_ativo_bytes()
                        except Exception:
                            pass

                        from gerar_oe_excel import configurar_impressao_excel
                        _orientacao = _cfg.get("orientacao", "Paisagem")
                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel(
                            template_bytes=_tmpl_bytes,
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                            logo_bytes=_logo_bytes,
                        )
                        from gerar_oe_excel import gerar_oe_pdf
                        _pdf_bytes = gerar_oe_pdf(
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                            logo_bytes=_logo_bytes,
                        )
                        _excel_bytes = configurar_impressao_excel(
                            _excel_bytes, _orientacao)
                        # Botoes download e visualizacao
                        _dc1, _dc2 = st.columns(2)
                        with _dc1:
                            st.download_button(
                                f"⬇️ Baixar OE {_noe} em PDF",
                                data=_pdf_bytes,
                                file_name=f"OE_{_noe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{_noe}",
                                type="primary",
                            )
                        with _dc2:
                            st.download_button(
                                f"📊 Baixar OE {_noe} em Excel",
                                data=_excel_bytes,
                                file_name=f"OE_{_noe}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_xlsx_{_noe}",
                            )

                    except Exception as _ex:
                        st.error(f"Erro ao gerar OE: {_ex}")

            st.divider()

    # ── Montar tabela de exibição ───────────────────────────────────────────
    def _col(col): return df[col] if col in df.columns else ""

    df_exib = pd.DataFrame({
        "Nº OE":       df["numero_oe"],
        "OF":          df["numero_of"],
        "Cliente":     _col("nome_cliente").where(_col("nome_cliente") != "", _col("of_cliente")),
        "Nº Pedido":   _col("num_pedido").where(_col("num_pedido") != "", _col("of_pedido")),
        "Referência":  _col("referencia"),
        "Liga":        _col("liga").where(_col("liga") != "", _col("of_liga")),
        "Corrida":     _col("corrida"),
        "Certificado": _col("certificado"),
        "Código Peça": _col("cod_peca"),
        "Descrição":   _col("descricao"),
        "Peso Unit.":  _col("peso_unit"),
        "Qtde (pçs)":  df["qtd_pecas"],
        "Série":       _col("serie"),
        "Preço Unit.": _col("preco_unit"),
        "Preço Total": _col("preco_total"),
        "Data":        pd.to_datetime(df["criado_em"], errors="coerce").dt.strftime("%d/%m/%Y"),
        "Observação":  df["observacao"].fillna(""),
    })

    # Selecionar linha para ver detalhes
    st.caption("💡 **Clique em uma linha** da tabela abaixo para ver os detalhes e gerar PDF/Excel da OE.")
    evento = st.dataframe(
        df_exib,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Peso Unit.":  st.column_config.NumberColumn(format="%.3f kg"),
            "Preço Unit.": st.column_config.NumberColumn(format="R$ %.2f"),
            "Preço Total": st.column_config.NumberColumn(format="R$ %.2f"),
            "Qtde (pçs)":  st.column_config.NumberColumn(format="%d"),
        }
    )

    # ── Detalhes da OE selecionada + PDF ────────────────────────────────────
    sel = evento.selection.rows if evento and evento.selection else []
    if sel:
        idx = sel[0]
        oe_row = df.iloc[idx]
        num_oe_sel = str(oe_row["numero_oe"])
        num_of_sel = str(oe_row.get("num_of", oe_row.get("numero_of", "")))

        with st.expander(f"📋 Detalhes da OE {num_oe_sel} — OF {num_of_sel}", expanded=True):

            d1, d2, d3, d4 = st.columns(4)
            d1.text_input("Nº OE", num_oe_sel, disabled=True)
            d2.text_input("OF", num_of_sel, disabled=True)
            cliente_val = str(oe_row.get("nome_cliente", "") or oe_row.get("of_cliente", ""))
            d3.text_input("Cliente", cliente_val, disabled=True)
            d4.text_input("Qtde (esta linha)", str(int(oe_row.get("qtd", 0))), disabled=True)

            d5, d6, d7, d8 = st.columns(4)
            d5.text_input("Referência", str(oe_row.get("referencia", "")), disabled=True)
            d6.text_input("Liga", str(oe_row.get("liga", "") or oe_row.get("of_liga", "")), disabled=True)
            d7.text_input("Corrida", str(oe_row.get("corrida", "")), disabled=True)
            d8.text_input("Certificado", str(oe_row.get("certificado", "")), disabled=True)

            d9, d10, d11, d12 = st.columns(4)
            d9.text_input("Código da Peça", str(oe_row.get("cod_peca", "")), disabled=True)
            d10.text_input("Descrição", str(oe_row.get("descricao", "")), disabled=True)
            d11.text_input("Série", str(oe_row.get("serie", "")), disabled=True)
            try:
                pt = float(oe_row.get("preco_total", 0) or 0)
                d12.text_input("Preço Total", f"R$ {pt:,.2f}", disabled=True)
            except Exception:
                d12.text_input("Preço Total", "", disabled=True)

            obs_val = str(oe_row.get("observacoes", "") or "")
            if obs_val:
                st.text_area("Observação", obs_val, disabled=True, height=60)




    # ── Exportar CSV ─────────────────────────────────────────────────────────
    st.divider()
    csv = df_exib.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar tabela como CSV",
        data=csv,
        file_name="ordens_entrega.csv",
        mime="text/csv",
        use_container_width=False,
    )


main()
