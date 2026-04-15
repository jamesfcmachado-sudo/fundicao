from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

for i, line in enumerate(lines):
    # Corrige indentacao do slider de OF para bater com sel_of (10 espacos)
    if 'key="altura_of"' in line and line.startswith('            '):
        lines[i] = line.replace('            _altura_of', '          _altura_of', 1)
        print(f"OK: Linha {i+1} corrigida para 10 espacos.")
        break

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
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
