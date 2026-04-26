from pathlib import Path
import re

CFG = Path("empresa_config.py")
lines = CFG.read_text(encoding="utf-8").split('\n')

print(f"Total de linhas: {len(lines)}")
print("\nLinhas 620-622 (fim do arquivo):")
for i in range(619, len(lines)):
    print(f"  {i+1}: {repr(lines[i])}")

# O erro diz linha 629 mas o arquivo tem 622 linhas
# Isso significa que o Streamlit Cloud ainda tem o arquivo antigo
# Vamos verificar se o empresa_config.py foi realmente atualizado no GitHub
print(f"\nUltimas 10 linhas do arquivo:")
for i, l in enumerate(lines[-10:]):
    print(f"  {len(lines)-9+i}: {repr(l)}")
