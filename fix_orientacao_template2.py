from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona configuracao de impressao apos gerar Excel
OLD = '''                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel('''

NEW = '''                        from gerar_oe_excel import configurar_impressao_excel
                        _orientacao = _cfg.get("orientacao", "Paisagem")
                        _tmpl_bytes = _b64mod.b64decode(_tmpl_b64)
                        _excel_bytes = gerar_oe_excel('''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Import configurar_impressao_excel adicionado.")
else:
    print("AVISO: Nao encontrado.")

# Adiciona chamada de configurar_impressao_excel apos gerar Excel
OLD2 = '''                        orient = _cfg.get("orientacao", "Paisagem")
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} (.xlsx) — {orient}",
                            data=_excel_bytes,'''

NEW2 = '''                        _excel_bytes = configurar_impressao_excel(
                            _excel_bytes, _orientacao)
                        orient = _cfg.get("orientacao", "Paisagem")
                        st.download_button(
                            f"\u2b07\ufe0f Baixar OE {_noe} (.xlsx) — {orient}",
                            data=_excel_bytes,'''

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("OK: configurar_impressao_excel aplicado.")
else:
    print("AVISO: Botao download nao encontrado.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Excel paisagem para PDF' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
