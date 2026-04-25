from pathlib import Path

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

print(f"Total antes: {len(lines)}")

# Remove linhas 624 ate o fim (indice 623 em diante)
# A linha 623 e 'st.divider()' que faz parte do bloco original
# Vamos manter ate a linha 622 e remover o resto
new_lines = lines[:622]

print(f"Total depois: {len(new_lines)}")
print("Ultimas 5 linhas:")
for i, l in enumerate(new_lines[-5:]):
    print(f"  {len(new_lines)-4+i}: {repr(l)}")

src = '\n'.join(new_lines)
CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove duplicata templates personalizados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-3), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
