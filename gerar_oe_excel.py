"""
gerar_oe_excel.py
=================
Preenche o template Excel de Ordem de Entrega com dados do banco
e gera um PDF para download.

Mapeamento das celulas do template:
- M5: Numero da OE (ex: "Nº 1628")
- C17: Nome do cliente
- Linhas 21-34: Itens (pedido, OF, referencia, liga, corrida, certificado, cod_peca, descricao, peso, qtd, serie, preco_unit, preco_total)
- B37: Observacoes
- C7: Nome do fornecedor (da config)
- C9: Endereco (da config)
- C11/M11: Bairro/Cidade (da config)
- C13: Contato (da config)
- E15: Telefone (da config)
- M15: Email (da config)
"""

from __future__ import annotations
import io
import copy
from datetime import date, datetime
from pathlib import Path

def gerar_oe_excel(
    template_bytes: bytes,
    numero_oe: str,
    nome_cliente: str,
    itens: list[dict],
    observacoes: str = "",
    config: dict = None,
) -> bytes:
    """
    Preenche o template Excel com os dados da OE e retorna bytes do arquivo.
    
    itens: lista de dicts com chaves:
        num_pedido, num_of, referencia, liga, corrida, certificado,
        cod_peca, descricao, peso_unit, qtd, serie, preco_unit, preco_total
    
    config: dict com dados da empresa (nome_empresa, endereco, cidade, etc.)
    """
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment

    if config is None:
        config = {}

    wb = load_workbook(io.BytesIO(template_bytes))

    # Usa a aba PADRAO como template base
    if "PADRÃO" in wb.sheetnames:
        ws_template = wb["PADRÃO"]
        # Copia a aba padrao para uma nova aba com o numero da OE
        ws = wb.copy_worksheet(ws_template)
        ws.title = str(numero_oe)
        # Remove a aba original de exemplo se existir (ex: "986")
        for nome in wb.sheetnames:
            if nome not in ["PADRÃO", str(numero_oe)]:
                try:
                    del wb[nome]
                except Exception:
                    pass
    else:
        ws = wb.active

    # ── Dados da empresa (da config) ─────────────────────────────────────────
    nome_empresa = config.get("nome_empresa", "Metalpoli - Fundição de Precisão")
    endereco = config.get("endereco", "Rua Umbuzeirro Nº 74")
    bairro = config.get("bairro", "Cidade Satélite")
    cidade = config.get("cidade", "Guarulhos")
    estado = config.get("estado", "SP")
    telefone = config.get("telefone", "(11) 2954-9908")
    email = config.get("email", "comercial@metalpoli.com.br")
    contato = config.get("contato", "James Machado")

    # Preenche dados da empresa
    ws["C7"] = nome_empresa
    ws["C9"] = endereco
    ws["C11"] = bairro
    ws["M11"] = cidade
    ws["C13"] = contato
    ws["M13"] = estado
    ws["E15"] = telefone
    ws["M15"] = email

    # ── Numero da OE ─────────────────────────────────────────────────────────
    ws["M5"] = f"Nº {numero_oe}"
    ws["P5"] = f"/{datetime.now().strftime('%y')}"

    # ── Cliente ───────────────────────────────────────────────────────────────
    ws["C17"] = nome_cliente

    # ── Itens (linhas 21 a 34) ────────────────────────────────────────────────
    LINHA_INICIO = 21
    MAX_ITENS = 14  # linhas 21 a 34

    for i, item in enumerate(itens[:MAX_ITENS]):
        linha = LINHA_INICIO + i
        ws[f"B{linha}"] = str(item.get("num_pedido", "") or "")
        ws[f"C{linha}"] = str(item.get("num_of", "") or "")
        ws[f"E{linha}"] = str(item.get("referencia", "") or "")
        ws[f"F{linha}"] = str(item.get("liga", "") or "")
        ws[f"G{linha}"] = str(item.get("corrida", "") or "")
        ws[f"H{linha}"] = str(item.get("certificado", "") or "")
        ws[f"I{linha}"] = str(item.get("cod_peca", "") or "")
        ws[f"K{linha}"] = str(item.get("descricao", "") or "")
        try:
            ws[f"M{linha}"] = float(item.get("peso_unit", 0) or 0)
        except Exception:
            ws[f"M{linha}"] = 0
        try:
            ws[f"N{linha}"] = int(item.get("qtd", 0) or 0)
        except Exception:
            ws[f"N{linha}"] = 0
        ws[f"O{linha}"] = str(item.get("serie", "") or "")
        try:
            ws[f"P{linha}"] = float(item.get("preco_unit", 0) or 0)
        except Exception:
            ws[f"P{linha}"] = 0
        # Formula para preco total
        ws[f"Q{linha}"] = f"=P{linha}*N{linha}"

    # Limpa linhas restantes
    for i in range(len(itens), MAX_ITENS):
        linha = LINHA_INICIO + i
        for col in ["B", "C", "E", "F", "G", "H", "I", "K", "M", "N", "O", "P", "Q"]:
            ws[f"{col}{linha}"] = None

    # ── Observacoes ───────────────────────────────────────────────────────────
    if observacoes:
        ws["B37"] = f" - {observacoes.upper()}"

    # ── Salva em bytes ────────────────────────────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


def gerar_oe_pdf_from_excel(excel_bytes: bytes) -> bytes | None:
    """
    Tenta converter o Excel para PDF usando reportlab como fallback.
    Retorna None se nao conseguir converter.
    """
    # Por ora retorna None - a conversao Excel->PDF requer LibreOffice no servidor
    # O usuario pode baixar o Excel e imprimir como PDF
    return None
