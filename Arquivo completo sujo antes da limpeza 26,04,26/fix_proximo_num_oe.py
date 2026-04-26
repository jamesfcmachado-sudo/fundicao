from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

OLD = '''    # ── Carregar próximo número sequencial via PostgreSQL ───────────────────
    try:
        from fundicao_db import engine as _eng_oe
        from sqlalchemy import text as _text_oe
        with _eng_oe.connect() as _conn_oe:
            _row = _conn_oe.execute(_text_oe(
                "SELECT MAX(CAST(numero_oe AS INTEGER)) FROM ordem_entrega "
                "WHERE numero_oe ~ '^[0-9]+$'"
            )).fetchone()
            proximo_num = (_row[0] or 1628) + 1
    except Exception:
        proximo_num = 1629'''

NEW = '''    # ── Carregar próximo número sequencial via PostgreSQL ───────────────────
    try:
        from fundicao_db import engine as _eng_oe
        from sqlalchemy import text as _text_oe
        with _eng_oe.connect() as _conn_oe:
            # Busca o maior numero entre ordem_entrega e oe_item
            _row = _conn_oe.execute(_text_oe("""
                SELECT GREATEST(
                    COALESCE((SELECT MAX(CAST(numero_oe AS INTEGER))
                              FROM ordem_entrega
                              WHERE numero_oe ~ '^[0-9]+$'), 0),
                    COALESCE((SELECT MAX(CAST(numero_oe AS INTEGER))
                              FROM oe_item
                              WHERE numero_oe ~ '^[0-9]+$'), 0)
                )
            """)).fetchone()
            proximo_num = (_row[0] or 1628) + 1
    except Exception:
        proximo_num = 1629'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Proximo numero OE corrigido.")
else:
    print("AVISO: Bloco nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Proximo numero OE correto' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
