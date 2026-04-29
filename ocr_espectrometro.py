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
Você é um assistente especializado em leitura de relatórios de espectrômetro de emissão óptica (OES) usados em fundição.

Analise a imagem e extraia APENAS os valores de composição química (% em massa de cada elemento).

Retorne SOMENTE um objeto JSON válido, sem nenhum texto adicional antes ou depois. Exemplo:
{
  "C": "0.18",
  "Si": "1.25",
  "Mn": "0.45",
  "P": "0.020",
  "S": "0.015",
  "Cr": "0.10",
  "Ni": "0.05",
  "Mo": "0.02",
  "Cu": "0.08",
  "V": "0.003",
  "Ti": "0.004",
  "Al": "0.025",
  "W": null,
  "Fe": "97.82"
}

Regras:
- Use null para elementos não encontrados na imagem.
- Valores como "< 0.001" devem ser retornados como "0.001".
- Se houver mais de uma leitura (ex.: duas amostras), use os valores da PRIMEIRA coluna válida.
- Não inclua unidades, apenas o número decimal com ponto.
- Se a imagem não for de um espectrômetro ou não contiver dados de composição química, retorne {"erro": "Imagem não reconhecida como relatório de espectrômetro"}.
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

        col_upload, col_preview = st.columns([1, 1])

        with col_upload:
            foto = st.file_uploader(
                "Selecionar imagem",
                type=["jpg", "jpeg", "png", "webp", "bmp"],
                key="ocr_foto_upload",
                help="Formatos aceitos: JPG, PNG, WEBP, BMP",
            )

        if foto is not None:
            with col_preview:
                st.image(foto, caption="Pré-visualização", use_container_width=True)

            st.markdown("##### Verificação antes de importar")
            st.caption(
                "Confirme que a imagem mostra claramente os valores numéricos dos "
                "elementos químicos antes de processar."
            )

            col_btn, col_status = st.columns([1, 2])
            with col_btn:
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

        else:
            st.markdown(
                """
                **Como usar:**
                1. Abra o relatório do espectrômetro na tela ou imprima-o
                2. Fotografe com o celular (câmera traseira, boa iluminação)
                3. Transfira a foto para este dispositivo ou use diretamente pelo celular
                4. Clique em **Selecionar imagem** acima e escolha a foto
                5. Clique em **Extrair composição química**
                """
            )

    st.markdown("---")
