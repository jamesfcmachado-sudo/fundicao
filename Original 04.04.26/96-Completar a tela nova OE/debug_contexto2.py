from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

print("Linhas 3600-3676:")
for i in range(3599, 3676):
    print(f"  {i+1}: {repr(lines[i])}")
