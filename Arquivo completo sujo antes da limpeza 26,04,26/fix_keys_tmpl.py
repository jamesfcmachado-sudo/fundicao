from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Renomeia as keys do formulario de templates personalizados
fixes = [
    ('key="novo_tmpl_nome"', 'key="novo_tmpl_custom_nome"'),
    ('key="novo_tmpl_resp"', 'key="novo_tmpl_custom_resp"'),
    ('key="novo_tmpl_orient"', 'key="novo_tmpl_custom_orient"'),
    ('key="upload_tmpl_custom"', 'key="upload_tmpl_custom_file"'),
    ('key="btn_add_custom"', 'key="btn_add_custom_tmpl"'),
]

for old, new in fixes:
    if old in src:
        src = src.replace(old, new)
        print(f"OK: {old} -> {new}")
    else:
        print(f"AVISO: {old} nao encontrado")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix keys tmpl personalizados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
