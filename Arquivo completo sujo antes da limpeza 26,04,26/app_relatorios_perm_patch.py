"""
app_relatorios_perm_patch.py
============================
Adiciona verificações de permissão dentro da página de Relatórios.
Execute na pasta do projeto:
    python app_relatorios_perm_patch.py
"""

from pathlib import Path

APP = Path("app.py")
BAK = Path("app_relatorios_perm_backup.py")

src = APP.read_text(encoding="utf-8")

if "relatorios_alterar_of" in src:
    print("Patch ja aplicado. Nenhuma alteracao feita.")
    exit(0)

BAK.write_text(src, encoding="utf-8")
print(f"Backup salvo em: {BAK}")

alteracoes = 0

# 1) Proteger "Alterar dados desta OF"
lines = src.split('\n')
new_lines = []
for line in lines:
    if 'Alterar dados desta OF' in line and 'expander' in line:
        indent = len(line) - len(line.lstrip())
        spaces = ' ' * indent
        new_lines.append(f'{spaces}if not tem_permissao("relatorios_alterar_of"):')
        new_lines.append(f'{spaces}    st.info("Sem permissao para alterar OFs.")')
        new_lines.append(f'{spaces}elif True:')
        new_lines.append(line)
        alteracoes += 1
        print("OK: Alterar OF protegido.")
    else:
        new_lines.append(line)
src = '\n'.join(new_lines)

# 2) Proteger "Alterar dados desta corrida"
lines = src.split('\n')
new_lines = []
for line in lines:
    if 'Alterar dados desta corrida' in line and 'expander' in line:
        indent = len(line) - len(line.lstrip())
        spaces = ' ' * indent
        new_lines.append(f'{spaces}if not tem_permissao("relatorios_alterar_corrida"):')
        new_lines.append(f'{spaces}    st.info("Sem permissao para alterar corridas.")')
        new_lines.append(f'{spaces}elif True:')
        new_lines.append(line)
        alteracoes += 1
        print("OK: Alterar Corrida protegido.")
    else:
        new_lines.append(line)
src = '\n'.join(new_lines)

# 3) Proteger tab4 Configuracoes - inserir verificacao apos "with tab4:"
lines = src.split('\n')
new_lines = []
i = 0
while i < len(lines):
    new_lines.append(lines[i])
    if '    with tab4:' in lines[i]:
        # Insere verificacao logo apos o with tab4:
        new_lines.append('        if not tem_permissao("configuracoes"):')
        new_lines.append('            st.warning("Voce nao tem permissao para acessar as Configuracoes.")')
        new_lines.append('            st.stop()')
        alteracoes += 1
        print("OK: Configuracoes protegidas.")
    i += 1
src = '\n'.join(new_lines)

APP.write_text(src, encoding="utf-8")
print(f"\nTotal: {alteracoes} protecoes adicionadas!")
print("\nAgora rode:")
print("  git add .")
print('  git commit -m "Permissoes nos relatorios"')
print("  git push")
