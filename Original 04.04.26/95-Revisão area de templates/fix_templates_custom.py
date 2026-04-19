from pathlib import Path
import json

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

if "Templates Personalizados" in src:
    print("Ja aplicado!")
    exit(0)

# Adiciona secao de templates personalizados no final da aba tab5
OLD_END = '''            if _up_cert:
                import base64
                _b64 = base64.b64encode(_up_cert.read()).decode()
                set_config("template_cert_base64", _b64)
                set_config("template_cert_nome", _up_cert.name)
                st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
                st.rerun()
'''

NEW_END = '''            if _up_cert:
                import base64
                _b64 = base64.b64encode(_up_cert.read()).decode()
                set_config("template_cert_base64", _b64)
                set_config("template_cert_nome", _up_cert.name)
                st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
                st.rerun()

        # ── TEMPLATES PERSONALIZADOS ──────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### ➕ Templates Personalizados")
            st.caption("Cadastre templates extras para futuras funcionalidades do sistema.")

            # Carrega lista de templates personalizados
            import json as _json
            try:
                _tmpls_custom = _json.loads(get_config("templates_custom", "[]"))
            except Exception:
                _tmpls_custom = []

            # Lista templates existentes
            if _tmpls_custom:
                st.markdown("**Templates cadastrados:**")
                for _idx_t, _tmpl in enumerate(_tmpls_custom):
                    with st.container(border=True):
                        _tc1, _tc2, _tc3 = st.columns([3,1,1])
                        with _tc1:
                            st.markdown(f"**{_tmpl.get('nome','Sem nome')}**")
                            st.caption(f"Responsável: {_tmpl.get('responsavel','—')} | Orientação: {_tmpl.get('orientacao','Retrato')}")
                        with _tc2:
                            if _tmpl.get("base64"):
                                import base64 as _b64m
                                st.download_button(
                                    "⬇️ Baixar",
                                    data=_b64m.b64decode(_tmpl["base64"]),
                                    file_name=_tmpl.get("arquivo","template.xlsx"),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"dl_custom_{_idx_t}"
                                )
                        with _tc3:
                            if st.button("🗑️ Remover", key=f"rm_custom_{_idx_t}"):
                                _tmpls_custom.pop(_idx_t)
                                set_config("templates_custom", _json.dumps(_tmpls_custom))
                                st.rerun()

                st.divider()

            # Formulario para novo template
            st.markdown("**Adicionar novo template:**")
            _nc1, _nc2 = st.columns(2)
            with _nc1:
                _novo_nome = st.text_input(
                    "Nome do template *",
                    placeholder="Ex: Ficha de Inspeção, Ordem de Compra...",
                    key="novo_tmpl_nome"
                )
                _novo_resp = st.text_input(
                    "👤 Responsável",
                    value=get_config("contato",""),
                    key="novo_tmpl_resp"
                )
            with _nc2:
                _novo_orient = st.radio(
                    "📐 Orientação",
                    options=["Retrato", "Paisagem"],
                    horizontal=True,
                    key="novo_tmpl_orient"
                )

            _novo_arquivo = st.file_uploader(
                "📤 Carregar template (.xlsx)",
                type=["xlsx"],
                key="upload_tmpl_custom"
            )

            if st.button("✅ Adicionar template", key="btn_add_custom", type="primary"):
                if not _novo_nome.strip():
                    st.error("Informe o nome do template.")
                elif not _novo_arquivo:
                    st.error("Selecione o arquivo .xlsx do template.")
                else:
                    import base64
                    _b64_new = base64.b64encode(_novo_arquivo.read()).decode()
                    _novo_tmpl = {
                        "nome":        _novo_nome.strip(),
                        "responsavel": _novo_resp.strip(),
                        "orientacao":  _novo_orient,
                        "arquivo":     _novo_arquivo.name,
                        "base64":      _b64_new,
                    }
                    _tmpls_custom.append(_novo_tmpl)
                    set_config("templates_custom", _json.dumps(_tmpls_custom))
                    st.success(f"✅ Template '{_novo_nome}' adicionado!")
                    st.rerun()
'''

if OLD_END in src:
    src = src.replace(OLD_END, NEW_END, 1)
    print("OK: Secao de templates personalizados adicionada.")
else:
    print("AVISO: Bloco nao encontrado.")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Templates personalizados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
