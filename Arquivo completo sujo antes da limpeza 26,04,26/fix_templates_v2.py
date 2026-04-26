from pathlib import Path

CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

if "fix_templates_v2" in src:
    print("Ja aplicado!")
    exit(0)

# Substitui toda a aba de Templates por versao reorganizada
OLD_TAB5 = '''

    # ── ABA 5: Templates ──────────────────────────────────────────────────────
    with tab5:
        st.subheader("Templates de documentos")
        st.caption("Faça upload dos templates Excel para geração automática de documentos.")

        st.markdown("##### Template — Ordem de Entrega (OE)")
        _resp_oe = st.text_input(
            "Responsável pela OE (aparece no campo Contato do documento)",
            value=get_config("template_oe_responsavel", get_config("contato")),
            key="resp_oe_input"
        )
        if st.button("💾 Salvar responsável OE", key="btn_resp_oe"):
            set_config("template_oe_responsavel", _resp_oe)
            st.success(f"✅ Responsável OE salvo: {_resp_oe}")

        _oe_tmpl = get_config("template_oe_base64", "")
        if _oe_tmpl:
            st.success(f"Template OE cadastrado: {get_config('template_oe_nome')}")
            if st.button("🗑️ Remover template OE", key="btn_rm_tmpl_oe"):
                set_config("template_oe_base64", "")
                set_config("template_oe_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de OE cadastrado.")

        st.markdown("**Orientação de impressão:**")
        _col_ort1, _col_ort2 = st.columns(2)
        with _col_ort1:
            _orient_oe = st.radio(
                "OE — Orientação",
                options=["Paisagem", "Retrato"],
                index=0 if get_config("template_oe_orientacao", "Paisagem") == "Paisagem" else 1,
                horizontal=True,
                key="orient_oe_radio"
            )
        with _col_ort2:
            if st.button("💾 Salvar orientação OE", key="btn_save_orient_oe"):
                set_config("template_oe_orientacao", _orient_oe)
                st.success(f"✅ Orientação OE: {_orient_oe}")

        _up_oe = st.file_uploader(
            "Carregar template de OE (.xlsx)",
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

        st.divider()

        st.markdown("##### Template — Certificado de Qualidade")
        _resp_cert = st.text_input(
            "Responsável pelo Certificado (aparece no documento)",
            value=get_config("template_cert_responsavel", get_config("contato")),
            key="resp_cert_input"
        )
        if st.button("💾 Salvar responsável Certificado", key="btn_resp_cert"):
            set_config("template_cert_responsavel", _resp_cert)
            st.success(f"✅ Responsável Certificado salvo: {_resp_cert}")

        _cert_tmpl = get_config("template_cert_base64", "")
        if _cert_tmpl:
            st.success(f"Template Certificado cadastrado: {get_config('template_cert_nome')}")
            if st.button("🗑️ Remover template Certificado", key="btn_rm_tmpl_cert"):
                set_config("template_cert_base64", "")
                set_config("template_cert_nome", "")
                st.rerun()
        else:
            st.info("Nenhum template de Certificado cadastrado.")

        st.markdown("**Orientação de impressão:**")
        _col_ort3, _col_ort4 = st.columns(2)
        with _col_ort3:
            _orient_cert = st.radio(
                "Certificado — Orientação",
                options=["Retrato", "Paisagem"],
                index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
                horizontal=True,
                key="orient_cert_radio"
            )
        with _col_ort4:
            if st.button("💾 Salvar orientação Certificado", key="btn_save_orient_cert"):
                set_config("template_cert_orientacao", _orient_cert)
                st.success(f"✅ Orientação Certificado: {_orient_cert}")

        _up_cert = st.file_uploader(
            "Carregar template de Certificado (.xlsx)",
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

NEW_TAB5 = '''
    # fix_templates_v2

    # ── ABA 5: Templates ──────────────────────────────────────────────────────
    with tab5:
        st.subheader("📋 Templates de documentos")
        st.caption("Configure os templates Excel para geração automática de documentos.")

        # ── TEMPLATE OE ──────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📦 Ordem de Entrega (OE)")

            # Responsavel
            _c1, _c2 = st.columns([3,1])
            with _c1:
                _resp_oe = st.text_input(
                    "👤 Responsável pela OE",
                    value=get_config("template_oe_responsavel", get_config("contato")),
                    placeholder="Nome do responsável que aparecerá no documento",
                    key="resp_oe_input"
                )
            with _c2:
                st.write("")
                st.write("")
                if st.button("💾 Salvar", key="btn_resp_oe"):
                    set_config("template_oe_responsavel", _resp_oe)
                    st.success("✅ Salvo!")

            st.divider()

            # Orientacao
            _orient_oe = st.radio(
                "📐 Orientação de impressão",
                options=["Paisagem", "Retrato"],
                index=0 if get_config("template_oe_orientacao", "Paisagem") == "Paisagem" else 1,
                horizontal=True,
                key="orient_oe_radio"
            )
            if st.button("💾 Salvar orientação", key="btn_save_orient_oe"):
                set_config("template_oe_orientacao", _orient_oe)
                st.success(f"✅ Orientação: {_orient_oe}")

            st.divider()

            # Template atual
            _oe_tmpl_b64 = get_config("template_oe_base64", "")
            _oe_tmpl_nome = get_config("template_oe_nome", "")
            if _oe_tmpl_b64:
                st.success(f"✅ Template atual: **{_oe_tmpl_nome}**")
                _dl1, _dl2 = st.columns(2)
                with _dl1:
                    # Botao para baixar template atual
                    import base64 as _b64mod
                    _tmpl_bytes = _b64mod.b64decode(_oe_tmpl_b64)
                    st.download_button(
                        "⬇️ Baixar template OE atual",
                        data=_tmpl_bytes,
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

            # Upload novo template
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

            # Responsavel
            _c3, _c4 = st.columns([3,1])
            with _c3:
                _resp_cert = st.text_input(
                    "👤 Responsável pelo Certificado",
                    value=get_config("template_cert_responsavel", get_config("contato")),
                    placeholder="Nome do responsável que aparecerá no documento",
                    key="resp_cert_input"
                )
            with _c4:
                st.write("")
                st.write("")
                if st.button("💾 Salvar", key="btn_resp_cert"):
                    set_config("template_cert_responsavel", _resp_cert)
                    st.success("✅ Salvo!")

            st.divider()

            # Orientacao
            _orient_cert = st.radio(
                "📐 Orientação de impressão",
                options=["Retrato", "Paisagem"],
                index=0 if get_config("template_cert_orientacao", "Retrato") == "Retrato" else 1,
                horizontal=True,
                key="orient_cert_radio"
            )
            if st.button("💾 Salvar orientação", key="btn_save_orient_cert"):
                set_config("template_cert_orientacao", _orient_cert)
                st.success(f"✅ Orientação: {_orient_cert}")

            st.divider()

            # Template atual
            _cert_tmpl_b64 = get_config("template_cert_base64", "")
            _cert_tmpl_nome = get_config("template_cert_nome", "")
            if _cert_tmpl_b64:
                st.success(f"✅ Template atual: **{_cert_tmpl_nome}**")
                _dl3, _dl4 = st.columns(2)
                with _dl3:
                    import base64 as _b64mod2
                    _cert_bytes = _b64mod2.b64decode(_cert_tmpl_b64)
                    st.download_button(
                        "⬇️ Baixar template Certificado atual",
                        data=_cert_bytes,
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

            # Upload novo template
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

if OLD_TAB5 in src:
    src = src.replace(OLD_TAB5, NEW_TAB5, 1)
    print("OK: Aba Templates reorganizada.")
else:
    print("AVISO: Bloco nao encontrado.")

CFG.write_text(src, encoding="utf-8")

import py_compile, tempfile, os
tmp = tempfile.mktemp(suffix='.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)
try:
    py_compile.compile(tmp, doraise=True)
    print("SINTAXE OK! Rode: git add . && git commit -m 'Templates reorganizados' && git push")
except py_compile.PyCompileError as e:
    print(f"ERRO: {e}")
finally:
    os.unlink(tmp)
