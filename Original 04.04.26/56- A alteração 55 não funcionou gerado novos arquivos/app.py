"""
Sistema de Controle de Fundição — interface Streamlit + SQLAlchemy (SQLite fundicao.db).

Na raiz do projeto:
    streamlit run app.py
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

import pandas as pd
import streamlit as st
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.sqlite_models import CertificadoPeca, Corrida, OrdemEntrega, OrdemFabricacao
from fundicao_db import SessionLocal, init_db, ping_database

import sqlite3


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


def _status_of(of: OrdemFabricacao) -> str:
    # Verifica status manual primeiro (Finalizada / Cancelada)
    _st = getattr(of, "status_of", None) or "Ativa"
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
    OEs e certificados são consolidados em uma única célula cada,
    separados por vírgula — sem duplicar linhas da OF.
    """
    rows = []
    for of in ofs_list:
        # Consolida todas as OEs e certificados em strings únicas
        oes   = list(of.ordens_entrega or [])
        certs = list(of.certificados   or [])
        oes_str   = ", ".join(o.numero_oe           for o in oes   if o.numero_oe)
        certs_str = ", ".join(c.numero_certificado  for c in certs if c.numero_certificado)

        _of_status = getattr(of, "status_of", None) or "Ativa"
        rows.append({
            "numero_of":            of.numero_of or "",
            "numero_nn":            (("⛔ OF CANCELADA") if _of_status == "Cancelada" else (of.numero_nn or "")),
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
            "status_of":            getattr(of, "status_of", None) or "Ativa",
        })

    return rows


def _df_of_formatado(rows: list[dict]) -> "pd.DataFrame":
    """Converte lista de dicts em DataFrame com títulos amigáveis na ordem certa."""
    df = pd.DataFrame(rows, columns=[k for k, _ in _OF_DISPLAY_COLS])
    df = df.rename(columns={k: v for k, v in _OF_DISPLAY_COLS})
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

def pagina_dashboard():
    st.title("Dashboard da Fundição")

    try:
        with db_session() as db:
            todas = list(db.scalars(select(OrdemFabricacao)).all())
            ultimas_corridas = list(
                db.scalars(select(Corrida).order_by(Corrida.data_fusao.desc()).limit(10)).all()
            )
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        todas = []
        ultimas_corridas = []

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("OFs cadastradas", len(todas))

    # Recarrega com OEs e certificados numa única sessão (evita DetachedInstanceError)
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
            # Extrai tudo dentro da sessão antes de fechar
            linhas_completas   = _montar_linhas_of(todas_completas)
            abertas_list       = [of for of in todas_completas if _status_of(of) in ("Aberta", "Expedição parcial", "Sem qtd. pedido", "Cancelada")]
            linhas_abertas     = _montar_linhas_of(abertas_list)
    except Exception as e:
        st.error(f"Erro ao carregar OEs/certificados: {e}")
        linhas_abertas   = []
        todas_completas  = todas

    soma_pedido  = sum(float(of.qtd_pecas_pedido or 0) for of in todas)
    abertas_ct   = sum(1 for of in (todas_completas if todas_completas else todas) if _status_of(of) == "Aberta")
    parciais_ct  = sum(1 for of in (todas_completas if todas_completas else todas) if _status_of(of) == "Expedição parcial")

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
        st.dataframe(
            _df_dash,
            height=400,
            use_container_width=True,
            hide_index=True,
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

    st.markdown("##### Ordens de entrega (OE) e certificados")
    st.caption("Defina quantas linhas deseja preencher (fora do formulário principal).")
    colx, coly = st.columns(2)
    with colx:
        n_oes = st.number_input("Quantas OEs?", min_value=0, max_value=30, value=0, step=1)
    with coly:
        n_certs = st.number_input("Quantos certificados?", min_value=0, max_value=30, value=0, step=1)

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
    st.caption("**Número da Corrida** e **Número da OP** (se informado): formato `000A0`.")

    with st.form("form_corrida", clear_on_submit=False):
        l1c1, l1c2, l1c3, l1c4, l1c5, l1c6 = st.columns(6)
        with l1c1:
            data_fusao = st.date_input(
                "Data de fusão *", value=date.today(), format=FORMATO_DATE_INPUT_BR
            )
        with l1c2:
            numero_corrida = st.text_input(
                "Número da corrida *",
                placeholder="001A6",
                help="Regex: ^\\d{3}[A-L]\\d$",
            )
        with l1c3:
            nome_cliente = st.text_input("Nome do cliente *")
        with l1c4:
            numero_of_str = st.text_input(
                "Número da OP",
                placeholder="001A6",
                help="Opcional. Mesmo padrão 000A0.",
            )
        with l1c5:
            qtd_fundidas = st.number_input("Qtd peças fundidas *", min_value=0, value=0, step=1)
        with l1c6:
            serie = st.text_input("Série das peças")

        l2c1, l2c2, l2c3, l2c4, l2c5, l2c6 = st.columns(6)
        with l2c1:
            liga = st.text_input("Liga")
        with l2c2:
            norma = st.text_input("Norma")
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
                    value="{}",
                    label_visibility="visible",
                )
        else:
            _els = ELEMENTOS_QUIMICOS
            with l3c1:
                st.number_input(_els[0], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[0]}")
            with l3c2:
                st.number_input(_els[1], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[1]}")
            with l3c3:
                st.number_input(_els[2], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[2]}")
            with l3c4:
                st.number_input(_els[3], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[3]}")
            with l3c5:
                st.number_input(_els[4], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[4]}")
            with l3c6:
                st.number_input(_els[5], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[5]}")

        if not usar_json:
            l4c1, l4c2, l4c3, l4c4, l4c5, l4c6 = st.columns(6)
            with l4c1:
                st.number_input(_els[6], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[6]}")
            with l4c2:
                st.number_input(_els[7], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[7]}")
            with l4c3:
                st.number_input(_els[8], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[8]}")
            with l4c4:
                st.number_input(_els[9], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[9]}")
            with l4c5:
                st.number_input(_els[10], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[10]}")
            with l4c6:
                st.number_input(_els[11], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[11]}")

            l5c1, l5c2, l5c3, l5c4, l5c5, l5c6 = st.columns(6)
            with l5c1:
                st.number_input(_els[12], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[12]}")
            with l5c2:
                st.number_input(_els[13], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[13]}")
            with l5c3:
                st.number_input(_els[14], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[14]}")
            with l5c4:
                st.number_input(_els[15], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[15]}")
            with l5c5:
                st.number_input(_els[16], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[16]}")
            with l5c6:
                st.number_input(_els[17], min_value=0.0, value=0.0, format="%.4f", key=f"chem_{_els[17]}")

        enviar = st.form_submit_button("Salvar corrida")

    if not enviar:
        return

    if not numero_corrida.strip() or not nome_cliente.strip():
        st.error("Preencha número da corrida e nome do cliente.")
        return

    if not codigo_op_ou_corrida_valido(numero_corrida):
        st.error(f"**Número da corrida:** {MSG_ERRO_FORMATO_OP_CORRIDA}")
        return

    nof_raw = numero_of_str.strip()
    if nof_raw and not codigo_op_ou_corrida_valido(nof_raw):
        st.error(f"**Número da OP:** {MSG_ERRO_FORMATO_OP_CORRIDA}")
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
        numero_corrida=numero_corrida.strip(),
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
        st.success(f"Corrida **{corrida.numero_corrida}** registrada em fundicao.db.")
        st.json(composicao)
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
                    by=["_sort_ano", "_sort_of"], ascending=[True, True], na_position="last"
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
                    by=["_sort_data", "_sort_c"], ascending=[True, True], na_position="last"
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
    - Remove "dev" (case-insensitive) antes de classificar.
    - Ignora qualquer texto após o padrão 000X0 (ex: "001A0 extra" → classifica como "001A0").
    - Ordena por: sufixo numérico final → letra central → número inicial.
    - Resultado: 001A6, 002A6, 003A6, 001B6, 002B6, 001C6...
    - Códigos fora do padrão vão para o final em ordem alfabética.
    """
    import re as _re
    if not codigo or not isinstance(codigo, str):
        return (9, "Z", 9999, codigo or "")
    # Remove "dev" e usa search (não fullmatch) para ignorar texto após o padrão
    limpo = _re.sub(r"(?i)dev", "", codigo.strip()).strip()
    m = _re.search(r"(\d{1,4})([A-Za-z])(\d)", limpo)
    if m:
        num, letra, sfx = m.groups()
        return (int(sfx), letra.upper(), int(num), codigo)
    return (9, "Z", 9999, codigo)

def pagina_relatorios() -> None:
    st.title("Relatórios")
    st.caption("Consultas e exportação a partir de **fundicao.db**.")

    with db_session() as db:
        ofs = list(db.scalars(select(OrdemFabricacao).order_by(OrdemFabricacao.criado_em.desc())).all())
        corridas = list(db.scalars(select(Corrida).order_by(Corrida.data_fusao.desc())).all())

    tab1, tab2, tab3, tab4 = st.tabs(["Ordens de fabricação", "Corridas", "Resumo", "⚙️ Configurações"])

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

            # Ordena: 1º pelo ANO de abertura (ignora dia e mês), 2º pela chave alfanumérica da OF
            # "dev" é ignorado na chave. Resultado: OFs do ano mais antigo primeiro,
            # dentro do mesmo ano segue 001A6, 002A6... 001B6... 001K9...
            if "Nº OF" in df.columns and "Abertura" in df.columns:
                df["_sort_ano"] = pd.to_datetime(
                    df["Abertura"], format="%d/%m/%Y", errors="coerce"
                ).dt.year.fillna(9999).astype(int)
                df["_sort_of"] = df["Nº OF"].fillna("").apply(_chave_of)
                df = df.sort_values(
                    by=["_sort_ano", "_sort_of"],
                    ascending=[True, True],
                    na_position="last",
                ).drop(columns=["_sort_ano", "_sort_of"]).reset_index(drop=True)

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
            sel_of = st.dataframe(
                df,
                height=500,
                use_container_width=True,
                hide_index=True,
                column_config=_OF_COL_CFG,
                on_select="rerun",
                selection_mode="single-row",
                key="sel_df_ofs",
            )

            buf = StringIO()
            df.to_csv(buf, index=False)
            st.download_button("⬇️ Baixar CSV — OFs completo", buf.getvalue(), file_name="relatorio_ofs.csv", mime="text/csv")

            # Identifica linha selecionada — usa o df ordenado como fonte da verdade
            _idx_of = (sel_of.selection.rows or [None])[0]
            if _idx_of is not None:
                _nof_sel = df.iloc[_idx_of]["Nº OF"] if _idx_of < len(df) else None
                if _nof_sel:
                    st.divider()
                    st.subheader(f"OF selecionada: **{_nof_sel}**")
                    _col_alt, _col_exc = st.columns(2)

                    # ── Alterar ──────────────────────────────────────────────
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
                                                    if _acao == "finalizar":
                                                        _of_save.status_of = "Finalizada"
                                                    elif _acao == "cancelar":
                                                        _of_save.status_of = "Cancelada"
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
                    with _col_exc:
                        with st.expander("🗑️ Excluir esta OF", expanded=False):
                            st.warning(f"Isso excluirá a OF **{_nof_sel}** e todos os seus registros vinculados (OEs, certificados). Esta ação **não pode ser desfeita**.")
                            if st.button(f"⚠️ Confirmar exclusão de {_nof_sel}", key=f"btn_exc_of_{_nof_sel}", type="primary"):
                                try:
                                    with db_session() as _db_del:
                                        _of_del = _db_del.scalar(
                                            select(OrdemFabricacao).where(OrdemFabricacao.numero_of == _nof_sel)
                                        )
                                        if _of_del:
                                            _db_del.delete(_of_del)
                                    st.success(f"OF **{_nof_sel}** excluída com sucesso.")
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

            # Configuração de colunas: largura adequada para cada campo
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

            # Ordena: 1º pela data de fusão (mais antiga primeiro), 2º pela chave alfanumérica
            if "Corrida" in df.columns and "Data fusão" in df.columns:
                df["_sort_data"] = pd.to_datetime(
                    df["Data fusão"], format="%d/%m/%Y", errors="coerce"
                )
                df["_sort_corrida"] = df["Corrida"].fillna("").apply(_chave_of)
                df = df.sort_values(
                    by=["_sort_data", "_sort_corrida"],
                    ascending=[True, True],
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

            # Guarda ids das corridas na mesma ordem do df
            _ids_corr = [c.id for c in corridas]
            # Reordena os ids junto com o df
            if "Corrida" in df.columns and "Data fusão" in df.columns:
                _df_ids = pd.DataFrame({"_id": [c.id for c in corridas], "Corrida": [c.numero_corrida or "" for c in corridas], "Data fusão": [_exibir_data_br(c.data_fusao) for c in corridas]})
                _df_ids["_sort_data"] = pd.to_datetime(_df_ids["Data fusão"], format="%d/%m/%Y", errors="coerce")
                _df_ids["_sort_c"]    = _df_ids["Corrida"].apply(_chave_of)
                _df_ids = _df_ids.sort_values(by=["_sort_data","_sort_c"], ascending=[True,True]).reset_index(drop=True)
                _ids_corr_ord = _df_ids["_id"].tolist()
            else:
                _ids_corr_ord = _ids_corr

            st.caption("Clique no ☐ à esquerda da linha para selecionar uma corrida e usar as opções abaixo.")
            sel_corr = st.dataframe(
                df,
                height=400,
                use_container_width=True,
                hide_index=True,
                column_config=col_config,
                on_select="rerun",
                selection_mode="single-row",
                key="sel_df_corridas",
            )

            buf = StringIO()
            df.to_csv(buf, index=False)
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

    if not st.button("✅ Confirmar importação de OFs", key="btn_confirmar_ofs"):
        return

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

    if not st.button("✅ Confirmar importação de Corridas", key="btn_confirmar_corridas"):
        return

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


def tela_importar_excel():
    st.header("📥 Importar Planilhas")
    st.caption(
        "Dois uploaders independentes: um para **Ordens de Fabricação** "
        "(`fabricacao.ordem_fabricacao`) e outro para **Corridas** (`corridas.corrida`)."
    )

    # --- Uploader 1: OFs ---
    st.subheader("1️⃣ Importar Ordens de Fabricação")
    st.caption(
        "Colunas obrigatórias: `numero_of`, `nome_cliente`, `data_abertura_pedido`. "
        "Demais colunas são opcionais — os nomes podem ser em português com espaço ou underscore."
    )
    arquivo_of = st.file_uploader(
        "Selecione a planilha de **OFs** (.xlsx)",
        type=["xlsx"],
        key="uploader_ofs",
    )
    if arquivo_of:
        _importar_ofs(arquivo_of)

    st.divider()

    # --- Uploader 2: Corridas ---
    st.subheader("2️⃣ Importar Corridas")
    st.caption(
        "Colunas obrigatórias: `data_fusao` (ou `data`), `numero_corrida` (ou `corrida`), `nome_cliente`. "
        "Elementos químicos (C, Si, Mn, …) podem ser colunas individuais na planilha."
    )
    arquivo_corrida = st.file_uploader(
        "Selecione a planilha de **Corridas** (.xlsx)",
        type=["xlsx"],
        key="uploader_corridas",
    )
    if arquivo_corrida:
        _importar_corridas(arquivo_corrida)


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
    _migrar_banco_of_status()   # garante coluna status_of
    _migrar_banco_corridas()     # garante constraint correta em bancos existentes

    if 'mostrar_importador' not in st.session_state:
        st.session_state.mostrar_importador = False

    if st.session_state.mostrar_importador:
        tela_importar_excel()
        if st.button("🏠 Voltar para Lançamentos"):
            st.session_state.mostrar_importador = False
        return

    with st.sidebar:
        st.header("Sistema de Controle de Fundição")
        ok, msg = ping_database()
        if ok:
            st.success(msg)
        else:
            st.error("Falha ao acessar o banco")
            st.caption(msg)
        st.divider()
        if st.button("📥 Importar Planilha Excel"):
            st.session_state.mostrar_importador = True
        pagina = st.radio(
            "Navegação",
            (
                "Dashboard",
                "Nova Ordem de Fabricação",
                "Lançar Corrida",
                "Consulta de Rastreabilidade",
                "Consulta de Corridas",
                "Relatórios",
            ),
            label_visibility="collapsed",
        )

    if pagina == "Dashboard":
        pagina_dashboard()
    elif pagina == "Nova Ordem de Fabricação":
        pagina_nova_of()
    elif pagina == "Lançar Corrida":
        pagina_lancar_corrida()
    elif pagina == "Consulta de Rastreabilidade":
        pagina_consulta_rastreabilidade()
    elif pagina == "Consulta de Corridas":
        pagina_consulta_corridas()
    else:
        pagina_relatorios()


main()
