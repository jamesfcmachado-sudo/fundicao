from pathlib import Path
import re

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")
lines = src.split('\n')
print(f"Total linhas local: {len(lines)}")

# Lista TODAS as keys em ordem
all_keys = []
for i, line in enumerate(lines):
    for m in re.finditer(r'key=["\']([^"\']+)["\']', line):
        all_keys.append((i+1, m.group(1)))

print(f"\nTotal de keys: {len(all_keys)}")
print("\nTodas as keys:")
seen = set()
for ln, k in all_keys:
    marker = " *** DUPLICATA ***" if k in seen else ""
    seen.add(k)
    print(f"  Linha {ln}: '{k}'{marker}")
