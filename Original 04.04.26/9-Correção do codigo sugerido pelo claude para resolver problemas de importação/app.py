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

    tab1, tab2, tab3, tab4 = st.tabs(["Ordens de fabricação", "Corridas", "Resumo", "⚙️ Configurações"])

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
    """Renomeia colunas do DataFrame usando o mapa (case-insensitive)."""
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
    Limpeza defensiva aplicada logo após pd.read_excel + _normalizar_colunas:

    1. Substitui variações de "cancelado" por 0 nas colunas numéricas presentes.
    2. Preenche NaN em colunas de texto com "" e em colunas numéricas com 0.
    3. Converte colunas inteiras para Int64 (nullable) e decimais para float,
       forçando valores não conversíveis a NaN → depois 0.
    """
    df = df.copy()

    # Passo 1 — substitui "cancelado" (qualquer capitalização) por 0
    #           nas colunas numéricas que existirem no DataFrame
    for col in cols_int + cols_float:
        if col in df.columns:
            mask = df[col].astype(str).str.match(_RE_CANCELADO)
            df.loc[mask, col] = 0

    # Passo 2 — preenche NaN
    for col in cols_text:
        if col in df.columns:
            df[col] = df[col].fillna("")
    for col in cols_int + cols_float:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Passo 3 — conversão explícita de tipos com coerce (erros → 0)
    for col in cols_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("Int64")
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
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0).astype('Int64')
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
            df[_c] = pd.to_numeric(df[_c], errors='coerce').fillna(0).astype('Int64')
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
                db.add(corrida)  # sempre nova linha — PK é UUID gerado automaticamente
            inseridos += 1
        except IntegrityError:
            erros.append(
                f"Linha {_ + 2} — duplicidade: corrida \"{row.get('numero_corrida', '?')}\""  
                f" / OF \"{nof or '—'}\" / Série \"{serie or '—'}\" já existe no banco."
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


def _migrar_banco_corridas() -> None:
    """
    Migração automática da constraint de unicidade da tabela corrida.

    Situação anterior:  UNIQUE (numero_corrida, data_fusao)
    Situação correta:   UNIQUE (numero_corrida, data_fusao, numero_ordem_fabricacao, serie_pecas_fundidas)

    Uma mesma corrida pode fundir peças de OFs distintas no mesmo dia;
    a OF faz parte da chave de negócio, não apenas data + numero.

    Esta função é idempotente — verifica se a migração já foi feita antes de executar.
    Compatível com SQLite (usado em desenvolvimento) e PostgreSQL (produção).
    """
    try:
        import sqlalchemy
        engine = SessionLocal().bind  # type: ignore[attr-defined]
    except Exception:
        # Fallback: tenta obter engine direto
        try:
            from fundicao_db import engine as _engine
            engine = _engine
        except Exception:
            return

    dialect = engine.dialect.name  # "sqlite" ou "postgresql"

    with engine.connect() as conn:
        if dialect == "sqlite":
            # SQLite não suporta DROP INDEX com schema; busca pelo nome do índice
            indexes = conn.execute(
                sqlalchemy.text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='corrida'")
            ).fetchall()
            index_names = [r[0] for r in indexes]

            old_index = "uq_corridas_numero_data"
            new_index = "uq_corridas_numero_data_of"

            if old_index in index_names and new_index not in index_names:
                conn.execute(sqlalchemy.text(f"DROP INDEX IF EXISTS {old_index}"))
                conn.execute(sqlalchemy.text(
                    "CREATE UNIQUE INDEX uq_corridas_numero_data_of "
                    "ON corrida (numero_corrida, data_fusao, numero_ordem_fabricacao, serie_pecas_fundidas)"
                ))
                conn.commit()

        elif dialect == "postgresql":
            # PostgreSQL: verifica no information_schema
            row = conn.execute(sqlalchemy.text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname = 'corridas' AND indexname = 'uq_corridas_numero_data'"
            )).fetchone()

            if row:
                conn.execute(sqlalchemy.text(
                    "DROP INDEX IF EXISTS corridas.uq_corridas_numero_data"
                ))
                conn.execute(sqlalchemy.text(
                    "CREATE UNIQUE INDEX uq_corridas_numero_data_of "
                    "ON corridas.corrida (numero_corrida, data_fusao, numero_ordem_fabricacao, serie_pecas_fundidas)"
                ))
                conn.commit()
    # Erros silenciosos: se o banco ainda não existir, init_db() criará do zero já com o índice correto
    

def main() -> None:
    st.set_page_config(
        page_title="Controle de Fundição",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()
    _migrar_banco_corridas()  # garante constraint correta em bancos existentes

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
