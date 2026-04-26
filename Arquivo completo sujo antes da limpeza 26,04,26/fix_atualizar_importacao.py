from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "_atualizar_ofs" in src:
    print("Ja aplicado!")
    exit(0)

# ── Adiciona funcoes de atualizacao antes de tela_importar_excel ──────────────
INSERCAO = '''

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

    st.info(f"Previa — {len(df)} linhas encontradas:")
    st.dataframe(df_exib.head(), height=400, use_container_width=True, hide_index=True)

    if not st.button("Confirmar atualizacao de OFs", key="btn_confirmar_atualizar_ofs"):
        return

    inseridos = 0
    atualizados = 0
    erros = []
    now = datetime.now().astimezone()

    for _, row in df.iterrows():
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

    if not st.button("Confirmar atualizacao de Corridas", key="btn_confirmar_atualizar_corridas"):
        return

    inseridos = 0
    atualizados = 0
    ignorados = 0
    erros = []
    now = datetime.now().astimezone()

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

'''

# Insere as novas funcoes antes de tela_importar_excel
OLD_TELA = 'def tela_importar_excel():'
if OLD_TELA in src:
    src = src.replace(OLD_TELA, INSERCAO + OLD_TELA, 1)
    print("OK: Funcoes _atualizar_ofs e _atualizar_corridas adicionadas.")
else:
    print("ERRO: tela_importar_excel nao encontrada!")
    exit(1)

# Adiciona as novas secoes na tela de importacao
OLD_TELA_BODY = ('    if arquivo_corrida:\n'
                 '        _importar_corridas(arquivo_corrida)\n'
                 '\n'
                 '\ndef _migrar_banco_of_status')

NEW_TELA_BODY = ('    if arquivo_corrida:\n'
                 '        _importar_corridas(arquivo_corrida)\n'
                 '\n'
                 '    st.divider()\n'
                 '\n'
                 '    # --- Atualizacao 1: OFs ---\n'
                 '    st.subheader("3\ufe0f\u20e3 Atualizar Ordens de Fabrica\u00e7\u00e3o")\n'
                 '    st.caption(\n'
                 '        "Importa a planilha e **atualiza** OFs j\u00e1 existentes (pelo N\u00ba OP) "\n'
                 '        "e **insere** as novas. Nenhum dado \u00e9 exclu\u00eddo."\n'
                 '    )\n'
                 '    arquivo_atualizar_of = st.file_uploader(\n'
                 '        "Selecione a planilha de OFs para atualizar (.xlsx)",\n'
                 '        type=["xlsx"],\n'
                 '        key="uploader_atualizar_ofs",\n'
                 '    )\n'
                 '    if arquivo_atualizar_of:\n'
                 '        _atualizar_ofs(arquivo_atualizar_of)\n'
                 '\n'
                 '    st.divider()\n'
                 '\n'
                 '    # --- Atualizacao 2: Corridas ---\n'
                 '    st.subheader("4\ufe0f\u20e3 Atualizar Corridas")\n'
                 '    st.caption(\n'
                 '        "Importa a planilha e **atualiza** corridas j\u00e1 existentes "\n'
                 '        "(pela chave Corrida + Data + OF + S\u00e9rie) "\n'
                 '        "e **insere** as novas. Nenhum dado \u00e9 exclu\u00eddo."\n'
                 '    )\n'
                 '    arquivo_atualizar_corrida = st.file_uploader(\n'
                 '        "Selecione a planilha de Corridas para atualizar (.xlsx)",\n'
                 '        type=["xlsx"],\n'
                 '        key="uploader_atualizar_corridas",\n'
                 '    )\n'
                 '    if arquivo_atualizar_corrida:\n'
                 '        _atualizar_corridas(arquivo_atualizar_corrida)\n'
                 '\n'
                 '\ndef _migrar_banco_of_status')

if OLD_TELA_BODY in src:
    src = src.replace(OLD_TELA_BODY, NEW_TELA_BODY, 1)
    print("OK: Secoes de atualizacao adicionadas na tela de importacao.")
else:
    print("AVISO: Nao encontrou o bloco de tela. Verificando...")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Atualizar OFs e Corridas via planilha' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
