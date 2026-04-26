from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Mostra linhas 3640-3675 para ver o contexto completo
print("Contexto completo:")
for i in range(3639, 3675):
    print(f"  {i+1}: {repr(lines[i])}")
