"""
Importação histórica de Ordens de Entrega — versão 2 (uma linha por item).

Cria a tabela oe_item no banco e importa cada linha individualmente.
Seguro para rodar múltiplas vezes (apaga e reimporta).

USO:
    python importar_oes_historicas.py
"""

import re, sqlite3, uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR   = Path(__file__).parent
DB_PATH    = BASE_DIR / "fundicao.db"
EXCEL_2019 = BASE_DIR / "Ordem_de_Entrega_2019_a_2023.xlsx"
EXCEL_2024 = BASE_DIR / "Ordem_de_Entrega_2024_a_2026.xlsx"


# ── Criar / recriar tabela oe_item ────────────────────────────────────────────
DDL_OE_ITEM = """
CREATE TABLE IF NOT EXISTS oe_item (
    id            TEXT PRIMARY KEY,
    numero_oe     TEXT NOT NULL,
    num_oe_seq    INTEGER,
    nome_cliente  TEXT,
    num_pedido    TEXT,
    num_of        TEXT,
    referencia    TEXT,
    liga          TEXT,
    corrida       TEXT,
    certificado   TEXT,
    cod_peca      TEXT,
    descricao     TEXT,
    peso_unit     REAL,
    qtd           INTEGER,
    serie         TEXT,
    preco_unit    REAL,
    preco_total   REAL,
    observacoes   TEXT,
    criado_em     TEXT
)
"""


# ── Extração de uma aba ────────────────────────────────────────────────────────
def extrair_aba(nome_aba: str, df: pd.DataFrame) -> dict | None:
    vals = list(df.values)
    if len(vals) < 16:
        return None

    header_row = vals[3] if len(vals) > 3 else []

    num_oe = None
    for v in header_row:
        if str(v).startswith("Nº "):
            num_oe = str(v).replace("Nº ", "").strip()
            break

    # Código (707-52) → num_oe_seq, qtd_total_codigo
    oe_num_codigo = None
    for v in header_row:
        m = re.search(r"\((\d+)-(\d+)\)", str(v))
        if m:
            oe_num_codigo = m.group(1)
            break

    cliente_row = vals[15] if len(vals) > 15 else []
    cliente = ""
    if len(cliente_row) > 2 and str(cliente_row[2]) not in ("nan", ""):
        cliente = str(cliente_row[2]).strip()

    obs = ""
    for row in vals[35:42]:
        v1 = str(row[1]) if len(row) > 1 else "nan"
        if v1 not in ("nan", "") and "Carregado" not in v1:
            obs = v1.strip().lstrip("- ").strip()
            break

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
        return None

    try:
        num_oe_seq = int(nome_aba.strip()) if nome_aba.strip().isdigit() else None
    except Exception:
        num_oe_seq = None

    return {
        "num_oe":      num_oe or nome_aba.strip(),
        "num_oe_seq":  num_oe_seq,
        "cliente":     cliente,
        "observacoes": obs,
        "itens":       itens,
    }


# ── Importação ─────────────────────────────────────────────────────────────────
def importar():
    if not DB_PATH.exists():
        print(f"❌  Banco não encontrado: {DB_PATH}")
        return

    cx = sqlite3.connect(DB_PATH)

    # Criar tabela oe_item (se não existir) e limpar para reimportar
    cx.execute(DDL_OE_ITEM)
    cx.execute("DELETE FROM oe_item")
    cx.commit()
    print("✅  Tabela oe_item pronta.")

    # Carregar OFs do banco {numero_of → id}
    ofs_map = {r[0]: r[1] for r in cx.execute("SELECT numero_of, id FROM ordem_fabricacao").fetchall()}
    print(f"📋  OFs no banco: {len(ofs_map)}")

    fontes = []
    for path in [EXCEL_2019, EXCEL_2024]:
        if path.exists():
            print(f"📂  Lendo {path.name}…")
            fontes.append(pd.read_excel(path, sheet_name=None))
        else:
            print(f"⚠️   Não encontrado: {path.name}")

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inseridas    = 0
    oes_ok       = 0
    oes_sem_of   = 0
    oes_vazias   = 0

    for planilha in fontes:
        for nome_aba, df in planilha.items():
            if nome_aba.strip() == "Plan1":
                continue

            oe = extrair_aba(nome_aba, df)
            if oe is None or not oe["itens"]:
                oes_vazias += 1
                continue

            tem_alguma_of = any(ofs_map.get(it["num_of"]) for it in oe["itens"])
            if not tem_alguma_of:
                oes_sem_of += 1
                continue

            oes_ok += 1
            for it in oe["itens"]:
                cx.execute(
                    """INSERT INTO oe_item
                       (id, numero_oe, num_oe_seq, nome_cliente,
                        num_pedido, num_of, referencia, liga, corrida,
                        certificado, cod_peca, descricao,
                        peso_unit, qtd, serie, preco_unit, preco_total,
                        observacoes, criado_em)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        oe["num_oe"], oe["num_oe_seq"], oe["cliente"],
                        it["num_pedido"], it["num_of"],
                        it["referencia"], it["liga"], it["corrida"],
                        it["certificado"], it["cod_peca"], it["descricao"],
                        it["peso_unit"], it["qtd"], it["serie"],
                        it["preco_unit"], it["preco_total"],
                        oe["observacoes"], agora,
                    ),
                )
                inseridas += 1

    cx.commit()
    cx.close()

    print(f"\n{'='*50}")
    print(f"✅  Linhas de itens inseridas:  {inseridas}")
    print(f"📦  OEs importadas:             {oes_ok}")
    print(f"⚠️   OEs sem OF no banco:        {oes_sem_of}")
    print(f"📭  Abas vazias:                {oes_vazias}")
    print(f"{'='*50}")
    print("Importação concluída!")


if __name__ == "__main__":
    importar()
