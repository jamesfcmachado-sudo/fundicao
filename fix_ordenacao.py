from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

changes = 0

# 1) OFs no Relatorio — muda ascending True,True para False,False
OLD1 = ('                df = df.sort_values(\n'
        '                    by=["_sort_ano", "_sort_of"],\n'
        '                    ascending=[True, True],\n'
        '                    na_position="last",\n'
        '                ).drop(columns=["_sort_ano", "_sort_of"]).reset_index(drop=True)')

NEW1 = ('                df = df.sort_values(\n'
        '                    by=["_sort_ano", "_sort_of"],\n'
        '                    ascending=[False, False],\n'
        '                    na_position="last",\n'
        '                ).drop(columns=["_sort_ano", "_sort_of"]).reset_index(drop=True)')

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes += 1
    print("OK: OFs ordenadas do mais recente para o mais antigo.")
else:
    print("AVISO: Ordenacao de OFs nao encontrada.")

# 2) Corridas no Relatorio — muda ascending True,True para False,False
OLD2 = ('                df = df.sort_values(\n'
        '                    by=["_sort_data", "_sort_corrida"],\n'
        '                    ascending=[True, True],\n'
        '                    na_position="last",\n'
        '                ).drop(columns=["_sort_data", "_sort_corrida"]).reset_index(drop=True)')

NEW2 = ('                df = df.sort_values(\n'
        '                    by=["_sort_data", "_sort_corrida"],\n'
        '                    ascending=[False, False],\n'
        '                    na_position="last",\n'
        '                ).drop(columns=["_sort_data", "_sort_corrida"]).reset_index(drop=True)')

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    changes += 1
    print("OK: Corridas ordenadas do mais recente para o mais antigo.")
else:
    print("AVISO: Ordenacao de Corridas nao encontrada.")

# 3) Dashboard — a query ja usa criado_em.desc() mas vamos garantir
# que o DataFrame tambem esteja ordenado por data decrescente
OLD3 = ('        abertas_list   = [of for of in todas_completas\n'
        '                          if _status_of_rapido(of, _smap) in\n'
        '                          ("Aberta", "Expedição parcial", "Sem qtd. pedido", "Cancelada")]')
NEW3 = ('        abertas_list   = sorted(\n'
        '            [of for of in todas_completas\n'
        '             if _status_of_rapido(of, _smap) in\n'
        '             ("Aberta", "Expedição parcial", "Sem qtd. pedido", "Cancelada")],\n'
        '            key=lambda x: x.criado_em or datetime.min,\n'
        '            reverse=True\n'
        '        )')

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes += 1
    print("OK: Dashboard ordenado do mais recente para o mais antigo.")
else:
    print("AVISO: Lista abertas_list nao encontrada.")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print(f"\nSINTAXE OK! {changes} alteracoes feitas.")
    print("Rode: git add . && git commit -m 'Ordenar tabelas mais recentes primeiro' && git push")
except py_compile.PyCompileError as e:
    print(f"\nERRO: {e}")
finally:
    os.unlink(tmp)
