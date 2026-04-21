from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("def tela_novo_certificado")
print(repr(src[idx:idx+2000]))
