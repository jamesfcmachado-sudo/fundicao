from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Corrige a linha com quebra de linha no string
OLD = '''    comp_hdr = [ph("OF"), ph("CORRIDA
HEAT Nº")] + [ph(e) for e in ELEM]'''

NEW = '''    comp_hdr = [ph("OF"), ph("CORRIDA\\nHEAT Nº")] + [ph(e) for e in ELEM]'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Corrigido.")
else:
    print("AVISO: Bloco nao encontrado.")
    # Tenta encontrar variacao
    idx = src.find('comp_hdr = [ph("OF"), ph("CORRIDA')
    print(repr(src[idx:idx+100]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'PDF cert layout final' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
