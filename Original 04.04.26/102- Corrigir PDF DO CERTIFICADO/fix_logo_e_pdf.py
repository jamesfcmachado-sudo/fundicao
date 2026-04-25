from pathlib import Path

# ── Fix 1: Move logo certificado para aba de Logotipos ────────────────────────
CFG = Path("empresa_config.py")
src = CFG.read_text(encoding="utf-8")

# Localiza fim da aba de logotipos (antes da aba tab3)
idx_tab3 = src.find("# ── ABA 3:")
idx_logo_cert = src.find("# Logo especifico do certificado")

print(f"tab3 na posicao: {idx_tab3}")
print(f"logo_cert na posicao: {idx_logo_cert}")

# Extrai o bloco do logo certificado da aba Templates
idx_logo_inicio = src.rfind("\n            st.divider()\n\n            # Logo especifico do certificado", 0, idx_logo_cert)
idx_logo_fim = src.find("\n            st.divider()\n\n     ", idx_logo_cert)
if idx_logo_fim == -1:
    idx_logo_fim = src.find("\n            # Upload novo template", idx_logo_cert)

print(f"Bloco logo: {idx_logo_inicio} ate {idx_logo_fim}")
bloco_logo = src[idx_logo_inicio:idx_logo_fim]
print(repr(bloco_logo[:100]))

# Remove o bloco da aba Templates
src_sem_logo = src[:idx_logo_inicio] + src[idx_logo_fim:]

# Adiciona na aba de Logotipos - apos o segundo logo
OLD_TAB2_FIM = '''    # ── ABA 3:'''
NOVO_LOGO_ABA2 = '''
    with tab2:
        # Adiciona logo do certificado no final da aba de logotipos
        st.divider()
        st.markdown("#### 🏅 Logotipo do Certificado de Qualidade")
        st.caption("Logo usado no PDF do Certificado. Se não configurado, usa o logotipo ativo.")

        _logo_cert_b64 = get_config("logo_certificado_base64", "")
        _logo_cert_nome = get_config("logo_certificado_nome", "")
        if _logo_cert_b64:
            import base64 as _b64lc2
            _lc_bytes2 = _b64lc2.b64decode(_logo_cert_b64)
            st.image(_lc_bytes2, width=200)
            st.success(f"✅ Logo certificado: **{_logo_cert_nome}**")
            _dlc1, _dlc2 = st.columns(2)
            with _dlc1:
                st.download_button(
                    "⬇️ Baixar logo certificado",
                    data=_lc_bytes2,
                    file_name=_logo_cert_nome,
                    mime="image/png",
                    key="dl_logo_cert2"
                )
            with _dlc2:
                if st.button("🗑️ Remover logo certificado", key="btn_rm_logo_cert2"):
                    set_config("logo_certificado_base64", "")
                    set_config("logo_certificado_nome", "")
                    st.rerun()
        else:
            st.info("Nenhum logo específico. Usando logo ativo da empresa.")

        _up_logo_cert2 = st.file_uploader(
            "📤 Carregar logo do Certificado (.png, .jpg)",
            type=["png","jpg","jpeg"],
            key="upload_logo_cert2"
        )
        if _up_logo_cert2:
            import base64 as _b64ulc2
            _b64lc_new2 = _b64ulc2.b64encode(_up_logo_cert2.read()).decode()
            set_config("logo_certificado_base64", _b64lc_new2)
            set_config("logo_certificado_nome", _up_logo_cert2.name)
            st.success(f"✅ Logo certificado salvo: {_up_logo_cert2.name}")
            st.rerun()

    # ── ABA 3:'''

# Verifica se tab2 ja tem with tab2 duplicado
if 'with tab2:\n        # Adiciona logo do certificado' in src_sem_logo:
    print("INFO: Logo ja esta na aba 2.")
else:
    src_sem_logo = src_sem_logo.replace('    # ── ABA 3:', NOVO_LOGO_ABA2, 1)
    print("OK: Logo certificado adicionado na aba Logotipos.")

CFG.write_text(src_sem_logo, encoding="utf-8")

# ── Fix 2: Corrige norma no PDF ──────────────────────────────────────────────
CERT = Path("certificados.py")
src_cert = CERT.read_text(encoding="utf-8")

# Corrige norma - garante que aparece no PDF
OLD_NORMA = '''    _norma_txt = norma if norma else liga
    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True), pl(""),
         pl("PROJETO / PROJECT", bold=True), pl(projeto)],
        [ph(f"{_norma_txt}", sz=13), "", "", ""],
    ], colWidths=[W*0.35, W*0.15, W*0.2, W*0.3])'''

NEW_NORMA = '''    _norma_txt = str(norma or liga or "")
    norma_tbl = Table([
        [pl("NORMA DA LIGA/ ALLOY STANDARD", bold=True), pl(""),
         pl("PROJETO / PROJECT", bold=True), pl(str(projeto or ""))],
        [ph(f"{_norma_txt}", sz=13), "", "", ""],
    ], colWidths=[W*0.35, W*0.15, W*0.2, W*0.3])'''

if OLD_NORMA in src_cert:
    src_cert = src_cert.replace(OLD_NORMA, NEW_NORMA, 1)
    print("OK: Norma corrigida no PDF.")

# Corrige decimais - usa format variavel
OLD_DECIMAL = '''            row.append(pc(f"{float(val):.4f}".replace(".", ",")))'''
NEW_DECIMAL = '''            # Usa 4 casas para valores < 1, 2 casas para >= 10
            _fv = float(val)
            if _fv == 0:
                _fs = "0"
            elif _fv < 1:
                _fs = f"{_fv:.4f}".rstrip("0").rstrip(",")
            elif _fv < 10:
                _fs = f"{_fv:.3f}".rstrip("0").rstrip(",")
            else:
                _fs = f"{_fv:.2f}".rstrip("0").rstrip(",")
            row.append(pc(_fs.replace(".", ",")))'''

if OLD_DECIMAL in src_cert:
    src_cert = src_cert.replace(OLD_DECIMAL, NEW_DECIMAL, 1)
    print("OK: Decimais corrigidos no PDF.")

CERT.write_text(src_cert, encoding="utf-8")

# Verifica sintaxe
import py_compile, tempfile, os
for nome, codigo in [("empresa_config.py", src_sem_logo), ("certificados.py", src_cert)]:
    tmp = tempfile.mktemp(suffix='.py')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(codigo)
    try:
        py_compile.compile(tmp, doraise=True)
        print(f"SINTAXE {nome} OK!")
    except py_compile.PyCompileError as e:
        print(f"ERRO {nome}: {e}")
    finally:
        os.unlink(tmp)

print("\nRode: git add . && git commit -m 'Logo cert aba logotipos e fix PDF' && git push")
