from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Remove o segundo botao (dentro do expander de detalhes)
# Localiza o bloco completo
OLD = '''            # ── Botao gerar OE com template Excel ────────────────────────────
            _tmpl_b64 = get_config("template_oe_base64", "")
            if _tmpl_b64:
                if st.button("📊 Gerar OE com Template Excel", key="btn_excel_oe", type="primary"):
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
                            """), {"oe": num_oe_sel}).fetchall()

                        if not _itens_oe:
                            st.warning("Nenhum item encontrado para esta OE na tabela oe_item.")
                        else:
                            _itens_lista = [dict(r._mapping) for r in _itens_oe]
                            _obs_oe = str(_itens_lista[0].get("observacoes", "") or obs_val or "")
                            _cliente_oe = str(oe_row.get("nome_cliente", "") or oe_row.get("of_cliente", ""))

                            # Config da empresa
                            _cfg = {
                                "nome_empresa": get_config("nome_empresa"),
                                "endereco":     get_config("endereco"),
                                "bairro":       "",
                                "cidade":       get_config("cidade"),
                                "estado":       get_config("estado"),
                                "telefone":     get_config("telefone"),
                                "email":        get_config("email"),
                            }

                            _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                            _excel_bytes = gerar_oe_excel(
                                template_bytes=_tmpl_bytes,
                                numero_oe=num_oe_sel,
                                nome_cliente=_cliente_oe,
                                itens=_itens_lista,
                                observacoes=_obs_oe,
                                config=_cfg,
                            )
                            st.download_button(
                                "⬇️ Baixar OE preenchida (.xlsx)",
                                data=_excel_bytes,
                                file_name=f"OE_{num_oe_sel}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                            st.success(f"OE {num_oe_sel} gerada com {len(_itens_lista)} item(ns)!")
                    except Exception as _ex:
                        st.error(f"Erro ao gerar OE: {_ex}")
            else:
                st.caption("Configure o template Excel em ⚙️ Administração → Configurações → Templates")'''

if OLD in src:
    src = src.replace(OLD, '', 1)
    print("OK: Segundo botao removido.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove segundo botao gerar OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
