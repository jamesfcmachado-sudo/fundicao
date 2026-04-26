from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "Gerar OE com Template" in src:
    # Remove versao anterior se existir
    pass

# Adiciona botao de gerar OE apos as metricas, antes da tabela
OLD = '''    if df.empty:
        st.warning("Nenhum resultado para os filtros aplicados.")
        return

    # ── Montar tabela de exibição ───────────────────────────────────────────'''

NEW = '''    if df.empty:
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

                if st.button(f"\U0001f4ca Gerar OE {_noe} com Template Excel",
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
                            "nome_empresa": get_config("nome_empresa"),
                            "endereco":     get_config("endereco"),
                            "cidade":       get_config("cidade"),
                            "estado":       get_config("estado"),
                            "telefone":     get_config("telefone"),
                            "email":        get_config("email"),
                        }
                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel(
                            template_bytes=_tmpl_bytes,
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                        )
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} preenchida (.xlsx)",
                            data=_excel_bytes,
                            file_name=f"OE_{_noe}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_oe_{_noe}",
                        )
                        st.success(f"OE {_noe} gerada com {len(_itens_lista)} item(ns)!")
                    except Exception as _ex:
                        st.error(f"Erro ao gerar OE: {_ex}")
            st.divider()

    # ── Montar tabela de exibição ───────────────────────────────────────────'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botao gerar OE adicionado apos metricas.")
else:
    print("AVISO: Texto nao encontrado.")

# Corrige tambem o KeyError num_of
OLD2 = '        num_of_sel = str(oe_row["num_of"])'
NEW2 = '        num_of_sel = str(oe_row.get("num_of", oe_row.get("numero_of", "")))'
if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK: KeyError num_of corrigido.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Gerar OE direto do filtro' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
