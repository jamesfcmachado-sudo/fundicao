from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    df = pd.DataFrame(rows, columns=["Nº Cert","Cliente","Norma","Liga",
                                      "Data","Tipo","id","Corridas"])

    # Aplica filtros
    if f_num.strip():
        df = df[df["Nº Cert"].str.contains(f_num.strip(), case=False, na=False)]
    if f_cli.strip():
        df = df[df["Cliente"].str.contains(f_cli.strip(), case=False, na=False)]
    if f_corrida.strip():
        df = df[df["Corridas"].str.contains(f_corrida.strip(), case=False, na=False)]

    m1, m2 = st.columns(2)
    # Normaliza tipo antes de qualquer operacao
    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df["Tipo"] = df["Tipo"].apply(_norm_tipo)

    m1.metric("Certificados encontrados", len(df))
    m2.metric("Com Ensaio", int((df["Tipo"] == "Com Ensaio").sum()))'''

NEW = '''    df = pd.DataFrame(rows, columns=["Nº Cert","Cliente","Norma","Liga",
                                      "Data","Tipo","id","Corridas"])

    # Normaliza tipo IMEDIATAMENTE apos criar o DataFrame
    def _norm_tipo(v):
        if v is None: return "Sem Ensaio"
        if isinstance(v, dict):
            return "Com Ensaio" if v.get("com_ensaio") else "Sem Ensaio"
        s = str(v)
        if "com_ensaio" in s: return "Com Ensaio"
        return "Sem Ensaio"
    df["Tipo"] = df["Tipo"].apply(_norm_tipo)

    # Aplica filtros
    if f_num.strip():
        df = df[df["Nº Cert"].str.contains(f_num.strip(), case=False, na=False)]
    if f_cli.strip():
        df = df[df["Cliente"].str.contains(f_cli.strip(), case=False, na=False)]
    if f_corrida.strip():
        df = df[df["Corridas"].fillna("").str.contains(f_corrida.strip(), case=False, na=False)]

    m1, m2 = st.columns(2)
    m1.metric("Certificados encontrados", len(df))
    m2.metric("Com Ensaio", int((df["Tipo"] == "Com Ensaio").sum()))'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Normalizacao movida para imediatamente apos criar DataFrame.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix normalizacao tipo imediata' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
