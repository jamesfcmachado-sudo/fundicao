from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

for i, line in enumerate(lines):
    if 'key="altura_of"' in line:
        lines[i] = '            _altura_of = st.slider("Altura da tabela (px)", min_value=200, max_value=1400, value=500, step=50, key="altura_of")'
        print(f"OK: Slider OF corrigido na linha {i+1} com 12 espacos.")

    if 'key="altura_corr"' in line:
        lines[i] = '            _altura_corr = st.slider("Altura da tabela (px)", min_value=200, max_value=1400, value=400, step=50, key="altura_corr")'
        print(f"OK: Slider Corridas corrigido na linha {i+1} com 12 espacos.")

    # Corrige height=_altura_corr que pode ter indentacao errada
    if 'height=_altura_corr' in line:
        lines[i] = '                height=_altura_corr,'
        print(f"OK: height corrida corrigido na linha {i+1}.")

src = '\n'.join(lines)
APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Slider altura tabelas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
