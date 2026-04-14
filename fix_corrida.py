from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = ('                with _cc1:\n'
       '                    with st.expander("\u270f\ufe0f Alterar dados desta corrida", expanded=False):')

NEW = ('                if pode_alterar_corrida:\n'
       '                 with _cc1:\n'
       '                  with st.expander("\u270f\ufe0f Alterar dados desta corrida", expanded=False):')

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Alterar Corrida ocultado!")
else:
    print("AVISO: Texto nao encontrado!")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Pode fazer git push.")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    print("Restaure: copy app_auth_backup.py app.py")
finally:
    os.unlink(tmp)
