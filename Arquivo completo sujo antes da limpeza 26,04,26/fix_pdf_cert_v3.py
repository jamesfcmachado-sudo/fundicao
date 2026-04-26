from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix 1: Cabecalho com logo
OLD_CAB = '''    # Logo e titulo
    cab = Table([[
        pl(""),  # Logo placeholder
        [ph("Certificado de Qualidade / Quality Certificate", fontSize=11),
         ph(f"Nº {num_cert}", fontSize=14)],
        [ph("INSPECTION\\nCERTIFICATE", fontSize=9),
         ph("SFS - EM 10204 - 3.1", fontSize=8)],
    ]], colWidths=[40*mm, W*0.55, W*0.3])
    cab.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",  (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",  (2,0),(2,0),   0.8, BK),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(cab)'''

NEW_CAB = '''    # Formata data
    if data_em:
        try:
            from datetime import datetime as _dt
            if hasattr(data_em, 'strftime'):
                data_em_fmt = data_em.strftime("%d/%m/%Y")
            else:
                _d = _dt.strptime(str(data_em), "%Y-%m-%d")
                data_em_fmt = _d.strftime("%d/%m/%Y")
        except Exception:
            data_em_fmt = str(data_em)
    else:
        data_em_fmt = ""

    # Busca logo do certificado ou logo ativo
    _logo_cell = pl("")
    try:
        from empresa_config import get_config as _gc
        import base64 as _b64logo, io as _io_logo
        _logo_b64 = (_gc("logo_certificado_base64","") or
                     _gc("logo1_base64","") or
                     _gc("logo2_base64",""))
        if _logo_b64:
            _logo_bytes = _b64logo.b64decode(_logo_b64)
            _logo_cell = RLImage(_io_logo.BytesIO(_logo_bytes),
                                 width=38*mm, height=20*mm)
    except Exception:
        pass

    # Logo e titulo
    cab = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", fontSize=10),
         ph(f"Nº {num_cert}", fontSize=13)],
        [ph("INSPECTION\\nCERTIFICATE", fontSize=9),
         ph("SFS - EM 10204 - 3.1", fontSize=8)],
    ]], colWidths=[42*mm, W*0.52, W*0.28], rowHeights=[26*mm])
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
    print("OK: Cabecalho com logo e data.")
else:
    print("AVISO: Cabecalho nao encontrado.")

# Fix 2: Composicao quimica
OLD_COMP = '''    ELEM_COLS = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_header = [ph("OF"), ph("CORRIDA\\nHEAT Nº")] + [ph(e) for e in ELEM_COLS]
    comp_rows = [comp_header]
    for corr in corridas:
        row = [pc(corr[1] if hasattr(corr,\'__getitem__\') else corr._mapping.get("numero_of","")),
               pc(corr[2] if hasattr(corr,\'__getitem__\') else corr._mapping.get("numero_corrida",""))]
        for j, el in enumerate(ELEM_COLS):
            val = corr[j+2] if hasattr(corr,\'__getitem__\') else 0
            row.append(pc(f"{float(val or 0):.3f}".replace(".",",")))
        comp_rows.append(row)

    cw_comp = [20*mm, 20*mm] + [W/10]*8
    comp_tbl = Table(comp_rows, colWidths=cw_comp)'''

NEW_COMP = '''    ELEM_COLS = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_header = [ph("OF"), ph("CORRIDA\\nHEAT Nº")] + [ph(e) for e in ELEM_COLS]
    comp_rows = [comp_header]
    for corr in corridas:
        _cm = corr._mapping if hasattr(corr, "_mapping") else {}
        _nof   = _cm.get("numero_of","") or ""
        _ncorr = _cm.get("numero_corrida","") or ""
        if not _nof and hasattr(corr, "__getitem__"):
            _nof   = str(corr[0] or "")
            _ncorr = str(corr[1] or "")
        row = [pc(_nof), pc(_ncorr)]
        _elem_keys = ["c","si","mn","p","s","cr","ni","mo"]
        for ek in _elem_keys:
            val = _cm.get(ek, 0) or 0
            if val == 0 and hasattr(corr, "__getitem__"):
                idx_ek = _elem_keys.index(ek)
                try: val = float(corr[idx_ek+2] or 0)
                except Exception: val = 0
            row.append(pc(f"{float(val):.4f}".replace(".",",")))
        comp_rows.append(row)

    # Linhas vazias ate completar 8
    while len(comp_rows) < 9:
        comp_rows.append(["","","","","","","","","",""])

    cw_comp = [20*mm, 22*mm] + [(W-42*mm)/8]*8
    comp_tbl = Table(comp_rows, colWidths=cw_comp)'''

if OLD_COMP in src:
    src = src.replace(OLD_COMP, NEW_COMP, 1)
    print("OK: Composicao quimica corrigida.")
else:
    print("AVISO: Composicao quimica nao encontrada.")

# Fix 3: Rodape com data formatada
OLD_RODAPE = '''        pl(f"Data / Date : {data_em}"),'''
NEW_RODAPE = '''        pl(f"Data / Date : {data_em_fmt if 'data_em_fmt' in dir() else data_em}"),'''

if OLD_RODAPE in src:
    src = src.replace(OLD_RODAPE, NEW_RODAPE, 1)
    print("OK: Data formatada no rodape.")
else:
    print("AVISO: Rodape data nao encontrado.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix PDF cert logo data composicao' && git push")
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
