from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona um comentario no topo para forcar novo deploy
OLD = '# -*- coding: utf-8 -*-'
NEW = '# -*- coding: utf-8 -*-\n# deploy: PDF fiel ao template v2'

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Comentario adicionado.")
else:
    # Adiciona no inicio do arquivo
    src = '# deploy: PDF fiel ao template v2\n' + src
    print("OK: Comentario adicionado no inicio.")

APP.write_text(src, encoding="utf-8")
print("Rode: git add app.py && git commit -m 'Force redeploy PDF' && git push")
