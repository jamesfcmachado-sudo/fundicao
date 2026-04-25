from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Mostra o bloco de templates personalizados
idx = src.find("Templates Personalizados")
print(repr(src[idx:idx+2000]))
