from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Verifica quantas vezes aparece logo_certificado_base64
count = src.count("logo_certificado_base64")
print(f"logo_certificado_base64 aparece {count} vezes")

# Localiza todos os blocos
import re
for m in re.finditer(r'logo_certificado_base64', src):
    print(f"  Posicao {m.start()}: {repr(src[max(0,m.start()-50):m.start()+80])}")
