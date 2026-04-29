"""
ocr_espectrometro.py
Módulo de OCR para leitura de tela/relatório do espectrômetro via API Anthropic (visão computacional).
Extrai valores de composição química e preenche os campos da corrida automaticamente.

Uso:
    from ocr_espectrometro import render_ocr_espectrometro
    render_ocr_espectrometro()   # dentro da seção Lançar Corridas do app.py
"""

import streamlit as st
import anthropic
import base64
import json
import re
from PIL import Image
import io

# ──────────────────────────────────────────────────────────────────────────────
# Elementos químicos mapeados para as chaves usadas no session_state (chem_*)
# Ajuste conforme os campos reais do seu banco / formulário.
# ──────────────────────────────────────────────────────────────────────────────
# Mesma ordem de ELEMENTOS_QUIMICOS do app.py
ELEMENTOS = {
    "C":  "chem_C",
    "Si": "chem_Si",
    "Mn": "chem_Mn",
    "P":  "chem_P",
    "S":  "chem_S",
    "Cr": "chem_Cr",
    "Ni": "chem_Ni",
    "Mo": "chem_Mo",
    "Cu": "chem_Cu",
    "W":  "chem_W",
    "Nb": "chem_Nb",
    "B":  "chem_B",
    "CE": "chem_CE",
    "V":  "chem_V",
    "Co": "chem_Co",
    "Fe": "chem_Fe",
    "N":  "chem_N",
    "Mg": "chem_Mg",
}

# Prompt enviado ao Claude Vision
PROMPT_OCR = """
Você é um assistente especializado em leitura de telas de espectrômetro de emissão óptica (OES) usados em fundição de aço.

A tela do espectrômetro mostra para cada elemento 3 linhas de valores:
  - linha superior: limite mínimo da norma
  - linha do meio (x̄): valor MEDIDO da amostra ← USE ESTE
  - linha inferior: limite máximo da norma

Extraia APENAS o valor medido (linha do meio, marcado com x̄ ou x) de cada elemento presente.

Retorne SOMENTE um objeto JSON válido, sem nenhum texto adicional antes ou depois. Exemplo:
{
  "C": "0.292",
  "Si": "0.393",
  "Mn": "0.94",
  "P": "0.019",
  "S": "0.0090",
  "Cr": "0.141",
  "Ni": "0.032",
  "Mo": "0.143",
  "Al": "0.037",
  "Cu": "0.011",
  "Co": "0.0054",
  "Ti": "0.0010",
  "Nb": "0.021",
  "V": "0.0019",
  "W": "0.010",
  "B": "0.0007",
  "Fe": "97.9"
}

Regras:
- Use SEMPRE o valor da linha do meio (x̄), nunca os limites superior/inferior.
- Valores como "<0.010" devem ser retornados como "0.010" (remova o sinal <).
- Use null para elementos não encontrados na imagem.
- Não inclua unidades, apenas o número decimal com ponto (não vírgula).
- Se a imagem não for de um espectrômetro, retorne {"erro": "Imagem não reconhecida como relatório de espectrômetro"}.
"""


def _imagen_para_base64(uploaded_file) -> tuple[str, str]:
    """Converte o arquivo enviado pelo usuário para base64 + media_type."""
    bytes_data = uploaded_file.read()
    # Verifica e converte se necessário (garante compatibilidade)
    img = Image.open(io.BytesIO(bytes_data))
    # Converte para RGB se for PNG com transparência (RGBA)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64, "image/jpeg"


def _chamar_claude_vision(b64_image: str, media_type: str) -> dict:
    """Envia a imagem para o Claude Vision e retorna o dict com os elementos."""
    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY do ambiente
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": PROMPT_OCR,
                    },
                ],
            }
        ],
    )
    raw = message.content[0].text.strip()
    # Remove possíveis blocos de código ```json ... ```
    raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    return json.loads(raw)


def _aplicar_valores_session_state(resultado: dict):
    """Grava os valores extraídos nas chaves chem_* do session_state."""
    aplicados = []
    ignorados = []
    for elem, chave in ELEMENTOS.items():
        valor = resultado.get(elem)
        if valor is not None and valor != "null":
            try:
                st.session_state[chave] = float(str(valor).replace(",", "."))
                aplicados.append(f"{elem}: {valor}")
            except ValueError:
                ignorados.append(f"{elem} (valor inválido: {valor})")
        # Se null, não altera o campo (mantém o que já estava)
    return aplicados, ignorados


# ──────────────────────────────────────────────────────────────────────────────
# Função principal — renderiza o bloco OCR dentro da tela Lançar Corridas
# ──────────────────────────────────────────────────────────────────────────────
def render_ocr_espectrometro():
    """
    Renderiza o botão/expander de importação de foto do espectrômetro.
    Chame esta função logo ANTES dos campos de composição química no formulário
    de Lançar Corridas.
    """
    st.markdown("---")

    with st.expander("📷 Importar foto do espectrômetro", expanded=False):
        st.info(
            "Tire uma foto da tela ou do relatório impresso do espectrômetro e "
            "faça o upload aqui. O sistema extrairá automaticamente os valores "
            "de composição química e preencherá os campos abaixo."
        )

        foto = st.file_uploader(
                "Selecionar imagem",
                type=["jpg", "jpeg", "png", "webp", "bmp"],
                key="ocr_foto_upload",
                help="Formatos aceitos: JPG, PNG, WEBP, BMP",
            )

        if foto is not None:
            st.image(foto, caption="Pré-visualização", use_container_width=True)

            processar = st.button(
                "🔍 Extrair composição química",
                type="primary",
                key="ocr_btn_processar",
                use_container_width=True,
            )

            if processar:
                with st.spinner("Analisando imagem com IA… aguarde alguns segundos."):
                    try:
                        foto.seek(0)  # reseta o cursor do arquivo
                        b64, mtype = _imagen_para_base64(foto)
                        resultado = _chamar_claude_vision(b64, mtype)

                        if "erro" in resultado:
                            st.error(f"❌ {resultado['erro']}")
                        else:
                            aplicados, ignorados = _aplicar_valores_session_state(resultado)

                            if aplicados:
                                st.success(
                                    f"✅ {len(aplicados)} elemento(s) importado(s) com sucesso!"
                                )
                                with st.expander("Ver valores extraídos", expanded=True):
                                    # Exibe em grid 4 colunas
                                    cols = st.columns(4)
                                    for i, item in enumerate(aplicados):
                                        cols[i % 4].markdown(f"• **{item}**")

                            if ignorados:
                                st.warning(
                                    "⚠️ Alguns valores não puderam ser importados: "
                                    + ", ".join(ignorados)
                                )

                            st.info(
                                "💡 Os campos de composição química foram preenchidos. "
                                "Revise os valores antes de salvar a corrida."
                            )
                            # Rerun para que os campos numéricos reflitam o session_state
                            st.rerun()

                    except json.JSONDecodeError as e:
                        st.error(
                            f"❌ A IA retornou uma resposta inesperada. Tente novamente ou "
                            f"preencha manualmente.\n\nDetalhe técnico: {e}"
                        )
                    except anthropic.APIError as e:
                        st.error(f"❌ Erro na API Anthropic: {e}")
                    except Exception as e:
                        st.error(f"❌ Erro inesperado: {e}")



    st.markdown("---")
