from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD_CAB = '''    # ── CABECALHO ─────────────────────────────────────────────────────────────
    # Logo | Titulo centralizado | INSPECTION CERTIFICATE
    cab = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", sz=10),
         Spacer(1, 1*mm),
         ph(f"Nº {num_cert}", sz=14)],
        [ph("INSPECTION", sz=9),
         ph("CERTIFICATE", sz=9),
         Spacer(1, 2*mm),
         ph("SFS - EM 10204 - 3.1", sz=8, bold=False)],
    ]], colWidths=[48*mm, W*0.50, W*0.27], rowHeights=[30*mm])
    cab.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",   (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",   (2,0),(2,0),   0.8, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(0,0),   "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cab)'''

NEW_CAB = '''    # ── CABECALHO ─────────────────────────────────────────────────────────────
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

if OLD_CAB in src:
    src = src.replace(OLD_CAB, NEW_CAB, 1)
    print("OK: Cabecalho ajustado.")
else:
    print("AVISO: Cabecalho nao encontrado.")

# Ajusta norma - mais espaco
OLD_NORMA = '''    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True, sz=8),
         pl(""),
         pl("PROJETO / PROJECT", bold=True, sz=8),
         pl(str(projeto or ""), sz=8)],
        [ph(f"{_norma_txt}", sz=13), "", "", ""],
    ], colWidths=[W*0.38, W*0.12, W*0.22, W*0.28])
    norma_tbl.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("SPAN",         (0,1),(3,1)),
        ("ALIGN",        (0,1),(3,1), "CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))'''

NEW_NORMA = '''    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True, sz=8),
         pl(""),
         pl("PROJETO / PROJECT", bold=True, sz=8),
         pl(str(projeto or ""), sz=8)],
        [ph(f"{_norma_txt}", sz=14), "", "", ""],
    ], colWidths=[W*0.38, W*0.12, W*0.22, W*0.28])
    norma_tbl.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("SPAN",         (0,1),(3,1)),
        ("ALIGN",        (0,1),(3,1), "CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("TOPPADDING",   (0,1),(3,1), 4),
    ]))'''

if OLD_NORMA in src:
    src = src.replace(OLD_NORMA, NEW_NORMA, 1)
    print("OK: Norma com mais espaco.")
else:
    print("AVISO: Norma nao encontrada.")

# Ajusta linhas vazias da composicao - altura maior
OLD_COMP_ROWS = '''    while len(comp_rows) < 9:
        comp_rows.append([""] * 10)

    cw_c = [20*mm, 22*mm] + [(W-42*mm)/8]*8
    tit_comp = Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION")]],'''

NEW_COMP_ROWS = '''    while len(comp_rows) < 9:
        comp_rows.append([""] * 10)

    # Altura das linhas: cabecalho maior, dados e vazias iguais
    _n_corr = len(corridas)
    _row_heights = [10*mm]  # cabecalho
    for _ri in range(8):
        if _ri < _n_corr:
            _row_heights.append(7*mm)  # linha com dados
        else:
            _row_heights.append(6*mm)  # linha vazia

    cw_c = [20*mm, 22*mm] + [(W-42*mm)/8]*8
    tit_comp = Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION")]],'''

if OLD_COMP_ROWS in src:
    src = src.replace(OLD_COMP_ROWS, NEW_COMP_ROWS, 1)
    print("OK: Alturas das linhas da composicao ajustadas.")
else:
    print("AVISO: Linhas composicao nao encontradas.")

# Aplica rowHeights na tabela de composicao
OLD_COMP_TBL = '''    comp_tbl = Table(comp_rows, colWidths=cw_c)'''
NEW_COMP_TBL = '''    comp_tbl = Table(comp_rows, colWidths=cw_c, rowHeights=_row_heights)'''

if OLD_COMP_TBL in src:
    src = src.replace(OLD_COMP_TBL, NEW_COMP_TBL, 1)
    print("OK: rowHeights aplicado na composicao.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Ajuste layout PDF cert' && git push")
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
