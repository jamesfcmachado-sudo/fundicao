"""
ocr_espectrometro.py
"""

import streamlit as st
import anthropic
import base64
import json
import re
from PIL import Image
import io

ELEMENTOS = [
    "C", "Si", "Mn", "P", "S", "Cr", "Ni", "Mo", "Cu",
    "W", "Nb", "B", "CE", "V", "Co", "Fe", "N", "Mg",
]

PROMPT_OCR = """
Voce e um assistente especializado em leitura de telas de espectrometro de emissao optica (OES) usados em fundicao de aco.

A tela do espectrometro mostra para cada elemento 3 linhas de valores:
  - linha superior: limite minimo da norma
  - linha do meio (x): valor MEDIDO da amostra - USE ESTE
  - linha inferior: limite maximo da norma

Extraia APENAS o valor medido (linha do meio) de cada elemento presente.

Retorne SOMENTE um objeto JSON valido, sem nenhum texto adicional antes ou depois. Exemplo:
{"C":"0.292","Si":"0.393","Mn":"0.94","P":"0.019","S":"0.0090","Cr":"0.141","Ni":"0.032","Mo":"0.143","Cu":"0.011","Co":"0.0054","Nb":"0.021","V":"0.0019","W":"0.010","B":"0.0007","Fe":"97.9"}

Regras:
- Use SEMPRE o valor da linha do meio, nunca os limites superior/inferior.
- Valores como <0.010 devem ser retornados como 0.010 (remova o sinal <).
- Use null para elementos nao encontrados na imagem.
- Nao inclua unidades, apenas o numero decimal com ponto.
- Se a imagem nao for de um espectrometro, retorne {"erro":"Imagem nao reconhecida"}.
"""


def _imagen_para_base64(uploaded_file):
    bytes_data = uploaded_file.read()
    img = Image.open(io.BytesIO(bytes_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64, "image/jpeg"


def _chamar_claude_vision(b64_image, media_type):
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_image}},
                {"type": "text", "text": PROMPT_OCR},
            ],
        }],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    return json.loads(raw)


def render_ocr_espectrometro():
    st.markdown("---")

    with st.expander("📷 Importar foto do espectrômetro", expanded=False):
        st.info("Selecione a foto da tela do espectrômetro. Os valores serão preenchidos automaticamente.")

        foto = st.file_uploader(
            "Selecionar imagem",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            key="ocr_foto_upload",
        )

        if foto is not None:
            foto_key = f"ocr_resultado_{foto.name}_{foto.size}"

            if foto_key not in st.session_state:
                with st.spinner("🔍 Analisando imagem... aguarde."):
                    try:
                        foto.seek(0)
                        b64, mtype = _imagen_para_base64(foto)
                        resultado = _chamar_claude_vision(b64, mtype)

                        if "erro" in resultado:
                            st.session_state[foto_key] = {"status": "erro", "msg": resultado["erro"]}
                        else:
                            # Grava valores e deleta chaves de widget para forçar rerenderização
                            aplicados = []
                            ignorados = []
                            for elem in ELEMENTOS:
                                valor = resultado.get(elem)
                                if valor is not None and valor != "null":
                                    try:
                                        chave = f"chem_{elem}"
                                        float_val = float(str(valor).replace(",", "."))
                                        # Deleta a chave do widget para o Streamlit aceitar o novo valor
                                        if chave in st.session_state:
                                            del st.session_state[chave]
                                        st.session_state[chave] = float_val
                                        aplicados.append(f"{elem}: {valor}")
                                    except ValueError:
                                        ignorados.append(elem)

                            st.session_state[foto_key] = {
                                "status": "ok",
                                "aplicados": aplicados,
                                "ignorados": ignorados,
                            }
                    except Exception as e:
                        st.session_state[foto_key] = {"status": "erro", "msg": str(e)}
                st.rerun()

            res = st.session_state.get(foto_key, {})
            if res.get("status") == "ok":
                aplicados = res.get("aplicados", [])
                ignorados = res.get("ignorados", [])
                st.success(f"✅ {len(aplicados)} elemento(s) preenchido(s)! Revise os valores abaixo.")
                if ignorados:
                    st.warning("Não importados: " + ", ".join(ignorados))
            elif res.get("status") == "erro":
                st.error(f"❌ {res.get('msg')}. Preencha manualmente.")

    st.markdown("---")
