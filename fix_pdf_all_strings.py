from pathlib import Path
import re

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Encontra a funcao gerar_certificado_pdf
idx_inicio = src.find("def gerar_certificado_pdf(")
idx_fim = src.find("\ndef ", idx_inicio + 100)

# Extrai a funcao
funcao = src[idx_inicio:idx_fim]

# Corrige todas as strings com quebra de linha literal dentro de ph(), pc(), pl()
# Padrao: ph("texto\n(continua na proxima linha)")
def fix_multiline_strings(text):
    # Corrige quebras de linha dentro de strings em chamadas de funcao
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Verifica se a linha tem uma string nao fechada
        # Conta aspas duplas nao escapadas
        quote_count = line.count('"') - line.count('\\"')
        if quote_count % 2 != 0:
            # String nao fechada - junta com proxima linha
            while i + 1 < len(lines) and quote_count % 2 != 0:
                i += 1
                next_line = lines[i].strip()
                line = line.rstrip() + '\\n' + next_line
                quote_count = line.count('"') - line.count('\\"')
        result.append(line)
        i += 1
    return '\n'.join(result)

funcao_corrigida = fix_multiline_strings(funcao)
src_novo = src[:idx_inicio] + funcao_corrigida + src[idx_fim:]
CERT.write_text(src_novo, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src_novo)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'PDF cert layout final' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src_novo.split('\n')
        for x in range(max(0,ln-3), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
