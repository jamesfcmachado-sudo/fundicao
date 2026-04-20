from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Busca o botao de download do PDF
for kw in ["dl_pdf_", "Baixar OE", "Baixar.*PDF", "download_button.*pdf"]:
    idx = src.find(kw)
    if idx > 0:
        print(f"=== '{kw}' na posicao {idx} ===")
        print(repr(src[max(0,idx-100):idx+200]))
        print()
