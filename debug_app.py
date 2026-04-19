from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Busca o trecho exato que precisa ser alterado
import re

# Encontra o padrao do botao de download da OE
padrao = r'(f"[^"]*Baixar OE \{_noe\} em PDF"[^\n]*\n\s+data=_pdf_bytes[^\n]*\n[^\n]*\n\s+key=f"dl_pdf_\{_noe\}"[^\n]*\n\s+type="primary"[^\n]*\n\s+\))'

match = re.search(padrao, src)
if match:
    print(f"Encontrado na posicao {match.start()}")
    print(repr(src[match.start()-200:match.start()+200]))
else:
    # Busca pelo trecho mais simples
    idx = src.find('Baixar OE')
    while idx != -1:
        trecho = src[max(0,idx-300):idx+300]
        if 'gerar' in trecho.lower() or 'pdf' in trecho.lower():
            print(f"Posicao {idx}:")
            print(repr(trecho))
            print("---")
        idx = src.find('Baixar OE', idx+1)
