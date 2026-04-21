from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("cert_cliente")
print(repr(src[max(0,idx-300):idx+200]))
