from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Substitui o botao de download Excel por PDF
OLD = '''                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} preenchida (.xlsx)",
                            data=_excel_bytes,
                            file_name=f"OE_{_noe}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_oe_{_noe}",
                        )
                        st.success(f"OE {_noe} gerada com {len(_itens_lista)} item(ns)!")'''

NEW = '''                        from gerar_oe_excel import gerar_oe_pdf
                        _pdf_bytes = gerar_oe_pdf(
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                        )
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                            data=_pdf_bytes,
                            file_name=f"OE_{_noe}.pdf",
                            mime="application/pdf",
                            key=f"dl_oe_{_noe}",
                        )
                        # Tambem oferece Excel com formulas
                        st.download_button(
                            f"\U0001f4ca Baixar OE {_noe} em Excel (com f\u00f3rmulas)",
                            data=_excel_bytes,
                            file_name=f"OE_{_noe}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_xlsx_{_noe}",
                        )
                        st.success(f"OE {_noe} gerada com {len(_itens_lista)} item(ns)!")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botao alterado para PDF + Excel.")
else:
    print("AVISO: Texto nao encontrado.")

# Corrige KeyError num_of
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
    print("SINTAXE OK! Rode: git add . && git commit -m 'OE gera PDF e Excel com formulas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
