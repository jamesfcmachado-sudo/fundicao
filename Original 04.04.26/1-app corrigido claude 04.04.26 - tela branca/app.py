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
    meta = of.qtd_pecas_pedido or 0
    exp = of.qtd_expedida or 0
    if meta <= 0:
        return "Sem qtd. pedido"
    if exp >= meta:
        return "Encerrada"
    if exp > 0:
        return "Expedição parcial"
    return "Aberta"


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

    linhas = []
    for of in todas:
        stt = _status_of(of)
        if stt in ("Aberta", "Expedição parcial", "Sem qtd. pedido"):
            linhas.append(
                {
                    "Status": stt,
                    "OF": of.numero_of,
                    "NN°": of.numero_nn or "",
                    "Cliente": of.nome_cliente,
                    "Abertura": _exibir_data_br(of.data_abertura_pedido),
                    "Prazo": _exibir_data_br(of.prazo_entrega_pedido) or "",
                    "Pedido": of.numero_pedido or "",
                    "Qtd pedido": of.qtd_pecas_pedido,
                    "Fundida": of.qtd_fundida,
                    "Expedida": of.qtd_expedida,
                    "Saldo": max(0, (of.qtd_pecas_pedido or 0) - (of.qtd_expedida or 0)),
                    "Liga": of.liga or "",
                    "Norma": of.norma or "",
                }
            )

    soma_pedido = sum(float(of.qtd_pecas_pedido or 0) for of in todas)
    abertas = sum(1 for r in linhas if r["Status"] == "Aberta")
    parciais = sum(1 for r in linhas if r["Status"] == "Expedição parcial")

    m2.metric("OFs em acompanhamento", len(linhas))
    m3.metric("Abertas / parciais", f"{abertas} / {parciais}")
    m4.metric("Peças pedido (total)", soma_pedido)

    st.divider()
    st.subheader("OFs abertas ou em expedição parcial")
    if not todas:
        st.info("Nenhuma OF cadastrada. Use **Nova Ordem de Fabricação**.")
    elif not linhas:
        st.info("Todas as OFs estão encerradas.")
    else:
        st.dataframe(
            formatar_datas_br(pd.DataFrame(linhas)),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("Últimas corridas")
    if not ultimas_corridas:
        st.info("Nenhuma corrida lançada.")
    else:
        lista_corridas = [
            {
                "Corrida": c.numero_corrida,
                "Data fusão": _exibir_data_br(c.data_fusao),
                "Cliente": c.nome_cliente,
                "OF (nº)": c.numero_ordem_fabricacao or "",
                "Qtd fundida": c.qtd_pecas_fundidas,
                "Série": (c.serie_pecas_fundidas or ""),
                "Liga": (c.liga or ""),
                "Norma": (c.norma or ""),
            }
            for c in ultimas_corridas
        ]
        df_corridas = pd.DataFrame(lista_corridas)
        st.dataframe(formatar_datas_br(df_corridas), use_container_width=True, hide_index=True)


def pagina_nova_of() -> None:
    st.title("Nova Ordem de Fabricação")
    st.caption("Dados gravados em **fundicao.db** (tabelas `ordem_fabricacao`, `ordem_entrega`, `certificado_peca`).")

    if st.session_state.get("nova_of_sucesso"):
        st.success(st.session_state["nova_of_sucesso"])
        if st.button("Fechar mensagem", key="btn_fechar_sucesso_of"):
            del st.session_state["nova_of_sucesso"]
            st.rerun()

    st.markdown("##### Ordens de entrega (OE) e certificados")
    st.caption("Defina quantas linhas deseja preencher (fora do formulário principal).")
    colx, coly = st.columns(2)
    with colx:
        n_oes = st.number_input("Quantas OEs?", min_value=0, max_value=30, value=0, step=1)
    with coly:
        n_certs = st.number_input("Quantos certificados?", min_value=0, max_value=30, value=0, step=1)

    with st.form("form_nova_of", clear_on_submit=True):
        st.markdown("##### Dados da OF")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("**Número da OP:** formato `000A0` — 3 dígitos + letra A–L + 1 dígito.")
            numero_of = st.text_input(
                "Número da OP *",
                placeholder="001A6",
                help="Regex: ^\\d{3}[A-L]\\d$ — apenas maiúsculas na letra central.",
            )
            numero_nn = st.text_input("NN°")
            nome_cliente = st.text_input("Nome do Cliente *")
            data_abertura = st.date_input(
                "Data de abertura do pedido *",
                value=date.today(),
                format=FORMATO_DATE_INPUT_BR,
            )
            tem_prazo = st.checkbox("Informar prazo de entrega do pedido", value=False)
            prazo_entrega = (
                st.date_input(
                    "Prazo de entrega do pedido",
                    value=date.today(),
                    format=FORMATO_DATE_INPUT_BR,
                )
                if tem_prazo
                else None
            )
            numero_pedido = st.text_input("Número do pedido")
            numero_modelo = st.text_input("Número do modelo")
        with c2:
            descricao_peca = st.text_area("Descrição da peça")
            numero_desenho = st.text_input("Número do desenho")
            peso_liquido = st.number_input("Peso líquido (kg)", min_value=0.0, value=0.0, format="%.4f")
            peso_bruto = st.number_input("Peso bruto (kg)", min_value=0.0, value=0.0, format="%.4f")
            liga = st.text_input("Liga")
            norma = st.text_input("Norma")
            qtd_pedido = st.number_input("Quantidade de peças do pedido *", min_value=0, value=0, step=1)
            qtd_fundida = st.number_input("Qtde fundida", min_value=0, value=0, step=1)
            qtd_expedida = st.number_input("Qtde expedida", min_value=0, value=0, step=1)

        valor_unit = st.number_input("Valor unitário", min_value=0.0, value=0.0, format="%.6f")
        valor_total = st.number_input("Valor total", min_value=0.0, value=0.0, format="%.2f")
        condicao_modelo = st.text_input("Condição do modelo")
        observacoes = st.text_area("Observações gerais da OF")

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
                        min_value=0,
                        value=0,
                        step=1,
                        key=f"ce_q_{i}",
                    )

        enviar = st.form_submit_button("Salvar no banco de dados")

    if not enviar:
        return

    if not numero_of.strip() or not nome_cliente.strip():
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
        nome_cliente=nome_cliente.strip(),
        data_abertura_pedido=data_abertura,
        prazo_entrega_pedido=prazo_entrega,
        numero_pedido=numero_pedido.strip() or None,
        numero_modelo=numero_modelo.strip() or None,
        descricao_peca=descricao_peca.strip() or None,
        numero_desenho=numero_desenho.strip() or None,
        peso_liquido_kg=Decimal(str(peso_liquido)) if peso_liquido else None,
        peso_bruto_kg=Decimal(str(peso_bruto)) if peso_bruto else None,
        liga=liga.strip() or None,
        norma=norma.strip() or None,
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
    base_opts = selectinload(OrdemFabricacao.ordens_entrega)

    if tipo == "join_oe":
        v = str(valor_busca).strip()
        stmt = (
            select(OrdemFabricacao)
            .options(base_opts)
            .join(OrdemEntrega, OrdemEntrega.ordem_fabricacao_id == OrdemFabricacao.id)
            .where(OrdemEntrega.numero_oe.ilike(f"%{v}%"))
        )
        return list(db.scalars(stmt).unique().all())

    if tipo == "join_cert":
        v = str(valor_busca).strip()
        stmt = (
            select(OrdemFabricacao)
            .options(base_opts)
            .join(CertificadoPeca, CertificadoPeca.ordem_fabricacao_id == OrdemFabricacao.id)
            .where(CertificadoPeca.numero_certificado.ilike(f"%{v}%"))
        )
        return list(db.scalars(stmt).unique().all())

    col = getattr(OrdemFabricacao, attr)
    stmt = select(OrdemFabricacao).options(base_opts)

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
    rows: list[dict] = []
    for of in ofs:
        base = {
            "OF": of.numero_of,
            "NN°": of.numero_nn or "",
            "Cliente": of.nome_cliente,
            "Data abertura": _exibir_data_br(of.data_abertura_pedido),
            "Prazo entrega": _exibir_data_br(of.prazo_entrega_pedido) or "",
            "Nº pedido": of.numero_pedido or "",
            "Nº modelo": of.numero_modelo or "",
            "Descrição peça": (of.descricao_peca or "")[:80],
            "Nº desenho": of.numero_desenho or "",
            "Peso líq.": float(of.peso_liquido_kg) if of.peso_liquido_kg is not None else None,
            "Peso bruto": float(of.peso_bruto_kg) if of.peso_bruto_kg is not None else None,
            "Liga": of.liga or "",
            "Norma": of.norma or "",
            "Qtd pedido": of.qtd_pecas_pedido,
            "Qtde fundida": of.qtd_fundida,
            "Qtde expedida": of.qtd_expedida,
            "Valor unit.": float(of.valor_unitario) if of.valor_unitario is not None else None,
            "Valor total": float(of.valor_total) if of.valor_total is not None else None,
            "Condição modelo": of.condicao_modelo or "",
        }
        if not of.ordens_entrega:
            rows.append({**base, "OE (nº)": "—", "Data OE": "", "Qtd OE": None})
        else:
            for oe in of.ordens_entrega:
                rows.append(
                    {
                        **base,
                        "OE (nº)": oe.numero_oe,
                        "Data OE": _exibir_data_br(_data_oe_para_tabela(oe)),
                        "Qtd OE": oe.qtd_pecas,
                    }
                )
    return pd.DataFrame(rows)


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
                if not ofs:
                    st.session_state["rastreio_df"] = None
                    st.session_state["rastreio_vazio"] = True
                else:
                    st.session_state["rastreio_df"] = _montar_df_rastreabilidade(ofs)
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
            st.dataframe(formatar_datas_br(st.session_state["rastreio_df"]), use_container_width=True, hide_index=True)


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
    rows: list[dict] = []
    for c in corridas:
        rows.append(
            {
                "id": c.id,
                "Data de fusão": _exibir_data_br(c.data_fusao),
                "Número da corrida": c.numero_corrida,
                "Nome do cliente": c.nome_cliente,
                "ID ordem fabricação (UUID)": c.ordem_fabricacao_id or "",
                "Número da Ordem de fabricação": c.numero_ordem_fabricacao or "",
                "Quantidade de peças fundidas": c.qtd_pecas_fundidas,
                "Série das peças fundidas": c.serie_pecas_fundidas or "",
                "Liga": c.liga or "",
                "Norma": c.norma or "",
                "Composição química (JSON)": json.dumps(c.composicao_quimica_pct, ensure_ascii=False),
                "Criado em": _exibir_data_br(c.criado_em),
                "Atualizado em": _exibir_data_br(c.atualizado_em),
            }
        )
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
            st.dataframe(formatar_datas_br(st.session_state["corr_consulta_df"]), use_container_width=True, hide_index=True)


def pagina_relatorios() -> None:
    st.title("Relatórios")
    st.caption("Consultas e exportação a partir de **fundicao.db**.")

    with db_session() as db:
        ofs = list(db.scalars(select(OrdemFabricacao).order_by(OrdemFabricacao.criado_em.desc())).all())
        corridas = list(db.scalars(select(Corrida).order_by(Corrida.data_fusao.desc())).all())

    tab1, tab2, tab3 = st.tabs(["Ordens de fabricação", "Corridas", "Resumo"])

    with tab1:
        if not ofs:
            st.info("Nenhuma OF para exibir.")
        else:
            rows = []
            for of in ofs:
                rows.append(
                    {
                        "OF": of.numero_of,
                        "NN°": of.numero_nn,
                        "Cliente": of.nome_cliente,
                        "Abertura": _exibir_data_br(of.data_abertura_pedido),
                        "Prazo": _exibir_data_br(of.prazo_entrega_pedido) or "",
                        "Pedido": of.numero_pedido,
                        "Modelo": of.numero_modelo,
                        "Qtd pedido": of.qtd_pecas_pedido,
                        "Fundida": of.qtd_fundida,
                        "Expedida": of.qtd_expedida,
                        "Valor total": float(of.valor_total) if of.valor_total is not None else None,
                        "Status": _status_of(of),
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(formatar_datas_br(df), use_container_width=True, hide_index=True)
            buf = StringIO()
            df.to_csv(buf, index=False)
            st.download_button("Baixar CSV — OFs", buf.getvalue(), file_name="relatorio_ofs.csv", mime="text/csv")

    with tab2:
        if not corridas:
            st.info("Nenhuma corrida para exibir.")
        else:
            rows = []
            for c in corridas:
                rows.append(
                    {
                        "Corrida": c.numero_corrida,
                        "Data fusão": _exibir_data_br(c.data_fusao),
                        "Cliente": c.nome_cliente,
                        "OF": c.numero_ordem_fabricacao,
                        "Qtd fundida": c.qtd_pecas_fundidas,
                        "Série": c.serie_pecas_fundidas,
                        "Liga": c.liga,
                        "Norma": c.norma,
                        "Composição (JSON)": json.dumps(c.composicao_quimica_pct, ensure_ascii=False),
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(formatar_datas_br(df), use_container_width=True, hide_index=True)
            buf = StringIO()
            df.to_csv(buf, index=False)
            st.download_button(
                "Baixar CSV — corridas", buf.getvalue(), file_name="relatorio_corridas.csv", mime="text/csv"
            )

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


def tela_importar_excel():
    st.header("📥 Importar Planilha de Produção")
    arquivo_subido = st.file_uploader("Arraste seu arquivo .xlsx aqui", type=['xlsx'])
    if arquivo_subido:
        df_temp = pd.read_excel(arquivo_subido)
        st.info("Prévia dos dados da planilha:")
        st.dataframe(formatar_datas_br(df_temp.head()))
        if st.button("Gravar tudo no Sistema"):
            with sqlite3.connect('fundicao.db') as conn:
                df_temp.to_sql('corridas', conn, if_exists='append', index=False)
                st.success("Dados importados com sucesso!")


def main() -> None:
    st.set_page_config(
        page_title="Controle de Fundição",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()

    if 'mostrar_importador' not in st.session_state:
        st.session_state.mostrar_importador = False

    if st.session_state.mostrar_importador:
        st.header("📥 Importar Dados da Produção (Excel)")
        arquivo_excel = st.file_uploader("Selecione o arquivo .xlsx", type=['xlsx'])
        if arquivo_excel:
            try:
                df_import = pd.read_excel(arquivo_excel)
                st.write("Visualização dos dados encontrados:")
                st.dataframe(formatar_datas_br(df_import.head()))
                if st.button("Confirmar Carga no Banco de Dados"):
                    with sqlite3.connect('fundicao.db') as conn:
                        df_import.to_sql('corridas', conn, if_exists='append', index=False)
                    st.success(f"Show! {len(df_import)} registros foram adicionados ao sistema.")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo: {e}")
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
