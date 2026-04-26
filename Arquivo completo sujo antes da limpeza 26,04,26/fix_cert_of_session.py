from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

OLD = '''        if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
            _of_data = _ofs_dict[_of_cert.strip()]
            st.success(f"✅ OF {_of_cert.strip()} — Cliente: {_of_data['cliente']}")
        else:
            _of_data = {"cliente": "", "norma": "", "liga": ""}'''

NEW = '''        if _of_cert.strip() and _of_cert.strip() in _ofs_dict:
            _of_data = _ofs_dict[_of_cert.strip()]
            st.session_state["_cert_of_data"] = _of_data
            st.success(f"✅ OF {_of_cert.strip()} — Cliente: {_of_data['cliente']}")
        elif st.session_state.get("_cert_of_data") and _of_cert.strip():
            _of_data = st.session_state["_cert_of_data"]
        else:
            _of_data = {"cliente": "", "norma": "", "liga": ""}
            if not _of_cert.strip():
                st.session_state.pop("_cert_of_data", None)'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Session_state para OF adicionado.")
else:
    print("AVISO: Bloco nao encontrado.")
    # Mostra o que tem
    idx = src.find("_of_data = _ofs_dict")
    print(repr(src[max(0,idx-50):idx+200]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix OF session_state certificado' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
