from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Ver onde fmt_num e chamado
import re
for m in re.finditer(r'fmt_num', src):
    linha = src[:m.start()].count('\n') + 1
    print(f"Linha {linha}: {repr(src[max(0,m.start()-20):m.start()+50])}")

# Ver o loop de composicao
idx = src.find("for ek in")
print(f"\nLoop composicao:")
print(repr(src[max(0,idx-50):idx+200]))
