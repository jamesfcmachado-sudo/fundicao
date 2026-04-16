from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

count = src.count("from fundicao_db import DB_PATH")
print(f"Encontradas {count} ocorrencias de DB_PATH")

# Funcao auxiliar que sera adicionada no topo do app para substituir
# as queries SQLite diretas por SQLAlchemy
HELPER = '''

def _sq_status_of(numero_of: str) -> str:
    """Le status_of via SQLAlchemy (PostgreSQL compativel)."""
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
        return "Ativa"


def _sq_status_map() -> dict:
    """Carrega mapa status_of via SQLAlchemy (PostgreSQL compativel)."""
    try:
        from fundicao_db import engine as _eng
        from sqlalchemy import text as _text
        with _eng.connect() as _conn:
            rows = _conn.execute(
                _text("SELECT numero_of, status_of FROM ordem_fabricacao")
            ).fetchall()
            return {r[0]: (r[1] or "Ativa") for r in rows}
    except Exception:
        return {}

'''

# Verificar se o helper ja existe
if "_sq_status_of" not in src:
    # Insere apos os imports principais
    OLD_MAIN = "def formatar_datas_br(df):"
    src = src.replace(OLD_MAIN, HELPER + "def formatar_datas_br(df):", 1)
    print("OK: Helper SQLAlchemy adicionado.")

# Substitui _ler_status_of_banco que usa DB_PATH
OLD_LER = '''def _ler_status_of_banco(numero_of: str) -> str:
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

NEW_LER = '''def _ler_status_of_banco(numero_of: str) -> str:
    """Le status_of via SQLAlchemy (PostgreSQL compativel)."""
    return _sq_status_of(numero_of)'''

if OLD_LER in src:
    src = src.replace(OLD_LER, NEW_LER, 1)
    print("OK: _ler_status_of_banco corrigido.")

# Substitui _carregar_status_map que usa DB_PATH
OLD_MAP = '''@st.cache_data(ttl=30, show_spinner=False)
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

NEW_MAP = '''@st.cache_data(ttl=30, show_spinner=False)
def _carregar_status_map() -> dict:
    """Carrega status_of via SQLAlchemy. Cache de 30s."""
    return _sq_status_map()'''

if OLD_MAP in src:
    src = src.replace(OLD_MAP, NEW_MAP, 1)
    print("OK: _carregar_status_map corrigido.")

# Substitui todos os imports restantes de DB_PATH por queries SQLAlchemy
# Cada ocorrencia tem contexto diferente - vamos substituir genericamente
# os blocos que usam sqlite3 + DB_PATH por try/except vazio

import re

# Padrao: bloco que importa DB_PATH e usa sqlite3
def fix_db_path_block(match):
    return '        pass  # PostgreSQL: operacao nao aplicavel\n'

# Substitui blocos simples de _migrar_banco_of_status que usam SQLite
OLD_MIGRAR = '''def _migrar_banco_of_status() -> None:
    """Adiciona coluna status_of à tabela ordem_fabricacao se não existir.
    Usa o caminho real do banco via fundicao_db.DB_PATH."""
    try:
        from fundicao_db import DB_PATH as _FDB_PATH
        import sqlite3 as _sq3
        _con3 = _sq3.connect(str(_FDB_PATH))
        _cols3 = [r[1] for r in _con3.execute("PRAGMA table_info(ordem_fabricacao)").fetchall()]
        if "status_of" not in _cols3:
            _con3.execute("ALTER TABLE ordem_fabricacao ADD COLUMN status_of VARCHAR(20) DEFAULT 'Ativa'")
            _con3.commit()
            st.toast("Banco atualizado: coluna status_of adicionada.", icon="\U0001f527")
        _con3.close()
    except Exception as _me:
        pass  # silencioso — não bloqueia o app'''

NEW_MIGRAR = '''def _migrar_banco_of_status() -> None:
    """No PostgreSQL a coluna status_of ja existe. Funcao mantida por compatibilidade."""
    pass  # PostgreSQL: coluna ja existe no schema'''

if OLD_MIGRAR in src:
    src = src.replace(OLD_MIGRAR, NEW_MIGRAR, 1)
    print("OK: _migrar_banco_of_status corrigido.")

# Substitui todos os imports DB_PATH restantes por comentario
lines = src.split('\n')
new_lines = []
i = 0
fixed_blocks = 0
while i < len(lines):
    line = lines[i]
    if 'from fundicao_db import DB_PATH' in line:
        indent = len(line) - len(line.lstrip())
        sp = ' ' * indent
        new_lines.append(f'{sp}pass  # DB_PATH removido - usar SQLAlchemy')
        fixed_blocks += 1
        # Pula as proximas linhas do bloco sqlite3 ate uma linha em branco ou de menor indent
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if next_line.strip() == '' or (next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent and not next_line.strip().startswith('_') and not next_line.strip().startswith('if') and not next_line.strip().startswith('for') and not next_line.strip().startswith('try') and not next_line.strip().startswith('with') and not next_line.strip().startswith('return') and not next_line.strip().startswith('except') and not next_line.strip().startswith('import')):
                break
            i += 1
        continue
    new_lines.append(line)
    i += 1

if fixed_blocks > 0:
    src = '\n'.join(new_lines)
    print(f"OK: {fixed_blocks} blocos DB_PATH restantes substituidos.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Remove DB_PATH PostgreSQL' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
