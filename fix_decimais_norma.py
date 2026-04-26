from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix 1: Corrige fmt_num - remove zeros a direita corretamente
OLD_FMT = '''    def fmt_num(v):
        """Formata numero com casas decimais variaveis como no template."""
        try:
            f = float(v or 0)
            if f == 0: return ""
            # Remove zeros a direita mas mantem pelo menos 2 casas
            s = f"{f:.4f}".rstrip("0")
            if s.endswith("."): s += "0"
            return s.replace(".", ",")
        except Exception:
            return str(v or "")'''

NEW_FMT = '''    def fmt_num(v):
        """Formata numero com casas decimais variaveis como no template."""
        try:
            f = float(v or 0)
            if f == 0: return ""
            # Usa 4 casas e remove zeros a direita
            s = f"{f:.4f}"
            # Remove zeros a direita apos a virgula
            s = s.rstrip("0").rstrip(".")
            # Garante pelo menos 1 casa decimal
            if "." not in s:
                s = s + ".0"
            return s.replace(".", ",")
        except Exception:
            return str(v or "")'''

if OLD_FMT in src:
    src = src.replace(OLD_FMT, NEW_FMT, 1)
    print("OK: fmt_num corrigido.")
else:
    print("AVISO: fmt_num nao encontrado.")

# Fix 2: Verifica por que a norma nao aparece
# Busca onde norma e definida
idx = src.find('norma    = cert_data.get("norma"')
print(f"\nnorma definida na posicao {idx}:")
print(repr(src[idx:idx+100]))

# Busca onde _norma_txt e usada na tabela
idx2 = src.find('ph(f"{_norma_txt}"')
print(f"\n_norma_txt usada na posicao {idx2}:")
print(repr(src[max(0,idx2-100):idx2+100]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("\nSINTAXE OK! Rode: git add . && git commit -m 'Fix decimais PDF cert' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
