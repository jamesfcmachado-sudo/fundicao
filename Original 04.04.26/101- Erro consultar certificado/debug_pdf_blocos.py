from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Cabecalho
idx = src.find("Logo e titulo")
if idx == -1:
    idx = src.find("Logo placeholder")
if idx == -1:
    idx = src.find("# Logo")
print("=== CABECALHO ===")
print(repr(src[max(0,idx-50):idx+400]))

# Composicao
print("\n=== COMPOSICAO ===")
idx2 = src.find("ELEM_COLS")
print(repr(src[max(0,idx2-50):idx2+400]))
