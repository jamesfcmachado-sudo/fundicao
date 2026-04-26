from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Verifica como está o bloco de visualizacao atualmente
idx = src.find('_pdf_cache_')
while idx > 0:
    print(f"Posicao {idx}:")
    print(repr(src[max(0,idx-50):idx+200]))
    print()
    idx = src.find('_pdf_cache_', idx+1)
