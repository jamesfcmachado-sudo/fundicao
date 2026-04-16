from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# 1) Remove o bloco de selecao de quantidade de OEs e certificados
OLD1 = ('    st.markdown("##### Ordens de entrega (OE) e certificados")\n'
        '    st.caption("Defina quantas linhas deseja preencher (fora do form\u00f3rio principal).")\n'
        '    colx, coly = st.columns(2)\n'
        '    with colx:\n'
        '        n_oes = st.number_input("Quantas OEs?", min_value=0, max_value=30, value=0, step=1)\n'
        '    with coly:\n'
        '        n_certs = st.number_input("Quantos certificados?", min_value=0, max_value=30, value=0, step=1)\n')

NEW1 = ('    # Campos de OE e certificados removidos - usar abas especificas\n'
        '    n_oes = 0\n'
        '    n_certs = 0\n')

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    print("OK: Campos de OE e certificados removidos do topo.")
else:
    # Tenta versao com caption diferente
    OLD1b = ('    st.markdown("##### Ordens de entrega (OE) e certificados")\n'
             '    st.caption("Defina quantas linhas deseja preencher (fora do formul\u00e1rio principal).")\n'
             '    colx, coly = st.columns(2)\n'
             '    with colx:\n'
             '        n_oes = st.number_input("Quantas OEs?", min_value=0, max_value=30, value=0, step=1)\n'
             '    with coly:\n'
             '        n_certs = st.number_input("Quantos certificados?", min_value=0, max_value=30, value=0, step=1)\n')
    if OLD1b in src:
        src = src.replace(OLD1b, NEW1, 1)
        print("OK: Campos de OE e certificados removidos do topo (v2).")
    else:
        print("AVISO: Bloco de OE/certificados nao encontrado. Buscando linha por linha...")
        lines = src.split('\n')
        new_lines = []
        skip = False
        i = 0
        while i < len(lines):
            line = lines[i]
            if 'Ordens de entrega (OE) e certificados' in line:
                new_lines.append('    # Campos de OE e certificados removidos')
                new_lines.append('    n_oes = 0')
                new_lines.append('    n_certs = 0')
                # Pula as proximas 7 linhas (o bloco inteiro)
                i += 8
                print("OK: Bloco removido via busca linha por linha.")
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
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove OE e cert da Nova OF' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
