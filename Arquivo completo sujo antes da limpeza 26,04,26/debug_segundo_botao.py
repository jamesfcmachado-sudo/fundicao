from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

idx = src.find('"📊 Gerar OE com Template Excel", key="btn_excel_oe"')
if idx > 0:
    print(repr(src[max(0,idx-300):idx+500]))
