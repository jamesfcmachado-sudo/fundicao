from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("btn_salvar_cer")
print(repr(src[max(0,idx-50):idx+500]))
