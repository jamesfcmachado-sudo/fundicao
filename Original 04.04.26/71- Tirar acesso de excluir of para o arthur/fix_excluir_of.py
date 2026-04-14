"""
fix_excluir_of.py
Oculta botao de excluir OF para usuarios sem permissao
e adiciona a permissao no auth.py
"""
from pathlib import Path

# ── 1) Adiciona permissao no auth.py ─────────────────────────────────────────
AUTH = Path("auth.py")
auth_src = AUTH.read_text(encoding="utf-8")

OLD_PERM = '"relatorios_alterar_of":  "Relat\u00f3rios \u2192 Alterar OF",'
NEW_PERM = ('"relatorios_alterar_of":  "Relat\u00f3rios \u2192 Alterar OF",\n'
            '    "relatorios_excluir_of":  "Relat\u00f3rios \u2192 Excluir OF",')

if OLD_PERM in auth_src:
    auth_src = auth_src.replace(OLD_PERM, NEW_PERM, 1)
    AUTH.write_text(auth_src, encoding="utf-8")
    print("OK: Permissao 'relatorios_excluir_of' adicionada no auth.py")
else:
    print("AVISO: Permissao ja existe ou texto nao encontrado no auth.py")

# ── 2) Adiciona variavel no app.py ────────────────────────────────────────────
APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "pode_excluir_of" in src:
    print("AVISO: Variavel ja existe no app.py")
else:
    OLD_VAR = ('    pode_alterar_of = tem_permissao("relatorios_alterar_of")\n'
               '    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")')
    NEW_VAR = ('    pode_alterar_of = tem_permissao("relatorios_alterar_of")\n'
               '    pode_excluir_of = tem_permissao("relatorios_excluir_of")\n'
               '    pode_alterar_corrida = tem_permissao("relatorios_alterar_corrida")')

    if OLD_VAR in src:
        src = src.replace(OLD_VAR, NEW_VAR, 1)
        print("OK: Variavel 'pode_excluir_of' adicionada.")
    else:
        print("AVISO: Bloco de variaveis nao encontrado.")

# ── 3) Oculta botao excluir OF ────────────────────────────────────────────────
OLD_EXC = ('                    with _col_exc:\n'
           '                        with st.expander("\U0001f5d1\ufe0f Excluir esta OF"')
NEW_EXC = ('                    if pode_excluir_of:\n'
           '                     with _col_exc:\n'
           '                      with st.expander("\U0001f5d1\ufe0f Excluir esta OF"')

if OLD_EXC in src:
    src = src.replace(OLD_EXC, NEW_EXC, 1)
    print("OK: Botao excluir OF ocultado.")
else:
    print("AVISO: Botao excluir OF nao encontrado.")

APP.write_text(src, encoding="utf-8")

# ── Verifica sintaxe ──────────────────────────────────────────────────────────
import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("\nSINTAXE OK! Rode: git add . && git commit -m 'Permissao excluir OF' && git push")
except py_compile.PyCompileError as e:
    print(f"\nERRO: {e}")
    print("Restaure: copy app_auth_backup.py app.py")
finally:
    os.unlink(tmp)
