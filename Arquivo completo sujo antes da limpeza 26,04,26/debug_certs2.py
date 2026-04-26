from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

for kw in ["_CERTS_OK", "from certificados", "init_certificados"]:
    idx = src.find(kw)
    if idx > 0:
        print(f"'{kw}' na posicao {idx}:")
        print(repr(src[max(0,idx-50):idx+150]))
    else:
        print(f"'{kw}' NAO ENCONTRADO")
    print()
