from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Encontra e remove a linha duplicada do if
fixed = 0
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Detecta duas linhas seguidas com o mesmo 'if st.session_state.get'
    if ('if st.session_state.get(f"_show_pdf_{_noe}"' in line and
        i + 1 < len(lines) and
        'if st.session_state.get(f"_show_pdf_{_noe}"' in lines[i+1]):
        # Pula a linha duplicada
        new_lines.append(line)
        i += 2  # pula a duplicata
        fixed += 1
        print(f"OK: Linha duplicada removida na linha {i}.")
        continue
    new_lines.append(line)
    i += 1

src = '\n'.join(new_lines)
APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Visualizar PDF OE na tela' && git push")
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
