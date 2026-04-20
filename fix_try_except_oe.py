from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Corrige linha 3655 - quebra de linha indevida no session_state
# E adiciona st.success antes do st.error

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # Corrige a linha 3655 que tem atribuicao quebrada
    if ('st.session_state[f"_show_pdf_{_noe}"] =' in line and
            'not st.session_state' in line):
        # Separa em duas linhas corretas
        indent = ' ' * (len(line) - len(line.lstrip()))
        new_lines.append(f'{indent}st.session_state[f"_show_pdf_{{_noe}}"] = \\')
        new_lines.append(f'{indent}    not st.session_state.get(f"_show_pdf_{{_noe}}", False)')
        i += 1
        continue

    # Adiciona st.success antes do st.error (linha 3669)
    if 'st.error(f"Erro ao gerar OE: {_ex}")' in line:
        indent = ' ' * (len(line) - len(line.lstrip()))
        new_lines.append(f'{indent}st.success(f"OE {{_noe}} gerada com sucesso!")')
        new_lines.append(line)
        i += 1
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
