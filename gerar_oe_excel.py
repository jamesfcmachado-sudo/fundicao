"""
gerar_oe_excel.py - Gera PDF fiel ao template Excel da OE Metalpoli
"""
from __future__ import annotations
import io
from datetime import datetime


def gerar_oe_excel(template_bytes, numero_oe, nome_cliente, itens,
                   observacoes="", config=None, logo_bytes=None):
    """Preenche template Excel com valores calculados."""
    from openpyxl import load_workbook
    if config is None:
        config = {}
    wb = load_workbook(io.BytesIO(template_bytes))
    ws = None
    for nome_aba in wb.sheetnames:
        if 'PADR' in nome_aba.upper():
            ws = wb[nome_aba]; break
    if ws is None:
        ws = wb[wb.sheetnames[-1]]

    ws["C7"]  = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    ws["C9"]  = config.get("endereco", "Rua Umbuzeirro Nº 74")
    ws["C11"] = config.get("bairro", "Cidade Satélite")
    ws["M11"] = config.get("cidade", "Guarulhos")
    ws["C13"] = config.get("contato", "James Machado")
    ws["M13"] = config.get("estado", "SP")
    ws["E15"] = config.get("telefone", "(11) 2954-9908")
    ws["M15"] = config.get("email", "comercial@metalpoli.com.br")
    ano = datetime.now().strftime("%y")
    # Numero e ano na mesma celula para ficar juntos
    ws["M5"] = f"Nº {numero_oe}/{ano}"
    ws["N5"] = None
    ws["O5"] = None
    ws["P5"] = None
    ws["C17"] = nome_cliente.upper()

    total_peso = total_qtd = total_valor = 0.0
    for i in range(14):
        ln = 21 + i
        if i < len(itens):
            it = itens[i]
            peso = float(it.get("peso_unit", 0) or 0)
            qtd  = int(it.get("qtd", 0) or 0)
            pu   = float(it.get("preco_unit", 0) or 0)
            pt   = float(it.get("preco_total", 0) or qtd * pu)
            ws[f"B{ln}"] = str(it.get("num_pedido","") or "")
            ws[f"C{ln}"] = str(it.get("num_of","") or "")
            ws[f"E{ln}"] = str(it.get("referencia","") or "")
            ws[f"F{ln}"] = str(it.get("liga","") or "")
            ws[f"G{ln}"] = str(it.get("corrida","") or "")
            ws[f"H{ln}"] = str(it.get("certificado","") or "")
            ws[f"I{ln}"] = str(it.get("cod_peca","") or "")
            ws[f"K{ln}"] = str(it.get("descricao","") or "")
            ws[f"M{ln}"] = peso
            ws[f"N{ln}"] = qtd
            ws[f"O{ln}"] = str(it.get("serie","") or "")
            ws[f"P{ln}"] = pu
            ws[f"Q{ln}"] = pt
            total_peso += peso * qtd; total_qtd += qtd; total_valor += pt
        else:
            for col in ["B","C","E","F","G","H","I","K","O"]:
                ws[f"{col}{ln}"] = None
            ws[f"M{ln}"] = None; ws[f"N{ln}"] = None
            ws[f"P{ln}"] = None; ws[f"Q{ln}"] = None

    ws["M35"] = total_peso
    ws["N35"] = int(total_qtd)
    ws["Q35"] = total_valor
    ws["B37"] = f" - {observacoes.upper()}" if observacoes else None

    out = io.BytesIO()
    wb.save(out); out.seek(0)
    return out.read()


def gerar_oe_pdf(numero_oe, nome_cliente, itens, observacoes="",
                 config=None, logo_bytes=None):
    """Gera PDF paisagem fiel ao template Excel da OE."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    if config is None:
        config = {}

    pagesize = landscape(A4)
    PW, PH = pagesize
    ML = MR = 10*mm
    MT = MB = 8*mm
    W = PW - ML - MR  # ~257mm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB)

    styles = getSampleStyleSheet()
    def PS(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    BK = colors.black
    GR = colors.HexColor("#D9D9D9")

    nome_empresa = config.get("nome_empresa", "Metalpoli Fundição de Precisão")
    endereco = config.get("endereco", "Rua Umbuzeirro Nº 74")
    bairro   = config.get("bairro", "Cidade Satélite")
    cidade   = config.get("cidade", "Guarulhos")
    estado   = config.get("estado", "SP")
    telefone = config.get("telefone", "(11) 2954-9908")
    email    = config.get("email", "comercial@metalpoli.com.br")
    contato  = config.get("contato", "James Machado")
    ano      = datetime.now().strftime("%y")

    def fbr(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    def fpeso(v):
        return f"{v:.3f}".replace(".",",")

    story = []

    # ═══════════════════════════════════════════════
    # CABECALHO
    # ═══════════════════════════════════════════════
    logo_w   = 52*mm
    titulo_w = 110*mm
    oe_w     = W - logo_w - titulo_w

    if logo_bytes:
        try:
            logo_img = RLImage(io.BytesIO(logo_bytes), width=logo_w-4*mm, height=18*mm)
            logo_cell = logo_img
        except Exception:
            logo_cell = Paragraph("", PS("lc"))
    else:
        logo_cell = Paragraph("", PS("lc2"))

    cab = Table([[
        logo_cell,
        Paragraph("<b>Fundição de Precisão</b>",
                  PS("ft", fontSize=22, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        [Paragraph("<b>Ordem de Entrega</b>",
                   PS("oe1", fontSize=12, fontName="Helvetica-Bold", alignment=TA_CENTER)),
         Paragraph(f"<b>Nº {numero_oe}/{ano}</b>",
                   PS("oe2", fontSize=12, fontName="Helvetica-Bold", alignment=TA_CENTER))],
    ]], colWidths=[logo_w, titulo_w, oe_w])

    cab.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBEFORE",   (1,0),(1,0),   0.8, BK),
        ("LINEBEFORE",   (2,0),(2,0),   0.8, BK),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(cab)

    # ═══════════════════════════════════════════════
    # DADOS FORNECEDOR
    # ═══════════════════════════════════════════════
    lw  = 20*mm
    lw2 = 15*mm
    vw  = W * 0.50
    vw2 = W - lw - vw - lw2

    def lbl(t): return Paragraph(f"<b>{t}</b>", PS("lb", fontSize=9, fontName="Helvetica-Bold"))
    def val(t): return Paragraph(str(t), PS("vl", fontSize=9))
    def valb(t): return Paragraph(f"<b>{t}</b>", PS("vb", fontSize=9, fontName="Helvetica-Bold"))

    dados = [
        [lbl("Fornecedor"), val(nome_empresa),       "",             ""],
        [lbl("Endereço"),   val(endereco),            "",             ""],
        [lbl("Bairro"),     val(bairro),   lbl("Cidade"), val(cidade)],
        [lbl("Contato"),    val(contato),  lbl("UF"),     val(estado)],
        [lbl("Tel."),       val(telefone), lbl("e-mail"), val(email)],
        [lbl("Cliente"),    valb(nome_cliente.upper()), "",           ""],
    ]

    tbl_d = Table(dados, colWidths=[lw, vw, lw2, vw2])
    tbl_d.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.8, BK),
        ("LINEBELOW",    (0,0),(-1,-2), 0.4, BK),
        ("LINEBEFORE",   (2,2),(2,4),   0.4, BK),
        ("SPAN",         (1,0),(3,0)),
        ("SPAN",         (1,1),(3,1)),
        ("SPAN",         (1,5),(3,5)),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
    ]))
    story.append(tbl_d)

    # ═══════════════════════════════════════════════
    # TABELA DE ITENS
    # Larguras baseadas no PDF original (total W~257mm)
    # Nº pedido | OF | Ref | Liga | Corr | Cert | Cod Peça | Descrição | Peso | Qtde | Série | Pr.Un | Pr.Total
    # ═══════════════════════════════════════════════
    # Proporcoes baseadas nas larguras reais do template Excel
    _escala = W / 342.1
    CW = [
        23.6*mm*_escala,   # Nº do pedido
        16.4*mm*_escala,   # OF
        23.6*mm*_escala,   # Referência
        14.7*mm*_escala,   # Liga
        12.1*mm*_escala,   # Corr.
        17.6*mm*_escala,   # Certificado
        40.0*mm*_escala,   # Codigo da Peça
        33.5*mm*_escala,   # Descrição
        16.2*mm*_escala,   # Peso uni.(kg)
        11.7*mm*_escala,   # Qtde(pçs)
        18.3*mm*_escala,   # Série
        26.1*mm*_escala,   # Preço Un.(R$)
        23.3*mm*_escala,   # Preço Total
    ]

    def ph(t): return Paragraph(t, PS("hd", fontSize=7.5, fontName="Helvetica-Bold",
                                       alignment=TA_CENTER, leading=9, wordWrap='CJK'))
    def pc(t,a=TA_LEFT):   return Paragraph(str(t), PS(f"c{a}", fontSize=7.5,
                                              alignment=a, leading=9, wordWrap='CJK'))

    HEADS = ["Nº do pedido","OF","Referência","Liga","Corr.","Certificado",
             "Codigo da Peça","Descrição","Peso uni.\n(kg)","Qtde\n(pçs)",
             "Série","Preço Un.\n(R$)","Preço Total\n(R$)"]

    rows = [[ph(h) for h in HEADS]]
    tp = tq = tv = 0.0

    for it in itens:
        peso = float(it.get("peso_unit",0) or 0)
        qtd  = int(it.get("qtd",0) or 0)
        pu   = float(it.get("preco_unit",0) or 0)
        pt   = float(it.get("preco_total",0) or qtd*pu)
        tp += peso*qtd; tq += qtd; tv += pt

        rows.append([
            pc(it.get("num_pedido","") or ""),
            pc(it.get("num_of","") or "", TA_CENTER),
            pc(it.get("referencia","") or "", TA_CENTER),
            pc(it.get("liga","") or "", TA_CENTER),
            pc(it.get("corrida","") or "", TA_CENTER),
            pc(it.get("certificado","") or "", TA_CENTER),
            pc(it.get("cod_peca","") or ""),
            pc(it.get("descricao","") or "", TA_CENTER),
            pc(fpeso(peso), TA_RIGHT),
            pc(str(qtd), TA_CENTER),
            pc(it.get("serie","") or "", TA_CENTER),
            pc(fbr(pu), TA_RIGHT),
            pc(fbr(pt), TA_RIGHT),
        ])

    # Linhas vazias ate 14
    for _ in range(max(0, 14-len(itens))):
        rows.append([""]*13)

    # Total
    n = len(rows)
    rows.append([
        pc("<b>Total</b>", TA_LEFT),
        "","","","","","","",
        pc(f"<b>{fpeso(tp)}</b>", TA_RIGHT),
        pc(f"<b>{int(tq)}</b>", TA_CENTER),
        "","",
        pc(f"<b>{fbr(tv)}</b>", TA_RIGHT),
    ])

    RH = [9*mm] + [5.5*mm]*(n-1) + [5.5*mm]
    tbl_i = Table(rows, colWidths=CW, rowHeights=RH, repeatRows=1)
    tbl_i.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),   GR),
        ("FONTNAME",      (0,0),(-1,0),   "Helvetica-Bold"),
        ("ALIGN",         (0,0),(-1,0),   "CENTER"),
        ("VALIGN",        (0,0),(-1,-1),  "MIDDLE"),
        ("GRID",          (0,0),(-1,-1),  0.5, BK),
        ("LEFTPADDING",   (0,0),(-1,-1),  2),
        ("RIGHTPADDING",  (0,0),(-1,-1),  2),
        ("TOPPADDING",    (0,0),(-1,-1),  1),
        ("BOTTOMPADDING", (0,0),(-1,-1),  1),
        ("FONTNAME",      (0,n),(-1,n),   "Helvetica-Bold"),
    ]))
    story.append(tbl_i)

    # ═══════════════════════════════════════════════
    # OBSERVACOES
    # ═══════════════════════════════════════════════
    obs_rows = [
        [Paragraph("<b>Observações</b>", PS("ot", fontSize=9,
                   fontName="Helvetica-Bold", alignment=TA_CENTER))],
        [Paragraph(f" - {observacoes.upper()}" if observacoes else "",
                   PS("ov", fontSize=9))],
    ]
    tbl_obs = Table(obs_rows, colWidths=[W])
    tbl_obs.setStyle(TableStyle([
        ("BOX",          (0,0),(-1,-1), 0.5, BK),
        ("LINEBELOW",    (0,0),(0,0),   0.3, BK),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(tbl_obs)

    # ═══════════════════════════════════════════════
    # ASSINATURAS
    # ═══════════════════════════════════════════════
    story.append(Spacer(1, 8*mm))
    tbl_ass = Table([[
        Paragraph("_"*45, PS("al", fontSize=9, alignment=TA_CENTER)),
        Paragraph("_"*45, PS("ar", fontSize=9, alignment=TA_CENTER)),
    ],[
        Paragraph("Carregado por:", PS("cl2", fontSize=9, alignment=TA_CENTER)),
        Paragraph("Coletado por:",  PS("cr2", fontSize=9, alignment=TA_CENTER)),
    ]], colWidths=[W/2, W/2])
    tbl_ass.setStyle(TableStyle([
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 1),
        ("BOTTOMPADDING",(0,0),(-1,-1), 1),
    ]))
    story.append(tbl_ass)

    # Rodapé
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        datetime.now().strftime("%d/%m/%Y\n%H:%M\nPg. 1"),
        PS("rd", fontSize=7, alignment=TA_RIGHT, textColor=colors.grey, leading=9)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def excel_para_pdf(excel_bytes):
    import subprocess, tempfile, os
    try:
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(excel_bytes); xlsx_path = f.name
        out_dir = tempfile.mkdtemp()
        subprocess.run(['libreoffice','--headless','--convert-to','pdf',
                        '--outdir', out_dir, xlsx_path],
                       capture_output=True, timeout=30)
        pdf_path = os.path.join(out_dir,
            os.path.splitext(os.path.basename(xlsx_path))[0]+'.pdf')
        if os.path.exists(pdf_path):
            pdf = open(pdf_path,'rb').read()
            os.unlink(xlsx_path); os.unlink(pdf_path); os.rmdir(out_dir)
            return pdf
        os.unlink(xlsx_path)
        return None
    except Exception:
        return None


def configurar_impressao_excel(excel_bytes, orientacao="Paisagem"):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(excel_bytes))
        for ws in wb.worksheets:
            try:
                ws.page_setup.orientation = "landscape" if orientacao=="Paisagem" else "portrait"
                ws.page_setup.fitToPage = True
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0
                ws.page_setup.paperSize = 9
            except Exception:
                pass
        out = io.BytesIO(); wb.save(out); out.seek(0)
        return out.read()
    except Exception:
        return excel_bytes
