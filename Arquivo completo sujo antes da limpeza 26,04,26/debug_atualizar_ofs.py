from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

idx = src.find("def _atualizar_ofs")
print(repr(src[idx:idx+2000]))
