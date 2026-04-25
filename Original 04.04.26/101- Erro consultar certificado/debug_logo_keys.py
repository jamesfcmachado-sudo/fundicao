from pathlib import Path
import re

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Verifica keys que aparecem nos blocos de logo
print("Keys relacionadas a logo:")
for m in re.finditer(r'key=["\']([^"\']*logo[^"\']*)["\']', src):
    linha = src[:m.start()].count('\n') + 1
    print(f"  Linha {linha}: key='{m.group(1)}'")

print("\nKeys relacionadas a dl_logo:")
for m in re.finditer(r'key=["\']([^"\']*dl_logo[^"\']*)["\']', src):
    linha = src[:m.start()].count('\n') + 1
    print(f"  Linha {linha}: key='{m.group(1)}'")

print("\nKeys relacionadas a rm_logo:")
for m in re.finditer(r'key=["\']([^"\']*rm_logo[^"\']*)["\']', src):
    linha = src[:m.start()].count('\n') + 1
    print(f"  Linha {linha}: key='{m.group(1)}'")

print("\nKeys relacionadas a upload_logo:")
for m in re.finditer(r'key=["\']([^"\']*upload_logo[^"\']*)["\']', src):
    linha = src[:m.start()].count('\n') + 1
    print(f"  Linha {linha}: key='{m.group(1)}'")
