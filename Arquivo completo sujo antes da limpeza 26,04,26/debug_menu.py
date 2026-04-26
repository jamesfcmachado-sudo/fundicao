from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Busca o menu lateral
idx = src.find('"Nova Ordem de Entrega"')
print(repr(src[max(0,idx-100):idx+400]))
