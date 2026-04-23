from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Adiciona secao de logo do certificado na aba de Logotipos
OLD_LOGO = '''        if st.button("💾 Salvar orientação Certificado", key="btn_save_orient_cert"):
            set_config("template_cert_orientacao", _orient_cert)
            st.success(f"✅ Orientação Certificado: {_orient_cert}")'''

NEW_LOGO = '''        if st.button("💾 Salvar orientação Certificado", key="btn_save_orient_cert"):
            set_config("template_cert_orientacao", _orient_cert)
            st.success(f"✅ Orientação Certificado: {_orient_cert}")

        st.divider()

        # Logo especifico do certificado
        st.markdown("**🖼️ Logotipo do Certificado:**")
        st.caption("Se não configurado, usa o logotipo ativo da empresa.")
        _logo_cert_b64 = get_config("logo_certificado_base64", "")
        _logo_cert_nome = get_config("logo_certificado_nome", "")
        if _logo_cert_b64:
            import base64 as _b64lc
            _lc_bytes = _b64lc.b64decode(_logo_cert_b64)
            st.image(_lc_bytes, width=200)
            st.success(f"✅ Logo certificado: **{_logo_cert_nome}**")
            _dlc1, _dlc2 = st.columns(2)
            with _dlc1:
                st.download_button(
                    "⬇️ Baixar logo certificado",
                    data=_lc_bytes,
                    file_name=_logo_cert_nome,
                    mime="image/png",
                    key="dl_logo_cert"
                )
            with _dlc2:
                if st.button("🗑️ Remover logo certificado", key="btn_rm_logo_cert"):
                    set_config("logo_certificado_base64", "")
                    set_config("logo_certificado_nome", "")
                    st.rerun()
        else:
            st.info("Nenhum logo específico para certificado. Usando logo ativo da empresa.")

        _up_logo_cert = st.file_uploader(
            "📤 Carregar logo do Certificado (.png, .jpg)",
            type=["png","jpg","jpeg"],
            key="upload_logo_cert"
        )
        if _up_logo_cert:
            import base64 as _b64ulc
            _b64lc = _b64ulc.b64encode(_up_logo_cert.read()).decode()
            set_config("logo_certificado_base64", _b64lc)
            set_config("logo_certificado_nome", _up_logo_cert.name)
            st.success(f"✅ Logo certificado salvo: {_up_logo_cert.name}")
            st.rerun()'''

if OLD_LOGO in src:
    src = src.replace(OLD_LOGO, NEW_LOGO, 1)
    print("OK: Logo certificado adicionado nas configuracoes.")
else:
    print("AVISO: Bloco nao encontrado.")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Logo certificado nas configuracoes' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
