from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# 1) Adiciona contato nos defaults
OLD_DEF = '"bairro":              "",'
NEW_DEF = ('"bairro":              "",\n'
           '        "contato":             "",')
if OLD_DEF in src and '"contato"' not in src:
    src = src.replace(OLD_DEF, NEW_DEF, 1)
    print("OK: contato adicionado nos defaults.")
else:
    print("INFO: contato ja existe ou bairro nao encontrado.")

# 2) Adiciona campo Contato na tela de dados da empresa
OLD_CAMPO = ('            bairro = st.text_input("Bairro",\n'
             '                value=get_config("bairro"))')
NEW_CAMPO = ('            bairro = st.text_input("Bairro",\n'
             '                value=get_config("bairro"))\n'
             '            contato = st.text_input("Contato / Responsável",\n'
             '                value=get_config("contato"))')
if OLD_CAMPO in src and 'contato = st.text_input' not in src:
    src = src.replace(OLD_CAMPO, NEW_CAMPO, 1)
    print("OK: Campo contato adicionado na tela.")
else:
    print("INFO: Campo contato ja existe.")

# 3) Adiciona contato no salvar
OLD_SAVE = '            set_config("bairro", bairro)'
NEW_SAVE = ('            set_config("bairro", bairro)\n'
            '            set_config("contato", contato)')
if OLD_SAVE in src and 'set_config("contato"' not in src:
    src = src.replace(OLD_SAVE, NEW_SAVE, 1)
    print("OK: Contato adicionado no salvar.")
else:
    print("INFO: Contato ja existe no salvar.")

# 4) Adiciona campo Responsavel na aba Templates - OE
OLD_TMPL_OE = '        st.markdown("##### Template — Ordem de Entrega (OE)")'
NEW_TMPL_OE = ('        st.markdown("##### Template — Ordem de Entrega (OE)")\n'
               '        _resp_oe = st.text_input(\n'
               '            "Responsável pela OE (aparece no campo Contato do documento)",\n'
               '            value=get_config("template_oe_responsavel", get_config("contato")),\n'
               '            key="resp_oe_input"\n'
               '        )\n'
               '        if st.button("💾 Salvar responsável OE", key="btn_resp_oe"):\n'
               '            set_config("template_oe_responsavel", _resp_oe)\n'
               '            st.success(f"✅ Responsável OE salvo: {_resp_oe}")\n')

if OLD_TMPL_OE in src:
    src = src.replace(OLD_TMPL_OE, NEW_TMPL_OE, 1)
    print("OK: Campo responsavel OE adicionado.")
else:
    print("AVISO: Secao OE nao encontrada.")

# 5) Adiciona campo Responsavel na aba Templates - Certificado
OLD_TMPL_CERT = '        st.markdown("##### Template — Certificado de Qualidade")'
NEW_TMPL_CERT = ('        st.markdown("##### Template — Certificado de Qualidade")\n'
                 '        _resp_cert = st.text_input(\n'
                 '            "Responsável pelo Certificado (aparece no documento)",\n'
                 '            value=get_config("template_cert_responsavel", get_config("contato")),\n'
                 '            key="resp_cert_input"\n'
                 '        )\n'
                 '        if st.button("💾 Salvar responsável Certificado", key="btn_resp_cert"):\n'
                 '            set_config("template_cert_responsavel", _resp_cert)\n'
                 '            st.success(f"✅ Responsável Certificado salvo: {_resp_cert}")\n')

if OLD_TMPL_CERT in src:
    src = src.replace(OLD_TMPL_CERT, NEW_TMPL_CERT, 1)
    print("OK: Campo responsavel Certificado adicionado.")
else:
    print("AVISO: Secao Certificado nao encontrada.")

CFG.write_text(src, encoding="utf-8")

# 6) Atualiza app.py para usar template_oe_responsavel como contato
APP = Path("app.py")
src_app = APP.read_text(encoding="utf-8")

OLD_CFG = '''                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        get_config("bairro"),
                            "cidade":        get_config("cidade"),
                            "estado":        get_config("estado"),
                            "telefone":      get_config("telefone"),
                            "email":         get_config("email"),
                            "rodape_pdf":    get_config("rodape_pdf"),
                            "orientacao":    get_config("template_oe_orientacao", "Paisagem"),
                        }'''

NEW_CFG = '''                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        get_config("bairro"),
                            "cidade":        get_config("cidade"),
                            "estado":        get_config("estado"),
                            "telefone":      get_config("telefone"),
                            "email":         get_config("email"),
                            "contato":       get_config("template_oe_responsavel") or get_config("contato"),
                            "rodape_pdf":    get_config("rodape_pdf"),
                            "orientacao":    get_config("template_oe_orientacao", "Paisagem"),
                        }'''

if OLD_CFG in src_app:
    src_app = src_app.replace(OLD_CFG, NEW_CFG, 1)
    print("OK: Contato adicionado no config do app.")
else:
    print("AVISO: Config app nao encontrado.")

APP.write_text(src_app, encoding="utf-8")

import py_compile, tempfile, os
for nome, codigo in [("empresa_config.py", src), ("app.py", src_app)]:
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

print("\nRode: git add . && git commit -m 'Contato e responsavel por template' && git push")
