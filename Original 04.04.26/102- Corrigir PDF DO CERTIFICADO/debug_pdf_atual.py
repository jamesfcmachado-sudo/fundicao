from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("def gerar_certificado_pdf")
print(repr(src[idx:idx+4000]))
