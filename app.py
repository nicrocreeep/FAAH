import streamlit as st
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
import re
import zipfile
import io

# Configuração da página Web
st.set_page_config(page_title="Renomeador de ASOs e Exames", page_icon="📄", layout="centered")

st.title("📄 Leitor e Renomeador Automático de ASOs/Exames")
st.write("Faça o upload dos PDFs abaixo para identificar e renomear automaticamente.")

# Mapeamento de Palavras-Chave para Exames
REGRAS_EXAMES = {
    "Audiometria": ["audiometria", "audiograma", "vias aereas", "limiar tonal"],
    "Hemograma": ["hemograma", "hemacias", "leucocitos", "plaquetas", "hematocrito"],
    "Acuidade_Visual": ["acuidade visual", "optotipos", "visao de perto", "snellen"],
    "Glicemia": ["glicemia", "glicose", "jejum"],
    "Raio_X_Torax": ["radiografia", "torax", "campos pulmonares"],
    "ECG": ["eletrocardiograma", "ritmo sinusal", "frequencia cardiaca"]
}

def extrair_codigo_aso(texto):
    """Busca o código do rodapé do ASO (ex: M65614...)"""
    resultado = re.search(r'#\s*([A-Z0-9]+)\s*\d+/\d+\s*#', texto)
    if resultado:
        return resultado.group(1)
    resultado_alt = re.search(r'#(M[A-Z0-9]+)', texto)
    if resultado_alt:
        return resultado_alt.group(1)
    return None

def identificar_exame(texto):
    """Identifica o tipo de exame por termos técnicos contidos no documento"""
    texto_lower = texto.lower()
    for tipo, palavras in REGRAS_EXAMES.items():
        for palavra in palavras:
            if palavra in texto_lower:
                return tipo
    return None

def processar_pdf(pdf_bytes, nome_original):
    texto = ""
    # Tenta extrair texto nativo do PDF
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
    except Exception:
        pass

    # Tenta identificar o código do ASO
    codigo = extrair_codigo_aso(texto)
    if codigo:
        return f"{codigo}.pdf"

    # Se não encontrou o código do ASO, tenta OCR via imagem para ler exames escaneados
    try:
        imagens = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
        if imagens:
            texto_ocr = pytesseract.image_to_string(imagens[0], lang='por')
            
            # Verifica se é ASO via OCR
            codigo_ocr = extrair_codigo_aso(texto_ocr)
            if codigo_ocr:
                return f"{codigo_ocr}.pdf"
            
            # Identifica o tipo de exame
            tipo_doc = identificar_exame(texto_ocr) or identificar_exame(texto)
            if tipo_doc:
                return f"{tipo_doc}_{nome_original}"
    except Exception:
        pass

    return f"NAO_IDENTIFICADO_{nome_original}"

# Upload dos arquivos pelo navegador
arquivos_enviados = st.file_uploader("Arraste os arquivos PDF aqui", type=["pdf"], accept_multiple_files=True)

if arquivos_enviados:
    if st.button("Processar e Renomear Arquivos"):
        zip_buffer = io.BytesIO()
        progresso = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for i, arq in enumerate(arquivos_enviados):
                conteudo = arq.read()
                novo_nome = processar_pdf(conteudo, arq.name)
                zip_file.writestr(novo_nome, conteudo)
                progresso.progress((i + 1) / len(arquivos_enviados))

        st.success("Processamento concluído!")
        
        # Botão para baixar todos os PDFs renomeados juntos em formato .ZIP
        st.download_button(
            label="📦 Baixar Todos os Arquivos Renomeados (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="arquivos_renomeados.zip",
            mime="application/zip"
        )