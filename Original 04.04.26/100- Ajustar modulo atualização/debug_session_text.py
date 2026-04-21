from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

for key in ["_df_imp_ofs", "_df_imp_corridas", "_df_atualizar_corridas"]:
    idx = src.find(f'st.session_state.get("{key}"')
    if idx > 0:
        print(f"=== {key} ===")
        print(repr(src[idx:idx+200]))
        print()
