from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

print("Buscando bloco da aba Templates...")

# Encontra o inicio da aba tab5
idx_tab5 = src.find("# ── ABA 5: Templates")
if idx_tab5 == -1:
    idx_tab5 = src.find("with tab5:")
    
print(f"Aba tab5 encontrada na posicao: {idx_tab5}")
if idx_tab5 > 0:
    print(repr(src[idx_tab5:idx_tab5+200]))

# Mostra as ultimas 50 linhas do arquivo para entender a estrutura
lines = src.split('\n')
print(f"\nTotal de linhas: {len(lines)}")
print("\nUltimas 30 linhas:")
for i, line in enumerate(lines[-30:], len(lines)-30):
    print(f"{i+1}: {repr(line)}")
