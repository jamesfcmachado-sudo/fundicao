"""
ocr_espectrometro.py
Módulo de OCR para leitura de tela do espectrômetro via Google Cloud Vision API.
"""

import streamlit as st
import base64
import json
import re
import requests
from PIL import Image
import io

ELEMENTOS = [
    "C", "Si", "Mn", "P", "S", "Cr", "Ni", "Mo", "Cu",
    "W", "Nb", "B", "CE", "V", "Co", "Fe", "N", "Mg",
]


def _imagen_para_base64(uploaded_file):
    bytes_data = uploaded_file.read()
    img = Image.open(io.BytesIO(bytes_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64


def _extrair_valores_do_texto(texto):
    """
    Analisa o texto extraído pelo Google Vision e mapeia os valores de composição química.
    Estratégia: para cada elemento, pega o valor numérico que aparece na linha do meio (x̄).
    """
    linhas = texto.split("\n")
    resultado = {}

    # Encontra os elementos na tabela e seus valores
    for i, linha in enumerate(linhas):
        linha = linha.strip()
        for elem in ELEMENTOS:
            # Verifica se a linha contém apenas o símbolo do elemento (cabeçalho da coluna)
            if re.match(rf'^{re.escape(elem)}\s*$', linha, re.IGNORECASE) or \
               re.match(rf'^{re.escape(elem)}\s*%\s*$', linha, re.IGNORECASE):
                # Procura o valor numérico nas próximas linhas
                for j in range(i+1, min(i+6, len(linhas))):
                    proxima = linhas[j].strip()
                    # Remove < e outros prefixos
                    proxima_limpa = re.sub(r'^[<>≤≥]', '', proxima).strip()
                    try:
                        valor = float(proxima_limpa.replace(",", "."))
                        if 0 <= valor <= 100:
                            if elem not in resultado:
                                resultado[elem] = str(valor)
                            break
                    except ValueError:
                        if proxima and not re.match(r'^[A-Za-z%]', proxima):
                            continue
                        break

    # Segunda estratégia: busca por padrões "ELEM valor" na mesma linha
    texto_completo = texto
    for elem in ELEMENTOS:
        if elem not in resultado:
            # Padrão: elemento seguido de número na mesma linha
            padrao = rf'\b{re.escape(elem)}\s*%?\s*([<>]?\s*\d+[.,]\d+)'
            match = re.search(padrao, texto_completo, re.IGNORECASE)
            if match:
                valor_str = re.sub(r'^[<>]', '', match.group(1)).strip()
                try:
                    valor = float(valor_str.replace(",", "."))
                    if 0 <= valor <= 100:
                        resultado[elem] = str(valor)
                except ValueError:
                    pass

    return resultado


def _chamar_google_vision(b64_image, api_key):
    """Chama a Google Cloud Vision API para extrair texto da imagem."""
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [{
            "image": {"content": b64_image},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Extrai o texto completo
    try:
        texto = data["responses"][0]["fullTextAnnotation"]["text"]
    except (KeyError, IndexError):
        texto = ""

    return texto


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
                        api_key = st.secrets.get("GOOGLE_VISION_API_KEY", "")
                        if not api_key:
                            raise ValueError("GOOGLE_VISION_API_KEY não configurada nos Secrets")

                        foto.seek(0)
                        b64 = _imagen_para_base64(foto)
                        texto_extraido = _chamar_google_vision(b64, api_key)

                        # DEBUG: salva texto extraído
                        st.session_state["ocr_debug_texto"] = texto_extraido

                        resultado = _extrair_valores_do_texto(texto_extraido)

                        aplicados = []
                        ignorados = []
                        for elem in ELEMENTOS:
                            valor = resultado.get(elem)
                            if valor:
                                try:
                                    chave = f"chem_{elem}"
                                    float_val = float(str(valor).replace(",", "."))
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
                if aplicados:
                    st.write(", ".join(aplicados))
                if ignorados:
                    st.warning("Não encontrados: " + ", ".join(ignorados))
            elif res.get("status") == "erro":
                st.error(f"❌ {res.get('msg')}")

            # DEBUG: mostra texto bruto extraído
            if "ocr_debug_texto" in st.session_state:
                with st.expander("🔧 DEBUG - Texto extraído"):
                    st.text(st.session_state["ocr_debug_texto"])

    st.markdown("---")
