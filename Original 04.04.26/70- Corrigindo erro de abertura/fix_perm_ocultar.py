"""
fix_perm_ocultar.py
Oculta botoes de alterar para usuarios sem permissao.
"""
from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "pode_alterar_of" in src:
    print("Ja aplicado!")
    exit(0)

changes = 0

# 1) Insere variaveis de permissao no inicio de pagina_relatorios
OLD1 = 'def pagina_relatorios() -> None:\n    st.title("Relat\u00f3rios")'
NEW1 = ('def pagina_relatorios() -> None:\n'
        '    st.title("Relat\u00f3rios")\n'
        '    pode_alterar_of = tem_permissao("relatorios_alterar_of")\n'
        '    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")\n'
        '    pode_configuracoes = tem_permissao("configuracoes")')

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes += 1
    print("OK: Variaveis de permissao adicionadas.")
else:
    print("ERRO: Funcao pagina_relatorios nao encontrada!")
    exit(1)

# 2) Envolve o bloco de alterar OF com if pode_alterar_of:
OLD2 = '                    # \u2500\u2500 Alterar \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n                    with _col_alt:'
NEW2 = ('                    # \u2500\u2500 Alterar \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
        '                    if pode_alterar_of:\n'
        '                     with _col_alt:')

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    changes += 1
    print("OK: Bloco alterar OF ocultado.")
else:
    # Tenta versao alternativa
    OLD2b = '                    with _col_alt:\n                        with st.expander("\u270f\ufe0f Alterar dados desta OF"'
    if OLD2b in src:
        NEW2b = ('                    if pode_alterar_of:\n'
                 '                     with _col_alt:\n'
                 '                      with st.expander("\u270f\ufe0f Alterar dados desta OF"')
        src = src.replace(OLD2b, NEW2b, 1)
        changes += 1
        print("OK: Bloco alterar OF ocultado (v2).")
    else:
        print("AVISO: Bloco alterar OF nao encontrado.")

# 3) Oculta expander de alterar Corrida
OLD3 = '                # \u2500\u2500 Alterar Corrida \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n                    with st.expander("\u270f\ufe0f Alterar dados desta corrida"'
NEW3 = ('                # \u2500\u2500 Alterar Corrida \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
        '                    if pode_alterar_corrida:\n'
        '                     with st.expander("\u270f\ufe0f Alterar dados desta corrida"')

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes += 1
    print("OK: Bloco alterar Corrida ocultado.")
else:
    print("AVISO: Bloco alterar Corrida nao encontrado.")

# 4) Oculta aba Configuracoes
OLD4 = ('    tab1, tab2, tab3, tab4 = st.tabs(["Ordens de fabrica\u00e7\u00e3o", "Corridas", "Resumo", "\u2699\ufe0f Configura\u00e7\u00f5es"])')
NEW4 = ('    if pode_configuracoes:\n'
        '        tab1, tab2, tab3, tab4 = st.tabs(["Ordens de fabrica\u00e7\u00e3o", "Corridas", "Resumo", "\u2699\ufe0f Configura\u00e7\u00f5es"])\n'
        '    else:\n'
        '        _tabs_sem_cfg = st.tabs(["Ordens de fabrica\u00e7\u00e3o", "Corridas", "Resumo"])\n'
        '        tab1, tab2, tab3, tab4 = _tabs_sem_cfg[0], _tabs_sem_cfg[1], _tabs_sem_cfg[2], None')

if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    changes += 1
    print("OK: Aba Configuracoes ocultada.")
else:
    print("AVISO: Linha de tabs nao encontrada.")

# 5) Protege o with tab4 para nao quebrar quando tab4 for None
OLD5 = '    with tab4:'
NEW5 = '    if tab4:\n     with tab4:'

# Substitui apenas a primeira ocorrencia de "    with tab4:"
idx = src.find(OLD5)
if idx != -1:
    src = src[:idx] + NEW5 + src[idx + len(OLD5):]
    changes += 1
    print("OK: with tab4 protegido.")

APP.write_text(src, encoding="utf-8")

# Verifica sintaxe
import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print(f"\nSINTAXE OK! {changes} alteracoes feitas.")
    print("Rode: git add . && git commit -m 'Oculta botoes sem permissao' && git push")
except py_compile.PyCompileError as e:
    print(f"\nERRO DE SINTAXE: {e}")
    print("Restaure: copy app_auth_backup.py app.py")
finally:
    os.unlink(tmp)
