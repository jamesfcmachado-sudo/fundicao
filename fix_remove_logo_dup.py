from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Remove o bloco da aba Templates (posicao ~18697)
# Localiza o inicio do bloco
idx_bloco = src.find('\n            st.divider()\n\n            # Logo especifico do certificado')
if idx_bloco == -1:
    idx_bloco = src.find('\n            # Logo especifico do certificado')

print(f"Bloco duplicado na posicao: {idx_bloco}")

if idx_bloco > 0:
    # Encontra o fim do bloco (proximo divider ou upload de template)
    idx_fim = src.find('\n            # Upload novo template', idx_bloco)
    if idx_fim == -1:
        idx_fim = src.find('\n\n        # ── TEMPLATES PERSONALIZADOS', idx_bloco)
    
    print(f"Fim do bloco: {idx_fim}")
    print(repr(src[idx_bloco:idx_bloco+100]))
    
    if idx_fim > 0:
        src = src[:idx_bloco] + src[idx_fim:]
        print("OK: Bloco duplicado removido da aba Templates.")
    else:
        print("AVISO: Fim do bloco nao encontrado.")
else:
    print("AVISO: Bloco nao encontrado.")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove logo cert duplicado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
