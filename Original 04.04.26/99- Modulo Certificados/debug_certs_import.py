from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

# Verifica o que tem nos imports
idx_streamlit = src.find("import streamlit as st")
print(f"'import streamlit as st' na posicao: {idx_streamlit}")
print(repr(src[idx_streamlit:idx_streamlit+300]))
