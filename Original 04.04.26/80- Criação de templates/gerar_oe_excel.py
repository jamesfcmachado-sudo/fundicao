"""
gerar_oe_excel.py - Preenche template Excel e gera PDF da OE
"""
from __future__ import annotations
import io
from datetime import datetime


def gerar_oe_excel(template_bytes, numero_oe, nome_cliente, itens, observacoes="", config=None):
    from openpyxl import load_workbook
    if config is None:
        config = {}
    wb = load_workbook(io.BytesIO(template_bytes))
    ws = wb["PADRÃO"] if "PADRÃO" in wb.sheetnames else wb.active

    ws["C7"]  = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    ws["C9"]  = config.get("endereco", "")
    ws["M11"] = config.get("cidade", "")
    ws["M13"] = config.get("estado", "")
    ws["E15"] = config.get("telefone", "")
    ws["M15"] = config.get("email", "")
    ws["M5"]  = f"Nº {numero_oe}"
    ws["P5"]  = f"/{datetime.now().strftime('%y')}"
    ws["C17"] = nome_cliente

    for i in range(14):
        ln = 21 + i
        if i < len(itens):
            it = itens[i]
            ws[f"B{ln}"] = str(it.get("num_pedido","") or "")
            ws[f"C{ln}"] = str(it.get("num_of","") or "")
            ws[f"E{ln}"] = str(it.get("referencia","") or "")
            ws[f"F{ln}"] = str(it.get("liga","") or "")
            ws[f"G{ln}"] = str(it.get("corrida","") or "")
            ws[f"H{ln}"] = str(it.get("certificado","") or "")
            ws[f"I{ln}"] = str(it.get("cod_peca","") or "")
            ws[f"K{ln}"] = str(it.get("descricao","") or "")
            try: ws[f"M{ln}"] = float(it.get("peso_unit",0) or 0)
            except: ws[f"M{ln}"] = 0
            try: ws[f"N{ln}"] = int(it.get("qtd",0) or 0)
            except: ws[f"N{ln}"] = 0
            ws[f"O{ln}"] = str(it.get("serie","") or "")
            try: ws[f"P{ln}"] = float(it.get("preco_unit",0) or 0)
            except: ws[f"P{ln}"] = 0
            ws[f"Q{ln}"] = f"=P{ln}*N{ln}"
        else:
            for col in ["B","C","E","F","G","H","I","K","O"]:
                ws[f"{col}{ln}"] = None
            ws[f"M{ln}"] = None; ws[f"N{ln}"] = None
            ws[f"P{ln}"] = None; ws[f"Q{ln}"] = f"=P{ln}*N{ln}"

    ws["M35"] = "=((M21*N21)+(M22*N22)+(M23*N23)+(M24*N24)+(M25*N25)+(M26*N26)+(M27*N27)+(M28*N28)+(M29*N29)+(M30*N30)+(M31*N31)+(M32*N32)+(M33*N33)+(M34*N34))"
    ws["N35"] = "=SUM(N21:N34)"
    ws["Q35"] = "=SUM(Q21:Q34)"
    if observacoes:
        ws["B37"] = f" - {observacoes.upper()}"

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()


def gerar_oe_pdf(numero_oe, nome_cliente, itens, observacoes="", config=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    if config is None:
        config = {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm)

    styles = getSampleStyleSheet()
    def P(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_titulo = P("t", fontSize=14, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2)
    s_sub    = P("s", fontSize=8,  alignment=TA_CENTER, textColor=colors.grey, spaceAfter=2)
    s_oe     = P("oe", fontSize=13, alignment=TA_CENTER, fontName="Helvetica-Bold",
                  textColor=colors.HexColor("#1a3a5c"), spaceAfter=3)
    s_label  = P("lb", fontSize=7, textColor=colors.grey)
    s_val    = P("vl", fontSize=9, fontName="Helvetica-Bold")
    s_head   = P("hd", fontSize=7, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_cell   = P("cl", fontSize=7, alignment=TA_LEFT,   leading=9)
    s_cellc  = P("cc", fontSize=7, alignment=TA_CENTER, leading=9)
    s_cellr  = P("cr", fontSize=7, alignment=TA_RIGHT,  leading=9)
    s_obs    = P("ob", fontSize=8)
    s_rod    = P("rd", fontSize=7, alignment=TA_CENTER, textColor=colors.grey)

    nome_empresa = config.get("nome_empresa","Metalpoli - Fundição de Precisão")
    endereco = config.get("endereco","")
    cidade   = config.get("cidade","")
    estado   = config.get("estado","")
    telefone = config.get("telefone","")
    email    = config.get("email","")

    def fmt_br(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    story = []
    story.append(Paragraph(nome_empresa, s_titulo))
    story.append(Paragraph(f"{endereco} — {cidade}/{estado} | Tel: {telefone} | {email}", s_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("ORDEM DE ENTREGA", s_oe))
    story.append(Paragraph(
        f"<b>Nº {numero_oe}</b> &nbsp;&nbsp;&nbsp; Emissão: {datetime.now().strftime('%d/%m/%Y')}",
        P("oe2", fontSize=10, alignment=TA_CENTER)))
    story.append(Spacer(1, 3*mm))

    dados = Table([[
        Paragraph("<b>Fornecedor:</b>", s_label), Paragraph(nome_empresa, s_val),
        Paragraph("<b>Cliente:</b>", s_label),    Paragraph(nome_cliente, s_val),
    ]], colWidths=[22*mm, 80*mm, 20*mm, 58*mm])
    dados.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2)]))
    story.append(dados)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 2*mm))

    CW = [22*mm,14*mm,20*mm,10*mm,13*mm,18*mm,28*mm,18*mm,12*mm,10*mm,14*mm,14*mm,15*mm]
    HEADS = ["Nº Pedido","OF","Referência","Liga","Corrida","Certificado",
             "Código Peça","Descrição","Peso\n(kg)","Qtde\n(pçs)","Série","Preço\nUnit.","Preço\nTotal"]

    rows = [[Paragraph(h, s_head) for h in HEADS]]
    total_peso = total_qtd = total_valor = 0

    for it in itens:
        peso  = float(it.get("peso_unit",0) or 0)
        qtd   = int(it.get("qtd",0) or 0)
        pu    = float(it.get("preco_unit",0) or 0)
        pt    = float(it.get("preco_total",0) or qtd*pu)
        total_peso  += peso*qtd
        total_qtd   += qtd
        total_valor += pt
        rows.append([
            Paragraph(str(it.get("num_pedido","") or ""), s_cell),
            Paragraph(str(it.get("num_of","") or ""), s_cellc),
            Paragraph(str(it.get("referencia","") or ""), s_cell),
            Paragraph(str(it.get("liga","") or ""), s_cellc),
            Paragraph(str(it.get("corrida","") or ""), s_cellc),
            Paragraph(str(it.get("certificado","") or ""), s_cellc),
            Paragraph(str(it.get("cod_peca","") or ""), s_cell),
            Paragraph(str(it.get("descricao","") or ""), s_cell),
            Paragraph(f"{peso:.3f}", s_cellr),
            Paragraph(str(qtd), s_cellc),
            Paragraph(str(it.get("serie","") or ""), s_cellc),
            Paragraph(fmt_br(pu), s_cellr),
            Paragraph(fmt_br(pt), s_cellr),
        ])

    n = len(rows)
    s_totb = P("tb", fontSize=7, fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_totr = P("tr", fontSize=7, fontName="Helvetica-Bold", alignment=TA_RIGHT)
    rows.append([
        Paragraph("<b>TOTAL</b>", s_totb),"","","","","","","",
        Paragraph(f"<b>{total_peso:.2f}</b>", s_totr),
        Paragraph(f"<b>{total_qtd}</b>", s_totb),
        "", "",
        Paragraph(f"<b>{fmt_br(total_valor)}</b>", s_totr),
    ])

    tbl = Table(rows, colWidths=CW, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),   colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",     (0,0),(-1,0),   colors.white),
        ("VALIGN",        (0,0),(-1,-1),  "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,n-1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("BACKGROUND",    (0,n),(-1,n),   colors.HexColor("#e8edf2")),
        ("FONTNAME",      (0,n),(-1,n),   "Helvetica-Bold"),
        ("GRID",          (0,0),(-1,-1),  0.3, colors.HexColor("#c0c8d0")),
        ("LEFTPADDING",   (0,0),(-1,-1),  2),
        ("RIGHTPADDING",  (0,0),(-1,-1),  2),
        ("TOPPADDING",    (0,0),(-1,-1),  2),
        ("BOTTOMPADDING", (0,0),(-1,-1),  2),
        ("SPAN",          (0,n),(7,n)),
    ]))
    story.append(tbl)
    story.append(Spacer(1,4*mm))

    if observacoes:
        story.append(Paragraph(f"<b>Observações:</b> {observacoes}", s_obs))
        story.append(Spacer(1,4*mm))

    ass = Table([[
        Paragraph("_"*35, s_cellc),
        Paragraph("_"*35, s_cellc),
    ],[
        Paragraph("Carregado por:", s_cellc),
        Paragraph("Recebido por:", s_cellc),
    ]], colWidths=[90*mm, 90*mm])
    ass.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("TOPPADDING",(0,0),(-1,-1),2)]))
    story.append(ass)
    story.append(Spacer(1,4*mm))

    rodape = config.get("rodape_pdf", f"{nome_empresa} | {telefone} | {email}")
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Paragraph(rodape, s_rod))

    doc.build(story)
    buf.seek(0)
    return buf.read()
