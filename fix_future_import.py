from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Remove a linha from __future__ import annotations que nao esta no inicio
new_lines = []
for i, line in enumerate(lines):
    if 'from __future__ import annotations' in line and i > 5:
        print(f"Removendo linha {i+1}: {repr(line)}")
        continue
    new_lines.append(line)

src = '\n'.join(new_lines)
APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix future import' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
