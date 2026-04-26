from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    m1.metric("Certificados encontrados", len(df))
    m2.metric("Tipos", df["Tipo"].value_counts().to_dict())

    st.caption("💡 **Clique em uma linha** para ver detalhes e gerar o certificado.")
    df_exib = df.drop(columns=["id"])
    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df_exib["Tipo"] = df_exib["Tipo"].apply(_norm_tipo)'''

NEW = '''    # Normaliza tipo antes de qualquer operacao
    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df["Tipo"] = df["Tipo"].apply(_norm_tipo)

    m1.metric("Certificados encontrados", len(df))
    m2.metric("Com Ensaio", int((df["Tipo"] == "Com Ensaio").sum()))

    st.caption("💡 **Clique em uma linha** para ver detalhes e gerar o certificado.")
    df_exib = df.drop(columns=["id"])'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Tipo normalizado antes do metric.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix tipo antes metric' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
