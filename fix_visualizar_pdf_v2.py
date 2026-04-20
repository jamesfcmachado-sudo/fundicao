from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Encontra o bloco completo do Excel para saber onde termina
idx = src.find('_dc1, _dc2 = st.columns(2)\n                        with _dc1:')
if idx == -1:
    print("AVISO: Bloco nao encontrado.")
    exit(1)

# Encontra o fim do bloco (key do Excel)
idx_xlsx_key = src.find('key=f"dl_xlsx_{_noe}"', idx)
idx_fim = src.find('\n', src.find(')', idx_xlsx_key)) + 1
# Pega mais algumas linhas para encontrar o fechamento completo
idx_fim2 = src.find('\n', idx_fim) + 1
idx_fim3 = src.find('\n', idx_fim2) + 1

bloco_antigo = src[idx-24:idx_fim3]
print("Bloco encontrado:")
print(repr(bloco_antigo[-200:]))

# Novo bloco com visualizacao
NOVO = '''                        # Botoes download e visualizacao
                        _dc1, _dc2, _dc3 = st.columns(3)
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
                            )
                        with _dc3:
                            if st.button(f"\U0001f441\ufe0f Visualizar PDF na tela",
                                         key=f"btn_view_{_noe}"):
                                st.session_state[f"_show_pdf_{_noe}"] = \
                                    not st.session_state.get(f"_show_pdf_{_noe}", False)

                        # Exibe PDF inline se solicitado
                        if st.session_state.get(f"_show_pdf_{_noe}", False):
                            import base64 as _b64v
                            _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()
                            st.markdown(
                                f\'\'\'<iframe src="data:application/pdf;base64,{_b64_pdf}"
                                    width="100%" height="750px"
                                    style="border:1px solid #444;border-radius:8px;margin-top:8px;">
                                </iframe>\'\'\',
                                unsafe_allow_html=True
                            )
'''

# Substitui o bloco antigo pelo novo
src_novo = src[:idx-24] + NOVO + src[idx_fim3:]

APP.write_text(src_novo, encoding="utf-8")
print("OK: Visualizacao PDF adicionada.")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src_novo)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Visualizar PDF OE na tela' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src_novo.split('\n')
        for x in range(max(0,ln-5), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
