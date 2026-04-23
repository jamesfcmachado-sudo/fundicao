from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

idx = src.find("orient_cert")
print(repr(src[max(0,idx-50):idx+300]))
