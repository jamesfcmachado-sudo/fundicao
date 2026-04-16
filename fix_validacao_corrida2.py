from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = ('    if not numero_corrida.strip() or not nome_cliente.strip():\n'
       '        st.error("Preencha n\u00famero da corrida e nome do cliente.")\n'
       '        return')

NEW = ('    if not numero_corrida.strip():\n'
       '        st.error("Preencha o numero da corrida.")\n'
       '        return\n'
       '    if not nome_cliente.strip():\n'
       '        st.error("Preencha o nome do cliente. Este campo e obrigatorio.")\n'
       '        return\n'
       '    if not data_fusao:\n'
       '        st.error("Preencha a data de fusao.")\n'
       '        return')

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Validacao reforçada.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Validacao campos corrida' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
