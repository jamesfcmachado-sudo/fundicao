from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Adiciona comentario no topo para forcar novo deploy
if "# redeploy-mover-alterar" not in src:
    src = "# redeploy-mover-alterar\n" + src
    APP.write_text(src, encoding="utf-8")
    print("OK: Forcando redeploy.")
else:
    print("Ja tem o comentario.")

# Verifica se alterar/excluir esta na Nova OE
if "Gerenciar OE existente" in src:
    print("OK: Alterar/Excluir JA esta na Nova OE.")
else:
    print("AVISO: Alterar/Excluir NAO esta na Nova OE!")

# Verifica se alterar/excluir ainda esta na Consulta de OEs
if 'with st.expander(f"✏️ Alterar OE {num_oe_sel}"' in src:
    print("AVISO: Alterar ainda esta na Consulta de OEs!")
else:
    print("OK: Alterar NAO esta mais na Consulta de OEs.")

if 'with st.expander(f"🗑️ Excluir OE {num_oe_sel}"' in src:
    print("AVISO: Excluir ainda esta na Consulta de OEs!")
else:
    print("OK: Excluir NAO esta mais na Consulta de OEs.")
