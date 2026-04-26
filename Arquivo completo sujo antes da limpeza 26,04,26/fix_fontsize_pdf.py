from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''    def ph(t, **kw): return Paragraph(t, PS("h", fontSize=8,
        fontName="Helvetica-Bold", alignment=TA_CENTER, **kw))
    def pc(t, **kw): return Paragraph(str(t or ""), PS("c", fontSize=8,
        fontName="Helvetica", alignment=TA_CENTER, **kw))
    def pl(t, **kw): return Paragraph(str(t or ""), PS("l", fontSize=8,
        fontName="Helvetica", alignment=TA_LEFT, **kw))
    def pb(t, **kw): return Paragraph(str(t or ""), PS("b", fontSize=8,
        fontName="Helvetica-Bold", alignment=TA_LEFT, **kw))'''

NEW = '''    def ph(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica-Bold")
        kw.setdefault("alignment", TA_CENTER)
        return Paragraph(t, PS("h", **kw))
    def pc(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("alignment", TA_CENTER)
        return Paragraph(str(t or ""), PS("c", **kw))
    def pl(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("alignment", TA_LEFT)
        return Paragraph(str(t or ""), PS("l", **kw))
    def pb(t, **kw):
        kw.setdefault("fontSize", 8)
        kw.setdefault("fontName", "Helvetica-Bold")
        kw.setdefault("alignment", TA_LEFT)
        return Paragraph(str(t or ""), PS("b", **kw))'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Funcoes helper PDF corrigidas.")
else:
    print("AVISO: Bloco nao encontrado.")
    # Tenta localizar
    idx = src.find("def ph(t, **kw)")
    print(repr(src[max(0,idx-50):idx+300]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix fontSize PDF certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
