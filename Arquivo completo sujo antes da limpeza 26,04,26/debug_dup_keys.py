from pathlib import Path

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

# Mostra linhas ao redor da 629
print("Linhas 625-635:")
for i in range(624, 635):
    print(f"  {i+1}: {repr(lines[i])}")

# Busca todas as keys de text_input para achar duplicatas
import re
keys = {}
for i, line in enumerate(lines):
    m = re.search(r'key=["\']([^"\']+)["\']', line)
    if m:
        k = m.group(1)
        if k in keys:
            print(f"\nDUPLICATA: key='{k}'")
            print(f"  Linha {keys[k]+1}: {repr(lines[keys[k]])}")
            print(f"  Linha {i+1}: {repr(line)}")
        else:
            keys[k] = i
