from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Verifica se logo certificado esta na aba de logotipos
idx = src.find("tab2")  # aba de logotipos
print(f"tab2 na posicao: {idx}")
print(repr(src[idx:idx+200]))

# Verifica se logo_certificado esta no arquivo
idx2 = src.find("logo_certificado_base64")
print(f"\nlogo_certificado_base64 na posicao: {idx2}")
if idx2 > 0:
    print(repr(src[max(0,idx2-100):idx2+200]))
