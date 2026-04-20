from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Localiza e remove o bloco completo do segundo botao
idx_inicio = src.find('            # Gerar PDF da OE selecionada\n            st.divider()\n\n            # ── Botao gerar OE com template Excel')
idx_fim = src.find('\n            else:\n                st.caption("Configure o template Excel em', idx_inicio)
idx_fim2 = src.find('\n', src.find('Templates")', idx_fim)) + 1

if idx_inicio > 0 and idx_fim2 > 0:
    bloco = src[idx_inicio:idx_fim2]
    print(f"Removendo {len(bloco)} chars:")
    print(repr(bloco[:100]))
    src = src[:idx_inicio] + src[idx_fim2:]
    print("OK: Segundo botao removido.")
else:
    print(f"AVISO: inicio={idx_inicio}, fim={idx_fim2}")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove segundo botao gerar OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-5), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
