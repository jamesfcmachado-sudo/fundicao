from pathlib import Path
import re

AUTH = Path("auth.py")
src = AUTH.read_text(encoding="utf-8")
lines = src.split('\n')

print(f"Total de linhas auth.py: {len(lines)}")

# Busca todas as keys duplicadas
keys = {}
duplicatas = []
for i, line in enumerate(lines):
    for m in re.finditer(r'key=["\']([^"\']+)["\']', line):
        k = m.group(1)
        if k in keys:
            duplicatas.append((k, keys[k]+1, i+1))
        else:
            keys[k] = i

if duplicatas:
    print(f"\n{len(duplicatas)} DUPLICATAS em auth.py:")
    for k, l1, l2 in duplicatas:
        print(f"  key='{k}': linhas {l1} e {l2}")
        print(f"    L{l1}: {repr(lines[l1-1])}")
        print(f"    L{l2}: {repr(lines[l2-1])}")
else:
    print("Nenhuma duplicata em auth.py")

# Verifica tambem o empresa_config importado
print("\n--- Verificando novo_tmpl_nome no empresa_config ---")
CFG = Path("empresa_config.py")
src2 = CFG.read_text(encoding="utf-8")
count = src2.count('"novo_tmpl_nome"')
print(f"'novo_tmpl_nome' aparece {count} vez(es)")
