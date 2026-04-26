from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

idx_inicio = src.find("def gerar_certificado_pdf(")
idx_fim = src.find("\ndef ", idx_inicio + 100)
if idx_fim == -1:
    idx_fim = len(src)

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
    BK  = colors.black
    CINZA = colors.HexColor("#D9D9D9")

    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    def ph(t, sz=8, bold=True):
        return Paragraph(str(t or ""), PS("h",
            fontSize=sz, fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_CENTER, leading=sz+2))
    def pc(t, sz=8):
        return Paragraph(str(t or ""), PS("c",
            fontSize=sz, fontName="Helvetica",
            alignment=TA_CENTER, leading=sz+2))
    def pl(t, sz=8, bold=False):
        return Paragraph(str(t or ""), PS("l",
            fontSize=sz, fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_LEFT, leading=sz+2))

    def fmt_num(v):
        """Formata numero com casas decimais variaveis como no template."""
        try:
            f = float(v or 0)
            if f == 0: return ""
            # Remove zeros a direita mas mantem pelo menos 2 casas
            s = f"{f:.4f}".rstrip("0")
            if s.endswith("."): s += "0"
            return s.replace(".", ",")
        except Exception:
            return str(v or "")

    story = []

    # Dados
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
                                 width=45*mm, height=24*mm)
    except Exception:
        pass

    # ── CABECALHO ─────────────────────────────────────────────────────────────
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
    story.append(cab)

    # ── CLIENTE ───────────────────────────────────────────────────────────────
    cli_tbl = Table([[
        pl("CLIENTE / CUSTOMER:", bold=True, sz=8),
        pl(cliente.upper(), bold=True, sz=9),
    ]], colWidths=[48*mm, W-48*mm])
    cli_tbl.setStyle(TableStyle([
        ("BOX",         (0,0),(-1,-1), 0.5, BK),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(cli_tbl)

    # ── NORMA / LIGA ──────────────────────────────────────────────────────────
    _norma_txt = str(norma or liga or "")
    norma_tbl = Table([
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
    ]))
    story.append(norma_tbl)
    story.append(Spacer(1, 2*mm))

    # ── COMPOSIÇÃO QUÍMICA ────────────────────────────────────────────────────
    ELEM = ["C","Si","Mn","P","S","Cr","Ni","Mo"]
    comp_hdr = [ph("OF"), ph("CORRIDA\nHEAT Nº")] + [ph(e) for e in ELEM]
    comp_rows = [comp_hdr]

    for corr in corridas:
        _cm = corr._mapping if hasattr(corr, "_mapping") else {}
        _nof   = str(_cm.get("numero_of","") or "")
        _ncorr = str(_cm.get("numero_corrida","") or "")
        row = [pc(_nof), pc(_ncorr)]
        for ek in ["c","si","mn","p","s","cr","ni","mo"]:
            row.append(pc(fmt_num(_cm.get(ek, 0))))
        comp_rows.append(row)

    while len(comp_rows) < 9:
        comp_rows.append([""] * 10)

    cw_c = [20*mm, 22*mm] + [(W-42*mm)/8]*8
    tit_comp = Table([[ph("I - COMPOSIÇÃO QUIMICA / CHEMICAL COMPOSITION")]],
                     colWidths=[W])
    tit_comp.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    comp_tbl = Table(comp_rows, colWidths=cw_c)
    comp_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), CINZA),
        ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 7),
        ("GRID",         (0,0),(-1,-1), 0.4, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(tit_comp)
    story.append(comp_tbl)
    story.append(Spacer(1, 2*mm))

    # ── ENSAIOS MECÂNICOS ─────────────────────────────────────────────────────
    if "com_ensaio" in tipo and ensaios:
        ens_hdr = [ph("LIM. RES.\n(MPa)"), ph("LIM. ESC.\n(MPa)"),
                   ph("ALONG.\n(%)"), ph("RED. ÁREA\n(%)"),
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
        tit_ens = Table([[ph("II - PROPRIEDADES MECÂNICAS / MECHANICAL PROPERTIES")]],
                        colWidths=[W])
        tit_ens.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), CINZA),
            ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ]))
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
        story.append(tit_ens)
        story.append(ens_tbl)
        story.append(Spacer(1, 2*mm))

    # ── ITENS ────────────────────────────────────────────────────────────────
    it_hdr = [ph("Pedido/Item\nP.O."), ph("Modelo\nPattern"),
              ph("Descrição\nDescription"),
              ph("Séries\nSeries"), ph("Quantidade\nQuantity")]
    it_rows = [it_hdr]
    for it in itens:
        im = it._mapping if hasattr(it,"_mapping") else it
        it_rows.append([
            pc(im.get("pedido","")),
            pc(im.get("modelo","")),
            pl(im.get("descricao","")),
            pc(im.get("series","")),
            pc(str(im.get("quantidade",""))),
        ])
    while len(it_rows) < 9:
        it_rows.append(["","","","",""])

    tit_it = Table([[ph("II - OUTROS DADOS / OTHER INFORMATIONS")]],
                   colWidths=[W])
    tit_it.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CINZA),
        ("BOX",        (0,0),(-1,-1), 0.5, BK),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    it_tbl = Table(it_rows, colWidths=[W*0.20, W*0.14, W*0.37, W*0.15, W*0.14])
    it_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), CINZA),
        ("GRID",         (0,0),(-1,-1), 0.4, BK),
        ("FONTSIZE",     (0,0),(-1,-1), 7),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0),(1,-1), "CENTER"),
        ("ALIGN",        (2,0),(2,-1), "LEFT"),
        ("ALIGN",        (3,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",  (2,0),(2,-1), 3),
    ]))
    story.append(tit_it)
    story.append(it_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OBSERVAÇÕES ───────────────────────────────────────────────────────────
    obs_data = [[ph("III - OBSERVAÇÕES / COMMENTS")]]
    for _ in range(7):
        obs_data.append([pl("")])
    if obs:
        obs_data[1] = [pl(f"  {obs}")]
    obs_tbl = Table(obs_data, colWidths=[W])
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), CINZA),
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEBELOW",    (0,0),(0,0), 0.5, BK),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 2*mm))

    # ── OUTROS ENSAIOS ────────────────────────────────────────────────────────
    out_tbl = Table([
        [ph("VI - OUTROS ENSAIOS / OTHER TESTS"), ph("ANEXO\nATTACHED")],
        [pl(outros or ""), pl("")],
        [pl(""), pl("")],
    ], colWidths=[W*0.85, W*0.15])
    out_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), CINZA),
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEBEFORE",   (1,0),(1,-1), 0.5, BK),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, BK),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
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
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEABOVE",    (0,2),(-1,2), 0.5, BK),
        ("LINEBEFORE",   (1,0),(1,-1), 0.5, BK),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(rod_tbl)

    doc.build(story)
    buf.seek(0)
    return buf.read()

'''

src = src[:idx_inicio] + NOVA_FUNCAO + src[idx_fim:]
CERT.write_text(src, encoding="utf-8")
print("OK: PDF reescrito.")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'PDF cert layout identico ao template' && git push")
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
