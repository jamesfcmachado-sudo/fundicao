from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Corrige: o try: precisa estar dentro do with st.expander
old = (
    '                            with st.expander("\u270f\ufe0f Alterar dados desta OF", expanded=False):\n'
    '                            try:\n'
)
new = (
    '                            with st.expander("\u270f\ufe0f Alterar dados desta OF", expanded=False):\n'
    '                             try:\n'
)

if old in src:
    src = src.replace(old, new, 1)
    print("OK: Indentacao do try corrigida!")
else:
    print("AVISO: Texto nao encontrado, verificando...")
    # Mostra as linhas ao redor para debug
    lines = src.split('\n')
    for i, line in enumerate(lines):
        if 'Alterar dados desta OF' in line:
            print(f"Linha {i}: {repr(line)}")
            print(f"Linha {i+1}: {repr(lines[i+1])}")
            print(f"Linha {i+2}: {repr(lines[i+2])}")

APP.write_text(src, encoding="utf-8")
print("Arquivo salvo!")
