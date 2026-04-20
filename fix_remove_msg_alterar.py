from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Remove a mensagem de dica
OLD1 = '            st.caption("👆 Role para baixo para ver as opções de Alterar e Excluir.")'
if OLD1 in src:
    src = src.replace(OLD1, '', 1)
    print("OK: Mensagem de dica removida.")
else:
    # Tenta variacao
    for kw in ["Role para baixo", "Alterar e Excluir", "alterar e excluir"]:
        idx = src.find(kw)
        if idx > 0:
            # Pega a linha inteira
            inicio = src.rfind('\n', 0, idx) + 1
            fim = src.find('\n', idx) + 1
            linha = src[inicio:fim]
            print(f"Encontrado: {repr(linha)}")
            src = src[:inicio] + src[fim:]
            print("OK: Linha removida.")
            break

# Remove texto da instrucao da tabela que menciona alterar/excluir
OLD2 = '    st.caption("💡 **Clique em uma linha** da tabela abaixo para ver os detalhes, gerar PDF/Excel, alterar ou excluir a OE.")'
NEW2 = '    st.caption("💡 **Clique em uma linha** da tabela abaixo para ver os detalhes e gerar PDF/Excel da OE.")'
if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK: Instrucao da tabela atualizada.")
else:
    print("AVISO: Instrucao nao encontrada.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove ref alterar excluir Consulta OEs' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
