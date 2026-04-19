"""
gerar_oe_excel.py
Preenche template Excel e gera PDF fiel ao layout original.
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
        n = nome_aba.upper().replace('\u00c3', 'A').replace('\u00e3', 'a')
        if 'PADRAO' in n or 'PADR' in n:
            ws = wb[nome_aba]
            break
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
    ws["M5"] = f"Nº {numero_oe}/{ano}"
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
            total_peso  += peso * qtd
            total_qtd   += qtd
            total_valor += pt
        else:
            for col in ["B","C","E","F","G","H","I","K","O"]:
                ws[f"{col}{ln}"] = None
            ws[f"M{ln}"] = None; ws[f"N{ln}"] = None
            ws[f"P{ln}"] = None; ws[f"Q{ln}"] = None

    ws["M35"] = total_peso
    ws["N35"] = int(total_qtd)
    ws["Q35"] = total_valor
    if observacoes:
        ws["B37"] = f" - {observacoes.upper()}"
    else:
        ws["B37"] = None

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.read()


def gerar_oe_pdf(numero_oe, nome_cliente, itens, observacoes="",
                 config=None, logo_bytes=None):
    """
    Gera PDF fiel ao layout do template Excel da OE.
    Orientacao paisagem, mesmo visual do Excel.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable, Image as RLImage, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    if config is None:
        config = {}

    orientacao = config.get("orientacao", "Paisagem")
    pagesize = landscape(A4) if orientacao == "Paisagem" else A4

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize,
        leftMargin=10*mm, rightMargin=10*mm,
        topMargin=8*mm, bottomMargin=8*mm)

    W = pagesize[0] - 20*mm  # largura util

    styles = getSampleStyleSheet()
    def P(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # Estilos
    s_empresa = P("emp", fontSize=16, fontName="Helvetica-Bold", alignment=TA_LEFT)
    s_oe_tit  = P("oet", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER,
                   textColor=colors.HexColor("#1a3a5c"))
    s_oe_num  = P("oen", fontSize=18, fontName="Helvetica-Bold", alignment=TA_CENTER,
                   textColor=colors.HexColor("#1a3a5c"))
    s_label   = P("lb",  fontSize=8,  textColor=colors.HexColor("#666666"),
                   fontName="Helvetica-Bold")
    s_val     = P("vl",  fontSize=9,  fontName="Helvetica")
    s_val_b   = P("vlb", fontSize=9,  fontName="Helvetica-Bold")
    s_head    = P("hd",  fontSize=7,  textColor=colors.white,
                   fontName="Helvetica-Bold", alignment=TA_CENTER, leading=8)
    s_cell    = P("cl",  fontSize=7,  alignment=TA_LEFT,   leading=8)
    s_cellc   = P("cc",  fontSize=7,  alignment=TA_CENTER, leading=8)
    s_cellr   = P("cr",  fontSize=7,  alignment=TA_RIGHT,  leading=8)
    s_total   = P("tot", fontSize=8,  fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_totalr  = P("tor", fontSize=8,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    s_obs     = P("obs", fontSize=8,  fontName="Helvetica")
    s_footer  = P("ft",  fontSize=7,  alignment=TA_CENTER, textColor=colors.grey)
    s_ass     = P("ass", fontSize=8,  alignment=TA_CENTER)

    nome_empresa = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    endereco = config.get("endereco", "Rua Umbuzeirro Nº 74")
    bairro   = config.get("bairro", "Cidade Satélite")
    cidade   = config.get("cidade", "Guarulhos")
    estado   = config.get("estado", "SP")
    telefone = config.get("telefone", "(11) 2954-9908")
    email    = config.get("email", "comercial@metalpoli.com.br")
    ano      = datetime.now().strftime("%y")

    def fmt_br(v):
        return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    def fmt_peso(v):
        return f"{v:.3f}".replace(".",",")

    story = []

    # ── CABECALHO ─────────────────────────────────────────────────────────────
    logo_w = 35*mm
    texto_w = W * 0.45
    oe_w    = W - logo_w - texto_w - 4*mm

    if logo_bytes:
        try:
            logo_img = RLImage(io.BytesIO(logo_bytes), width=logo_w, height=22*mm)
            logo_cell = logo_img
        except Exception:
            logo_cell = Paragraph(nome_empresa, s_empresa)
            logo_w = 0
    else:
        logo_cell = Paragraph("", s_obs)
        logo_w = 0

    cab = Table([[
        logo_cell,
        [Paragraph(nome_empresa, s_empresa),
         Paragraph(f"{endereco} — {bairro}", P("sb", fontSize=8, textColor=colors.grey)),
         Paragraph(f"{cidade}/{estado} | Tel: {telefone} | {email}",
                   P("sb2", fontSize=8, textColor=colors.grey))],
        [Paragraph("ORDEM DE ENTREGA", s_oe_tit),
         Paragraph(f"Nº {numero_oe}/{ano}", s_oe_num)],
    ]], colWidths=[logo_w if logo_bytes else 5*mm, texto_w, oe_w])

    cab.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0),(-1,-1), 3),
        ("RIGHTPADDING",(0,0),(-1,-1), 3),
        ("LINEBELOW",   (0,0),(-1,0),  1.5, colors.HexColor("#1a3a5c")),
        ("LINEBEFORE",  (2,0),(2,0),   1, colors.HexColor("#cccccc")),
    ]))
    story.append(cab)
    story.append(Spacer(1, 3*mm))

    # ── DADOS FORNECEDOR / CLIENTE ────────────────────────────────────────────
    info = Table([[
        Paragraph("<b>Fornecedor:</b>", s_label),
        Paragraph(nome_empresa, s_val_b),
        Paragraph("<b>Cliente:</b>", s_label),
        Paragraph(nome_cliente.upper(), s_val_b),
    ]], colWidths=[22*mm, W*0.35, 18*mm, W*0.35])
    info.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("BOX",         (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND",  (0,0),(0,0),   colors.HexColor("#f0f4f8")),
        ("BACKGROUND",  (2,0),(2,0),   colors.HexColor("#f0f4f8")),
    ]))
    story.append(info)
    story.append(Spacer(1, 3*mm))

    # ── TABELA DE ITENS ───────────────────────────────────────────────────────
    # Proporcoes baseadas nas larguras do Excel
    CW = [
        W*0.115,  # Nº Pedido
        W*0.075,  # OF
        W*0.09,   # Referência
        W*0.05,   # Liga
        W*0.065,  # Corrida
        W*0.08,   # Certificado
        W*0.115,  # Código Peça
        W*0.095,  # Descrição
        W*0.06,   # Peso (kg)
        W*0.05,   # Qtde
        W*0.075,  # Série
        W*0.065,  # Preço Unit.
        W*0.065,  # Preço Total
    ]

    HEADS = [
        "Nº do\nPedido", "OF", "Referência", "Liga", "Corr.",
        "Certificado", "Código da Peça", "Descrição",
        "Peso\nuni.(kg)", "Qtde\n(pçs)", "Série",
        "Preço Un.\n(R$)", "Preço Total\n(R$)"
    ]

    azul_esc = colors.HexColor("#1a3a5c")
    cinza_cl = colors.HexColor("#f0f4f8")

    rows = [[Paragraph(h, s_head) for h in HEADS]]
    total_peso = total_qtd = total_valor = 0.0

    for it in itens:
        peso = float(it.get("peso_unit", 0) or 0)
        qtd  = int(it.get("qtd", 0) or 0)
        pu   = float(it.get("preco_unit", 0) or 0)
        pt   = float(it.get("preco_total", 0) or qtd * pu)
        total_peso  += peso * qtd
        total_qtd   += qtd
        total_valor += pt

        rows.append([
            Paragraph(str(it.get("num_pedido","") or ""), s_cell),
            Paragraph(str(it.get("num_of","") or ""), s_cellc),
            Paragraph(str(it.get("referencia","") or ""), s_cellc),
            Paragraph(str(it.get("liga","") or ""), s_cellc),
            Paragraph(str(it.get("corrida","") or ""), s_cellc),
            Paragraph(str(it.get("certificado","") or ""), s_cellc),
            Paragraph(str(it.get("cod_peca","") or ""), s_cell),
            Paragraph(str(it.get("descricao","") or ""), s_cellc),
            Paragraph(fmt_peso(peso), s_cellr),
            Paragraph(str(qtd), s_cellc),
            Paragraph(str(it.get("serie","") or ""), s_cellc),
            Paragraph(fmt_br(pu), s_cellr),
            Paragraph(fmt_br(pt), s_cellr),
        ])

    # Linha total
    n = len(rows)
    rows.append([
        Paragraph("<b>Total</b>", s_total), "", "", "", "", "", "", "",
        Paragraph(f"<b>{fmt_peso(total_peso)}</b>", s_totalr),
        Paragraph(f"<b>{int(total_qtd)}</b>", s_total),
        "", "",
        Paragraph(f"<b>{fmt_br(total_valor)}</b>", s_totalr),
    ])

    tbl = Table(rows, colWidths=CW, repeatRows=1)
    row_bg = [colors.white, cinza_cl]
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),    azul_esc),
        ("TEXTCOLOR",     (0,0),(-1,0),    colors.white),
        ("FONTNAME",      (0,0),(-1,0),    "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0),    7),
        ("ALIGN",         (0,0),(-1,0),    "CENTER"),
        ("VALIGN",        (0,0),(-1,-1),   "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,n-1),  row_bg),
        ("BACKGROUND",    (0,n),(-1,n),    colors.HexColor("#dce4f0")),
        ("FONTNAME",      (0,n),(-1,n),    "Helvetica-Bold"),
        ("GRID",          (0,0),(-1,-1),   0.3, colors.HexColor("#b0b8c4")),
        ("LEFTPADDING",   (0,0),(-1,-1),   2),
        ("RIGHTPADDING",  (0,0),(-1,-1),   2),
        ("TOPPADDING",    (0,0),(-1,-1),   2),
        ("BOTTOMPADDING", (0,0),(-1,-1),   2),
        ("SPAN",          (0,n),(7,n)),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4*mm))

    # ── OBSERVACOES ───────────────────────────────────────────────────────────
    if observacoes:
        obs_tbl = Table([[Paragraph(
            f"<b>Observações:</b> {observacoes}", s_obs)
        ]], colWidths=[W])
        obs_tbl.setStyle(TableStyle([
            ("BOX",        (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("LEFTPADDING",(0,0),(-1,-1), 5),
            ("TOPPADDING", (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ]))
        story.append(obs_tbl)
        story.append(Spacer(1, 4*mm))

    # ── ASSINATURAS ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    ass = Table([[
        Paragraph("_" * 40, s_ass),
        Paragraph("_" * 40, s_ass),
    ],[
        Paragraph("Carregado por:", s_ass),
        Paragraph("Recebido por:", s_ass),
    ]], colWidths=[W/2, W/2])
    ass.setStyle(TableStyle([
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0),(-1,-1), 2),
    ]))
    story.append(ass)
    story.append(Spacer(1, 4*mm))

    # ── RODAPE ────────────────────────────────────────────────────────────────
    rodape = config.get("rodape_pdf",
        f"{nome_empresa} | {telefone} | {email}")
    story.append(HRFlowable(width=W, thickness=0.5,
                             color=colors.HexColor("#cccccc")))
    story.append(Paragraph(rodape, s_footer))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def configurar_impressao_excel(excel_bytes, orientacao="Paisagem"):
    """Configura orientacao de impressao no Excel."""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(excel_bytes))
        for ws in wb.worksheets:
            try:
                ws.page_setup.orientation = (
                    "landscape" if orientacao == "Paisagem" else "portrait")
                ws.page_setup.fitToPage = True
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0
                ws.page_setup.paperSize = 9  # A4
            except Exception:
                pass
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out.read()
    except Exception:
        return excel_bytes
