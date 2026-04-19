"""
gerar_oe_excel.py
Preenche template Excel de OE com dados do banco.
Calcula valores no Python (sem depender do Excel recalcular).
"""
from __future__ import annotations
import io
from datetime import datetime


def gerar_oe_excel(template_bytes, numero_oe, nome_cliente, itens,
                   observacoes="", config=None, logo_bytes=None):
    """Preenche template Excel e retorna bytes .xlsx com valores calculados."""
    from openpyxl import load_workbook

    if config is None:
        config = {}

    wb = load_workbook(io.BytesIO(template_bytes))
    ws = wb["PADRAO"] if "PADRAO" in wb.sheetnames else (
         wb["PADRÃO"] if "PADRÃO" in wb.sheetnames else wb.active)

    # ── Logo ──────────────────────────────────────────────────────────────────
    if logo_bytes:
        try:
            from openpyxl.drawing.image import Image as XLImage
            from PIL import Image as PILImage
            # Redimensiona logo para caber no cabecalho
            pil_img = PILImage.open(io.BytesIO(logo_bytes))
            pil_img.thumbnail((120, 80))
            img_buf = io.BytesIO()
            pil_img.save(img_buf, format="PNG")
            img_buf.seek(0)
            xl_img = XLImage(img_buf)
            xl_img.anchor = "B2"
            # Remove logo antigo se existir
            ws._images = []
            ws.add_image(xl_img)
        except Exception:
            pass
    else:
        # Mantem logo original do template
        pass

    # ── Dados empresa ─────────────────────────────────────────────────────────
    ws["C7"]  = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    ws["C9"]  = config.get("endereco", "Rua Umbuzeirro Nº 74")
    ws["C11"] = config.get("bairro", "Cidade Satélite")
    ws["M11"] = config.get("cidade", "Guarulhos")
    ws["C13"] = config.get("contato", "James Machado")
    ws["M13"] = config.get("estado", "SP")
    ws["E15"] = config.get("telefone", "(11) 2954-9908")
    ws["M15"] = config.get("email", "comercial@metalpoli.com.br")

    # ── Numero OE — M5 e P5 juntos ────────────────────────────────────────────
    ano = datetime.now().strftime("%y")
    ws["M5"] = f"Nº {numero_oe}/{ano}"
    ws["P5"] = None  # limpa o campo separado

    # ── Cliente ───────────────────────────────────────────────────────────────
    ws["C17"] = nome_cliente.upper()

    # ── Itens: calcula valores no Python e insere como valores (nao formulas) ─
    LINHA_INICIO = 21
    MAX_ITENS = 14

    total_peso  = 0.0
    total_qtd   = 0
    total_valor = 0.0

    for i in range(MAX_ITENS):
        ln = LINHA_INICIO + i
        if i < len(itens):
            it = itens[i]
            peso  = float(it.get("peso_unit", 0) or 0)
            qtd   = int(it.get("qtd", 0) or 0)
            pu    = float(it.get("preco_unit", 0) or 0)
            pt    = float(it.get("preco_total", 0) or qtd * pu)

            ws[f"B{ln}"] = str(it.get("num_pedido", "") or "")
            ws[f"C{ln}"] = str(it.get("num_of", "") or "")
            ws[f"E{ln}"] = str(it.get("referencia", "") or "")
            ws[f"F{ln}"] = str(it.get("liga", "") or "")
            ws[f"G{ln}"] = str(it.get("corrida", "") or "")
            ws[f"H{ln}"] = str(it.get("certificado", "") or "")
            ws[f"I{ln}"] = str(it.get("cod_peca", "") or "")
            ws[f"K{ln}"] = str(it.get("descricao", "") or "")
            ws[f"M{ln}"] = peso
            ws[f"N{ln}"] = qtd
            ws[f"O{ln}"] = str(it.get("serie", "") or "")
            ws[f"P{ln}"] = pu
            ws[f"Q{ln}"] = pt  # valor calculado (nao formula)

            total_peso  += peso * qtd
            total_qtd   += qtd
            total_valor += pt
        else:
            for col in ["B","C","E","F","G","H","I","K","O"]:
                ws[f"{col}{ln}"] = None
            ws[f"M{ln}"] = None
            ws[f"N{ln}"] = None
            ws[f"P{ln}"] = None
            ws[f"Q{ln}"] = None

    # Totais calculados diretamente
    ws["M35"] = total_peso
    ws["N35"] = total_qtd
    ws["Q35"] = total_valor

    # ── Observacoes ───────────────────────────────────────────────────────────
    if observacoes:
        ws["B37"] = f" - {observacoes.upper()}"
    else:
        ws["B37"] = None

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()


def gerar_oe_pdf(numero_oe, nome_cliente, itens, observacoes="", config=None, logo_bytes=None):
    """Gera PDF da OE usando reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable, Image as RLImage)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    if config is None:
        config = {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=10*mm, bottomMargin=10*mm)

    styles = getSampleStyleSheet()
    def P(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_emp   = P("emp", fontSize=13, fontName="Helvetica-Bold",
                alignment=TA_LEFT, spaceAfter=1)
    s_sub   = P("sub", fontSize=8, textColor=colors.grey, spaceAfter=1)
    s_oe    = P("oe",  fontSize=16, fontName="Helvetica-Bold",
                alignment=TA_CENTER, textColor=colors.HexColor("#1a3a5c"))
    s_oen   = P("oen", fontSize=12, fontName="Helvetica-Bold",
                alignment=TA_CENTER, spaceAfter=3)
    s_label = P("lb",  fontSize=7,  textColor=colors.grey)
    s_val   = P("vl",  fontSize=9,  fontName="Helvetica-Bold")
    s_head  = P("hd",  fontSize=7,  textColor=colors.white,
                fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_cell  = P("cl",  fontSize=7,  alignment=TA_LEFT,   leading=9)
    s_cellc = P("cc",  fontSize=7,  alignment=TA_CENTER, leading=9)
    s_cellr = P("cr",  fontSize=7,  alignment=TA_RIGHT,  leading=9)
    s_obs   = P("ob",  fontSize=8)
    s_rod   = P("rd",  fontSize=7,  alignment=TA_CENTER,
                textColor=colors.grey)

    nome_empresa = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    endereco = config.get("endereco", "")
    cidade   = config.get("cidade", "")
    estado   = config.get("estado", "")
    telefone = config.get("telefone", "")
    email    = config.get("email", "")
    ano      = datetime.now().strftime("%y")

    def fmt_br(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    story = []

    # ── Cabecalho com logo ────────────────────────────────────────────────────
    if logo_bytes:
        try:
            logo_buf = io.BytesIO(logo_bytes)
            logo_img = RLImage(logo_buf, width=35*mm, height=22*mm)
            cab_data = [[
                logo_img,
                [Paragraph(nome_empresa, s_emp),
                 Paragraph(f"{endereco} — {cidade}/{estado}", s_sub),
                 Paragraph(f"Tel: {telefone} | {email}", s_sub)],
                [Paragraph("ORDEM DE ENTREGA", s_oe),
                 Paragraph(f"Nº {numero_oe}/{ano}", s_oen)],
            ]]
            cab_tbl = Table(cab_data, colWidths=[38*mm, 80*mm, 62*mm])
        except Exception:
            logo_bytes = None

    if not logo_bytes:
        cab_data = [[
            [Paragraph(nome_empresa, s_emp),
             Paragraph(f"{endereco} — {cidade}/{estado}", s_sub),
             Paragraph(f"Tel: {telefone} | {email}", s_sub)],
            [Paragraph("ORDEM DE ENTREGA", s_oe),
             Paragraph(f"Nº {numero_oe}/{ano}", s_oen)],
        ]]
        cab_tbl = Table(cab_data, colWidths=[100*mm, 80*mm])

    cab_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("LINEBELOW", (0,0), (-1,0), 1, colors.HexColor("#1a3a5c")),
    ]))
    story.append(cab_tbl)
    story.append(Spacer(1, 3*mm))

    # ── Dados fornecedor / cliente ────────────────────────────────────────────
    info_data = [[
        Paragraph("<b>Fornecedor:</b>", s_label),
        Paragraph(nome_empresa, s_val),
        Paragraph("<b>Cliente:</b>", s_label),
        Paragraph(nome_cliente.upper(), s_val),
    ]]
    info_tbl = Table(info_data, colWidths=[22*mm, 78*mm, 18*mm, 62*mm])
    info_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LINEBELOW", (0,0), (-1,0), 0.5, colors.HexColor("#cccccc")),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 2*mm))

    # ── Tabela de itens ───────────────────────────────────────────────────────
    CW = [22*mm,13*mm,19*mm,9*mm,12*mm,17*mm,25*mm,17*mm,
          11*mm,10*mm,13*mm,13*mm,14*mm]
    HEADS = ["Nº Pedido","OF","Referência","Liga","Corrida","Certificado",
             "Código Peça","Descrição","Peso\n(kg)","Qtde\n(pçs)",
             "Série","Preço\nUnit.(R$)","Preço\nTotal(R$)"]

    rows = [[Paragraph(h, s_head) for h in HEADS]]
    total_peso = total_qtd = total_valor = 0.0

    for it in itens:
        peso  = float(it.get("peso_unit", 0) or 0)
        qtd   = int(it.get("qtd", 0) or 0)
        pu    = float(it.get("preco_unit", 0) or 0)
        pt    = float(it.get("preco_total", 0) or qtd*pu)
        total_peso  += peso * qtd
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
        Paragraph(f"<b>{int(total_qtd)}</b>", s_totb),
        "",
        "",
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

    # ── Assinaturas ───────────────────────────────────────────────────────────
    ass = Table([[
        Paragraph("_"*35, s_cellc),
        Paragraph("_"*35, s_cellc),
    ],[
        Paragraph("Carregado por:", s_cellc),
        Paragraph("Recebido por:", s_cellc),
    ]], colWidths=[90*mm, 90*mm])
    ass.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                              ("TOPPADDING",(0,0),(-1,-1),2)]))
    story.append(ass)
    story.append(Spacer(1,3*mm))

    rodape = config.get("rodape_pdf", f"{nome_empresa} | {telefone} | {email}")
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#cccccc")))
    story.append(Paragraph(rodape, s_rod))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def configurar_impressao_excel(excel_bytes, orientacao="Paisagem"):
    """Configura orientacao de impressao no Excel e retorna bytes."""
    from openpyxl import load_workbook
    from openpyxl.worksheet.page import PageMargins

    wb = load_workbook(io.BytesIO(excel_bytes))
    for ws in wb.worksheets:
        if orientacao == "Paisagem":
            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        else:
            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins = PageMargins(
            left=0.5, right=0.5, top=0.75, bottom=0.75)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()
