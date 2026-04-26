from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx = src.find("tela_consulta_certificados")
func_start = src.find("def tela_consulta_certificados")
print(f"Funcao na posicao: {func_start}")

# Mostra o bloco que processa o tipo
idx_tipo = src.find("_norm_tipo", func_start)
print(repr(src[max(0,idx_tipo-200):idx_tipo+300]))
