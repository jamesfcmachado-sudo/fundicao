from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

for key in ["btn_confirmar_atualizar_corridas", "btn_confirmar_ofs", 
            "btn_confirmar_corridas", "btn_confirmar_oes",
            "btn_atualizar_oes", "btn_confirmar_certs", "btn_atualizar_certs"]:
    idx = src.find(f'key="{key}"')
    if idx > 0:
        print(f"=== {key} ===")
        print(repr(src[max(0,idx-200):idx+50]))
        print()
    else:
        print(f"NAO ENCONTRADO: {key}")
