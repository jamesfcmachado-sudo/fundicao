from pathlib import Path
import re

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Pega a funcao tela_novo_certificado
idx_ini = src.find("def tela_novo_certificado(")
idx_fim = src.find("\ndef tela_consulta_certificados")

funcao = src[idx_ini:idx_fim]

# Lista todas as keys do formulario
print("=== KEYS DO FORMULARIO ===")
for m in re.finditer(r'key="([^"]+)"', funcao):
    linha = funcao[:m.start()].count('\n') + 1
    print(f"  Linha {linha}: key='{m.group(1)}'")
