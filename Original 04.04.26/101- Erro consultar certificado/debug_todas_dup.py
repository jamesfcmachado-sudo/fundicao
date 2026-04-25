from pathlib import Path
import re

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

print(f"Total de linhas: {len(lines)}")

keys = {}
duplicatas = []
for i, line in enumerate(lines):
    m = re.search(r'key=["\']([^"\']+)["\']', line)
    if m:
        k = m.group(1)
        if k in keys:
            duplicatas.append((k, keys[k]+1, i+1))
        else:
            keys[k] = i

if duplicatas:
    print(f"\n{len(duplicatas)} DUPLICATAS encontradas:")
    for k, l1, l2 in duplicatas:
        print(f"  key='{k}': linhas {l1} e {l2}")
else:
    print("Nenhuma duplicata encontrada!")
