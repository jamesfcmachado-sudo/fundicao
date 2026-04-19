from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''            _edit_of = st.selectbox(
                "Ordem de Fabricação (OF)",
                options=_ofs_lista,
                index=_of_idx,
                key="edit_of_cons"
            )'''

NEW = '''            _edit_of = st.selectbox(
                "Ordem de Fabricação (OF)",
                options=_ofs_lista,
                index=_of_idx,
                key="edit_of_cons",
                placeholder="Digite ou selecione a OF...",
            )
            st.caption(f"OF atual: **{_of_atual}** | Digite para filtrar a lista acima.")'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Dica de digitacao adicionada.")
else:
    print("AVISO: selectbox nao encontrado.")

# Melhor solucao: usar text_input com sugestoes
OLD2 = '''            _edit_of = st.selectbox(
                "Ordem de Fabricação (OF)",
                options=_ofs_lista,
                index=_of_idx,
                key="edit_of_cons",
                placeholder="Digite ou selecione a OF...",
            )
            st.caption(f"OF atual: **{_of_atual}** | Digite para filtrar a lista acima.")'''

NEW2 = '''            # Campo de texto com sugestoes para buscar OF
            _edit_of_texto = st.text_input(
                "Ordem de Fabricação (OF) — Digite o número",
                value=_of_atual,
                key="edit_of_texto",
                placeholder="Ex: 015B6"
            )
            # Filtra sugestoes com base no que foi digitado
            if _edit_of_texto:
                _sugestoes = [o for o in _ofs_lista
                              if _edit_of_texto.upper() in o.upper()][:10]
                if _sugestoes and _edit_of_texto not in _ofs_lista:
                    st.caption(f"Sugestões: {', '.join(_sugestoes)}")
            _edit_of = _edit_of_texto.strip() if _edit_of_texto.strip() in _ofs_lista else _of_atual
            if _edit_of_texto.strip() and _edit_of_texto.strip() not in _ofs_lista:
                st.warning(f"OF '{_edit_of_texto}' não encontrada. Usando OF atual: {_of_atual}")'''

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK: text_input com sugestoes adicionado.")
else:
    print("AVISO: Bloco v2 nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'OF digitavel no alterar OE' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
