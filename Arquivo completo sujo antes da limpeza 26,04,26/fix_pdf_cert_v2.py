from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Fix 1: Corrige cabecalho - adiciona logo e melhora layout
OLD_CAB = '''    # ── Cabecalho ─────────────────────────────────────────────────────────────
    num_cert = cert_data.get("numero_cert","")
    cliente  = cert_data.get("cliente","")
    norma    = cert_data.get("norma","")
    liga     = cert_data.get("liga","")
    data_em  = cert_data.get("data_emissao","")
    nf       = cert_data.get("nota_fiscal","")
    obs      = cert_data.get("observacoes","")
    outros   = cert_data.get("outros_ensaios","")
    tipo     = cert_data.get("tipo_template","sem_ensaio")

    # Logo e titulo
    cab = Table([[
        pl(""),  # Logo placeholder
        [ph("Certificado de Qualidade / Quality Certificate", fontSize=11),
         ph(f"Nº {num_cert}", fontSize=14)],
        [ph("INSPECTION\nCERTIFICATE", fontSize=9),
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

NEW_CAB = '''    # ── Cabecalho ─────────────────────────────────────────────────────────────
    num_cert = cert_data.get("numero_cert","")
    cliente  = cert_data.get("cliente","")
    norma    = cert_data.get("norma","")
    liga     = cert_data.get("liga","")
    data_em  = cert_data.get("data_emissao","")
    nf       = cert_data.get("nota_fiscal","")
    obs      = cert_data.get("observacoes","")
    outros   = cert_data.get("outros_ensaios","")
    tipo     = cert_data.get("tipo_template","sem_ensaio")

    # Formata data
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

    # Busca logo
    _logo_cell = pl("")
    try:
        from empresa_config import get_config as _gc
        _logo_b64 = _gc("logo_certificado_base64","") or _gc("logo_ativo_base64","")
        if not _logo_b64:
            # Tenta logo 1
            _logo_b64 = _gc("logo1_base64","")
        if _logo_b64:
            import base64 as _b64logo, io as _io_logo
            _logo_bytes = _b64logo.b64decode(_logo_b64)
            _logo_cell = RLImage(_io_logo.BytesIO(_logo_bytes), width=38*mm, height=20*mm)
    except Exception:
        pass

    # Cabecalho
    cab = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", fontSize=10),
         ph(f"Nº {num_cert}", fontSize=13)],
        [ph("INSPECTION\nCERTIFICATE", fontSize=9),
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
    print("OK: Cabecalho com logo e data formatada.")
else:
    print("AVISO: Cabecalho nao encontrado.")

# Fix 2: Corrige rodape - adiciona BILL e data formatada
OLD_RODAPE = '''    rodape = Table([[
        pl(f"Nota Fiscal Nº : {nf}"),
        pl(""),
    ],[
        pl(f"Data / Date : {data_em}"),
        ph("CONTROLE DE QUALIDADE"),
    ]], colWidths=[W*0.5, W*0.5])'''

NEW_RODAPE = '''    rodape = Table([[
        pl(f"Nota Fiscal Nº : {nf}"),
        pl(""),
    ],[
        pl("BILL :"),
        pl(""),
    ],[
        pl(f"Data / Date : {data_em_fmt}"),
        ph("CONTROLE DE QUALIDADE"),
    ]], colWidths=[W*0.5, W*0.5])'''

if OLD_RODAPE in src:
    src = src.replace(OLD_RODAPE, NEW_RODAPE, 1)
    print("OK: Rodape com BILL e data formatada.")
else:
    print("AVISO: Rodape nao encontrado.")

# Fix 3: Corrige composicao quimica - remove coluna C duplicada e adiciona OF
OLD_COMP_HDR = '''    ELEM_COLS = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_header = [ph("OF"), ph("CORRIDA\nHEAT Nº")] + [ph(e) for e in ELEM_COLS]
    comp_rows = [comp_header]
    for corr in corridas:
        row = [pc(corr[1] if hasattr(corr,'__getitem__') else corr._mapping.get("numero_of","")),
               pc(corr[2] if hasattr(corr,'__getitem__') else corr._mapping.get("numero_corrida",""))]
        for j, el in enumerate(ELEM_COLS):
            val = corr[j+2] if hasattr(corr,'__getitem__') else 0
            row.append(pc(f"{float(val or 0):.3f}".replace(".",",")))
        comp_rows.append(row)

    cw_comp = [20*mm, 20*mm] + [W/10]*8
    comp_tbl = Table(comp_rows, colWidths=cw_comp)'''

NEW_COMP_HDR = '''    ELEM_COLS = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_header = [ph("OF"), ph("CORRIDA\nHEAT Nº")] + [ph(e) for e in ELEM_COLS]
    comp_rows = [comp_header]
    for corr in corridas:
        _cm = corr._mapping if hasattr(corr,'_mapping') else {}
        _nof  = _cm.get("numero_of","") or (corr[0] if hasattr(corr,'__getitem__') else "")
        _ncorr = _cm.get("numero_corrida","") or (corr[1] if hasattr(corr,'__getitem__') else "")
        row = [pc(_nof), pc(_ncorr)]
        _elem_keys = ["c","si","mn","p","s","cr","ni","mo"]
        for ek in _elem_keys:
            val = _cm.get(ek, 0) or 0
            row.append(pc(f"{float(val):.4f}".replace(".",",")))
        comp_rows.append(row)

    # Linhas vazias ate 8
    while len(comp_rows) < 9:
        comp_rows.append(["","","","","","","","","",""])

    cw_comp = [20*mm, 20*mm] + [(W-40*mm)/8]*8
    comp_tbl = Table(comp_rows, colWidths=cw_comp)'''

if OLD_COMP_HDR in src:
    src = src.replace(OLD_COMP_HDR, NEW_COMP_HDR, 1)
    print("OK: Composicao quimica corrigida.")
else:
    print("AVISO: Composicao quimica nao encontrada.")

# Fix 4: Norma com liga destacada
OLD_NORMA = '''    norma_tbl = Table([[
        pb("NORMA DA LIGA/ ALLOY STANDARD"), pl(""),
        pb("PROJETO / PROJECT"), pl(cert_data.get("projeto",""))
    ],[
        ph(f"{norma}", fontSize=12), "", "", ""
    ]], colWidths=[W*0.3, W*0.2, W*0.2, W*0.3])'''

NEW_NORMA = '''    _norma_texto = norma if norma else f"{liga}" if liga else ""
    norma_tbl = Table([[
        pb("NORMA DA LIGA/ ALLOY STANDARD"), pl(""),
        pb("PROJETO / PROJECT"), pl(cert_data.get("projeto",""))
    ],[
        ph(f"{_norma_texto}", fontSize=12), "", "", ""
    ]], colWidths=[W*0.3, W*0.2, W*0.2, W*0.3])'''

if OLD_NORMA in src:
    src = src.replace(OLD_NORMA, NEW_NORMA, 1)
    print("OK: Norma com liga.")
else:
    print("AVISO: Norma nao encontrada.")

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Melhora PDF certificado' && git push")
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
