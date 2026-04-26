from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                corridas_db = conn.execute(text("""
                    SELECT numero_of, numero_corrida, "C","Si","Mn","P","S","Cr","Ni","Mo"
                    FROM certificado_corrida WHERE certificado_id=:id ORDER BY criado_em
                """), {"id": cert_id}).fetchall()'''

NEW = '''                corridas_db = conn.execute(text("""
                    SELECT numero_of, numero_corrida, c, si, mn, p, s, cr, ni, mo
                    FROM certificado_corrida WHERE certificado_id=:id ORDER BY criado_em
                """), {"id": cert_id}).fetchall()'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Query corridas corrigida.")
else:
    print("AVISO: Bloco nao encontrado.")
    idx = src.find('SELECT numero_of, numero_corrida, "C"')
    if idx > 0:
        print(repr(src[idx:idx+200]))

# Tambem corrige o DataFrame das corridas
OLD_DF = '''                df_comp = pd.DataFrame(corridas_db,
                    columns=["OF","Corrida","C","Si","Mn","P","S","Cr","Ni","Mo"])'''

NEW_DF = '''                df_comp = pd.DataFrame(corridas_db,
                    columns=["OF","Corrida","C","Si","Mn","P","S","Cr","Ni","Mo"])
                # Formata valores numericos
                for _ec in ["C","Si","Mn","P","S","Cr","Ni","Mo"]:
                    df_comp[_ec] = pd.to_numeric(df_comp[_ec], errors="coerce").round(4)'''

if OLD_DF in src:
    src = src.replace(OLD_DF, NEW_DF, 1)
    print("OK: DataFrame corridas com formatacao.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix query corridas minusculas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
