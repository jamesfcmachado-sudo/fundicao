from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Remove linhas orfas apos a substituicao do bloco sqlite3
# Linhas 3232-3236 (indices 3231-3235) tem codigo sqlite3 orfa
new_lines = []
i = 0
removed = 0
while i < len(lines):
    line = lines[i]
    
    # Remove linha com "import sqlite3 as _sq2" (orfa)
    if line.strip() == 'import sqlite3 as _sq2':
        removed += 1
        i += 1
        continue
    
    # Remove linha com "import sqlite3 as _sq" (orfa)  
    if line.strip() == 'import sqlite3 as _sq':
        removed += 1
        i += 1
        continue

    # Remove linha com apenas ")" que vem apos "pass  # DB_PATH removido"
    if line.strip() == ')' and i > 0 and 'DB_PATH removido' in lines[i-1]:
        removed += 1
        i += 1
        continue
    
    # Remove linhas _cx3.commit() e _cx3.close() orfas
    if line.strip() in ('_cx3.commit()', '_cx3.close()', '_cx2.commit()', '_cx2.close()'):
        removed += 1
        i += 1
        continue

    # Remove linhas com _sq2.connect ou _cx3 = que ficaram orfas
    if '_cx3 = ' in line or '_cx2 = ' in line or '_sq2.connect' in line:
        removed += 1
        i += 1
        continue

    new_lines.append(line)
    i += 1

print(f"Removidas {removed} linhas orfas.")
src = '\n'.join(new_lines)
APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove DB_PATH PostgreSQL' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    # Mostra contexto do erro
    msg = str(e)
    import re
    m = re.search(r'line (\d+)', msg)
    if m:
        ln = int(m.group(1))
        lines2 = src.split('\n')
        for x in range(max(0,ln-5), min(len(lines2),ln+3)):
            print(f"  {x+1}: {repr(lines2[x])}")
finally:
    os.unlink(tmp)
