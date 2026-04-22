from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Localiza o trecho da query na consulta
idx = src.find("def tela_consulta_certificados")
trecho = src[idx:idx+3000]
print(repr(trecho[1000:2000]))
