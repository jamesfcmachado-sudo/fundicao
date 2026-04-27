"""
certificados.py
===============
Módulo de Certificados de Qualidade para o sistema de controle de fundição.
Inclui: criação, consulta, ensaios mecânicos e geração de PDF.
v2026.04.26
"""
from __future__ import annotations
import io
import json
from datetime import datetime, date
from sqlalchemy import text
import streamlit as st
import pandas as pd


def _get_engine():
    from fundicao_db import engine
    return engine


# ── Inicializa tabelas no banco ───────────────────────────────────────────────
def init_certificados_db() -> None:
    engine = _get_engine()
    with engine.begin() as conn:
        # Tabela principal do certificado
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS certificado_qualidade (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                numero_cert     VARCHAR(30) NOT NULL UNIQUE,
                ano             SMALLINT NOT NULL,
                seq             INTEGER NOT NULL,
                cliente         VARCHAR(200),
                norma           VARCHAR(100),
                liga            VARCHAR(50),
                projeto         VARCHAR(200),
                data_emissao    DATE,
                nota_fiscal     VARCHAR(100),
                observacoes     TEXT,
                outros_ensaios  TEXT,
                tipo_template   VARCHAR(20) DEFAULT 'sem_ensaio',
                criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # Corridas vinculadas ao certificado
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS certificado_corrida (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                certificado_id  UUID NOT NULL REFERENCES certificado_qualidade(id) ON DELETE CASCADE,
                numero_of       VARCHAR(20),
                numero_corrida  VARCHAR(20),
                C NUMERIC(8,4), Si NUMERIC(8,4), Mn NUMERIC(8,4),
                P NUMERIC(8,4), S NUMERIC(8,4), Cr NUMERIC(8,4),
                Ni NUMERIC(8,4), Mo NUMERIC(8,4), Cu NUMERIC(8,4),
                W NUMERIC(8,4), Nb NUMERIC(8,4), V NUMERIC(8,4),
                Fe NUMERIC(8,4), CE NUMERIC(8,4), N NUMERIC(8,4),
                Mg NUMERIC(8,4), B NUMERIC(8,4),
                criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # Itens do certificado (pedido/modelo/descricao/series/qtd)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS certificado_item (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                certificado_id  UUID NOT NULL REFERENCES certificado_qualidade(id) ON DELETE CASCADE,
                pedido          VARCHAR(100),
                modelo          VARCHAR(100),
                descricao       VARCHAR(200),
                series          VARCHAR(50),
                quantidade      INTEGER,
                criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # Ensaios Mecânicos vinculados à corrida
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ensaio_mecanico (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                numero_corrida  VARCHAR(20) NOT NULL,
                numero_of       VARCHAR(20),
                certificado_id  UUID REFERENCES certificado_qualidade(id) ON DELETE SET NULL,
                lim_resistencia NUMERIC(10,2),
                lim_escoamento  NUMERIC(10,2),
                alongamento     NUMERIC(8,2),
                red_area        NUMERIC(8,2),
                impacto_j1      NUMERIC(8,2),
                impacto_j2      NUMERIC(8,2),
                impacto_j3      NUMERIC(8,2),
                temperatura     NUMERIC(8,2),
                observacoes     TEXT,
                criado_em       TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))


def _proximo_numero_cert() -> tuple[int, int, str]:
    """Retorna (seq, ano, numero_formatado) para o próximo certificado."""
    ano = datetime.now().year % 100
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT MAX(seq) FROM certificado_qualidade WHERE ano = :ano
        """), {"ano": ano}).fetchone()
    seq = (row[0] or 0) + 1
    return seq, ano, f"{seq:04d}/{ano:02d}"


# ── Tela Novo Certificado ─────────────────────────────────────────────────────
def tela_novo_certificado():
    # Verifica modo edicao
    _modo_ed = st.session_state.get("_modo_edicao_cert_id", "")
    _modo_ed_num = st.session_state.get("_modo_edicao_cert_num", "")

    if _modo_ed:
        st.title(f"✏️ Editando Certificado {_modo_ed_num}")
        st.warning(f"⚠️ Você está editando o certificado **{_modo_ed_num}**. "
                   f"Ao salvar, os dados serão atualizados no banco.")
        if st.button("❌ Cancelar edição e criar novo", key="btn_cancelar_modo_ed"):
            for _k in list(st.session_state.keys()):
                if _k.startswith("cert_") or _k.startswith("_modo_edicao") or _k.startswith("_cert_"):
                    st.session_state.pop(_k, None)
            st.rerun()
    else:
        st.title("🏅 Novo Certificado de Qualidade")

    engine = _get_engine()

    # Tipo de template
    _tipo_raw = st.radio(
        "Tipo de certificado:",
        options=["sem_ensaio", "com_ensaio"],
        format_func=lambda x: "Sem Ensaio Mecânico" if x == "sem_ensaio" else "Com Ensaio Mecânico",
        horizontal=True,
        key="tipo_cert"
    )
    # Garante que tipo seja sempre string
    tipo = str(_tipo_raw) if not isinstance(_tipo_raw, dict) else (
        "com_ensaio" if _tipo_raw.get("com_ensaio") else "sem_ensaio"
    )

    # ── Número do certificado editável ──────────────────────────────────────
    seq, ano, num_cert_sug = _proximo_numero_cert()

    with st.container(border=True):
        st.subheader("Identificação")
        _id1, _id2 = st.columns(2)
        with _id1:
            num_cert = st.text_input(
                "🔢 Nº do Certificado *",
                value=num_cert_sug,
                help=f"Último gerado: {num_cert_sug}. Edite se necessário.",
                key="cert_numero_edit"
            )
        with _id2:
            # Busca OFs do banco
            try:
                with engine.connect() as _conn_ac:
                    _ofs_ac = _conn_ac.execute(text(
                        "SELECT numero_of, nome_cliente, norma, liga "
                        "FROM ordem_fabricacao ORDER BY numero_of"
                    )).fetchall()
                    _ofs_dict = {r[0]: {"cliente": r[1] or "", "norma": r[2] or "", "liga": r[3] or ""}
                                 for r in _ofs_ac}
                    _ofs_lista = list(_ofs_dict.keys())
            except Exception:
                _ofs_dict = {}
                _ofs_lista = []

            _of_cert = st.text_input(
                "📋 Nº da OF *",
                placeholder="Ex: 015B6",
                help="Informe a OF para buscar cliente, norma e liga automaticamente.",
                key="cert_of_ref"
            )
            # Sugestoes de OF
            if _of_cert.strip():
                _sugestoes_of = [o for o in _ofs_lista if _of_cert.strip().upper() in o.upper()][:5]
                if _sugestoes_of and _of_cert.strip() not in _ofs_dict:
                    st.caption(f"Sugestões: {', '.join(_sugestoes_of)}")

        if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
            _of_data = _ofs_dict[_of_cert.strip()]
            st.session_state["_cert_of_data"] = _of_data
            st.success(f"✅ OF {_of_cert.strip()} — Cliente: {_of_data['cliente']}")
        elif st.session_state.get("_cert_of_data") and _of_cert.strip():
            _of_data = st.session_state["_cert_of_data"]
        else:
            _of_data = {"cliente": "", "norma": "", "liga": ""}
            if not _of_cert.strip():
                st.session_state.pop("_cert_of_data", None)

    # ── Dados principais ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Dados Gerais")

        # Busca clientes para autocomplete
        try:
            with engine.connect() as _conn_cli:
                _clientes_ac = _conn_cli.execute(text(
                    "SELECT DISTINCT nome_cliente FROM ordem_fabricacao "
                    "WHERE nome_cliente IS NOT NULL ORDER BY nome_cliente"
                )).fetchall()
                _clientes_lista = [r[0] for r in _clientes_ac]
        except Exception:
            _clientes_lista = []

        # Preenche automaticamente a partir da OF
        _cliente_auto = _of_data.get("cliente", "")
        _norma_auto   = _of_data.get("norma", "")
        _liga_auto    = _of_data.get("liga", "")

        c1, c2, c3 = st.columns(3)
        with c1:
            # Cliente com autocomplete
            _cliente_default = _of_data["cliente"] or ""
            cliente = st.selectbox(
                "Cliente *",
                options=[""] + _clientes_lista,
                index=(_clientes_lista.index(_cliente_default) + 1)
                      if _cliente_default in _clientes_lista else 0,
                key="cert_cliente"
            )
            if not cliente:
                cliente = st.text_input("Ou digite o cliente", key="cert_cliente_manual")
        with c2:
            norma = st.text_input("Norma da Liga",
                value=_of_data["norma"],
                placeholder="Ex: ASTM-A351 (CF8)",
                key="cert_norma")
        with c3:
            liga = st.text_input("Liga",
                value=_of_data["liga"],
                placeholder="Ex: CF8", key="cert_liga")

        c4, c5, c6 = st.columns(3)
        with c4:
            projeto = st.text_input("Projeto", key="cert_projeto")
        with c5:
            data_emissao = st.date_input("Data de Emissão", value=date.today(),
                                          format="DD/MM/YYYY", key="cert_data")
        with c6:
            nota_fiscal = st.text_input("Nota Fiscal", key="cert_nf")

    # ── Corridas e Composição Química ─────────────────────────────────────────
    with st.container(border=True):
        st.subheader("I - Composição Química (Corridas)")
        st.caption("Informe OF e Corrida, depois clique em 🔍 para buscar a composição.")

        n_corridas = st.number_input("Número de corridas", min_value=1, max_value=15,
                                      value=1, key="cert_n_corridas")
        corridas = []
        ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","CE"]

        for i in range(int(n_corridas)):
            with st.container(border=True):
                st.caption(f"Corrida {i+1}")
                cc1, cc2, cc3 = st.columns([2, 2, 1])
                with cc1:
                    nof_corr = st.text_input("OF", key=f"cert_of_{i}")
                with cc2:
                    num_corr = st.text_input("Nº Corrida", key=f"cert_corr_{i}")
                with cc3:
                    st.write("")
                    st.write("")
                    _btn_buscar = st.button("🔍 Buscar",
                                            key=f"btn_comp_{i}",
                                            help="Busca composição química desta corrida")

                _key_comp = f"_cert_comp_corrida_{i}"

                if _btn_buscar and num_corr.strip():
                    try:
                        with engine.connect() as _conn_comp:
                            _rc = _conn_comp.execute(text("""
                                SELECT composicao_quimica_pct
                                FROM corrida
                                WHERE numero_corrida = :nc
                                AND composicao_quimica_pct IS NOT NULL
                                AND composicao_quimica_pct::text != '{}'
                                ORDER BY criado_em DESC LIMIT 1
                            """), {"nc": num_corr.strip()}).fetchone()
                            if _rc and _rc[0]:
                                raw = _rc[0]
                                _comp_found = raw if isinstance(raw, dict) else json.loads(raw)
                                st.session_state[_key_comp] = _comp_found
                                st.success(f"✅ Composição da corrida {num_corr.strip()} carregada!")
                            else:
                                st.warning(f"Corrida {num_corr.strip()} sem composição.")
                    except Exception as _e:
                        st.warning(f"Erro: {_e}")
                elif _key_comp in st.session_state:
                    st.success(f"✅ Composição carregada — {num_corr.strip()}")

                # Tabela editável de composição química
                _comp_loaded = st.session_state.get(_key_comp, {})
                if _comp_loaded:
                    import pandas as _pd_comp
                    _comp_df = _pd_comp.DataFrame([{
                        el: float(_comp_loaded.get(el, 0.0) or 0.0)
                        for el in ELEM
                    }])
                    _comp_edited = st.data_editor(
                        _comp_df,
                        key=f"cert_comp_table_{i}",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            el: st.column_config.NumberColumn(
                                el, format="%.4f", min_value=0.0
                            ) for el in ELEM
                        }
                    )
                    comp_editada = {el: float(_comp_edited.iloc[0][el] or 0.0)
                                    for el in ELEM}
                else:
                    st.caption("Digite o número da corrida e clique 🔍 Buscar")
                    comp_editada = {el: 0.0 for el in ELEM}

                corridas.append({
                    "num_of": nof_corr.strip(),
                    "num_corrida": num_corr.strip(),
                    "comp": comp_editada
                })

    # ── Ensaios Mecânicos (só se com_ensaio) ──────────────────────────────────
    ensaios_cert = []
    if tipo == "com_ensaio":
        with st.container(border=True):
            st.subheader("II - Propriedades Mecânicas (Ensaios)")
            n_ensaios = st.number_input("Número de ensaios", min_value=1, max_value=10,
                                         value=1, key="cert_n_ensaios")
            for i in range(int(n_ensaios)):
                with st.container(border=True):
                    st.caption(f"Ensaio {i+1}")
                    e1, e2, e3, e4 = st.columns(4)
                    with e1:
                        lim_res = st.number_input("Lim. Resistência (MPa)",
                            value=0.0, key=f"cert_lim_res_{i}")
                        lim_esc = st.number_input("Lim. Escoamento (MPa)",
                            value=0.0, key=f"cert_lim_esc_{i}")
                    with e2:
                        along = st.number_input("Alongamento (%)",
                            value=0.0, key=f"cert_along_{i}")
                        red_area = st.number_input("Red. Área (%)",
                            value=0.0, key=f"cert_red_{i}")
                    with e3:
                        j1 = st.number_input("Impacto J1",
                            value=0.0, key=f"cert_j1_{i}")
                        j2 = st.number_input("Impacto J2",
                            value=0.0, key=f"cert_j2_{i}")
                        j3 = st.number_input("Impacto J3",
                            value=0.0, key=f"cert_j3_{i}")
                    with e4:
                        temp = st.number_input("Temperatura",
                            value=0.0, key=f"cert_temp_{i}")
                    ensaios_cert.append({
                        "lim_res": lim_res, "lim_esc": lim_esc,
                        "along": along, "red_area": red_area,
                        "j1": j1, "j2": j2, "j3": j3, "temp": temp
                    })

    # ── Busca dados da OF para preencher itens ───────────────────────────────
    _pedido_auto  = ""
    _modelo_auto  = ""
    _descricao_auto = ""
    _of_key = f"_cert_of_item_{_of_cert.strip()}"

    if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
        # Verifica se ja tem no session_state
        if _of_key not in st.session_state:
            try:
                with engine.connect() as _conn_of_item:
                    _of_item = _conn_of_item.execute(text("""
                        SELECT numero_pedido, numero_modelo,
                               descricao_peca, numero_desenho
                        FROM ordem_fabricacao WHERE numero_of = :of
                    """), {"of": _of_cert.strip()}).fetchone()
                    if _of_item:
                        st.session_state[_of_key] = {
                            "pedido":   str(_of_item[0] or ""),
                            "modelo":   str(_of_item[1] or ""),
                            "descricao": str(_of_item[2] or _of_item[3] or ""),
                        }
            except Exception:
                pass

        _of_item_data = st.session_state.get(_of_key, {})
        _pedido_auto   = _of_item_data.get("pedido", "")
        _modelo_auto   = _of_item_data.get("modelo", "")
        _descricao_auto = _of_item_data.get("descricao", "")

        # Seta no session_state para os campos renderizados
        n_itens_atual = int(st.session_state.get("cert_n_itens", 1))
        for _ii in range(n_itens_atual):
            if f"cert_ped_{_ii}" not in st.session_state or not st.session_state.get(f"cert_ped_{_ii}"):
                st.session_state[f"cert_ped_{_ii}"] = _pedido_auto
            if f"cert_mod_{_ii}" not in st.session_state or not st.session_state.get(f"cert_mod_{_ii}"):
                st.session_state[f"cert_mod_{_ii}"] = _modelo_auto
            if f"cert_desc_{_ii}" not in st.session_state or not st.session_state.get(f"cert_desc_{_ii}"):
                st.session_state[f"cert_desc_{_ii}"] = _descricao_auto

    # Busca ultima serie emitida para esta OF nos certificados anteriores
    def _proxima_serie(of_num, qtd_nova):
        """Retorna (inicio, fim, serie_str) para a proxima serie."""
        if not of_num:
            return 1, qtd_nova, f"1 A {qtd_nova}" if qtd_nova > 1 else "1"
        try:
            with engine.connect() as _conn_s:
                # Busca o maior numero de serie ja emitido para esta OF
                _rows_s = _conn_s.execute(text("""
                    SELECT ci.series, ci.quantidade
                    FROM certificado_item ci
                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                    WHERE cc.numero_of = :of
                    AND ci.series IS NOT NULL AND ci.series != ''
                    ORDER BY cq.criado_em DESC
                """), {"of": of_num}).fetchall()

                ultimo = 0
                for _rs in _rows_s:
                    serie_str = str(_rs[0] or "")
                    # Extrai o ultimo numero da serie (ex: "1 A 20" -> 20)
                    import re as _re
                    nums = _re.findall(r'\d+', serie_str)
                    if nums:
                        ultimo = max(ultimo, max(int(n) for n in nums))

                inicio = ultimo + 1
                fim = ultimo + qtd_nova
                serie_str = f"{inicio} A {fim}" if qtd_nova > 1 else str(inicio)
                return inicio, fim, serie_str
        except Exception:
            return 1, qtd_nova, f"1 A {qtd_nova}" if qtd_nova > 1 else "1"

    # ── Itens (Pedido/Modelo/Descrição/Qtd/Séries) ────────────────────────────
    with st.container(border=True):
        st.subheader("III - Outros Dados (Itens)")
        n_itens = st.number_input("Número de itens", min_value=1, max_value=20,
                                   value=1, key="cert_n_itens")
        itens_cert = []
        _serie_acumulada = 0  # acumula series dentro do mesmo certificado

        for i in range(int(n_itens)):
            with st.container(border=True):
                st.caption(f"Item {i+1}")
                ir1, ir2, ir3 = st.columns([2, 2, 3])
                with ir1:
                    pedido = st.text_input("Pedido/Item",
                        value=_pedido_auto, key=f"cert_ped_{i}")
                with ir2:
                    modelo = st.text_input("Modelo",
                        value=_modelo_auto, key=f"cert_mod_{i}")
                with ir3:
                    descricao = st.text_input("Descrição",
                        value=_descricao_auto, key=f"cert_desc_{i}")

                ir4, ir5 = st.columns([1, 2])
                with ir4:
                    qtd = st.number_input("Quantidade", min_value=0, value=0,
                                           key=f"cert_qtd_{i}")
                with ir5:
                    # Calcula e seta serie no session_state
                    _qtd_atual = st.session_state.get(f"cert_qtd_{i}", 0)
                    if _qtd_atual > 0 and not st.session_state.get(f"cert_serie_{i}"):
                        try:
                            import re as _re3
                            with engine.connect() as _conn_s3:
                                _rows_s3 = _conn_s3.execute(text("""
                                    SELECT ci.series
                                    FROM certificado_item ci
                                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                                    WHERE cc.numero_of = :of
                                    AND ci.series IS NOT NULL AND ci.series != ''
                                    ORDER BY cq.criado_em DESC
                                """), {"of": _of_cert.strip() or ""}).fetchall()
                                _ult = 0
                                for _rs3 in _rows_s3:
                                    _ns = _re3.findall(r'\d+', str(_rs3[0] or ""))
                                    if _ns:
                                        _ult = max(_ult, max(int(n) for n in _ns))
                                _ini = _ult + _serie_acumulada + 1
                                _fim2 = _ini + _qtd_atual - 1
                                _sa = f"{_ini} A {_fim2}" if _qtd_atual > 1 else str(_ini)
                                st.session_state[f"cert_serie_{i}"] = _sa
                        except Exception:
                            pass

                    # Calcula serie automaticamente
                    if qtd > 0:
                        _of_para_serie = _of_cert.strip() if _of_cert.strip() else ""
                        # Calcula inicio considerando acumulado no certificado atual
                        try:
                            with engine.connect() as _conn_s2:
                                _rows_s2 = _conn_s2.execute(text("""
                                    SELECT ci.series
                                    FROM certificado_item ci
                                    JOIN certificado_qualidade cq ON cq.id = ci.certificado_id
                                    JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                                    WHERE cc.numero_of = :of
                                    AND ci.series IS NOT NULL AND ci.series != ''
                                    ORDER BY cq.criado_em DESC
                                """), {"of": _of_para_serie}).fetchall()
                                import re as _re2
                                _ultimo = 0
                                for _rs2 in _rows_s2:
                                    nums2 = _re2.findall(r'\d+', str(_rs2[0] or ""))
                                    if nums2:
                                        _ultimo = max(_ultimo, max(int(n) for n in nums2))
                                _inicio = _ultimo + _serie_acumulada + 1
                                _fim = _inicio + qtd - 1
                                _serie_auto = f"{_inicio} A {_fim}" if qtd > 1 else str(_inicio)
                        except Exception:
                            _inicio = _serie_acumulada + 1
                            _fim = _serie_acumulada + qtd
                            _serie_auto = f"{_inicio} A {_fim}" if qtd > 1 else str(_inicio)
                    else:
                        _serie_auto = ""

                    series = st.text_input("Série",
                        value=_serie_auto,
                        key=f"cert_serie_{i}",
                        help="Preenchido automaticamente. Edite se necessário.")

                if qtd > 0:
                    _serie_acumulada += qtd

            itens_cert.append({
                "pedido": pedido, "modelo": modelo,
                "descricao": descricao, "series": series, "quantidade": qtd
            })

    # ── Observações e Outros Ensaios ──────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Observações e Outros Ensaios")
        obs = st.text_area("Observações", key="cert_obs", height=80)
        outros = st.text_area("Outros Ensaios", key="cert_outros", height=80)

    # ── Salvar ────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("💾 Salvar Certificado", type="primary", key="btn_salvar_cert"):
        if not cliente.strip():
            st.error("Informe o cliente.")
            return
        try:
            import uuid as _uuid
            now = datetime.now().astimezone()
            _cert_id_edicao = st.session_state.get("_modo_edicao_cert_id", "")
            cert_id = _cert_id_edicao if _cert_id_edicao else str(_uuid.uuid4())
            _eh_edicao = bool(_cert_id_edicao)

            with engine.begin() as conn:
                # Insere ou atualiza certificado
                if _eh_edicao:
                    conn.execute(text("""
                        UPDATE certificado_qualidade SET
                            cliente=:cliente, norma=:norma, liga=:liga,
                            nota_fiscal=:nota_fiscal, observacoes=:observacoes,
                            outros_ensaios=:outros_ensaios,
                            tipo_template=:tipo,
                            atualizado_em=:now
                        WHERE id=:id
                    """), {"cliente": cliente, "norma": norma, "liga": liga,
                           "nota_fiscal": nf, "observacoes": obs,
                           "outros_ensaios": outros, "tipo": tipo,
                           "now": now, "id": cert_id})
                    # Remove corridas e itens antigos
                    conn.execute(text("DELETE FROM certificado_corrida WHERE certificado_id=:id"), {"id": cert_id})
                    conn.execute(text("DELETE FROM certificado_item WHERE certificado_id=:id"), {"id": cert_id})
                    conn.execute(text("DELETE FROM ensaio_mecanico WHERE certificado_id=:id"), {"id": cert_id})
                else:
                    conn.execute(text("""
                    INSERT INTO certificado_qualidade (
                        id, numero_cert, ano, seq, cliente, norma, liga,
                        projeto, data_emissao, nota_fiscal, observacoes,
                        outros_ensaios, tipo_template, criado_em
                    ) VALUES (
                        :id, :num, :ano, :seq, :cli, :norma, :liga,
                        :proj, :data, :nf, :obs, :outros, :tipo, :now
                    )
                """), {
                    "id": cert_id, "num": num_cert, "ano": ano, "seq": seq,
                    "cli": cliente.strip(), "norma": norma.strip(),
                    "liga": liga.strip(), "proj": projeto.strip(),
                    "data": data_emissao, "nf": nota_fiscal.strip(),
                    "obs": obs.strip(), "outros": outros.strip(),
                    "tipo": str(tipo) if not isinstance(tipo, dict) else ("com_ensaio" if tipo.get("com_ensaio") else "sem_ensaio"), "now": now
                })

                # Insere corridas — colunas em minusculas no PostgreSQL
                for c in corridas:
                    if c["num_corrida"]:
                        comp = c["comp"]
                        conn.execute(text("""
                            INSERT INTO certificado_corrida (
                                certificado_id, numero_of, numero_corrida,
                                c, si, mn, p, s, cr, ni, mo,
                                cu, w, nb, v, fe, ce
                            ) VALUES (
                                :cid, :nof, :nc,
                                :c, :si, :mn, :p, :s, :cr, :ni, :mo,
                                :cu, :w, :nb, :v, :fe, :ce
                            )
                        """), {
                            "cid": cert_id,
                            "nof": c["num_of"],
                            "nc":  c["num_corrida"],
                            "c":   float(comp.get("C", 0) or 0),
                            "si":  float(comp.get("Si", 0) or 0),
                            "mn":  float(comp.get("Mn", 0) or 0),
                            "p":   float(comp.get("P", 0) or 0),
                            "s":   float(comp.get("S", 0) or 0),
                            "cr":  float(comp.get("Cr", 0) or 0),
                            "ni":  float(comp.get("Ni", 0) or 0),
                            "mo":  float(comp.get("Mo", 0) or 0),
                            "cu":  float(comp.get("Cu", 0) or 0),
                            "w":   float(comp.get("W", 0) or 0),
                            "nb":  float(comp.get("Nb", 0) or 0),
                            "v":   float(comp.get("V", 0) or 0),
                            "fe":  float(comp.get("Fe", 0) or 0),
                            "ce":  float(comp.get("CE", 0) or 0),
                        })

                # Insere itens
                for it in itens_cert:
                    if it["pedido"] or it["descricao"]:
                        conn.execute(text("""
                            INSERT INTO certificado_item (
                                certificado_id, pedido, modelo,
                                descricao, series, quantidade
                            ) VALUES (:cid,:ped,:mod,:desc,:serie,:qtd)
                        """), {
                            "cid": cert_id, "ped": it["pedido"],
                            "mod": it["modelo"], "desc": it["descricao"],
                            "serie": it["series"], "qtd": it["quantidade"]
                        })

                # Insere ensaios mecânicos
                for i, en in enumerate(ensaios_cert):
                    nc = corridas[i]["num_corrida"] if i < len(corridas) else ""
                    if nc:
                        conn.execute(text("""
                            INSERT INTO ensaio_mecanico (
                                numero_corrida, numero_of, certificado_id,
                                lim_resistencia, lim_escoamento, alongamento,
                                red_area, impacto_j1, impacto_j2, impacto_j3,
                                temperatura, criado_em
                            ) VALUES (
                                :nc,:nof,:cid,:lr,:le,:al,:ra,:j1,:j2,:j3,:temp,:now
                            )
                        """), {
                            "nc": nc, "nof": corridas[i]["num_of"],
                            "cid": cert_id,
                            "lr": en["lim_res"], "le": en["lim_esc"],
                            "al": en["along"], "ra": en["red_area"],
                            "j1": en["j1"], "j2": en["j2"], "j3": en["j3"],
                            "temp": en["temp"], "now": now
                        })

            st.success(f"✅ Certificado **{num_cert}** salvo com sucesso!")
            st.session_state["_cert_salvo"] = num_cert
            st.session_state["_cert_salvo_id"] = cert_id

        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # ── Formulario de Edicao ──────────────────────────────────────────────────
    if st.session_state.get("_editar_cert_id"):
        _ed_data     = st.session_state.get("_editar_cert_data", {})
        _ed_corridas = st.session_state.get("_editar_cert_corridas", [])
        _ed_itens    = st.session_state.get("_editar_cert_itens", [])
        _ed_num      = st.session_state.get("_editar_cert_num", "")

        st.divider()
        st.subheader(f"✏️ Editando Certificado {_ed_num}")

        with st.container(border=True):
            st.markdown("**Dados Gerais**")
            _ec1, _ec2 = st.columns(2)
            with _ec1:
                _ed_cliente = st.text_input("Cliente", value=_ed_data.get("cliente",""), key="ed_cliente")
                _ed_norma   = st.text_input("Norma", value=_ed_data.get("norma",""), key="ed_norma")
            with _ec2:
                _ed_liga    = st.text_input("Liga", value=_ed_data.get("liga",""), key="ed_liga")
                _ed_nf      = st.text_input("Nota Fiscal", value=str(_ed_data.get("nota_fiscal","") or ""), key="ed_nf")
            _ed_obs    = st.text_area("Observações", value=str(_ed_data.get("observacoes","") or ""), key="ed_obs", height=60)
            _ed_outros = st.text_area("Outros Ensaios", value=str(_ed_data.get("outros_ensaios","") or ""), key="ed_outros", height=60)

        # Corridas
        with st.container(border=True):
            st.markdown("**Composição Química (Corridas)**")
            ELEM_ED = ["c","si","mn","p","s","cr","ni","mo"]
            _ed_corridas_novo = []
            for _eci, _ec in enumerate(_ed_corridas):
                st.caption(f"Corrida {_eci+1}")
                _ecc1, _ecc2 = st.columns(2)
                with _ecc1:
                    _ec_nof  = st.text_input("OF", value=_ec.get("numero_of",""), key=f"ed_nof_{_eci}")
                with _ecc2:
                    _ec_ncorr = st.text_input("Nº Corrida", value=_ec.get("numero_corrida",""), key=f"ed_ncorr_{_eci}")
                _ec_cols = st.columns(8)
                _ec_comp = {}
                for _ej, _ek in enumerate(ELEM_ED):
                    with _ec_cols[_ej]:
                        _ec_comp[_ek] = st.number_input(
                            _ek.upper(),
                            value=float(_ec.get(_ek, 0) or 0),
                            format="%.4f",
                            key=f"ed_comp_{_eci}_{_ek}",
                            min_value=0.0
                        )
                _ed_corridas_novo.append({
                    "numero_of": _ec_nof, "numero_corrida": _ec_ncorr,
                    **_ec_comp
                })

        # Itens
        with st.container(border=True):
            st.markdown("**Itens**")
            _ed_itens_novo = []
            for _eii, _ei in enumerate(_ed_itens):
                _ei1, _ei2, _ei3, _ei4, _ei5 = st.columns([2,2,3,2,1])
                with _ei1:
                    _ei_ped = st.text_input("Pedido", value=_ei.get("pedido",""), key=f"ed_ped_{_eii}")
                with _ei2:
                    _ei_mod = st.text_input("Modelo", value=_ei.get("modelo",""), key=f"ed_mod_{_eii}")
                with _ei3:
                    _ei_desc = st.text_input("Descrição", value=_ei.get("descricao",""), key=f"ed_desc_{_eii}")
                with _ei4:
                    _ei_ser = st.text_input("Série", value=str(_ei.get("series","") or ""), key=f"ed_ser_{_eii}")
                with _ei5:
                    _ei_qtd = st.number_input("Qtd", value=int(_ei.get("quantidade",0) or 0), min_value=0, key=f"ed_qtd_{_eii}")
                _ed_itens_novo.append({
                    "pedido": _ei_ped, "modelo": _ei_mod,
                    "descricao": _ei_desc, "series": _ei_ser, "quantidade": _ei_qtd
                })

        _ebtn1, _ebtn2 = st.columns(2)
        with _ebtn1:
            if st.button("💾 Salvar Alterações", key="btn_salvar_edicao", type="primary"):
                try:
                    _cert_id_ed = st.session_state["_editar_cert_id"]
                    with engine.begin() as _conn_save:
                        # Atualiza dados gerais
                        _conn_save.execute(text("""
                            UPDATE certificado_qualidade
                            SET cliente=:cli, norma=:nor, liga=:lig,
                                nota_fiscal=:nf, observacoes=:obs,
                                outros_ensaios=:out
                            WHERE id=:id
                        """), {"cli": _ed_cliente, "nor": _ed_norma,
                               "lig": _ed_liga, "nf": _ed_nf,
                               "obs": _ed_obs, "out": _ed_outros,
                               "id": _cert_id_ed})

                        # Deleta e reinicia corridas
                        _conn_save.execute(text(
                            "DELETE FROM certificado_corrida WHERE certificado_id=:id"
                        ), {"id": _cert_id_ed})
                        for _nc in _ed_corridas_novo:
                            if _nc["numero_corrida"]:
                                _conn_save.execute(text("""
                                    INSERT INTO certificado_corrida
                                    (certificado_id, numero_of, numero_corrida,
                                     c, si, mn, p, s, cr, ni, mo)
                                    VALUES (:cid, :nof, :nc,
                                     :c, :si, :mn, :p, :s, :cr, :ni, :mo)
                                """), {"cid": _cert_id_ed,
                                       "nof": _nc["numero_of"],
                                       "nc":  _nc["numero_corrida"],
                                       "c":   _nc["c"],  "si": _nc["si"],
                                       "mn":  _nc["mn"], "p":  _nc["p"],
                                       "s":   _nc["s"],  "cr": _nc["cr"],
                                       "ni":  _nc["ni"], "mo": _nc["mo"]})

                        # Deleta e reinicia itens
                        _conn_save.execute(text(
                            "DELETE FROM certificado_item WHERE certificado_id=:id"
                        ), {"id": _cert_id_ed})
                        for _ni in _ed_itens_novo:
                            if _ni["pedido"] or _ni["descricao"]:
                                _conn_save.execute(text("""
                                    INSERT INTO certificado_item
                                    (certificado_id, pedido, modelo,
                                     descricao, series, quantidade)
                                    VALUES (:cid, :ped, :mod, :desc, :ser, :qtd)
                                """), {"cid": _cert_id_ed,
                                       "ped": _ni["pedido"],
                                       "mod": _ni["modelo"],
                                       "desc": _ni["descricao"],
                                       "ser": _ni["series"],
                                       "qtd": _ni["quantidade"]})

                    st.success(f"✅ Certificado {_ed_num} atualizado com sucesso!")
                    # Limpa session_state
                    for _k in ["_editar_cert_id","_editar_cert_num",
                               "_editar_cert_data","_editar_cert_corridas",
                               "_editar_cert_itens"]:
                        st.session_state.pop(_k, None)
                    st.rerun()
                except Exception as _e:
                    st.error(f"Erro ao salvar: {_e}")

        with _ebtn2:
            if st.button("❌ Cancelar Edição", key="btn_cancelar_edicao"):
                for _k in ["_editar_cert_id","_editar_cert_num",
                           "_editar_cert_data","_editar_cert_corridas",
                           "_editar_cert_itens"]:
                    st.session_state.pop(_k, None)
                st.rerun()

    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    st.subheader("🔧 Alterar ou Excluir Certificado Existente")
    with st.expander("Clique para buscar um certificado", expanded=False):
        st.caption("Busque um certificado pelo número para editar ou excluir.")

        _num_alt = st.text_input("Nº do Certificado",
                                  placeholder="Ex: 2034/26",
                                  key="alt_cert_num")

        if _num_alt.strip():
            try:
                with engine.connect() as _conn_alt:
                    _cert_alt = _conn_alt.execute(text("""
                        SELECT id, numero_cert, cliente, norma, liga,
                               data_emissao, nota_fiscal, observacoes,
                               outros_ensaios, tipo_template
                        FROM certificado_qualidade
                        WHERE numero_cert = :nc
                        LIMIT 1
                    """), {"nc": _num_alt.strip()}).fetchone()
            except Exception as _e:
                st.error(f"Erro ao buscar: {_e}")
                _cert_alt = None

            if _cert_alt:
                _cm_alt = _cert_alt._mapping
                st.success(f"✅ Certificado encontrado: {_cm_alt['numero_cert']} — {_cm_alt['cliente']}")

                _col1, _col2 = st.columns(2)
                with _col1:
                    if st.button("✏️ Editar este certificado",
                                 key="btn_editar_cert",
                                 type="primary"):
                        try:
                            with engine.connect() as _conn_ed:
                                _corridas_ed = _conn_ed.execute(text("""
                                    SELECT numero_of, numero_corrida,
                                           c, si, mn, p, s, cr, ni, mo
                                    FROM certificado_corrida
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()
                                _itens_ed = _conn_ed.execute(text("""
                                    SELECT pedido, modelo, descricao,
                                           series, quantidade
                                    FROM certificado_item
                                    WHERE certificado_id = :id
                                    ORDER BY criado_em
                                """), {"id": str(_cm_alt["id"])}).fetchall()

                            # Seta flag de edicao
                            st.session_state["_modo_edicao_cert_id"]  = str(_cm_alt["id"])
                            st.session_state["_modo_edicao_cert_num"] = _cm_alt["numero_cert"]

                            # Preenche campos do formulario principal
                            st.session_state["cert_numero_edit"] = _cm_alt["numero_cert"]
                            st.session_state["cert_norma"]       = str(_cm_alt.get("norma","") or "")
                            st.session_state["cert_liga"]        = str(_cm_alt.get("liga","") or "")
                            st.session_state["cert_projeto"]     = str(_cm_alt.get("projeto","") or "")
                            st.session_state["cert_nf"]          = str(_cm_alt.get("nota_fiscal","") or "")
                            st.session_state["cert_obs"]         = str(_cm_alt.get("observacoes","") or "")
                            st.session_state["cert_outros"]      = str(_cm_alt.get("outros_ensaios","") or "")
                            st.session_state["cert_cliente_manual"] = str(_cm_alt.get("cliente","") or "")

                            # Corridas
                            _lista_corr = [dict(r._mapping) for r in _corridas_ed]
                            st.session_state["cert_n_corridas"] = len(_lista_corr)
                            for _ci, _cr in enumerate(_lista_corr):
                                st.session_state[f"cert_of_{_ci}"]   = str(_cr.get("numero_of","") or "")
                                st.session_state[f"cert_corr_{_ci}"] = str(_cr.get("numero_corrida","") or "")
                                _key_comp = f"_cert_comp_corrida_{_ci}"
                                _comp_dict = {
                                    el.upper(): float(_cr.get(el.lower(), 0) or 0)
                                    for el in ["C","Si","Mn","P","S","Cr","Ni","Mo"]
                                }
                                st.session_state[_key_comp] = _comp_dict
                                for _el in ["C","Si","Mn","P","S","Cr","Ni","Mo"]:
                                    st.session_state[f"cert_comp_{_ci}_{_el}"] = float(_cr.get(_el.lower(), 0) or 0)

                            # Itens
                            _lista_itens = [dict(r._mapping) for r in _itens_ed]
                            st.session_state["cert_n_itens"] = len(_lista_itens)
                            for _ii, _it in enumerate(_lista_itens):
                                st.session_state[f"cert_ped_{_ii}"]   = str(_it.get("pedido","") or "")
                                st.session_state[f"cert_mod_{_ii}"]   = str(_it.get("modelo","") or "")
                                st.session_state[f"cert_desc_{_ii}"]  = str(_it.get("descricao","") or "")
                                st.session_state[f"cert_serie_{_ii}"] = str(_it.get("series","") or "")
                                st.session_state[f"cert_qtd_{_ii}"]   = int(_it.get("quantidade",0) or 0)

                            st.success(f"✅ Dados carregados! Role para cima para editar.")
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Erro ao carregar dados: {_e}")

                with _col2:
                    if st.button("🗑️ Excluir este certificado",
                                 key="btn_excluir_cert",
                                 type="secondary"):
                        st.session_state["_confirmar_excluir_cert"] = str(_cm_alt["id"])
                        st.session_state["_confirmar_excluir_num"]  = _cm_alt["numero_cert"]

                # Confirmacao de exclusao
                if st.session_state.get("_confirmar_excluir_cert") == str(_cm_alt["id"]):
                    st.warning(f"⚠️ Tem certeza que deseja excluir o certificado "
                               f"**{_cm_alt['numero_cert']}**? Esta ação não pode ser desfeita!")
                    _cc1, _cc2 = st.columns(2)
                    with _cc1:
                        if st.button("✅ Sim, excluir", key="btn_confirmar_excluir",
                                     type="primary"):
                            try:
                                with engine.begin() as _conn_del:
                                    _cert_id_del = str(_cm_alt["id"])
                                    # Exclui registros filhos primeiro
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_item WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_corrida WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM ensaio_mecanico WHERE certificado_id = :id"
                                    ), {"id": _cert_id_del})
                                    _conn_del.execute(text(
                                        "DELETE FROM certificado_qualidade WHERE id = :id"
                                    ), {"id": _cert_id_del})
                                st.success(f"✅ Certificado {_cm_alt['numero_cert']} excluído!")
                                st.session_state.pop("_confirmar_excluir_cert", None)
                                st.session_state.pop("_confirmar_excluir_num", None)
                                st.rerun()
                            except Exception as _e:
                                st.error(f"Erro ao excluir: {_e}")
                    with _cc2:
                        if st.button("❌ Cancelar", key="btn_cancelar_excluir"):
                            st.session_state.pop("_confirmar_excluir_cert", None)
                            st.session_state.pop("_confirmar_excluir_num", None)
                            st.rerun()
            else:
                st.warning(f"Certificado '{_num_alt.strip()}' não encontrado.")


# ── Tela Consulta de Certificados ─────────────────────────────────────────────
def tela_consulta_certificados():
    st.title("🔍 Consulta de Certificados")
    engine = _get_engine()

    # Filtros
    with st.container(border=True):
        st.subheader("Filtros")
        f1, f2, f3 = st.columns(3)
        with f1:
            f_num = st.text_input("Nº Certificado", placeholder="Ex: 2034/26")
        with f2:
            f_cli = st.text_input("Cliente")
        with f3:
            f_corrida = st.text_input("Corrida")

    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT cq.numero_cert, cq.cliente, cq.norma, cq.liga,
                       cq.data_emissao, cq.tipo_template, cq.id,
                       STRING_AGG(cc.numero_corrida, ', ') AS corridas
                FROM certificado_qualidade cq
                LEFT JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                GROUP BY cq.id, cq.numero_cert, cq.cliente, cq.norma,
                         cq.liga, cq.data_emissao, cq.tipo_template
                ORDER BY cq.criado_em DESC
            """)).fetchall()
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if not rows:
        st.info("Nenhum certificado encontrado.")
        return

    df = pd.DataFrame(rows, columns=["Nº Cert","Cliente","Norma","Liga",
                                      "Data","Tipo","id","Corridas"])

    # Normaliza tipo IMEDIATAMENTE apos criar o DataFrame
    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df["Tipo"] = df["Tipo"].apply(_norm_tipo)

    # Aplica filtros
    if f_num.strip():
        df = df[df["Nº Cert"].str.contains(f_num.strip(), case=False, na=False)]
    if f_cli.strip():
        df = df[df["Cliente"].str.contains(f_cli.strip(), case=False, na=False)]
    if f_corrida.strip():
        df = df[df["Corridas"].fillna("").str.contains(f_corrida.strip(), case=False, na=False)]

    m1, m2 = st.columns(2)
    m1.metric("Certificados encontrados", len(df))
    m2.metric("Com Ensaio", int((df["Tipo"] == "Com Ensaio").sum()))

    st.caption("💡 **Clique em uma linha** para ver detalhes e gerar o certificado.")
    df_exib = df.drop(columns=["id"])

    evento = st.dataframe(df_exib, use_container_width=True, hide_index=True,
                           on_select="rerun", selection_mode="single-row")

    sel = evento.selection.rows if evento and evento.selection else []
    if sel:
        cert_row = df.iloc[sel[0]]
        cert_id = cert_row["id"]
        num_cert = cert_row["Nº Cert"]

        with st.expander(f"📋 Certificado {num_cert}", expanded=True):
            # Busca dados completos
            with engine.connect() as conn:
                corridas_db = conn.execute(text("""
                    SELECT numero_of, numero_corrida, c, si, mn, p, s, cr, ni, mo
                    FROM certificado_corrida WHERE certificado_id=:id ORDER BY criado_em
                """), {"id": cert_id}).fetchall()

                itens_db = conn.execute(text("""
                    SELECT pedido, modelo, descricao, series, quantidade
                    FROM certificado_item WHERE certificado_id=:id ORDER BY criado_em
                """), {"id": cert_id}).fetchall()

                ensaios_db = conn.execute(text("""
                    SELECT numero_corrida, lim_resistencia, lim_escoamento,
                           alongamento, red_area, impacto_j1, impacto_j2, impacto_j3
                    FROM ensaio_mecanico WHERE certificado_id=:id ORDER BY criado_em
                """), {"id": cert_id}).fetchall()

                cert_data = conn.execute(text("""
                    SELECT * FROM certificado_qualidade WHERE id=:id
                """), {"id": cert_id}).fetchone()

            if corridas_db:
                st.markdown("**Composição Química:**")
                df_comp = pd.DataFrame(corridas_db,
                    columns=["OF","Corrida","C","Si","Mn","P","S","Cr","Ni","Mo"])
                # Formata valores numericos
                for _ec in ["C","Si","Mn","P","S","Cr","Ni","Mo"]:
                    df_comp[_ec] = pd.to_numeric(df_comp[_ec], errors="coerce").round(4)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

            if itens_db:
                st.markdown("**Itens:**")
                df_itens = pd.DataFrame(itens_db,
                    columns=["Pedido","Modelo","Descrição","Séries","Qtd"])
                st.dataframe(df_itens, use_container_width=True, hide_index=True)

            if ensaios_db:
                st.markdown("**Ensaios Mecânicos:**")
                df_ens = pd.DataFrame(ensaios_db,
                    columns=["Corrida","Lim.Res.(MPa)","Lim.Esc.(MPa)",
                             "Along.(%)","Red.Área(%)","J1","J2","J3"])
                st.dataframe(df_ens, use_container_width=True, hide_index=True)

            # Botoes gerar PDF
            _tmpl_b64_sem = None
            _tmpl_b64_com = None
            try:
                from empresa_config import get_config
                _tmpl_b64_sem = get_config("template_cert_base64","")
                _tmpl_b64_com = get_config("template_cert_base64","")
            except Exception:
                pass

            if _tmpl_b64_sem:
                if st.button(f"⬇️ Gerar PDF do Certificado {num_cert}",
                             key=f"btn_cert_pdf_{num_cert}", type="primary"):
                    try:
                        pdf = gerar_certificado_pdf(
                            cert_data=dict(cert_data._mapping),
                            corridas=corridas_db,
                            itens=itens_db,
                            ensaios=ensaios_db,
                        )
                        st.download_button(
                            f"⬇️ Baixar Certificado {num_cert}.pdf",
                            data=pdf,
                            file_name=f"CERT_{num_cert.replace('/','_')}.pdf",
                            mime="application/pdf",
                            key=f"dl_cert_{num_cert}"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
            else:
                st.caption("Configure o template de Certificado em ⚙️ Administração → Templates.")


# ── Tela Ensaios Mecânicos ────────────────────────────────────────────────────
def tela_ensaios_mecanicos():
    st.title("🔬 Ensaios Mecânicos")
    engine = _get_engine()

    tab1, tab2 = st.tabs(["➕ Novo Ensaio", "🔍 Consultar Ensaios"])

    with tab1:
        st.subheader("Registrar Ensaio Mecânico")
        with st.container(border=True):
            e1, e2 = st.columns(2)
            with e1:
                num_corr = st.text_input("Nº da Corrida *", key="ensaio_corrida")
                num_of   = st.text_input("Nº da OF", key="ensaio_of")
            with e2:
                # Busca certificados vinculados à corrida
                cert_options = ["(Nenhum)"]
                if num_corr.strip():
                    try:
                        with engine.connect() as conn:
                            certs = conn.execute(text("""
                                SELECT DISTINCT cq.numero_cert, cq.id
                                FROM certificado_qualidade cq
                                JOIN certificado_corrida cc ON cc.certificado_id = cq.id
                                WHERE cc.numero_corrida = :nc
                            """), {"nc": num_corr.strip()}).fetchall()
                            cert_options += [f"{r[0]}" for r in certs]
                    except Exception:
                        pass
                cert_sel = st.selectbox("Certificado vinculado", cert_options,
                                         key="ensaio_cert")

        with st.container(border=True):
            st.markdown("**Propriedades Mecânicas:**")
            p1, p2, p3, p4 = st.columns(4)
            with p1:
                lim_res = st.number_input("Lim. Resistência (MPa)", value=0.0,
                                           key="ensaio_lr", format="%.2f")
                lim_esc = st.number_input("Lim. Escoamento (MPa)", value=0.0,
                                           key="ensaio_le", format="%.2f")
            with p2:
                along   = st.number_input("Alongamento (%)", value=0.0,
                                           key="ensaio_al", format="%.2f")
                red_area= st.number_input("Red. Área (%)", value=0.0,
                                           key="ensaio_ra", format="%.2f")
            with p3:
                j1 = st.number_input("Impacto J1", value=0.0, key="ensaio_j1", format="%.2f")
                j2 = st.number_input("Impacto J2", value=0.0, key="ensaio_j2", format="%.2f")
                j3 = st.number_input("Impacto J3", value=0.0, key="ensaio_j3", format="%.2f")
            with p4:
                temp = st.number_input("Temperatura", value=0.0, key="ensaio_temp", format="%.2f")
                obs_ens = st.text_area("Observações", key="ensaio_obs", height=80)

        if st.button("💾 Salvar Ensaio", type="primary", key="btn_salvar_ensaio"):
            if not num_corr.strip():
                st.error("Informe o número da corrida.")
                return
            try:
                import uuid as _uuid
                now = datetime.now().astimezone()

                # Busca ID do certificado
                cert_id = None
                if cert_sel != "(Nenhum)":
                    with engine.connect() as conn:
                        r = conn.execute(text(
                            "SELECT id FROM certificado_qualidade WHERE numero_cert=:n"
                        ), {"n": cert_sel}).fetchone()
                        if r:
                            cert_id = str(r[0])

                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO ensaio_mecanico (
                            numero_corrida, numero_of, certificado_id,
                            lim_resistencia, lim_escoamento, alongamento,
                            red_area, impacto_j1, impacto_j2, impacto_j3,
                            temperatura, observacoes, criado_em
                        ) VALUES (
                            :nc,:nof,:cid,:lr,:le,:al,:ra,:j1,:j2,:j3,:temp,:obs,:now
                        )
                    """), {
                        "nc": num_corr.strip(), "nof": num_of.strip(),
                        "cid": cert_id,
                        "lr": lim_res, "le": lim_esc, "al": along,
                        "ra": red_area, "j1": j1, "j2": j2, "j3": j3,
                        "temp": temp, "obs": obs_ens, "now": now
                    })
                st.success(f"✅ Ensaio da corrida {num_corr} salvo!")
            except Exception as e:
                st.error(f"Erro: {e}")

    with tab2:
        st.subheader("Consultar Ensaios Mecânicos")
        f_corr = st.text_input("Filtrar por corrida", key="filtro_ensaio_corr")
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT e.numero_corrida, e.numero_of,
                           cq.numero_cert,
                           e.lim_resistencia, e.lim_escoamento,
                           e.alongamento, e.red_area,
                           e.impacto_j1, e.impacto_j2, e.impacto_j3,
                           e.temperatura, e.criado_em
                    FROM ensaio_mecanico e
                    LEFT JOIN certificado_qualidade cq ON cq.id = e.certificado_id
                    ORDER BY e.criado_em DESC
                    LIMIT 200
                """)).fetchall()

            if rows:
                df_ens = pd.DataFrame(rows, columns=[
                    "Corrida","OF","Certificado",
                    "Lim.Res.(MPa)","Lim.Esc.(MPa)",
                    "Along.(%)","Red.Área(%)",
                    "J1","J2","J3","Temperatura","Data"
                ])
                if f_corr.strip():
                    df_ens = df_ens[df_ens["Corrida"].str.contains(
                        f_corr.strip(), case=False, na=False)]
                st.dataframe(df_ens, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum ensaio registrado ainda.")
        except Exception as e:
            st.error(f"Erro: {e}")


# ── Geração de PDF do Certificado ─────────────────────────────────────────────
def gerar_certificado_pdf(cert_data, corridas, itens, ensaios=None):
    """Gera PDF do certificado fiel ao template."""
    import io as _io_pdf
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = _io_pdf.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=8*mm, bottomMargin=8*mm)

    W = A4[0] - 20*mm
    styles = getSampleStyleSheet()
    BK  = colors.black
    CINZA = colors.HexColor("#D9D9D9")

    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    def ph(t, sz=8, bold=True):
        return Paragraph(str(t or ""), PS("h",
            fontSize=sz, fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_CENTER, leading=sz+2))
    def pc(t, sz=8):
        return Paragraph(str(t or ""), PS("c",
            fontSize=sz, fontName="Helvetica",
            alignment=TA_CENTER, leading=sz+2))
    def pl(t, sz=8, bold=False):
        return Paragraph(str(t or ""), PS("l",
            fontSize=sz, fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_LEFT, leading=sz+2))

    def fmt_num(v):
        """Formata numero com casas decimais variaveis como no template."""
        try:
            f = float(v or 0)
            if f == 0: return ""
            # Usa 4 casas e remove zeros a direita
            s = f"{f:.4f}"
            # Remove zeros a direita apos a virgula
            s = s.rstrip("0").rstrip(".")
            # Garante pelo menos 1 casa decimal
            if "." not in s:
                s = s + ".0"
            return s.replace(".", ",")
        except Exception:
            return str(v or "")

    story = []

    # Dados
    num_cert = cert_data.get("numero_cert", "")
    cliente  = cert_data.get("cliente", "")
    norma    = cert_data.get("norma", "")
    liga     = cert_data.get("liga", "")
    projeto  = cert_data.get("projeto", "")
    data_em  = cert_data.get("data_emissao", "")
    nf       = cert_data.get("nota_fiscal", "")
    obs      = cert_data.get("observacoes", "")
    outros   = cert_data.get("outros_ensaios", "")
    tipo     = str(cert_data.get("tipo_template", "sem_ensaio"))

    # Busca norma e liga da OF se nao estiver preenchida no certificado
    if not norma and corridas:
        try:
            from fundicao_db import engine as _eng
            from sqlalchemy import text as _text
            # Pega a primeira OF das corridas
            _cm0 = corridas[0]._mapping if hasattr(corridas[0], "_mapping") else {}
            _nof0 = _cm0.get("numero_of", "")
            if _nof0:
                with _eng.connect() as _conn_of:
                    _of_row = _conn_of.execute(_text("""
                        SELECT norma, liga FROM ordem_fabricacao
                        WHERE numero_of = :nof LIMIT 1
                    """), {"nof": _nof0}).fetchone()
                    if _of_row:
                        norma = str(_of_row[0] or "")
                        liga  = str(_of_row[1] or liga or "")
        except Exception:
            pass

    # Formata data
    try:
        from datetime import datetime as _dtt
        if hasattr(data_em, "strftime"):
            data_fmt = data_em.strftime("%d/%m/%Y")
        else:
            data_fmt = _dtt.strptime(str(data_em), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        data_fmt = str(data_em or "")

    # ── CABECALHO ─────────────────────────────────────────────────────────────
    # Layout identico ao template:
    #   Col 0 (70mm): Logo grande ocupando toda a altura
    #   Col 1 (82mm): "Certificado de Qualidade..." + "No XXXX/XX"
    #   Col 2 (38mm): INSPECTION CERTIFICATE + SFS
    # larguras definidas abaixo no bloco do cabecalho

    def _ph_cab(t, sz=8, bold=True):
        return Paragraph(str(t or ""), ParagraphStyle(
            "cab", parent=styles["Normal"],
            fontSize=sz,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_CENTER,
            leading=sz * 1.4,
            wordWrap="LTR",
        ))

    # ── CABECALHO: 2 colunas identico ao template ────────────────────────────
    # Coluna E (larga): Logo em cima + "Certificado..." abaixo + "No XXXX/XX"
    # Coluna D (estreita): INSPECTION / CERTIFICATE / SFS
    _W_ESQUERDA = W - 42*mm   # ~148mm
    _W_DIREITA  = 42*mm
    _H_LOGO_MAX = 22*mm       # altura maxima reservada para o logo

    # Logo: calcula dimensoes respeitando proporcao original da imagem
    _logo_cell = Paragraph("", ParagraphStyle("empty", parent=styles["Normal"]))
    try:
        from empresa_config import get_config as _gc
        import base64 as _b64l
        from PIL import Image as _PILImg
        _lb = (_gc("logo_certificado_base64","") or
               _gc("logo1_base64","") or _gc("logo2_base64",""))
        if _lb:
            _img_bytes = _b64l.b64decode(_lb)
            _pil = _PILImg.open(_io_pdf.BytesIO(_img_bytes))
            _iw, _ih = _pil.size  # dimensoes originais em pixels
            _proporcao = _iw / _ih
            # Largura maxima disponivel = largura da coluna - 4mm padding
            _logo_w = _W_ESQUERDA - 4*mm
            _logo_h = _logo_w / _proporcao
            # Se altura calculada exceder o maximo, limita pela altura
            if _logo_h > _H_LOGO_MAX:
                _logo_h = _H_LOGO_MAX
                _logo_w = _logo_h * _proporcao
                # Garante que nao ultrapasse a largura da coluna
                if _logo_w > _W_ESQUERDA - 4*mm:
                    _logo_w = _W_ESQUERDA - 4*mm
                    _logo_h = _logo_w / _proporcao
            _logo_cell = RLImage(_io_pdf.BytesIO(_img_bytes),
                                 width=_logo_w, height=_logo_h)
    except Exception:
        pass

    # Cabecalho: 2 colunas, SEM SPAN
    # Coluna esquerda: 3 linhas (logo | certificado | numero)
    # Coluna direita: 1 celula alta com tabela interna (INSPECTION/CERTIFICATE/SFS)
    # Assim as linhas horizontais atravessam toda a largura corretamente

    # Cabecalho: 2 linhas x 2 colunas
    # Linha 0: Logo (esq) | INSPECTION\nCERTIFICATE\nSFS (dir) — linha 0 alta
    # Linha 1: "Certificado..." + "Nº XXXX" (esq, 2 paragrafos) | vazio (dir)
    # Linha horizontal separa linha 0 de linha 1
    # BOX fecha tudo por fora

    _H_TOPO   = _H_LOGO_MAX + 9*mm   # logo + titulo
    _H_BAIXO  = 11*mm                 # numero sozinho

    # Celula esquerda linha 0: logo + titulo abaixo do logo
    _cel_esq_0 = [
        _logo_cell,
        Spacer(1, 1*mm),
        _ph_cab("Certificado de Qualidade / Quality Certificate", sz=9),
    ]

    # Celula direita linha 0: INSPECTION CERTIFICATE SFS empilhados
    _cel_dir_0 = [
        Spacer(1, 4*mm),
        _ph_cab("INSPECTION",           sz=10),
        _ph_cab("CERTIFICATE",          sz=10),
        Spacer(1, 2*mm),
        _ph_cab("SFS - EM 10204 - 3.1", sz=7, bold=False),
    ]

    # Celula esquerda linha 1: apenas numero do certificado - centralizado e maior
    _cel_esq_1 = Paragraph(f"N\u00ba {num_cert}", ParagraphStyle(
        "num_cert", parent=styles["Normal"],
        fontSize=16, fontName="Helvetica-Bold",
        alignment=TA_CENTER, leading=20,
    ))

    cab = Table([
        [_cel_esq_0, _cel_dir_0],
        [_cel_esq_1, ""],
    ], colWidths=[_W_ESQUERDA, _W_DIREITA],
       rowHeights=[_H_TOPO, _H_BAIXO])

    cab.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.8, BK),
        # Linha vertical separando col direita — apenas na linha 0
        ("LINEBEFORE",  (1,0),(1,0),   0.8, BK),
        # Linha horizontal completa separando linha 0 de linha 1
        ("LINEBELOW",   (0,0),(-1,0),  0.5, BK),
        # Numero do certificado ocupa TODA a largura (span linha 1)
        ("SPAN",        (0,1),(1,1)),
        # Alinhamentos
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("VALIGN",      (1,0),(1,0),   "MIDDLE"),
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("TOPPADDING",  (1,0),(1,0),   5),
    ]))
    story.append(cab)

    # ── CLIENTE ───────────────────────────────────────────────────────────────
    cli_tbl = Table([[
        pl("CLIENTE / CUSTOMER:", bold=True, sz=8),
        pl(cliente.upper(), bold=True, sz=11),
    ]], colWidths=[38*mm, W-38*mm])
    cli_tbl.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(cli_tbl)

    # ── NORMA / LIGA ──────────────────────────────────────────────────────────
    _norma_txt = str(norma or liga or "")
    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True, sz=8),
         Paragraph("PROJETO / PROJECT", ParagraphStyle("pr", parent=styles["Normal"],
             fontSize=8, fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=10))],
        [ph(f"{_norma_txt}", sz=14), ""],
    ], colWidths=[W*0.60, W*0.40])
    norma_tbl.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("SPAN",         (0,1),(1,1)),
        ("ALIGN",        (0,1),(1,1), "CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("TOPPADDING",   (0,1),(1,1), 4),
    ]))
    story.append(norma_tbl)
    story.append(Spacer(1, 2*mm))

    # ── COMPOSIÇÃO QUÍMICA ────────────────────────────────────────────────────
    # Verifica quais elementos extras estao preenchidos (Cu, V, etc)
    _elem_extras = []
    for _ek in ["cu","v","w","nb","b","n","mg","co"]:
        for _corr in corridas:
            _cm_chk = _corr._mapping if hasattr(_corr, "_mapping") else {}
            if _cm_chk.get(_ek, 0):
                _elem_extras.append(_ek)
                break

    ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    ELEM_KEYS = ["c","si","mn","p","s","cr","ni","mo"]
    # Adiciona extras se existirem
    for _ek in _elem_extras:
        ELEM.append(_ek.upper())
        ELEM_KEYS.append(_ek)

    _n_elem = len(ELEM)
    _w_of   = 20*mm
    _w_corr = 22*mm
    _w_elem = (W - _w_of - _w_corr) / _n_elem
    cw_c = [_w_of, _w_corr] + [_w_elem]*_n_elem

    comp_hdr1 = [ph("OF"), ph("CORRIDA")] + [ph(e) for e in ELEM]
    comp_hdr2 = [ph(""),   ph("HEAT Nº")] + [ph("") for _ in ELEM]
    comp_rows = [comp_hdr1, comp_hdr2]

    for corr in corridas:
        _cm = corr._mapping if hasattr(corr, "_mapping") else {}
        _nof   = str(_cm.get("numero_of","") or "")
        _ncorr = str(_cm.get("numero_corrida","") or "")
        row = [pc(_nof), pc(_ncorr)]
        for ek in ELEM_KEYS:
            row.append(pc(fmt_num(_cm.get(ek, 0))))
        comp_rows.append(row)

    while len(comp_rows) < 10:
        comp_rows.append([""] * (2 + _n_elem))

    # Altura das linhas
    _n_corr = len(corridas)
    _row_heights = [5*mm, 5*mm]  # 2 linhas de cabecalho
    for _ri in range(8):
        if _ri < _n_corr:
            _row_heights.append(7*mm)
        else:
            _row_heights.append(6*mm)
    tit_comp = Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION")]],
                     colWidths=[W])
    tit_comp.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    comp_tbl = Table(comp_rows, colWidths=cw_c, rowHeights=_row_heights)
    comp_tbl.setStyle(TableStyle([
        # Fundo cinza em todo o cabecalho (linhas 0 e 1)
        ("BACKGROUND",   (0,0),(-1,1), CINZA),
        ("FONTNAME",     (0,0),(-1,1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 7),
        ("GRID",         (0,0),(-1,-1), 0.4, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 1),
        ("BOTTOMPADDING",(0,0),(-1,-1), 1),
        # SPAN vertical: coluna OF ocupa as 2 linhas do cabecalho
        ("SPAN",         (0,0),(0,1)),
        # Remove linha interna entre as 2 linhas do cabecalho na col OF
        ("LINEBELOW",    (0,0),(0,0), 0, BK),
    ]))
    story.append(tit_comp)
    story.append(comp_tbl)
    story.append(Spacer(1, 2*mm))

    # ── ENSAIOS MECÂNICOS ─────────────────────────────────────────────────────
    if "com_ensaio" in tipo and ensaios:
        ens_hdr = [ph("LIM. RES.\n(MPa)"), ph("LIM. ESC.\n(MPa)"),
                   ph("ALONG.\n(%)"), ph("RED. ÁREA\n(%)"),
                   ph("J1"), ph("J2"), ph("J3"), ph("TEMP.")]
        ens_rows = [ens_hdr]
        for en in ensaios:
            em = en._mapping if hasattr(en,"_mapping") else {}
            ens_rows.append([
                pc(f"{float(em.get('lim_resistencia',0) or 0):.1f}"),
                pc(f"{float(em.get('lim_escoamento',0) or 0):.1f}"),
                pc(f"{float(em.get('alongamento',0) or 0):.1f}"),
                pc(f"{float(em.get('red_area',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j1',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j2',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j3',0) or 0):.1f}"),
                pc(f"{float(em.get('temperatura',0) or 0):.1f}"),
            ])
        tit_ens = Table([[ph("II - PROPRIEDADES MECÂNICAS / MECHANICAL PROPERTIES")]],
                        colWidths=[W])
        tit_ens.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), CINZA),
            ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ]))
        ens_tbl = Table(ens_rows, colWidths=[W/8]*8)
        ens_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0), CINZA),
            ("GRID",       (0,0),(-1,-1), 0.4, BK),
            ("FONTSIZE",   (0,0),(-1,-1), 7),
            ("ALIGN",      (0,0),(-1,-1), "CENTER"),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0),(-1,-1), 2),
            ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ]))
        story.append(tit_ens)
        story.append(ens_tbl)
        story.append(Spacer(1, 2*mm))

    # ── ITENS ────────────────────────────────────────────────────────────────
    # Cabecalho em 2 linhas identico ao template
    it_hdr1 = [ph("Pedido/Item"), ph("Modelo"),    ph("Descrição"),       ph("Séries"),  ph("Quantidade")]
    it_hdr2 = [ph("P.O."),        ph("Pattern"),   ph("Description"),     ph("Series"),  ph("Quantity")]
    it_rows = [it_hdr1, it_hdr2]
    for it in itens:
        im = it._mapping if hasattr(it,"_mapping") else it
        it_rows.append([
            pc(im.get("pedido","")),
            pc(im.get("modelo","")),
            pl(im.get("descricao","")),
            pc(im.get("series","")),
            pc(str(im.get("quantidade",""))),
        ])
    while len(it_rows) < 10:
        it_rows.append(["","","","",""])

    tit_it = Table([[ph("II - OUTROS DADOS / OTHER INFORMATIONS")]],
                   colWidths=[W])
    tit_it.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    _it_row_h = [5*mm, 5*mm] + [7*mm]*len(itens) + [6*mm]*(8-len(itens))
    it_tbl = Table(it_rows, colWidths=[W*0.20, W*0.14, W*0.37, W*0.15, W*0.14],
                   rowHeights=_it_row_h[:len(it_rows)])
    it_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,1), CINZA),
        ("FONTNAME",     (0,0),(-1,1), "Helvetica-Bold"),
        ("GRID",         (0,0),(-1,-1), 0.4, BK),
        ("FONTSIZE",     (0,0),(-1,-1), 7),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(1,-1), "CENTER"),
        ("ALIGN",        (2,0),(2,-1), "LEFT"),
        ("ALIGN",        (3,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 1),
        ("BOTTOMPADDING",(0,0),(-1,-1), 1),
        ("LEFTPADDING",  (2,0),(2,-1), 3),
    ]))
    story.append(tit_it)
    story.append(it_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OBSERVAÇÕES ───────────────────────────────────────────────────────────
    obs_data = [[ph("III - OBSERVAÇÕES / COMMENTS")]]
    for _ in range(7):
        obs_data.append([pl("")])
    if obs:
        obs_data[1] = [pl(f"  {obs}")]
    obs_tbl = Table(obs_data, colWidths=[W])
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), CINZA),
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEBELOW",    (0,0),(0,0), 0.5, BK),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OUTROS ENSAIOS ────────────────────────────────────────────────────────
    out_tbl = Table([
        [ph("VI - OUTROS ENSAIOS / OTHER TESTS"), ph("ANEXO\nATTACHED")],
        [pl(outros or ""), pl("")],
        [pl(""), pl("")],
    ], colWidths=[W*0.85, W*0.15])
    out_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), CINZA),
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEBEFORE",   (1,0),(1,-1), 0.5, BK),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, BK),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
    ]))
    story.append(out_tbl)
    story.append(Spacer(1, 2*mm))

    # ── RODAPÉ ────────────────────────────────────────────────────────────────
    rod_tbl = Table([
        [pl(f"Nota Fiscal Nº : {nf or ''}"), pl("")],
        [pl("BILL :"),                        pl("")],
        [pl(f"Data / Date : {data_fmt}"),     ph("CONTROLE DE QUALIDADE")],
    ], colWidths=[W*0.5, W*0.5])
    rod_tbl.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEABOVE",    (0,2),(-1,2), 0.5, BK),
        ("LINEBEFORE",   (1,0),(1,-1), 0.5, BK),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(rod_tbl)

    doc.build(story)
    buf.seek(0)
    return buf.read()

