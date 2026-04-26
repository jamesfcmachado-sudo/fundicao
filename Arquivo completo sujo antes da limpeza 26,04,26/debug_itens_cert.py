from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("III - Outros Dados (Itens)")
print(repr(src[idx:idx+1500]))
