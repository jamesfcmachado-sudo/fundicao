from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                            data=_pdf_bytes,
                            file_name=f"OE_{_noe}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{_noe}",
                            type="primary",
                        )'''

NEW = '''                        _dc1, _dc2 = st.columns(2)
                        with _dc1:
                            st.download_button(
                                f"\u2b07\ufe0f Baixar OE {_noe} em PDF",
                                data=_pdf_bytes,
                                file_name=f"OE_{_noe}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{_noe}",
                                type="primary",
                            )
                        with _dc2:
                            st.download_button(
                                f"\U0001f4ca Baixar OE {_noe} em Excel",
                                data=_excel_bytes,
                                file_name=f"OE_{_noe}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_xlsx_{_noe}",
                            )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Botoes PDF e Excel adicionados.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Botoes PDF e Excel OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
