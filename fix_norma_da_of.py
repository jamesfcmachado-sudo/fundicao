from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    # Dados
    num_cert = cert_data.get("numero_cert", "")
    cliente  = cert_data.get("cliente", "")
    norma    = cert_data.get("norma", "")
    liga     = cert_data.get("liga", "")
    projeto  = cert_data.get("projeto", "")
    data_em  = cert_data.get("data_emissao", "")
    nf       = cert_data.get("nota_fiscal", "")
    obs      = cert_data.get("observacoes", "")
    outros   = cert_data.get("outros_ensaios", "")
    tipo     = str(cert_data.get("tipo_template", "sem_ensaio"))'''

NEW = '''    # Dados
    num_cert = cert_data.get("numero_cert", "")
    cliente  = cert_data.get("cliente", "")
    norma    = cert_data.get("norma", "")
    liga     = cert_data.get("liga", "")
    projeto  = cert_data.get("projeto", "")
    data_em  = cert_data.get("data_emissao", "")
    nf       = cert_data.get("nota_fiscal", "")
    obs      = cert_data.get("observacoes", "")
    outros   = cert_data.get("outros_ensaios", "")
    tipo     = str(cert_data.get("tipo_template", "sem_ensaio"))

    # Busca norma e liga da OF se nao estiver preenchida no certificado
    if not norma and corridas:
        try:
            from fundicao_db import engine as _eng
            from sqlalchemy import text as _text
            # Pega a primeira OF das corridas
            _cm0 = corridas[0]._mapping if hasattr(corridas[0], "_mapping") else {}
            _nof0 = _cm0.get("numero_of", "")
            if _nof0:
                with _eng.connect() as _conn_of:
                    _of_row = _conn_of.execute(_text("""
                        SELECT norma, liga FROM ordem_fabricacao
                        WHERE numero_of = :nof LIMIT 1
                    """), {"nof": _nof0}).fetchone()
                    if _of_row:
                        norma = str(_of_row[0] or "")
                        liga  = str(_of_row[1] or liga or "")
        except Exception:
            pass'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Norma buscada da OF.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Norma da OF no PDF cert' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
