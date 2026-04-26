from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("I - Composição Química (Corridas)")
print(repr(src[idx:idx+300]))
