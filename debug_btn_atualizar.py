from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Localiza o bloco do botao de confirmacao
idx = src.find('"btn_confirmar_atualizar_ofs"')
print(f"Botao encontrado na posicao: {idx}")
print(repr(src[max(0,idx-200):idx+200]))
