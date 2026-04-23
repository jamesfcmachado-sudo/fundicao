from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

if "logo_certificado" in src:
    idx = src.find("logo_certificado")
    print("OK: Encontrado!")
    print(repr(src[max(0,idx-100):idx+200]))
else:
    print("AVISO: 'logo_certificado' NAO encontrado no arquivo!")
    print(f"Tamanho do arquivo: {len(src)} chars")
