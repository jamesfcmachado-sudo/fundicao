from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Atualiza chamada das funcoes para incluir o logo
OLD = '''                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel(
                            template_bytes=_tmpl_bytes,
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                        )
                        from gerar_oe_excel import gerar_oe_pdf
                        _pdf_bytes = gerar_oe_pdf(
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                        )'''

NEW = '''                        # Busca logo ativo
                        _logo_bytes = None
                        try:
                            from empresa_config import get_logo_ativo_bytes
                            _logo_bytes = get_logo_ativo_bytes()
                        except Exception:
                            pass

                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel(
                            template_bytes=_tmpl_bytes,
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                            logo_bytes=_logo_bytes,
                        )
                        from gerar_oe_excel import gerar_oe_pdf
                        _pdf_bytes = gerar_oe_pdf(
                            numero_oe=str(_noe),
                            nome_cliente=_cliente_oe,
                            itens=_itens_lista,
                            observacoes=_obs_oe,
                            config=_cfg,
                            logo_bytes=_logo_bytes,
                        )'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Logo adicionado nas chamadas.")
else:
    print("AVISO: Texto nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'OE PDF com logo e calculos corretos' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
