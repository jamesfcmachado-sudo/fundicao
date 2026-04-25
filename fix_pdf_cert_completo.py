from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# Localiza inicio e fim da funcao
idx_inicio = src.find("def gerar_certificado_pdf(")
idx_fim = src.find("\ndef ", idx_inicio + 100)
if idx_fim == -1:
    idx_fim = len(src)

print(f"Funcao de {idx_inicio} ate {idx_fim}")

NOVA_FUNCAO = '''def gerar_certificado_pdf(cert_data, corridas, itens, ensaios=None):
    """Gera PDF do certificado fiel ao template."""
    import io as _io_pdf
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = _io_pdf.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=8*mm, bottomMargin=8*mm)

    W = A4[0] - 20*mm
    styles = getSampleStyleSheet()
    BK = colors.black
    CINZA = colors.HexColor("#D9D9D9")

    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    def ph(t, sz=8, bold=True):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(str(t or ""), PS("h", fontSize=sz,
            fontName=fn, alignment=TA_CENTER, leading=sz+2))
    def pc(t, sz=8):
        return Paragraph(str(t or ""), PS("c", fontSize=sz,
            fontName="Helvetica", alignment=TA_CENTER, leading=sz+2))
    def pl(t, sz=8, bold=False):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(str(t or ""), PS("l", fontSize=sz,
            fontName=fn, alignment=TA_LEFT, leading=sz+2))

    story = []

    # Dados do certificado
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

    # Formata data
    try:
        from datetime import datetime as _dtt
        if hasattr(data_em, "strftime"):
            data_fmt = data_em.strftime("%d/%m/%Y")
        else:
            data_fmt = _dtt.strptime(str(data_em), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        data_fmt = str(data_em or "")

    # Logo
    _logo_cell = pl("")
    try:
        from empresa_config import get_config as _gc
        import base64 as _b64l
        _lb = (_gc("logo_certificado_base64","") or
               _gc("logo1_base64","") or _gc("logo2_base64",""))
        if _lb:
            _logo_cell = RLImage(_io_pdf.BytesIO(_b64l.b64decode(_lb)),
                                 width=38*mm, height=20*mm)
    except Exception:
        pass

    # ── CABECALHO ────────────────────────────────────────────────────────────
    cab = Table([[
        _logo_cell,
        [ph("Certificado de Qualidade / Quality Certificate", sz=10),
         ph(f"Nº {num_cert}", sz=13)],
        [ph("INSPECTION\\nCERTIFICATE", sz=9),
         ph("SFS - EM 10204 - 3.1", sz=8, bold=False)],
    ]], colWidths=[42*mm, W*0.52, W*0.28], rowHeights=[26*mm])
    cab.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",  (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",  (2,0),(2,0),   0.8, BK),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",       (0,0),(0,0),   "CENTER"),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cab)

    # ── CLIENTE ───────────────────────────────────────────────────────────────
    cli_tbl = Table([
        [pl("CLIENTE / CUSTOMER:", bold=True),
         pl(cliente.upper(), bold=True, sz=9)],
    ], colWidths=[45*mm, W-45*mm])
    cli_tbl.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cli_tbl)

    # ── NORMA / LIGA ──────────────────────────────────────────────────────────
    _norma_txt = norma if norma else liga
    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True), pl(""),
         pl("PROJETO / PROJECT", bold=True), pl(projeto)],
        [ph(f"{_norma_txt}", sz=13), "", "", ""],
    ], colWidths=[W*0.35, W*0.15, W*0.2, W*0.3])
    norma_tbl.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("SPAN",        (0,1),(3,1)),
        ("ALIGN",       (0,1),(3,1), "CENTER"),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(norma_tbl)
    story.append(Spacer(1, 2*mm))

    # ── COMPOSIÇÃO QUÍMICA ────────────────────────────────────────────────────
    ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_hdr = [ph("OF"), ph("CORRIDA\\nHEAT Nº")] + [ph(e) for e in ELEM]
    comp_rows = [comp_hdr]

    for corr in corridas:
        _cm = corr._mapping if hasattr(corr, "_mapping") else {}
        _nof   = str(_cm.get("numero_of","") or "")
        _ncorr = str(_cm.get("numero_corrida","") or "")
        row = [pc(_nof), pc(_ncorr)]
        for ek in ["c","si","mn","p","s","cr","ni","mo"]:
            v = float(_cm.get(ek, 0) or 0)
            row.append(pc(f"{v:.4f}".replace(".", ",")))
        comp_rows.append(row)

    # Linhas vazias
    while len(comp_rows) < 9:
        comp_rows.append([""] * 10)

    cw_c = [20*mm, 22*mm] + [(W-42*mm)/8]*8
    comp_tbl = Table(comp_rows, colWidths=cw_c)
    comp_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), CINZA),
        ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 7),
        ("GRID",        (0,0),(-1,-1), 0.4, BK),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))

    # Titulo composicao
    tit_comp = Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION", sz=8)]],
                     colWidths=[W])
    tit_comp.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(tit_comp)
    story.append(comp_tbl)
    story.append(Spacer(1, 2*mm))

    # ── ENSAIOS MECÂNICOS (só com_ensaio) ────────────────────────────────────
    if "com_ensaio" in tipo and ensaios:
        ens_hdr = [ph("LIM. RES.\\n(MPa)"), ph("LIM. ESC.\\n(MPa)"),
                   ph("ALONG.\\n(%)"), ph("RED. ÁREA\\n(%)"),
                   ph("J1"), ph("J2"), ph("J3"), ph("TEMP.")]
        ens_rows = [ens_hdr]
        for en in ensaios:
            em = en._mapping if hasattr(en,"_mapping") else {}
            ens_rows.append([
                pc(f"{float(em.get('lim_resistencia',0) or 0):.1f}"),
                pc(f"{float(em.get('lim_escoamento',0) or 0):.1f}"),
                pc(f"{float(em.get('alongamento',0) or 0):.1f}"),
                pc(f"{float(em.get('red_area',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j1',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j2',0) or 0):.1f}"),
                pc(f"{float(em.get('impacto_j3',0) or 0):.1f}"),
                pc(f"{float(em.get('temperatura',0) or 0):.1f}"),
            ])

        ens_tbl = Table(ens_rows, colWidths=[W/8]*8)
        ens_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0), CINZA),
            ("GRID",       (0,0),(-1,-1), 0.4, BK),
            ("FONTSIZE",   (0,0),(-1,-1), 7),
            ("ALIGN",      (0,0),(-1,-1), "CENTER"),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0),(-1,-1), 2),
            ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ]))
        tit_ens = Table([[ph("II - PROPRIEDADES MECÂNICAS / MECHANICAL PROPERTIES")]],
                        colWidths=[W])
        tit_ens.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), CINZA),
            ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ]))
        story.append(tit_ens)
        story.append(ens_tbl)
        story.append(Spacer(1, 2*mm))

    # ── ITENS ────────────────────────────────────────────────────────────────
    it_hdr = [ph("Pedido/Item\\nP.O."), ph("Modelo\\nPattern"),
              ph("Descrição\\nDescription"), ph("Séries\\nSeries"),
              ph("Quantidade\\nQuantity")]
    it_rows = [it_hdr]
    for it in itens:
        im = it._mapping if hasattr(it,"_mapping") else it
        it_rows.append([
            pc(im.get("pedido","")), pc(im.get("modelo","")),
            pl(im.get("descricao","")),
            pc(im.get("series","")),
            pc(str(im.get("quantidade",""))),
        ])
    while len(it_rows) < 9:
        it_rows.append(["","","","",""])

    it_tbl = Table(it_rows, colWidths=[W*0.20, W*0.14, W*0.37, W*0.15, W*0.14])
    it_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), CINZA),
        ("GRID",        (0,0),(-1,-1), 0.4, BK),
        ("FONTSIZE",    (0,0),(-1,-1), 7),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",       (0,0),(1,-1), "CENTER"),
        ("ALIGN",       (2,0),(2,-1), "LEFT"),
        ("ALIGN",       (3,0),(-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING", (2,0),(2,-1), 3),
    ]))
    tit_it = Table([[ph("II - OUTROS DADOS / OTHER INFORMATIONS")]],
                   colWidths=[W])
    tit_it.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
    ]))
    story.append(tit_it)
    story.append(it_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OBSERVAÇÕES ───────────────────────────────────────────────────────────
    obs_rows = [[ph("III - OBSERVAÇÕES / COMMENTS")]]
    for _ in range(6):
        obs_rows.append([pl("")])
    obs_tbl = Table(obs_rows, colWidths=[W])
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(0,0), CINZA),
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LINEBELOW",   (0,0),(0,0), 0.5, BK),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    if obs:
        obs_rows[1] = [pl(f"  {obs}")]
    story.append(obs_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OUTROS ENSAIOS ────────────────────────────────────────────────────────
    out_tbl = Table([
        [ph("VI - OUTROS ENSAIOS / OTHER TESTS"), ph("ANEXO\\nATTACHED")],
        [pl(outros or ""), pl("")],
        [pl(""), pl("")],
    ], colWidths=[W*0.85, W*0.15])
    out_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), CINZA),
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LINEBEFORE",  (1,0),(1,-1), 0.5, BK),
        ("LINEBELOW",   (0,0),(-1,0), 0.5, BK),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
    ]))
    story.append(out_tbl)
    story.append(Spacer(1, 2*mm))

    # ── RODAPÉ ────────────────────────────────────────────────────────────────
    rod_tbl = Table([
        [pl(f"Nota Fiscal Nº : {nf or ''}"), pl("")],
        [pl("BILL :"),                        pl("")],
        [pl(f"Data / Date : {data_fmt}"),     ph("CONTROLE DE QUALIDADE")],
    ], colWidths=[W*0.5, W*0.5])
    rod_tbl.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LINEABOVE",   (0,2),(-1,2), 0.5, BK),
        ("LINEBEFORE",  (1,0),(1,-1), 0.5, BK),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(rod_tbl)

    doc.build(story)
    buf.seek(0)
    return buf.read()

'''

# Substitui a funcao completa
src = src[:idx_inicio] + NOVA_FUNCAO + src[idx_fim:]
CERT.write_text(src, encoding="utf-8")
print("OK: Funcao gerar_certificado_pdf reescrita.")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'PDF certificado fiel ao template' && git push")
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
