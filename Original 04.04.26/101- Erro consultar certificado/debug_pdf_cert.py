from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Localiza o problema - PS() com fontSize duplicado
import re

# Encontra todas as chamadas PS() com fontSize
matches = [(m.start(), m.group()) for m in re.finditer(r'PS\([^)]+fontSize[^)]+fontSize[^)]+\)', src)]
for pos, match in matches:
    print(f"Posicao {pos}: {repr(match)}")

# O problema comum e: PS("name", fontSize=8, fontName="...", **kw) onde kw ja tem fontSize
# Vou localizar a funcao PS no certificados.py
idx_ps = src.find("def PS(")
if idx_ps > 0:
    print(f"\nFuncao PS na posicao {idx_ps}:")
    print(repr(src[idx_ps:idx_ps+200]))
else:
    # PS e um alias
    idx_ps2 = src.find("PS = ")
    if idx_ps2 > 0:
        print(f"\nPS alias na posicao {idx_ps2}:")
        print(repr(src[idx_ps2:idx_ps2+100]))

# Procura o padrao problematico
for kw in ["ph(", "pc(", "pl(", "pb("]:
    idx = src.find(kw, src.find("def gerar_certificado_pdf"))
    if idx > 0:
        print(f"\n{kw} na posicao {idx}:")
        print(repr(src[idx:idx+100]))
        break
