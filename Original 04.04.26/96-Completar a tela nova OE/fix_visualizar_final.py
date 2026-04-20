from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Remove linhas 3657-3669 (indices 3656-3668) e reinsere corretamente
# O bloco de visualizacao deve ficar FORA do try/except

new_lines = []
i = 0
skip_until = None
visualizacao_inserida = False

while i < len(lines):
    line = lines[i]

    # Marca o inicio do bloco de visualizacao dentro do try (para remover)
    if '# Exibe PDF inline se solicitado' in line and not visualizacao_inserida:
        # Pula este bloco ate o st.error
        i += 1
        while i < len(lines):
            if 'st.error(f"Erro ao gerar OE: {_ex}")' in lines[i]:
                break
            i += 1
        continue

    # No st.success (que foi adicionado antes do st.error), substituimos
    if 'st.success(f"OE {_noe} gerada com sucesso!")' in line:
        indent = '                        '
        new_lines.append(line)  # mantem o st.success
        i += 1
        continue

    # No st.error, fechamos o try/except e adicionamos a visualizacao depois
    if 'st.error(f"Erro ao gerar OE: {_ex}")' in line:
        new_lines.append(line)  # st.error
        i += 1
        # Adiciona visualizacao FORA do try/except
        new_lines.append('')
        new_lines.append('                        # Exibe PDF inline se solicitado')
        new_lines.append('                        if st.session_state.get(f"_show_pdf_{_noe}", False) and "_pdf_bytes" in dir():')
        new_lines.append('                            try:')
        new_lines.append('                                import base64 as _b64v')
        new_lines.append('                                _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()')
        new_lines.append('                                _html_pdf = (')
        new_lines.append('                                    \'<iframe src="data:application/pdf;base64,\'')
        new_lines.append('                                    + _b64_pdf +')
        new_lines.append('                                    \'" width="100%" height="750px"\'')
        new_lines.append('                                    \' style="border:1px solid #444;border-radius:8px;">\'')
        new_lines.append("                                    '</iframe>'")
        new_lines.append('                                )')
        new_lines.append('                                st.markdown(_html_pdf, unsafe_allow_html=True)')
        new_lines.append('                            except Exception:')
        new_lines.append('                                pass')
        visualizacao_inserida = True
        continue

    # Corrige a linha com session_state quebrada
    if ('st.session_state[f"_show_pdf_{_noe}"] =' in line and
            'not st.session_state' in line):
        indent = ' ' * (len(line) - len(line.lstrip()))
        new_lines.append(f'{indent}st.session_state[f"_show_pdf_{{_noe}}"] = \\')
        new_lines.append(f'{indent}    not st.session_state.get(f"_show_pdf_{{_noe}}", False)')
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
