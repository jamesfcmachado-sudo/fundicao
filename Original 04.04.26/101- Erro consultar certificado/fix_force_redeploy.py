from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Adiciona comentario no topo para forcar mudanca real
if "# fix-duplicatas-v2" not in src:
    src = "# fix-duplicatas-v2\n" + src
    CFG.write_text(src, encoding="utf-8")
    print(f"OK: Comentario adicionado. Total linhas: {len(src.split(chr(10)))}")
else:
    print("Ja tem o comentario.")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK!")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
