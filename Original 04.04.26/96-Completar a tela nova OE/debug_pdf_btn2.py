from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

idx = src.find('dl_pdf_')
print(repr(src[max(0,idx-400):idx+400]))
