from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix na consulta - trata tipo_template como string
OLD = '''    df_exib["Tipo"] = df_exib["Tipo"].map({
        "sem_ensaio": "Sem Ensaio",
        "com_ensaio": "Com Ensaio"
    })'''

NEW = '''    # Normaliza tipo_template que pode ser string ou dict
    def _norm_tipo(v):
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        return {"sem_ensaio": "Sem Ensaio", "com_ensaio": "Com Ensaio"}.get(str(v), str(v))
    df_exib["Tipo"] = df_exib["Tipo"].apply(_norm_tipo)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Tipo normalizado na consulta.")
else:
    print("AVISO: Bloco nao encontrado.")

# Fix no salvar - garante que tipo seja string
OLD_SAVE = '''                    "tipo": tipo, "now": now'''
NEW_SAVE = '''                    "tipo": str(tipo) if not isinstance(tipo, dict) else ("com_ensaio" if tipo.get("com_ensaio") else "sem_ensaio"), "now": now'''

if OLD_SAVE in src:
    src = src.replace(OLD_SAVE, NEW_SAVE, 1)
    print("OK: Tipo corrigido no salvar.")
else:
    print("AVISO: Bloco salvar nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix tipo_template consulta cert' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
