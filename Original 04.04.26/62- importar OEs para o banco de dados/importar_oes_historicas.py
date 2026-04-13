"""
Importação histórica de Ordens de Entrega das planilhas Excel para o banco fundicao.db.

USO:
    python importar_oes_historicas.py

Coloque este arquivo na mesma pasta que app.py, fundicao_db.py e os dois arquivos Excel.
Os Excel devem se chamar:
    - Ordem_de_Entrega_2019_a_2023.xlsx
    - Ordem_de_Entrega_2024_a_2026.xlsx

O script é seguro para rodar múltiplas vezes (idempotente — não duplica registros).
"""

import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── Localização do banco e dos Excels ─────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "fundicao.db"
EXCEL_2019 = BASE_DIR / "Ordem_de_Entrega_2019_a_2023.xlsx"
EXCEL_2024 = BASE_DIR / "Ordem_de_Entrega_2024_a_2026.xlsx"


# ── Extração de uma aba ────────────────────────────────────────────────────────
def extrair_aba(nome_aba: str, df: pd.DataFrame) -> dict | None:
    vals = list(df.values)
    if len(vals) < 16:
        return None

    header_row = vals[3] if len(vals) > 3 else []

    # Número da OE
    num_oe = None
    for v in header_row:
        if str(v).startswith("Nº "):
            num_oe = str(v).replace("Nº ", "").strip()
            break

    # Código (707-52) → num_pedido_externo, qtd_total
    oe_cod = qtd_cod = None
    for v in header_row:
        m = re.search(r"\((\d+)-(\d+)\)", str(v))
        if m:
            oe_cod = m.group(1)
            qtd_cod = int(m.group(2))
            break

    # Cliente (linha 17, índice 15)
    cliente_row = vals[15] if len(vals) > 15 else []
    cliente = ""
    if len(cliente_row) > 2 and str(cliente_row[2]) not in ("nan", ""):
        cliente = str(cliente_row[2]).strip()

    # Observações (linha 37~41)
    obs = ""
    for row in vals[35:42]:
        v1 = str(row[1]) if len(row) > 1 else "nan"
        if v1 not in ("nan", "") and "Carregado" not in v1:
            obs = v1.strip().lstrip("- ").strip()
            break

    # Itens (a partir da linha 21, índice 20)
    itens = []
    for row in vals[20:]:
        nped = str(row[1]) if len(row) > 1 else "nan"
        if str(nped) == "Total":
            break
        if nped in ("nan", ""):
            continue

        def sv(r, i):
            v = r[i] if len(r) > i else None
            return "" if (v is None or str(v) == "nan") else str(v).strip()

        def fv(r, i):
            v = r[i] if len(r) > i else None
            if v is None or str(v) == "nan":
                return 0.0
            try:
                return float(v)
            except Exception:
                return 0.0

        qtd = row[13] if len(row) > 13 else None
        try:
            qtd_val = int(float(qtd)) if qtd and str(qtd) != "nan" else 0
        except Exception:
            qtd_val = 0
        if qtd_val == 0:
            continue

        itens.append({
            "num_pedido":  nped,
            "num_of":      sv(row, 2),
            "referencia":  sv(row, 4),
            "liga":        sv(row, 5),
            "corrida":     sv(row, 6),
            "certificado": sv(row, 7),
            "cod_peca":    sv(row, 8),
            "descricao":   sv(row, 10),
            "peso_unit":   fv(row, 12),
            "qtd":         qtd_val,
            "serie":       sv(row, 14),
            "preco_unit":  fv(row, 15),
            "preco_total": fv(row, 16),
        })

    if not itens and not cliente:
        return None  # aba vazia

    try:
        num_oe_seq = int(nome_aba.strip()) if nome_aba.strip().isdigit() else None
    except Exception:
        num_oe_seq = None

    return {
        "num_oe":      num_oe or nome_aba.strip(),
        "num_oe_seq":  num_oe_seq,
        "oe_cod":      oe_cod,
        "qtd_cod":     qtd_cod,
        "cliente":     cliente,
        "observacoes": obs,
        "itens":       itens,
    }


# ── Importação para o banco ────────────────────────────────────────────────────
def importar():
    if not DB_PATH.exists():
        print(f"❌  Banco não encontrado: {DB_PATH}")
        return

    # Verificar / migrar colunas extras em ordem_entrega
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    cols = {r[1] for r in cx.execute("PRAGMA table_info(ordem_entrega)").fetchall()}
    extras = {
        "numero_oe_seq":  "INTEGER",
        "data_emissao":   "DATE",
        "transportadora": "TEXT",
        "placa_veiculo":  "TEXT",
        "nota_fiscal":    "TEXT",
        "num_pedido":     "TEXT",
        "num_of_ref":     "TEXT",
        "referencia":     "TEXT",
        "liga":           "TEXT",
        "corrida":        "TEXT",
        "certificado":    "TEXT",
        "cod_peca":       "TEXT",
        "descricao":      "TEXT",
        "peso_unit":      "REAL",
        "serie":          "TEXT",
        "preco_unit":     "REAL",
        "preco_total":    "REAL",
        "nome_cliente":   "TEXT",
    }
    for col, tipo in extras.items():
        if col not in cols:
            cx.execute(f"ALTER TABLE ordem_entrega ADD COLUMN {col} {tipo}")
    cx.commit()
    print("✅  Migração das colunas extras concluída.")

    # Carregar mapa de OFs do banco  {numero_of → id}
    ofs_map = {r["numero_of"]: r["id"] for r in cx.execute("SELECT id, numero_of FROM ordem_fabricacao").fetchall()}
    print(f"📋  OFs no banco: {len(ofs_map)}")

    # OEs já importadas (numero_oe_seq) para evitar duplicatas
    ja_importadas = {r[0] for r in cx.execute("SELECT numero_oe_seq FROM ordem_entrega WHERE numero_oe_seq IS NOT NULL").fetchall()}
    print(f"📋  OEs já no banco: {len(ja_importadas)}")

    # Ler as duas planilhas
    fontes = []
    for path in [EXCEL_2019, EXCEL_2024]:
        if path.exists():
            print(f"📂  Lendo {path.name}…")
            fontes.append(pd.read_excel(path, sheet_name=None))
        else:
            print(f"⚠️   Arquivo não encontrado: {path}")

    agora = datetime.now().strftime("%Y-%m-%d %Human:%M:%S")
    inseridas = 0
    ignoradas  = 0
    sem_of     = 0
    sem_itens  = 0

    for planilha in fontes:
        for nome_aba, df in planilha.items():
            if nome_aba.strip() == "Plan1":
                continue

            oe = extrair_aba(nome_aba, df)
            if oe is None:
                sem_itens += 1
                continue

            seq = oe["num_oe_seq"]
            if seq and seq in ja_importadas:
                ignoradas += 1
                continue

            # Determinar of_id: primeiro item com OF conhecida
            of_id = None
            for it in oe["itens"]:
                of_id = ofs_map.get(it["num_of"])
                if of_id:
                    break

            if not of_id:
                # Tentar pelo oe_cod (número do pedido externo)
                sem_of += 1
                # Ainda assim inserimos — vinculado à primeira OF que aparecer ou NULL
                # mas precisamos de um of_id válido (FK obrigatória)
                # Vamos criar uma OF "fantasma" só se necessário, ou simplesmente pular
                if not oe["itens"]:
                    sem_itens += 1
                    continue
                # Tentar qualquer OF do banco como âncora (usar a primeira OF do banco)
                # Melhor: pular OEs sem OF vinculada para não poluir o banco
                continue

            # Dados do primeiro item para preencher a OE
            it0 = oe["itens"][0]
            total_qtd = sum(i["qtd"] for i in oe["itens"])
            total_val = sum(i["preco_total"] for i in oe["itens"])

            oe_id = str(uuid.uuid4())
            cx.execute(
                """INSERT INTO ordem_entrega
                   (id, ordem_fabricacao_id, numero_oe, qtd_pecas, observacao, criado_em,
                    numero_oe_seq, nome_cliente,
                    num_pedido, num_of_ref, referencia, liga, corrida,
                    certificado, cod_peca, descricao,
                    peso_unit, serie, preco_unit, preco_total)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    oe_id, of_id, oe["num_oe"], total_qtd,
                    oe["observacoes"], agora,
                    seq, oe["cliente"],
                    it0["num_pedido"], it0["num_of"],
                    it0["referencia"], it0["liga"],
                    it0["corrida"], it0["certificado"],
                    it0["cod_peca"], it0["descricao"],
                    it0["peso_unit"], it0["serie"],
                    it0["preco_unit"], total_val,
                ),
            )
            inseridas += 1
            ja_importadas.add(seq)

    cx.commit()
    cx.close()

    print(f"\n{'='*50}")
    print(f"✅  OEs inseridas:              {inseridas}")
    print(f"⏭️   Já existiam (ignoradas):    {ignoradas}")
    print(f"⚠️   Sem OF vinculada no banco:  {sem_of}")
    print(f"📭  Abas vazias (sem itens):    {sem_itens}")
    print(f"{'='*50}")
    print("Importação concluída!")


if __name__ == "__main__":
    importar()
