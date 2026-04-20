from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Problemas identificados:
# 1. Linha 3624-3632: gerar_oe_pdf duplicado - remover
# 2. Linha 3658: st.error fora do try - mover para dentro
# 3. Linha 3660-3674: visualizacao fora do try - manter mas corrigir indentacao

new_lines = []
i = 0
skip_dup = False

while i < len(lines):
    line = lines[i]
    ln = i + 1

    # Remove bloco duplicado de gerar_oe_pdf (linhas 3624-3632)
    if ln == 3624 and 'from gerar_oe_excel import gerar_oe_pdf' in line:
        # Pula ate linha 3632
        while i < len(lines) and i + 1 <= 3632:
            i += 1
        continue

    # Na linha 3657 (linha vazia apos session_state), adiciona o except
    if ln == 3657 and line == '':
        new_lines.append('')
        new_lines.append('                    except Exception as _ex:')
        new_lines.append('                        st.error(f"Erro ao gerar OE: {_ex}")')
        i += 1
        continue

    # Pula a linha 3658 (st.error duplicado e fora do lugar)
    if ln == 3658 and 'st.error(f"Erro ao gerar OE: {_ex}")' in line:
        i += 1
        continue

    # Linha 3659 vazia apos o erro - pula
    if ln == 3659 and line == '':
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
        ln2 = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln2-5), min(len(ls),ln2+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
