from pathlib import Path

APP = Path("app.py")
lines = APP.read_text(encoding="utf-8").split('\n')

# Mostra linhas ao redor do erro
print("Linhas 3660-3670:")
for i in range(3659, 3670):
    print(f"  {i+1}: {repr(lines[i])}")

# Encontra a linha com o iframe problemático
for i, line in enumerate(lines):
    if "iframe" in line and "border-radius:8px" in line:
        print(f"\nLinha {i+1} com iframe: {repr(line)}")
        # Mostra contexto
        for j in range(max(0,i-5), min(len(lines),i+10)):
            print(f"  {j+1}: {repr(lines[j])}")
        break
