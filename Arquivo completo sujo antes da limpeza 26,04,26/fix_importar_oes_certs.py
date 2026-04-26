from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# ── Reordena e adiciona novos uploaders ──────────────────────────────────────
OLD_TELA = '''def tela_importar_excel():
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

    st.divider()

    # --- Atualizacao 1: OFs ---
    st.subheader("3️⃣ Atualizar Ordens de Fabricação")
    st.caption(
        "Importa a planilha e **atualiza** OFs já existentes (pelo Nº OP) "
        "e **insere** as novas. Nenhum dado é excluído."
    )
    arquivo_atualizar_of = st.file_uploader(
        "Selecione a planilha de OFs para atualizar (.xlsx)",
        type=["xlsx"],
        key="uploader_atualizar_ofs",
    )
    if arquivo_atualizar_of:
        _atualizar_ofs(arquivo_atualizar_of)

    st.divider()

    # --- Atualizacao 2: Corridas ---
    st.subheader("4️⃣ Atualizar Corridas")
    st.caption(
        "Importa a planilha e **atualiza** corridas já existentes "
        "(pela chave Corrida + Data + OF + Série) "
        "e **insere** as novas. Nenhum dado é excluído."
    )
    arquivo_atualizar_corrida = st.file_uploader(
        "Selecione a planilha de Corridas para atualizar (.xlsx)",
        type=["xlsx"],
        key="uploader_atualizar_corridas",
    )
    if arquivo_atualizar_corrida:
        _atualizar_corridas(arquivo_atualizar_corrida)'''

NEW_TELA = '''def tela_importar_excel():
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
        _atualizar_certificados(arquivo_atualizar_cert)'''

if OLD_TELA in src:
    src = src.replace(OLD_TELA, NEW_TELA, 1)
    print("OK: Tela de importacao reorganizada.")
else:
    print("AVISO: Bloco nao encontrado.")

# ── Adiciona funções de importar/atualizar OEs e Certificados ─────────────────
NOVAS_FUNCOES = '''

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

    if not st.button("✅ Confirmar importação de OEs", key="btn_confirmar_oes"):
        return

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

    if not st.button("✅ Confirmar atualização de OEs", key="btn_atualizar_oes"):
        return

    atualizados = inseridos = erros = 0
    now = datetime.now().astimezone()
    from fundicao_db import engine as _eng_upd_oe
    from sqlalchemy import text as _text_upd_oe

    for _, row in df.iterrows():
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

    if not st.button("✅ Confirmar importação de Certificados", key="btn_confirmar_certs"):
        return

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

    if not st.button("✅ Confirmar atualização de Certificados", key="btn_atualizar_certs"):
        return

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

    st.success(f"Certificados atualizados: **{atualizados}** | Novos: **{inseridos}** | Erros: **{erros}**")

'''

# Insere as novas funcoes antes de tela_importar_excel
OLD_FUNC = 'def tela_importar_excel():'
if NOVAS_FUNCOES.strip()[:30] not in src:
    src = src.replace(OLD_FUNC, NOVAS_FUNCOES + OLD_FUNC, 1)
    print("OK: Funcoes de OEs e Certificados adicionadas.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Importar OEs e Certificados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-5), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
