from pathlib import Path

# 1) Adiciona bairro no empresa_config.py
CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Adiciona bairro nos defaults
OLD_DEF = '"endereco":            "",'
NEW_DEF = ('"endereco":            "",\n'
           '        "bairro":              "",')
if OLD_DEF in src and '"bairro"' not in src:
    src = src.replace(OLD_DEF, NEW_DEF, 1)
    print("OK: bairro adicionado nos defaults.")

# Adiciona campo bairro na tela de dados
OLD_CAMPO = '            endereco = st.text_input("Endereço",\n                value=get_config("endereco"))'
NEW_CAMPO = ('            endereco = st.text_input("Endereço",\n'
             '                value=get_config("endereco"))\n'
             '            bairro = st.text_input("Bairro",\n'
             '                value=get_config("bairro"))')
if OLD_CAMPO in src:
    src = src.replace(OLD_CAMPO, NEW_CAMPO, 1)
    print("OK: Campo bairro adicionado na tela.")
else:
    # Tenta alternativa
    OLD_CAMPO2 = '            endereco = st.text_input("Endere\u00e7o",'
    idx = src.find(OLD_CAMPO2)
    if idx != -1:
        # Encontra o fim da linha de endereco
        fim = src.find('\n', src.find(')', idx)) + 1
        src = src[:fim] + '            bairro = st.text_input("Bairro",\n                value=get_config("bairro"))\n' + src[fim:]
        print("OK: Campo bairro adicionado (alternativo).")
    else:
        print("AVISO: Campo endereco nao encontrado.")

# Adiciona bairro no botao salvar
OLD_SAVE = '            set_config("endereco", endereco)'
NEW_SAVE = ('            set_config("endereco", endereco)\n'
            '            set_config("bairro", bairro)')
if OLD_SAVE in src:
    src = src.replace(OLD_SAVE, NEW_SAVE, 1)
    print("OK: Bairro adicionado no salvar.")

CFG.write_text(src, encoding="utf-8")

# 2) Atualiza o config passado para gerar_oe_pdf no app.py
APP = Path("app.py")
src_app = APP.read_text(encoding="utf-8")

OLD_CFG = '''                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        "",
                            "cidade":        get_config("cidade"),'''

NEW_CFG = '''                        _cfg = {
                            "nome_empresa":  get_config("nome_empresa"),
                            "endereco":      get_config("endereco"),
                            "bairro":        get_config("bairro"),
                            "cidade":        get_config("cidade"),'''

if OLD_CFG in src_app:
    src_app = src_app.replace(OLD_CFG, NEW_CFG, 1)
    print("OK: Bairro adicionado no config do app.")
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

print("\nRode: git add . && git commit -m 'Bairro config empresa e fix Fornecedor PDF' && git push")
