"""
fix_tabelas_altura.py
- Exibe itens mais recentes primeiro (já está correto em maioria)
- Adiciona slider de altura nas 3 tabelas principais
"""
from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

if "altura_tabela" in src:
    print("Ja aplicado!")
    exit(0)

changes = 0

# ── 1) DASHBOARD — adiciona slider de altura antes do dataframe ───────────────
OLD1 = ('        st.dataframe(\n'
        '            _df_dash.style.apply(_style_canceladas, axis=1),\n'
        '            height=400,\n'
        '            use_container_width=True,\n'
        '            hide_index=True,\n'
        '            column_config=_DASH_COL_CFG,\n'
        '        )')

NEW1 = ('        _altura_dash = st.slider("Altura da tabela (linhas)", '
        'min_value=200, max_value=1200, value=400, step=50, '
        'key="altura_dash")\n'
        '        st.dataframe(\n'
        '            _df_dash.style.apply(_style_canceladas, axis=1),\n'
        '            height=_altura_dash,\n'
        '            use_container_width=True,\n'
        '            hide_index=True,\n'
        '            column_config=_DASH_COL_CFG,\n'
        '        )')

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes += 1
    print("OK: Slider adicionado no Dashboard.")
else:
    print("AVISO: Dataframe do Dashboard nao encontrado.")

# ── 2) RELATORIOS OFs — adiciona slider antes do dataframe de OFs ─────────────
OLD2 = ('            sel_of = st.dataframe(\n'
        '                _df_of_formatado(_linhas_of),\n'
        '                height=500,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

NEW2 = ('            _altura_of = st.slider("Altura da tabela (px)", '
        'min_value=200, max_value=1400, value=500, step=50, '
        'key="altura_of")\n'
        '            sel_of = st.dataframe(\n'
        '                _df_of_formatado(_linhas_of),\n'
        '                height=_altura_of,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    changes += 1
    print("OK: Slider adicionado nas OFs dos Relatorios.")
else:
    print("AVISO: Dataframe de OFs nao encontrado.")

# ── 3) RELATORIOS Corridas — adiciona slider antes do dataframe de corridas ───
OLD3 = ('            sel_corr = st.dataframe(\n'
        '                _df_corridas,\n'
        '                height=400,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

NEW3 = ('            _altura_corr = st.slider("Altura da tabela (px)", '
        'min_value=200, max_value=1400, value=400, step=50, '
        'key="altura_corr")\n'
        '            sel_corr = st.dataframe(\n'
        '                _df_corridas,\n'
        '                height=_altura_corr,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes += 1
    print("OK: Slider adicionado nas Corridas dos Relatorios.")
else:
    print("AVISO: Dataframe de Corridas nao encontrado.")

APP.write_text(src, encoding="utf-8")

# Verifica sintaxe
import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print(f"\nSINTAXE OK! {changes} alteracoes feitas.")
    print("Rode: git add . && git commit -m 'Slider altura tabelas' && git push")
except py_compile.PyCompileError as e:
    print(f"\nERRO: {e}")
finally:
    os.unlink(tmp)
