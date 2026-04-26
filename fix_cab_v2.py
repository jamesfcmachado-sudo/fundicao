from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    _W_LOGO = 70*mm
    _W_MEIO = W - _W_LOGO - 45*mm
    _W_INSP = 45*mm

    # Linha 1: Logo | titulo | INSPECTION
    cab_linha1 = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", sz=10),
         ph(f"Nº {num_cert}", sz=14)],
        [ph("INSPECTION", sz=10),
         ph("CERTIFICATE", sz=10),
         Spacer(1, 1*mm),
         ph("SFS - EM 10204 - 3.1", sz=8, bold=False)],
    ]], colWidths=[_W_LOGO, _W_MEIO, _W_INSP], rowHeights=[30*mm])
    cab_linha1.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",   (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",   (2,0),(2,0),   0.8, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(0,0),   "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cab_linha1)'''

NEW = '''    _W_LOGO = 55*mm
    _W_MEIO = W - _W_LOGO - 40*mm
    _W_INSP = 40*mm

    # Cabecalho identico ao template
    cab_linha1 = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", sz=9),
         ph(f"Nº {num_cert}", sz=14)],
        [ph("INSPECTION", sz=10),
         ph("CERTIFICATE", sz=10),
         Spacer(1, 1*mm),
         ph("SFS - EM 10204 - 3.1", sz=7, bold=False)],
    ]], colWidths=[_W_LOGO, _W_MEIO, _W_INSP], rowHeights=[28*mm])
    cab_linha1.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",   (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",   (2,0),(2,0),   0.8, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(0,0),   "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cab_linha1)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Cabecalho corrigido.")
else:
    print("AVISO: Bloco nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix cabecalho PDF cert v2' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
