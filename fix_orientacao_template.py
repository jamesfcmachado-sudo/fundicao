from pathlib import Path

# 1) Adiciona configuracao de orientacao na aba Templates do empresa_config.py
CFG = Path("empresa_config.py")
src_cfg = CFG.read_text(encoding="utf-8")

OLD_OE_UPLOAD = '''        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_oe"
        )
        if _up_oe:
            import base64
            _b64 = base64.b64encode(_up_oe.read()).decode()
            set_config("template_oe_base64", _b64)
            set_config("template_oe_nome", _up_oe.name)
            st.success(f"✅ Template OE salvo: {_up_oe.name}")
            st.rerun()'''

NEW_OE_UPLOAD = '''        _orient_oe = st.radio(
            "Orientação da página",
            options=["Retrato", "Paisagem"],
            index=0 if get_config("template_oe_orientacao", "Paisagem") == "Retrato" else 1,
            horizontal=True,
            key="orient_oe"
        )
        if st.button("💾 Salvar orientação OE", key="btn_orient_oe"):
            set_config("template_oe_orientacao", _orient_oe)
            st.success(f"✅ Orientação OE salva: {_orient_oe}")

        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_oe"
        )
        if _up_oe:
            import base64
            _b64 = base64.b64encode(_up_oe.read()).decode()
            set_config("template_oe_base64", _b64)
            set_config("template_oe_nome", _up_oe.name)
            st.success(f"✅ Template OE salvo: {_up_oe.name}")
            st.rerun()'''

OLD_CERT_UPLOAD = '''        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_cert"
        )
        if _up_cert:
            import base64
            _b64 = base64.b64encode(_up_cert.read()).decode()
            set_config("template_cert_base64", _b64)
            set_config("template_cert_nome", _up_cert.name)
            st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
            st.rerun()'''

NEW_CERT_UPLOAD = '''        _orient_cert = st.radio(
            "Orientação da página",
            options=["Retrato", "Paisagem"],
            index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
            horizontal=True,
            key="orient_cert"
        )
        if st.button("💾 Salvar orientação Certificado", key="btn_orient_cert"):
            set_config("template_cert_orientacao", _orient_cert)
            st.success(f"✅ Orientação Certificado salva: {_orient_cert}")

        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_cert"
        )
        if _up_cert:
            import base64
            _b64 = base64.b64encode(_up_cert.read()).decode()
            set_config("template_cert_base64", _b64)
            set_config("template_cert_nome", _up_cert.name)
            st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
            st.rerun()'''

if OLD_OE_UPLOAD in src_cfg:
    src_cfg = src_cfg.replace(OLD_OE_UPLOAD, NEW_OE_UPLOAD, 1)
    print("OK: Orientacao OE adicionada.")
else:
    print("AVISO: Upload OE nao encontrado.")

if OLD_CERT_UPLOAD in src_cfg:
    src_cfg = src_cfg.replace(OLD_CERT_UPLOAD, NEW_CERT_UPLOAD, 1)
    print("OK: Orientacao Certificado adicionada.")
else:
    print("AVISO: Upload Cert nao encontrado.")

CFG.write_text(src_cfg, encoding="utf-8")

# 2) Atualiza app.py para converter Excel para PDF usando subprocess/LibreOffice
# Como nao temos LibreOffice no Streamlit Cloud, vamos usar xlwings ou
# simplesmente oferecer apenas o Excel (que o usuario converte para PDF)
# A melhor solucao: usar openpyxl para configurar a orientacao no Excel
# e o usuario imprime como PDF direto do Excel

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Atualiza chamada do gerar_oe_excel para passar orientacao
OLD_CFG = '''                        _cfg = {
                            "nome_empresa": get_config("nome_empresa"),
                            "endereco":     get_config("endereco"),
                            "cidade":       get_config("cidade"),
                            "estado":       get_config("estado"),
                            "telefone":     get_config("telefone"),
                            "email":        get_config("email"),
                        }'''

NEW_CFG = '''                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        "",
                            "cidade":        get_config("cidade"),
                            "estado":        get_config("estado"),
                            "telefone":      get_config("telefone"),
                            "email":         get_config("email"),
                            "rodape_pdf":    get_config("rodape_pdf"),
                            "orientacao":    get_config("template_oe_orientacao", "Paisagem"),
                        }'''

if OLD_CFG in src:
    src = src.replace(OLD_CFG, NEW_CFG, 1)
    print("OK: Config atualizada com orientacao.")
else:
    print("AVISO: Config nao encontrada.")

# Remove botao de PDF (geraremos apenas Excel configurado para imprimir em paisagem)
OLD_PDF_BTN = '''                        st.download_button(
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
                        )'''

NEW_PDF_BTN = '''                        orient = _cfg.get("orientacao", "Paisagem")
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} (.xlsx) — {orient}",
                            data=_excel_bytes,
                            file_name=f"OE_{_noe}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_oe_{_noe}",
                        )
                        st.caption(f"\U0001f4a1 Abra o arquivo e use **Arquivo → Imprimir → Salvar como PDF** para gerar o PDF em {orient}.")'''

if OLD_PDF_BTN in src:
    src = src.replace(OLD_PDF_BTN, NEW_PDF_BTN, 1)
    print("OK: Botao simplificado para Excel.")
else:
    print("AVISO: Botao PDF nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
for nome, codigo in [("empresa_config.py", src_cfg), ("app.py", src)]:
    tmp = tempfile.mktemp(suffix='.py')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(codigo)
    try:
        py_compile.compile(tmp, doraise=True)
        print(f"SINTAXE {nome} OK!")
    except py_compile.PyCompileError as e:
        print(f"ERRO {nome}: {e}")
    finally:
        os.unlink(tmp)

print("\nRode: git add . && git commit -m 'Orientacao template e Excel para PDF' && git push")
