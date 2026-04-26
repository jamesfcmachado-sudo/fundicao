from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("def tela_novo_certificado")
print(f"Funcao na posicao: {idx}")
print(repr(src[idx:idx+300]))

idx_fim = src.find("\ndef ", idx + 100)
print(f"\nFim na posicao: {idx_fim}")
print(repr(src[idx_fim-200:idx_fim+50]))
