from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Encontra o inicio da aba tab5
idx_inicio = src.find("    # ── ABA 5: Templates")
if idx_inicio == -1:
    print("ERRO: Aba Templates nao encontrada!")
    exit(1)

# O bloco da aba vai ate o final da funcao (ultimo caractere)
bloco_antigo = src[idx_inicio:]

NOVO_BLOCO = '''    # fix_templates_v2
    # ── ABA 5: Templates ──────────────────────────────────────────────────────
    with tab5:
        st.subheader("📋 Templates de documentos")
        st.caption("Configure os templates Excel para geração automática de documentos.")

        # ── TEMPLATE OE ──────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📦 Ordem de Entrega (OE)")

            _c1, _c2 = st.columns([3,1])
            with _c1:
                _resp_oe = st.text_input(
                    "👤 Responsável pela OE",
                    value=get_config("template_oe_responsavel", get_config("contato")),
                    placeholder="Nome que aparecerá no campo Contato do documento",
                    key="resp_oe_input"
                )
            with _c2:
                st.write("")
                st.write("")
                if st.button("💾 Salvar", key="btn_resp_oe"):
                    set_config("template_oe_responsavel", _resp_oe)
                    st.success("✅ Salvo!")

            st.divider()

            _orient_oe = st.radio(
                "📐 Orientação de impressão",
                options=["Paisagem", "Retrato"],
                index=0 if get_config("template_oe_orientacao", "Paisagem") == "Paisagem" else 1,
                horizontal=True,
                key="orient_oe_radio"
            )
            if st.button("💾 Salvar orientação OE", key="btn_save_orient_oe"):
                set_config("template_oe_orientacao", _orient_oe)
                st.success(f"✅ Orientação OE: {_orient_oe}")

            st.divider()

            _oe_tmpl_b64 = get_config("template_oe_base64", "")
            _oe_tmpl_nome = get_config("template_oe_nome", "")
            if _oe_tmpl_b64:
                st.success(f"✅ Template atual: **{_oe_tmpl_nome}**")
                _dl1, _dl2 = st.columns(2)
                with _dl1:
                    import base64 as _b64mod
                    st.download_button(
                        "⬇️ Baixar template OE atual",
                        data=_b64mod.b64decode(_oe_tmpl_b64),
                        file_name=_oe_tmpl_nome,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_tmpl_oe"
                    )
                with _dl2:
                    if st.button("🗑️ Remover template OE", key="btn_rm_tmpl_oe"):
                        set_config("template_oe_base64", "")
                        set_config("template_oe_nome", "")
                        st.rerun()
            else:
                st.info("Nenhum template de OE cadastrado.")

            _up_oe = st.file_uploader(
                "📤 Carregar novo template de OE (.xlsx)",
                type=["xlsx"],
                key="upload_tmpl_oe"
            )
            if _up_oe:
                import base64
                _b64 = base64.b64encode(_up_oe.read()).decode()
                set_config("template_oe_base64", _b64)
                set_config("template_oe_nome", _up_oe.name)
                st.success(f"✅ Template OE salvo: {_up_oe.name}")
                st.rerun()

        # ── TEMPLATE CERTIFICADO ─────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🏅 Certificado de Qualidade")

            _c3, _c4 = st.columns([3,1])
            with _c3:
                _resp_cert = st.text_input(
                    "👤 Responsável pelo Certificado",
                    value=get_config("template_cert_responsavel", get_config("contato")),
                    placeholder="Nome que aparecerá no documento",
                    key="resp_cert_input"
                )
            with _c4:
                st.write("")
                st.write("")
                if st.button("💾 Salvar", key="btn_resp_cert"):
                    set_config("template_cert_responsavel", _resp_cert)
                    st.success("✅ Salvo!")

            st.divider()

            _orient_cert = st.radio(
                "📐 Orientação de impressão",
                options=["Retrato", "Paisagem"],
                index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
                horizontal=True,
                key="orient_cert_radio"
            )
            if st.button("💾 Salvar orientação Certificado", key="btn_save_orient_cert"):
                set_config("template_cert_orientacao", _orient_cert)
                st.success(f"✅ Orientação Certificado: {_orient_cert}")

            st.divider()

            _cert_tmpl_b64 = get_config("template_cert_base64", "")
            _cert_tmpl_nome = get_config("template_cert_nome", "")
            if _cert_tmpl_b64:
                st.success(f"✅ Template atual: **{_cert_tmpl_nome}**")
                _dl3, _dl4 = st.columns(2)
                with _dl3:
                    import base64 as _b64mod2
                    st.download_button(
                        "⬇️ Baixar template Certificado atual",
                        data=_b64mod2.b64decode(_cert_tmpl_b64),
                        file_name=_cert_tmpl_nome,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_tmpl_cert"
                    )
                with _dl4:
                    if st.button("🗑️ Remover template Certificado", key="btn_rm_tmpl_cert"):
                        set_config("template_cert_base64", "")
                        set_config("template_cert_nome", "")
                        st.rerun()
            else:
                st.info("Nenhum template de Certificado cadastrado.")

            _up_cert = st.file_uploader(
                "📤 Carregar novo template de Certificado (.xlsx)",
                type=["xlsx"],
                key="upload_tmpl_cert"
            )
            if _up_cert:
                import base64
                _b64 = base64.b64encode(_up_cert.read()).decode()
                set_config("template_cert_base64", _b64)
                set_config("template_cert_nome", _up_cert.name)
                st.success(f"✅ Template Certificado salvo: {_up_cert.name}")
                st.rerun()
'''

src = src[:idx_inicio] + NOVO_BLOCO
CFG.write_text(src, encoding="utf-8")
print("OK: Aba Templates reorganizada!")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Templates reorganizados v2' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
