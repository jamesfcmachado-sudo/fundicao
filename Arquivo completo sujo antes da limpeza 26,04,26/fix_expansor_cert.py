from pathlib import Path

CERT = Path("certificados.py")
src = CERT.read_text(encoding="utf-8")

# O expansor esta com indentacao de 4 espaços (dentro do if button salvar)
# Precisa estar com indentacao de 0 (no nivel da funcao)

OLD = '''        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    with st.expander("🔧 Alterar ou Excluir Certificado Existente"):'''

NEW = '''        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # ── Alterar / Excluir Certificado ─────────────────────────────────────────
    st.divider()
    st.subheader("🔧 Alterar ou Excluir Certificado Existente")
    with st.expander("Clique para buscar um certificado", expanded=False):'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("OK: Expansor ajustado.")
else:
    print("AVISO: Bloco nao encontrado.")
    # Mostra contexto
    idx = src.find("Alterar / Excluir Certificado")
    print(repr(src[max(0,idx-100):idx+200]))

CERT.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Fix expansor alterar cert' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
