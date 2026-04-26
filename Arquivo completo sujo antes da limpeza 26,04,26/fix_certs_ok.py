from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Verifica se _CERTS_OK esta sendo definido antes do uso
idx_certs_ok = src.find("_CERTS_OK = True")
idx_uso = src.find("if _CERTS_OK:")
print(f"_CERTS_OK definido na posicao: {idx_certs_ok}")
print(f"_CERTS_OK usado na posicao: {idx_uso}")

# Garante que _CERTS_OK tem valor padrao no inicio do main()
OLD_MAIN = "def main():"
NEW_MAIN = """def main():
    global _CERTS_OK
    if '_CERTS_OK' not in dir():
        _CERTS_OK = False"""

if OLD_MAIN in src and "global _CERTS_OK" not in src:
    src = src.replace(OLD_MAIN, NEW_MAIN, 1)
    print("OK: _CERTS_OK garantido no main().")
else:
    print("INFO: Ja existe ou main nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix _CERTS_OK NameError' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
