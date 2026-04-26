from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

idx = src.find("def tela_importar_excel()")
fim = src.find("\ndef ", idx + 100)
print(repr(src[idx:idx+3000]))
