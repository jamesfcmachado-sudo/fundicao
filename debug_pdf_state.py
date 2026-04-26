from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Verifica se fmt_num existe
print("fmt_num:", "def fmt_num" in src)

# Verifica norma
idx = src.find("_norma_txt")
print(f"\n_norma_txt na posicao {idx}:")
print(repr(src[max(0,idx-50):idx+200]))

# Verifica decimais na composicao
idx2 = src.find("fmt_num")
print(f"\nfmt_num usado na posicao {idx2}:")
print(repr(src[max(0,idx2-50):idx2+100]))

# Verifica se a funcao foi realmente reescrita
idx3 = src.find("def gerar_certificado_pdf")
print(f"\nFuncao na posicao {idx3}")
print(repr(src[idx3:idx3+200]))
