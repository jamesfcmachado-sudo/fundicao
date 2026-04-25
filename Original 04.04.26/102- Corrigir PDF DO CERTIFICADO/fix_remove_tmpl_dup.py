from pathlib import Path

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

# A primeira ocorrencia e nas linhas ~509-535
# A segunda ocorrencia e nas linhas ~625-660
# Vamos remover as linhas 620-665 (segunda ocorrencia)

# Encontra a segunda ocorrencia do bloco
segundo_inicio = None
segundo_fim = None

for i, line in enumerate(lines):
    if i > 550 and '# Formulario para novo template' in line:
        segundo_inicio = i - 5  # inclui algumas linhas antes
        print(f"Segunda ocorrencia encontrada na linha {i+1}")
        print(repr(lines[i]))
        break

if segundo_inicio:
    # Encontra o fim do bloco
    for i in range(segundo_inicio, len(lines)):
        if 'fix_templates_v2' in lines[i] or '# ── ABA' in lines[i]:
            segundo_fim = i
            break
    
    print(f"Removendo linhas {segundo_inicio+1} a {segundo_fim}")
    print("Primeiras linhas a remover:")
    for i in range(segundo_inicio, min(segundo_inicio+5, len(lines))):
        print(f"  {i+1}: {repr(lines[i])}")

    if segundo_fim:
        new_lines = lines[:segundo_inicio] + lines[segundo_fim:]
        src = '\n'.join(new_lines)
        CFG.write_text(src, encoding="utf-8")
        print("OK: Bloco duplicado removido.")

        import py_compile, tempfile, os
        tmp = tempfile.mktemp(suffix='.py')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(src)
        try:
            py_compile.compile(tmp, doraise=True)
            print("SINTAXE OK! Rode: git add . && git commit -m 'Remove templates personalizados duplicado' && git push")
        except py_compile.PyCompileError as e:
            print(f"ERRO: {e}")
        finally:
            os.unlink(tmp)
