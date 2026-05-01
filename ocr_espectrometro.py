"""
ocr_espectrometro.py - OCR via Google Vision API com detecção por coordenadas
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
    "Al", "Ti", "Pb", "Sn", "As", "Bi", "Ca", "Zr", "La",
]

def _imagen_para_base64(uploaded_file):
    bytes_data = uploaded_file.read()
    img = Image.open(io.BytesIO(bytes_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64


def _chamar_google_vision_completo(b64_image, api_key):
    """Chama Google Vision e retorna anotações completas com coordenadas."""
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [{
            "image": {"content": b64_image},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
        }]
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def _extrair_palavras_com_posicao(data):
    """Extrai todas as palavras com suas coordenadas centrais."""
    palavras = []
    try:
        pages = data["responses"][0]["fullTextAnnotation"]["pages"]
        for page in pages:
            for block in page["blocks"]:
                for par in block["paragraphs"]:
                    for word in par["words"]:
                        texto = "".join(s["text"] for s in word["symbols"])
                        verts = word["boundingBox"]["vertices"]
                        xs = [v.get("x", 0) for v in verts]
                        ys = [v.get("y", 0) for v in verts]
                        cx = sum(xs) / len(xs)
                        cy = sum(ys) / len(ys)
                        palavras.append({"texto": texto, "cx": cx, "cy": cy})
    except (KeyError, IndexError):
        pass
    return palavras


def _extrair_valores_por_coordenadas(palavras):
    """
    Estratégia principal: encontra os cabeçalhos dos elementos pela posição X
    e associa o valor da linha X (média) que está abaixo deles.
    """
    resultado = {}

    # 1. Encontra todas as palavras que são símbolos de elementos
    elem_set = set(ELEMENTOS)
    headers = []
    for p in palavras:
        t = p["texto"].strip().rstrip("%").strip()
        if t in elem_set:
            headers.append({"elem": t, "cx": p["cx"], "cy": p["cy"]})

    if not headers:
        return resultado

    # 2. Para cada header, encontra o valor numérico mais próximo abaixo
    # A linha "x" (média) fica entre a linha superior e inferior
    # Agrupa palavras por faixa de Y para identificar as linhas
    palavras_sorted_y = sorted(palavras, key=lambda p: p["cy"])

    # Identifica a linha com símbolo X (linha do meio = valor medido)
    # Busca palavras "X" ou "x" isoladas
    linha_x_y = None
    for p in palavras:
        if p["texto"].strip() in ("X", "x", "×", "x̄"):
            linha_x_y = p["cy"]
            break

    # Para cada elemento, busca os valores numéricos na mesma coluna
    # e pega o valor do MEIO (linha x̄ = valor medido)
    tol_x = 60

    for h in headers:
        elem = h["elem"]
        if elem in resultado:
            continue

        # Candidatos: palavras na mesma coluna X, abaixo do cabeçalho
        candidatos = [
            p for p in palavras
            if abs(p["cx"] - h["cx"]) < tol_x
            and p["cy"] > h["cy"] + 5
            and p["cy"] < h["cy"] + 350
        ]

        # Filtra apenas valores numéricos válidos
        numericos = []
        for c in candidatos:
            txt = c["texto"].strip()
            txt_limpo = re.sub(r'^[<>≤≥]', '', txt).strip()
            txt_limpo = txt_limpo.replace(",", ".")
            try:
                valor = float(txt_limpo)
                if 0 <= valor <= 100:
                    numericos.append({"valor": valor, "cy": c["cy"], "txt": txt})
            except ValueError:
                continue

        if not numericos:
            continue

        numericos = sorted(numericos, key=lambda x: x["cy"])

        if len(numericos) == 1:
            resultado[elem] = str(numericos[0]["valor"])
        elif linha_x_y:
            # Filtra candidatos na faixa da linha X (±30px)
            na_linha_x = [n for n in numericos if abs(n["cy"] - linha_x_y) <= 30]
            if na_linha_x:
                resultado[elem] = str(na_linha_x[0]["valor"])
            else:
                # Fallback: pega o mais próximo do X
                mais_proximo = min(numericos, key=lambda n: abs(n["cy"] - linha_x_y))
                resultado[elem] = str(mais_proximo["valor"])
        elif len(numericos) == 2:
            resultado[elem] = str(numericos[1]["valor"])
        elif len(numericos) >= 3:
            resultado[elem] = str(numericos[1]["valor"])

    return resultado


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
                        data = _chamar_google_vision_completo(b64, api_key)

                        # Salva texto bruto para debug
                        try:
                            texto_bruto = data["responses"][0]["fullTextAnnotation"]["text"]
                            st.session_state["ocr_debug_texto"] = texto_bruto
                        except:
                            st.session_state["ocr_debug_texto"] = "Sem texto extraído"

                        palavras = _extrair_palavras_com_posicao(data)
                        resultado = _extrair_valores_por_coordenadas(palavras)

                        # Salva palavras para debug
                        st.session_state["ocr_debug_palavras"] = [
                            f"{p['texto']} (x={p['cx']:.0f}, y={p['cy']:.0f})"
                            for p in palavras if p["texto"].strip()
                        ]

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
                if aplicados:
                    st.success(f"✅ {len(aplicados)} elemento(s) preenchido(s)! Revise os valores abaixo.")
                    st.write(", ".join(aplicados))
                else:
                    st.warning("⚠️ Nenhum elemento encontrado. Verifique a foto e tente novamente.")
                if ignorados:
                    st.warning("Não encontrados: " + ", ".join(ignorados))
            elif res.get("status") == "erro":
                st.error(f"❌ {res.get('msg')}")

            # DEBUG
            if "ocr_debug_palavras" in st.session_state:
                with st.expander("🔧 DEBUG - Palavras e posições"):
                    st.text("\n".join(st.session_state["ocr_debug_palavras"][:80]))

    st.markdown("---")
