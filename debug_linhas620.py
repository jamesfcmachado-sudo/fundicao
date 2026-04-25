from pathlib import Path

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

print(f"Total de linhas: {len(lines)}")
print("\nLinhas 615-670:")
for i in range(614, min(670, len(lines))):
    print(f"  {i+1}: {repr(lines[i])}")
