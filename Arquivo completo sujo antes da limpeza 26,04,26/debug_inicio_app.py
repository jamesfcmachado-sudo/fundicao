from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Mostra as primeiras 30 linhas
print("Primeiras 30 linhas do app.py:")
for i, line in enumerate(lines[:30]):
    print(f"  {i+1}: {repr(line)}")
