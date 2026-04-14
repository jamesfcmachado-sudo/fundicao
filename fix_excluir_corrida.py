"""
fix_excluir_corrida.py
Oculta botao de excluir corrida para usuarios sem permissao
e adiciona a permissao no auth.py
"""
from pathlib import Path

# ── 1) Adiciona permissao no auth.py ─────────────────────────────────────────
AUTH = Path("auth.py")
auth_src = AUTH.read_text(encoding="utf-8")

OLD_PERM = '"relatorios_alterar_corrida": "Relat\u00f3rios \u2192 Alterar Corridas",'
NEW_PERM = ('"relatorios_alterar_corrida": "Relat\u00f3rios \u2192 Alterar Corridas",\n'
            '    "relatorios_excluir_corrida": "Relat\u00f3rios \u2192 Excluir Corridas",')

if "relatorios_excluir_corrida" in auth_src:
    print("AVISO: Permissao ja existe no auth.py")
elif OLD_PERM in auth_src:
    auth_src = auth_src.replace(OLD_PERM, NEW_PERM, 1)
    AUTH.write_text(auth_src, encoding="utf-8")
    print("OK: Permissao 'relatorios_excluir_corrida' adicionada no auth.py")
else:
    print("AVISO: Texto nao encontrado no auth.py")

# ── 2) Adiciona variavel no app.py ────────────────────────────────────────────
APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "pode_excluir_corrida" in src:
    print("AVISO: Variavel ja existe no app.py")
else:
    OLD_VAR = ('    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")\n'
               '    pode_configuracoes = tem_permissao("configuracoes")')
    NEW_VAR = ('    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")\n'
               '    pode_excluir_corrida = tem_permissao("relatorios_excluir_corrida")\n'
               '    pode_configuracoes = tem_permissao("configuracoes")')

    if OLD_VAR in src:
        src = src.replace(OLD_VAR, NEW_VAR, 1)
        print("OK: Variavel 'pode_excluir_corrida' adicionada.")
    else:
        print("AVISO: Bloco de variaveis nao encontrado.")

# ── 3) Oculta botao excluir Corrida ──────────────────────────────────────────
OLD_EXC = ('                with _cc2:\n'
           '                    with st.expander("\U0001f5d1\ufe0f Excluir esta corrida", expanded=False):')
NEW_EXC = ('                if pode_excluir_corrida:\n'
           '                 with _cc2:\n'
           '                  with st.expander("\U0001f5d1\ufe0f Excluir esta corrida", expanded=False):')

if OLD_EXC in src:
    src = src.replace(OLD_EXC, NEW_EXC, 1)
    print("OK: Botao excluir Corrida ocultado.")
else:
    print("AVISO: Botao excluir Corrida nao encontrado.")

APP.write_text(src, encoding="utf-8")

# ── Verifica sintaxe ──────────────────────────────────────────────────────────
import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("\nSINTAXE OK! Rode: git add . && git commit -m 'Permissao excluir corrida' && git push")
except py_compile.PyCompileError as e:
    print(f"\nERRO: {e}")
finally:
    os.unlink(tmp)
