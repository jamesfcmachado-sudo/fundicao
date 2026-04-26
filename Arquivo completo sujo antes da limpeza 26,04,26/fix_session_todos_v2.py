from pathlib import Path

APP = Path("app.py")
src = APP.read_text(encoding="utf-8")

fixes = [
    # Atualizar Corridas
    (
        'if not st.button("Confirmar atualizacao de Corridas", key="btn_confirmar_atualizar_corridas"):\n        return',
        'st.session_state["_df_atualizar_corridas"] = df\n    if not st.button("✅ Confirmar atualização de Corridas", key="btn_confirmar_atualizar_corridas", type="primary"):\n        return\n    df = st.session_state.get("_df_atualizar_corridas", df)'
    ),
    # Importar OFs
    (
        'if not st.button("✅ Confirmar importação de OFs", key="btn_confirmar_ofs"):\n        return',
        'st.session_state["_df_imp_ofs"] = df\n    if not st.button("✅ Confirmar importação de OFs", key="btn_confirmar_ofs", type="primary"):\n        return\n    df = st.session_state.get("_df_imp_ofs", df)'
    ),
    # Importar Corridas
    (
        'if not st.button("✅ Confirmar importação de Corridas", key="btn_confirmar_corridas"):\n        return',
        'st.session_state["_df_imp_corridas"] = df\n    if not st.button("✅ Confirmar importação de Corridas", key="btn_confirmar_corridas", type="primary"):\n        return\n    df = st.session_state.get("_df_imp_corridas", df)'
    ),
    # Importar OEs
    (
        'if not st.button("✅ Confirmar importação de OEs", key="btn_confirmar_oes"):\n        return',
        'st.session_state["_df_imp_oes"] = df\n    if not st.button("✅ Confirmar importação de OEs", key="btn_confirmar_oes", type="primary"):\n        return\n    df = st.session_state.get("_df_imp_oes", df)'
    ),
    # Atualizar OEs
    (
        'if not st.button("✅ Confirmar atualização de OEs", key="btn_atualizar_oes"):\n        return',
        'st.session_state["_df_atu_oes"] = df\n    if not st.button("✅ Confirmar atualização de OEs", key="btn_atualizar_oes", type="primary"):\n        return\n    df = st.session_state.get("_df_atu_oes", df)'
    ),
    # Importar Certificados
    (
        'if not st.button("✅ Confirmar importação de Certificados", key="btn_confirmar_certs"):\n        return',
        'st.session_state["_df_imp_certs"] = df\n    if not st.button("✅ Confirmar importação de Certificados", key="btn_confirmar_certs", type="primary"):\n        return\n    df = st.session_state.get("_df_imp_certs", df)'
    ),
    # Atualizar Certificados
    (
        'if not st.button("✅ Confirmar atualização de Certificados", key="btn_atualizar_certs"):\n        return',
        'st.session_state["_df_atu_certs"] = df\n    if not st.button("✅ Confirmar atualização de Certificados", key="btn_atualizar_certs", type="primary"):\n        return\n    df = st.session_state.get("_df_atu_certs", df)'
    ),
]

for old, new in fixes:
    if old in src:
        src = src.replace(old, new, 1)
        print(f"OK: {old[:50]}...")
    else:
        print(f"AVISO: Nao encontrado: {old[:50]}...")

APP.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix session_state todos importadores' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
