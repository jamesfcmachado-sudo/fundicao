"""
certificados.py
===============
Módulo de Certificados de Qualidade para o sistema de controle de fundição.
Inclui: criação, consulta, ensaios mecânicos e geração de PDF.
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
            cert_id = str(_uuid.uuid4())

            with engine.begin() as conn:
                # Insere certificado
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
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=10*mm)

    W = A4[0] - 24*mm
    styles = getSampleStyleSheet()

    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    BK = colors.black
    AZUL = colors.HexColor("#1F3864")
    CINZA = colors.HexColor("#D9D9D9")

    def ph(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica-Bold")
        kw.setdefault("alignment", TA_CENTER)
        return Paragraph(t, PS("h", **kw))
    def pc(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("alignment", TA_CENTER)
        return Paragraph(str(t or ""), PS("c", **kw))
    def pl(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("alignment", TA_LEFT)
        return Paragraph(str(t or ""), PS("l", **kw))
    def pb(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica-Bold")
        kw.setdefault("alignment", TA_LEFT)
        return Paragraph(str(t or ""), PS("b", **kw))

    story = []

    # ── Cabecalho ─────────────────────────────────────────────────────────────
    num_cert = cert_data.get("numero_cert","")
    cliente  = cert_data.get("cliente","")
    norma    = cert_data.get("norma","")
    liga     = cert_data.get("liga","")
    data_em  = cert_data.get("data_emissao","")
    nf       = cert_data.get("nota_fiscal","")
    obs      = cert_data.get("observacoes","")
    outros   = cert_data.get("outros_ensaios","")
    tipo     = cert_data.get("tipo_template","sem_ensaio")

    # Logo e titulo
    cab = Table([[
        pl(""),  # Logo placeholder
        [ph("Certificado de Qualidade / Quality Certificate", fontSize=11),
         ph(f"Nº {num_cert}", fontSize=14)],
        [ph("INSPECTION\nCERTIFICATE", fontSize=9),
         ph("SFS - EM 10204 - 3.1", fontSize=8)],
    ]], colWidths=[40*mm, W*0.55, W*0.3])
    cab.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",  (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",  (2,0),(2,0),   0.8, BK),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(cab)

    # Cliente
    cli_tbl = Table([[pb("CLIENTE / CUSTOMER:"), pl(cliente.upper())]],
                     colWidths=[45*mm, W-45*mm])
    cli_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,BK),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    story.append(cli_tbl)

    # Norma/Liga/Projeto
    norma_tbl = Table([[
        pb("NORMA DA LIGA/ ALLOY STANDARD"), pl(""),
        pb("PROJETO / PROJECT"), pl(cert_data.get("projeto",""))
    ],[
        ph(f"{norma}", fontSize=12), "", "", ""
    ]], colWidths=[W*0.3, W*0.2, W*0.2, W*0.3])
    norma_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.5,BK),
        ("SPAN",(0,1),(3,1)),
        ("ALIGN",(0,1),(3,1),"CENTER"),
        ("FONTNAME",(0,1),(3,1),"Helvetica-Bold"),
        ("FONTSIZE",(0,1),(3,1),14),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(norma_tbl)

    # ── Composição Química ────────────────────────────────────────────────────
    story.append(Spacer(1,2*mm))
    ELEM_COLS = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_header = [ph("OF"), ph("CORRIDA\nHEAT Nº")] + [ph(e) for e in ELEM_COLS]
    comp_rows = [comp_header]
    for corr in corridas:
        row = [pc(corr[1] if hasattr(corr,'__getitem__') else corr._mapping.get("numero_of","")),
               pc(corr[2] if hasattr(corr,'__getitem__') else corr._mapping.get("numero_corrida",""))]
        for j, el in enumerate(ELEM_COLS):
            val = corr[j+2] if hasattr(corr,'__getitem__') else 0
            row.append(pc(f"{float(val or 0):.3f}".replace(".",",")))
        comp_rows.append(row)

    cw_comp = [20*mm, 20*mm] + [W/10]*8
    comp_tbl = Table(comp_rows, colWidths=cw_comp)
    comp_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),CINZA),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.4,BK),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION")]],
                        colWidths=[W]))
    story.append(comp_tbl)

    # ── Ensaios Mecânicos ─────────────────────────────────────────────────────
    if tipo == "com_ensaio":
        story.append(Spacer(1,2*mm))
        ens_header = [ph("LIM. RES.\n(MPA)"), ph("LIM. ESC.\n(MPA)"),
                      ph("ALONGAMENTO\n(%)"), ph("RED. ÁREA\n(%)"),
                      ph("J1"), ph("J2"), ph("J3"), ph("TEMP.")]
        ens_rows = [ens_header]
        if ensaios:
            for en in ensaios:
                em = en._mapping if hasattr(en,'_mapping') else en
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
        else:
            for _ in range(3):
                ens_rows.append(["","","","","","","",""])

        ens_tbl = Table(ens_rows, colWidths=[W/8]*8)
        ens_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),CINZA),
            ("GRID",(0,0),(-1,-1),0.4,BK),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING",(0,0),(-1,-1),2),
            ("RIGHTPADDING",(0,0),(-1,-1),2),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ]))
        story.append(Table([[ph("II - PROPRIEDADES MECÂNICAS / MECHANICAL PROPERTIES")]],
                            colWidths=[W]))
        story.append(ens_tbl)

    # ── Itens ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1,2*mm))
    it_header = [ph("Pedido/Item\nP.O."), ph("Modelo\nPattern"),
                 ph("Descrição\nDescription"), ph("Séries\nSeries"),
                 ph("Quantidade\nQuantity")]
    it_rows = [it_header]
    for it in itens:
        im = it._mapping if hasattr(it,'_mapping') else it
        it_rows.append([
            pc(im.get("pedido","")), pc(im.get("modelo","")),
            pl(im.get("descricao","")), pc(im.get("series","")),
            pc(str(im.get("quantidade",""))),
        ])
    # Linhas vazias
    for _ in range(max(0, 8-len(itens))):
        it_rows.append(["","","","",""])

    it_tbl = Table(it_rows, colWidths=[W*0.18, W*0.15, W*0.37, W*0.15, W*0.15])
    it_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),CINZA),
        ("GRID",(0,0),(-1,-1),0.4,BK),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),3),
        ("RIGHTPADDING",(0,0),(-1,-1),3),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(Table([[ph("II - OUTROS DADOS / OTHER INFORMATIONS")]],
                        colWidths=[W]))
    story.append(it_tbl)

    # ── Observações ───────────────────────────────────────────────────────────
    story.append(Spacer(1,2*mm))
    obs_tbl = Table([
        [ph("III - OBSERVAÇÕES / COMMENTS")],
        [pl(obs)],
    ], colWidths=[W])
    obs_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.4,BK),
        ("LINEBELOW",(0,0),(0,0),0.4,BK),
        ("BACKGROUND",(0,0),(0,0),CINZA),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(obs_tbl)

    # ── Outros Ensaios ────────────────────────────────────────────────────────
    outros_tbl = Table([
        [ph("VI - OUTROS ENSAIOS / OTHER TESTS"),
         ph("ANEXO\nATTACHED")],
        [pl(outros), pl("")],
    ], colWidths=[W*0.85, W*0.15])
    outros_tbl.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.4,BK),
        ("LINEBELOW",(0,0),(-1,0),0.4,BK),
        ("LINEBEFORE",(1,0),(1,-1),0.4,BK),
        ("BACKGROUND",(0,0),(-1,0),CINZA),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(outros_tbl)

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(Spacer(1,3*mm))
    rodape = Table([[
        pl(f"Nota Fiscal Nº : {nf}"),
        pl(""),
    ],[
        pl(f"Data / Date : {data_em}"),
        ph("CONTROLE DE QUALIDADE"),
    ]], colWidths=[W*0.5, W*0.5])
    rodape.setStyle(TableStyle([
        ("BOX",(0,0),(-1,-1),0.4,BK),
        ("LINEABOVE",(0,1),(-1,1),0.4,BK),
        ("LINEBEFORE",(1,0),(1,-1),0.4,BK),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    story.append(rodape)

    doc.build(story)
    buf.seek(0)
    return buf.read()
