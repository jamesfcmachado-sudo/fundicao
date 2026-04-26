from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''                        _dc1, _dc2 = st.columns(2)
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
                                mime="applicati'''

# Busca o texto completo
idx = src.find('_dc1, _dc2 = st.columns(2)')
if idx > 0:
    # Pega o bloco completo ate o fim do download Excel
    trecho = src[idx-24:idx+800]
    print("Trecho encontrado:")
    print(repr(trecho))
else:
    print("NAO ENCONTRADO")
