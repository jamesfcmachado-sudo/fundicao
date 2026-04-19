from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Localiza o bloco de alterar OE
idx = src.find("✏️ Alterar OE")
if idx == -1:
    print("AVISO: Bloco alterar OE nao encontrado.")
    exit(1)

print(f"Bloco encontrado na posicao {idx}")
print(repr(src[idx:idx+800]))
