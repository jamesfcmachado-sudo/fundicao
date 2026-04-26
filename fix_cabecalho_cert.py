from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD_CAB = '''    # ── CABECALHO ─────────────────────────────────────────────────────────────
    # Linha 1: Logo | Titulo + Numero | INSPECTION CERTIFICATE
    _insp_cell = [
        ph("INSPECTION", sz=9),
        ph("CERTIFICATE", sz=9),
        Spacer(1, 2*mm),
        ph("SFS - EM 10204 - 3.1", sz=8, bold=False),
    ]
    _titulo_cell = [
        ph("Certificado de Qualidade / Quality Certificate", sz=10),
        ph(f"Nº {num_cert}", sz=14),
    ]
    cab = Table([[
        _logo_cell,
        _titulo_cell,
        _insp_cell,
    ]], colWidths=[50*mm, W*0.48, W*0.26], rowHeights=[32*mm])
    cab.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",   (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",   (2,0),(2,0),   0.8, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(0,0),   "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(cab)'''

NEW_CAB = '''    # ── CABECALHO ─────────────────────────────────────────────────────────────
    # Layout identico ao template:
    # Linha superior: Logo grande | vazio | INSPECTION CERTIFICATE
    # Linha inferior: vazio | Certificado de Qualidade / Nº | vazio
    _W_LOGO = 70*mm
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

if OLD_CAB in src:
    src = src.replace(OLD_CAB, NEW_CAB, 1)
    print("OK: Cabecalho ajustado.")
else:
    print("AVISO: Cabecalho nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix cabecalho PDF cert' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
    import re
    m = re.search(r'line (\d+)', str(e))
    if m:
        ln = int(m.group(1))
        ls = src.split('\n')
        for x in range(max(0,ln-3), min(len(ls),ln+3)):
            print(f"  {x+1}: {repr(ls[x])}")
finally:
    os.unlink(tmp)
