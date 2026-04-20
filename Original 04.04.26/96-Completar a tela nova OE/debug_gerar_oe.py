from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Busca todas as ocorrencias do botao
count = 0
idx = 0
while True:
    idx = src.find("Gerar OE", idx)
    if idx == -1:
        break
    count += 1
    print(f"=== Ocorrencia {count} na posicao {idx} ===")
    print(repr(src[max(0,idx-100):idx+150]))
    print()
    idx += 1

print(f"Total: {count} ocorrencias")
