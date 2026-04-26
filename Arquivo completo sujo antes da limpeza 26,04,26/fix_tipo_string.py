from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix no radio - garante que retorna string
OLD = '''    tipo = st.radio(
        "Tipo de certificado:",
        options=["sem_ensaio", "com_ensaio"],
        format_func=lambda x: "Sem Ensaio Mecânico" if x == "sem_ensaio" else "Com Ensaio Mecânico",
        horizontal=True,
        key="tipo_cert"
    )'''

NEW = '''    _tipo_raw = st.radio(
        "Tipo de certificado:",
        options=["sem_ensaio", "com_ensaio"],
        format_func=lambda x: "Sem Ensaio Mecânico" if x == "sem_ensaio" else "Com Ensaio Mecânico",
        horizontal=True,
        key="tipo_cert"
    )
    # Garante que tipo seja sempre string
    tipo = str(_tipo_raw) if not isinstance(_tipo_raw, dict) else (
        "com_ensaio" if _tipo_raw.get("com_ensaio") else "sem_ensaio"
    )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: tipo garantido como string.")
else:
    print("AVISO: Bloco radio nao encontrado.")

# Fix na consulta - trata tipo de forma mais robusta
OLD_MAP = '''    # Normaliza tipo_template que pode ser string ou dict
    def _norm_tipo(v):
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        return {"sem_ensaio": "Sem Ensaio", "com_ensaio": "Com Ensaio"}.get(str(v), str(v))
    df_exib["Tipo"] = df_exib["Tipo"].apply(_norm_tipo)'''

NEW_MAP = '''    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df_exib["Tipo"] = df_exib["Tipo"].apply(_norm_tipo)'''

if OLD_MAP in src:
    src = src.replace(OLD_MAP, NEW_MAP, 1)
    print("OK: Mapa tipo mais robusto.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix tipo_template string' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
