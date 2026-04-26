from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

changes = 0

# ── Relatorios OFs ────────────────────────────────────────────────────────────
OLD2 = ('          sel_of = st.dataframe(\n'
        '                df,\n'
        '                height=500,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

NEW2 = ('          _altura_of = st.slider("Altura da tabela (px)", '
        'min_value=200, max_value=1400, value=500, step=50, key="altura_of")\n'
        '          sel_of = st.dataframe(\n'
        '                df,\n'
        '                height=_altura_of,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    changes += 1
    print("OK: Slider adicionado nas OFs.")
else:
    print("AVISO: OFs nao encontrado.")

# ── Relatorios Corridas ───────────────────────────────────────────────────────
OLD3 = ('            sel_corr = st.dataframe(\n'
        '                _df_corridas,\n'
        '                height=400,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

NEW3 = ('            _altura_corr = st.slider("Altura da tabela (px)", '
        'min_value=200, max_value=1400, value=400, step=50, key="altura_corr")\n'
        '            sel_corr = st.dataframe(\n'
        '                _df_corridas,\n'
        '                height=_altura_corr,\n'
        '                use_container_width=True,\n'
        '                hide_index=True,')

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes += 1
    print("OK: Slider adicionado nas Corridas.")
else:
    # Tenta encontrar o texto exato
    idx = src.find('sel_corr = st.dataframe')
    if idx != -1:
        print(f"Texto encontrado em idx {idx}:")
        print(repr(src[idx-5:idx+120]))
    else:
        print("AVISO: sel_corr nao encontrado.")

APP.write_text(src, encoding="utf-8")

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
