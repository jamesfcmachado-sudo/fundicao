from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")
lines = src.split('\n')

# Mostra contexto ao redor das linhas chave
def show_context(keyword, n=3):
    for i, line in enumerate(lines):
        if keyword in line:
            print(f"\n=== Linha {i+1}: {repr(line)} ===")
            for j in range(max(0,i-n), min(len(lines),i+n+1)):
                print(f"  {j+1}: {repr(lines[j])}")

show_context("Histórico de OEs emitidas")
show_context("Historico removido")
show_context("btn_pdf_cons")
show_context("Gerar PDF desta OE")
