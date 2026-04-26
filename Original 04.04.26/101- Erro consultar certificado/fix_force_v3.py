from pathlib import Path

# Adiciona versao no empresa_config.py
CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Remove comentario antigo e adiciona novo com timestamp
import time
ts = int(time.time())
src = src.replace("# fix-duplicatas-v2\n", "")
src = f"# fix-duplicatas-v3-{ts}\n" + src
CFG.write_text(src, encoding="utf-8")
print(f"OK: Versao {ts} adicionada. Total linhas: {len(src.split(chr(10)))}")

# Tambem adiciona no app.py para garantir redeploy
APP = Path("app.py")
src_app = APP.read_text(encoding="utf-8")
# Atualiza o marcador de redeploy
import re
src_app = re.sub(r'# redeploy-[^\n]+', f'# redeploy-{ts}', src_app, count=1)
APP.write_text(src_app, encoding="utf-8")
print("OK: app.py atualizado.")

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

print("\nRode: git add empresa_config.py app.py && git commit -m 'Force redeploy v3' && git push")
