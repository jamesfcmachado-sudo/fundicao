"""
app_pg_patch.py
===============
Aplica sobre o app.py original as duas correções necessárias para PostgreSQL:
  1. _ler_status_of_banco()  — usava sqlite3 + PRAGMA
  2. _carregar_status_map()  — usava sqlite3 + PRAGMA

Execute UMA VEZ para gerar o app.py final compatível com Supabase:
    python app_pg_patch.py
"""

from pathlib import Path

APP = Path("app.py")
BAK = Path("app_pg_backup.py")

OLD_LER = '''\
def _ler_status_of_banco(numero_of: str) -> str:
    """Lê status_of diretamente do banco via SQL — bypass total do ORM."""
    try:
        import sqlite3 as _sq
        from fundicao_db import DB_PATH as _FP
        _cx = _sq.connect(str(_FP))
        _cols = [r[1] for r in _cx.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]
        if "status_of" in _cols:
            _r = _cx.execute(
                "SELECT status_of FROM ordem_fabricacao WHERE numero_of=?", (numero_of,)
            ).fetchone()
            _cx.close()
            return (_r[0] or "Ativa") if _r else "Ativa"
        _cx.close()
    except Exception:
        pass
    return "Ativa"'''

NEW_LER = '''\
def _ler_status_of_banco(numero_of: str) -> str:
    """Lê status_of diretamente do banco via SQLAlchemy (PostgreSQL compatível)."""
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text
        with _eng.connect() as _conn:
            _r = _conn.execute(
                _text("SELECT status_of FROM ordem_fabricacao WHERE numero_of = :n"),
                {"n": numero_of},
            ).fetchone()
            return (_r[0] or "Ativa") if _r else "Ativa"
    except Exception:
        pass
    return "Ativa"'''

OLD_MAP = '''\
@st.cache_data(ttl=30, show_spinner=False)
def _carregar_status_map() -> dict:
    """Carrega status_of de todas as OFs em uma única query SQL. Cache de 30s."""
    try:
        import sqlite3 as _sq
        from fundicao_db import DB_PATH as _FP
        _cx = _sq.connect(str(_FP))
        _cols = [r[1] for r in _cx.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]
        if "status_of" in _cols:
            _map = {r[0]: (r[1] or "Ativa") for r in
                    _cx.execute("SELECT numero_of, status_of FROM ordem_fabricacao").fetchall()}
        else:
            _map = {}
        _cx.close()
        return _map
    except Exception:
        return {}'''

NEW_MAP = '''\
@st.cache_data(ttl=30, show_spinner=False)
def _carregar_status_map() -> dict:
    """Carrega status_of de todas as OFs em uma única query (PostgreSQL compatível). Cache de 30s."""
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text
        with _eng.connect() as _conn:
            rows = _conn.execute(
                _text("SELECT numero_of, status_of FROM ordem_fabricacao")
            ).fetchall()
            return {r[0]: (r[1] or "Ativa") for r in rows}
    except Exception:
        return {}'''

# Também remove o import sqlite3 que está no topo do app (não é mais necessário)
OLD_IMPORT = "import sqlite3\n"
NEW_IMPORT = "# sqlite3 removido — agora usa PostgreSQL via SQLAlchemy\n"

src = APP.read_text(encoding="utf-8")

if "_sq.connect" not in src:
    print("⚠️  app.py já parece estar adaptado para PostgreSQL. Nenhuma alteração feita.")
else:
    BAK.write_text(src, encoding="utf-8")
    print(f"✅  Backup salvo em: {BAK}")

    src = src.replace(OLD_LER, NEW_LER, 1)
    src = src.replace(OLD_MAP, NEW_MAP, 1)
    src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)

    APP.write_text(src, encoding="utf-8")
    print("✅  app.py atualizado com sucesso para PostgreSQL!")
    print("   Funções alteradas:")
    print("     • _ler_status_of_banco()  → usa SQLAlchemy engine")
    print("     • _carregar_status_map()  → usa SQLAlchemy engine")
    print("     • import sqlite3 removido do topo")
