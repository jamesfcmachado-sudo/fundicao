from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Verifica como está atualmente
idx = src.find("proximo_num")
print("Contexto atual:")
print(repr(src[max(0,idx-200):idx+300]))
