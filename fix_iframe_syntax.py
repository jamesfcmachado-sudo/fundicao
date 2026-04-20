from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Substitui as linhas 3658-3667 (indices 3657-3666) pelo codigo correto
# Primeiro encontra o indice exato da linha com _b64_pdf = _b64v
idx_inicio = None
for i, line in enumerate(lines):
    if '_b64_pdf = _b64v.b64encode(_pdf_bytes).decode()' in line:
        idx_inicio = i - 1  # linha do "if st.session_state"
        break

if idx_inicio is None:
    print("AVISO: Linha nao encontrada.")
    exit(1)

print(f"Bloco encontrado a partir da linha {idx_inicio+1}")

# Encontra o fim do bloco (linha com st.error apos o iframe)
idx_fim = None
for i in range(idx_inicio, idx_inicio + 20):
    if 'st.error(f"Erro ao gerar OE' in lines[i]:
        idx_fim = i
        break

print(f"Fim do bloco na linha {idx_fim+1}")
print("Linhas a substituir:")
for i in range(idx_inicio, idx_fim):
    print(f"  {i+1}: {repr(lines[i])}")

# Substitui as linhas problematicas
NOVAS_LINHAS = [
    '                        if st.session_state.get(f"_show_pdf_{_noe}", False):',
    '                            import base64 as _b64v',
    '                            _b64_pdf = _b64v.b64encode(_pdf_bytes).decode()',
    '                            _html_pdf = (',
    '                                \'<iframe src="data:application/pdf;base64,\'',
    '                                + _b64_pdf +',
    '                                \'" width="100%" height="750px"\'',
    '                                \' style="border:1px solid #444;border-radius:8px;">\'',
    '                                \'</iframe>\'',
    '                            )',
    '                            st.markdown(_html_pdf, unsafe_allow_html=True)',
]

new_lines = lines[:idx_inicio] + NOVAS_LINHAS + lines[idx_fim:]
src = '\n'.join(new_lines)
APP.write_text(src, encoding="utf-8")
print("OK: Linhas substituidas!")

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
