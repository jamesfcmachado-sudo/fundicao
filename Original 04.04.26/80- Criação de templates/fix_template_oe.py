"""
fix_template_oe.py
Integra a geracao de OE preenchida no template Excel
"""
from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "gerar_oe_excel" in src:
    print("Ja aplicado!")
    exit(0)

# 1) Adiciona import do modulo
OLD_IMP = "from empresa_config import ("
NEW_IMP = ("from gerar_oe_excel import gerar_oe_excel\n"
           "from empresa_config import (")

if OLD_IMP in src:
    src = src.replace(OLD_IMP, NEW_IMP, 1)
    print("OK: Import gerar_oe_excel adicionado.")
else:
    print("AVISO: Import empresa_config nao encontrado.")

# 2) Adiciona upload do template e botao de gerar OE nas configuracoes da empresa
# Adiciona na aba de Configuracoes da empresa em empresa_config.py
AUTH2 = Path("empresa_config.py")
src2 = AUTH2.read_text(encoding="utf-8")

if "template_oe" in src2:
    print("Template OE ja existe no empresa_config.py")
else:
    # Adiciona aba de Templates na tela de configuracoes
    OLD_TABS = ('    tab1, tab2, tab3, tab4 = st.tabs([\n'
                '        "\U0001f3e2 Dados da Empresa",\n'
                '        "\U0001f5bc\ufe0f Logotipos",\n'
                '        "\U0001f522 Numera\u00e7\u00e3o e Siglas",\n'
                '        "\U0001f4c4 Relat\u00f3rios e PDFs",\n'
                '    ])')

    NEW_TABS = ('    tab1, tab2, tab3, tab4, tab5 = st.tabs([\n'
                '        "\U0001f3e2 Dados da Empresa",\n'
                '        "\U0001f5bc\ufe0f Logotipos",\n'
                '        "\U0001f522 Numera\u00e7\u00e3o e Siglas",\n'
                '        "\U0001f4c4 Relat\u00f3rios e PDFs",\n'
                '        "\U0001f4cb Templates",\n'
                '    ])')

    if OLD_TABS in src2:
        src2 = src2.replace(OLD_TABS, NEW_TABS, 1)
        print("OK: Aba Templates adicionada.")

    # Adiciona conteudo da aba Templates antes do fechamento da funcao
    OLD_END = "\n    # ── ABA 4: Relatórios e PDFs"
    NEW_END = "\n    # ── ABA 4: Relatórios e PDFs"

    # Adiciona aba 5 no final da funcao
    NOVA_ABA = '''

    # ── ABA 5: Templates ──────────────────────────────────────────────────────
    with tab5:
        st.subheader("Templates de documentos")
        st.caption("Faça upload dos templates Excel para geração automática de documentos.")

        st.markdown("##### Template — Ordem de Entrega (OE)")
        _oe_tmpl = get_config("template_oe_base64", "")
        if _oe_tmpl:
            st.success(f"Template OE cadastrado: {get_config('template_oe_nome')}")
            if st.button("🗑️ Remover template OE", key="btn_rm_tmpl_oe"):
                set_config("template_oe_base64", "")
                set_config("template_oe_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de OE cadastrado.")

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
            st.rerun()

        st.divider()

        st.markdown("##### Template — Certificado de Qualidade")
        _cert_tmpl = get_config("template_cert_base64", "")
        if _cert_tmpl:
            st.success(f"Template Certificado cadastrado: {get_config('template_cert_nome')}")
            if st.button("🗑️ Remover template Certificado", key="btn_rm_tmpl_cert"):
                set_config("template_cert_base64", "")
                set_config("template_cert_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de Certificado cadastrado.")

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
            st.rerun()
'''

    # Insere antes do ultimo fechamento da funcao
    OLD_LAST = "\n    # ── ABA 4: Relatórios e PDFs ──────────────────────────────────────────────"
    if OLD_LAST in src2:
        src2 = src2.replace(OLD_LAST, NOVA_ABA + OLD_LAST, 1)
        print("OK: Conteudo da aba Templates adicionado.")
    else:
        # Adiciona no final da funcao
        src2 = src2.rstrip() + NOVA_ABA + "\n"
        print("OK: Aba Templates adicionada no final.")

    AUTH2.write_text(src2, encoding="utf-8")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
for nome, codigo in [("app.py", src), ("empresa_config.py", src2)]:
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

print("\nAgora rode: git add . && git commit -m 'Template OE Excel' && git push")
