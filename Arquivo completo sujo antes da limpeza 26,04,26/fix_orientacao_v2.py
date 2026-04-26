from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

if "template_oe_orientacao" in src:
    print("Ja aplicado!")
    exit(0)

# Adiciona opcao de orientacao antes do uploader de OE
OLD = '''        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_oe"
        )'''

NEW = '''        st.markdown("**Orientação de impressão:**")
        _col_ort1, _col_ort2 = st.columns(2)
        with _col_ort1:
            _orient_oe = st.radio(
                "OE — Orientação",
                options=["Paisagem", "Retrato"],
                index=0 if get_config("template_oe_orientacao", "Paisagem") == "Paisagem" else 1,
                horizontal=True,
                key="orient_oe_radio"
            )
        with _col_ort2:
            if st.button("💾 Salvar orientação OE", key="btn_save_orient_oe"):
                set_config("template_oe_orientacao", _orient_oe)
                st.success(f"✅ Orientação OE: {_orient_oe}")

        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_oe"
        )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Orientacao OE adicionada.")
else:
    print("AVISO: Uploader OE nao encontrado.")

# Adiciona opcao de orientacao antes do uploader de Certificado
OLD2 = '''        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_cert"
        )'''

NEW2 = '''        st.markdown("**Orientação de impressão:**")
        _col_ort3, _col_ort4 = st.columns(2)
        with _col_ort3:
            _orient_cert = st.radio(
                "Certificado — Orientação",
                options=["Retrato", "Paisagem"],
                index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
                horizontal=True,
                key="orient_cert_radio"
            )
        with _col_ort4:
            if st.button("💾 Salvar orientação Certificado", key="btn_save_orient_cert"):
                set_config("template_cert_orientacao", _orient_cert)
                st.success(f"✅ Orientação Certificado: {_orient_cert}")

        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
            type=["xlsx"],
            key="upload_tmpl_cert"
        )'''

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK: Orientacao Certificado adicionada.")
else:
    print("AVISO: Uploader Certificado nao encontrado.")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Orientacao template' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
