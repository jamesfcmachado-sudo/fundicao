from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Remove botao Excel, mantem apenas PDF
OLD = '''                        orient = _cfg.get("orientacao", "Paisagem")
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} (.xlsx) — {orient}",
                            data=_excel_bytes,
                            file_name=f"OE_{_noe}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_oe_{_noe}",
                        )
                        st.caption(f"\U0001f4a1 Abra o arquivo e use **Arquivo \u2192 Imprimir \u2192 Salvar como PDF** para gerar o PDF em {orient}.")'''

NEW = '''                        from gerar_oe_excel import gerar_oe_pdf
                        _pdf_bytes = gerar_oe_pdf(
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                            logo_bytes=_logo_bytes,
                        )
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                            data=_pdf_bytes,
                            file_name=f"OE_{_noe}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{_noe}",
                            type="primary",
                        )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Somente PDF.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'OE somente PDF' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
