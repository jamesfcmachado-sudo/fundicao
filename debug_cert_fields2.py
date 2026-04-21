from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Localiza o bloco exato
idx = src.find('_cliente_default')
print(repr(src[max(0,idx-200):idx+600]))
