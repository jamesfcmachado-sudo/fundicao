from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''                # Insere corridas
                for c in corridas:
                    if c["num_corrida"]:
                        comp = c["comp"]
                        # Salva composicao como JSON
                        conn.execute(text("""
                            INSERT INTO certificado_corrida (
                                certificado_id, numero_of, numero_corrida,
                                composicao_json
                            ) VALUES (
                                :cid, :nof, :nc, :comp
                            )
                        """), {
                            "cid":  cert_id,
                            "nof":  c["num_of"],
                            "nc":   c["num_corrida"],
                            "comp": json.dumps(comp),
                        })'''

NEW = '''                # Insere corridas — colunas em minusculas no PostgreSQL
                for c in corridas:
                    if c["num_corrida"]:
                        comp = c["comp"]
                        conn.execute(text("""
                            INSERT INTO certificado_corrida (
                                certificado_id, numero_of, numero_corrida,
                                c, si, mn, p, s, cr, ni, mo,
                                cu, w, nb, v, fe, ce
                            ) VALUES (
                                :cid, :nof, :nc,
                                :c, :si, :mn, :p, :s, :cr, :ni, :mo,
                                :cu, :w, :nb, :v, :fe, :ce
                            )
                        """), {
                            "cid": cert_id,
                            "nof": c["num_of"],
                            "nc":  c["num_corrida"],
                            "c":   float(comp.get("C", 0) or 0),
                            "si":  float(comp.get("Si", 0) or 0),
                            "mn":  float(comp.get("Mn", 0) or 0),
                            "p":   float(comp.get("P", 0) or 0),
                            "s":   float(comp.get("S", 0) or 0),
                            "cr":  float(comp.get("Cr", 0) or 0),
                            "ni":  float(comp.get("Ni", 0) or 0),
                            "mo":  float(comp.get("Mo", 0) or 0),
                            "cu":  float(comp.get("Cu", 0) or 0),
                            "w":   float(comp.get("W", 0) or 0),
                            "nb":  float(comp.get("Nb", 0) or 0),
                            "v":   float(comp.get("V", 0) or 0),
                            "fe":  float(comp.get("Fe", 0) or 0),
                            "ce":  float(comp.get("CE", 0) or 0),
                        })'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: INSERT corrida com colunas minusculas.")
else:
    # Tenta o original
    OLD2 = '''                # Insere corridas
                for c in corridas:
                    if c["num_corrida"]:
                        comp = c["comp"]
                        conn.execute(text("""
                            INSERT INTO certificado_corrida (
                                certificado_id, numero_of, numero_corrida,
                                "C","Si","Mn","P","S","Cr","Ni","Mo","Cu","W","Nb","V","Fe","CE"
                            ) VALUES (
                                :cid, :nof, :nc,
                                :C,:Si,:Mn,:P,:S,:Cr,:Ni,:Mo,:Cu,:W,:Nb,:V,:Fe,:CE
                            )
                        """), {
                            "cid": cert_id, "nof": c["num_of"], "nc": c["num_corrida"],
                            "C": comp.get("C",0), "Si": comp.get("Si",0),
                            "Mn": comp.get("Mn",0), "P": comp.get("P",0),
                            "S": comp.get("S",0), "Cr": comp.get("Cr",0),
                            "Ni": comp.get("Ni",0), "Mo": comp.get("Mo",0),
                            "Cu": comp.get("Cu",0), "W": comp.get("W",0),
                            "Nb": comp.get("Nb",0), "V": comp.get("V",0),
                            "Fe": comp.get("Fe",0), "CE": comp.get("CE",0),
                        })'''
    if OLD2 in src:
        src = src.replace(OLD2, NEW, 1)
        print("OK: INSERT corrida original corrigido.")
    else:
        print("AVISO: Bloco nao encontrado.")
        # Mostra o que tem
        idx = src.find("Insere corridas")
        print(repr(src[idx:idx+500]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix INSERT corrida minusculas' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
