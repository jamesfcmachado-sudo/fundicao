from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

changes = 0

OLD = ('     sel_corr = st.dataframe(\n'
       '                df,\n'
       '                height=400,\n'
       '                use_container_width=True,\n')

NEW = ('     _altura_corr = st.slider("Altura da tabela (px)", '
       'min_value=200, max_value=1400, value=400, step=50, key="altura_corr")\n'
       '     sel_corr = st.dataframe(\n'
       '                df,\n'
       '                height=_altura_corr,\n'
       '                use_container_width=True,\n')

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    changes += 1
    print("OK: Slider adicionado nas Corridas.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print(f"SINTAXE OK! {changes} alteracoes feitas.")
    print("Rode: git add . && git commit -m 'Slider altura tabelas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
