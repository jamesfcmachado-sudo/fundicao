from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

for i, line in enumerate(lines):
    if line.startswith('          sel_of = st.dataframe('):
        lines[i] = '            sel_of = st.dataframe('
        print(f"OK: sel_of corrigido na linha {i+1} para 12 espacos.")

src = '\n'.join(lines)
APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Slider altura tabelas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO linha {e.lineno}: {e.msg}")
finally:
    os.unlink(tmp)
