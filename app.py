import io
import re
import os
import zipfile
import streamlit as st
import pdfplumber
from pypdf import PdfReader, PdfWriter
import pytesseract

st.set_page_config(page_title="Separador de Prontuários SST", layout="wide")
st.title("Separador e Renomeador de Prontuários SST")

def extrair_texto_com_ocr(page_plumber):
    """Extrai texto diretamente ou utiliza OCR caso a página seja imagem/escaneada."""
    texto = page_plumber.extract_text() or ""
    if not texto.strip():
        try:
            img = page_plumber.to_image(resolution=150).original
            texto = pytesseract.image_to_string(img, lang="por")
        except Exception:
            texto = ""
    return texto

def classificar_documento(texto_pagina):
    if not texto_pagina:
        return None
    
    texto = texto_pagina.upper()
    
    # 1. ASO (PRIORIDADE MÁXIMA)
    # Se contiver a frase do cabeçalho oficial, classifica como ASO imediatamente,
    # ignorando se "Psicológica" aparece listado no checklist de exames complementares.
    if "ATESTADO DE SAÚDE OCUPACIONAL" in texto or "ATESTADO DE SAUDE OCUPACIONAL" in texto:
        return "ASO"
    
    # 2. AVALIAÇÃO PSICOLÓGICA / PSICOSSOCIAL
    # Só valida se for o documento/protocolo de avaliação propriamente dito
    if "PROTOCOLO MÉDICO COMPLEMENTAR PARA AVALIAÇÃO PSICOSOCIAL" in texto or \
       "AVALIAÇÃO PSICOLÓGICA" in texto or "AVALIAÇÃO PSICOSOCIAL" in texto or \
       "QUESTIONÁRIO SRQ-20" in texto:
        return "AVALIAÇÃO PSICOLÓGICA"

    # 3. EXAMES LABORATORIAIS DE URINA / SANGUE (Prioridade sobre termos ambíguos)
    analitos_urina_sangue = [
        "HIPÚRICO", "HIPURICO", "METILHIPÚRICO", "METILHIPURICO", 
        "CREATININA", "GAMA GT", "GLICOSE", "HEMOGRAMA", "PLAQUETAS",
        "G/G CREATININA", "MG/DL", "U/L", "SANGUE VENOSO", "TGP", "TGO"
    ]
    if any(analito in texto for analito in analitos_urina_sangue):
        return "EXAME HEMOGRAMA"
    
    # 4. EXAMES VISUAIS (Checagem por padrões específicos de acuidade/cores)
    if "ACUIDADE VISUAL" in texto or "OD:20/" in texto or "OE:20/" in texto:
        return "EXAME ACUIDADE VISUAL"
    if "ISHIHARA" in texto or "JAEGER" in texto or "SENSIBILIDADE DE CONTRASTE" in texto:
        return "EXAME SENSIBILIDADE E CORES"
    
    # 5. OUTROS EXAMES ESPECÍFICOS E LAUDOS
    if "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL" in texto or "ENCAMINHAMENTO" in texto:
        return "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"
    elif "FICHA CLÍNICA" in texto or "FICHA CLINICA" in texto or "ANAMNESE" in texto:
        return "FICHA CLÍNICA"
    elif "AUDIOMÉTRICO" in texto or "AUDIOMETRIA" in texto or "AUDIOGRAMA" in texto or "AVALIAÇÃO AUDIOLÓGICA" in texto:
        return "LAUDO AUDIOMÉTRICO"
    elif "PNEUMOCONIOSE" in texto or "RAIO X DO TORAX PA-OIT" in texto or "RADIOLÓGICA" in texto or "RADIOGRAFIA" in texto or "RAIO X" in texto or "RAIO-X" in texto or "RX " in texto:
        return "LAUDO RAIO X TORAX OIT"
    elif "ROMBERG" in texto:
        return "EXAME ROMBERG"
    elif "TIPAGEM SANGUÍNEA" in texto or "TIPAGEM SANGUINEA" in texto or "ABO" in texto or "FATOR RH" in texto:
        return "LAUDO TIPAGEM SANGUINEA"
    elif "ELETROENCEFALOGRAMA" in texto or "EEG" in texto:
        return "LAUDO ELETROENCEFALOGRAMA"
    elif "ELETROCARDIOGRAMA" in texto or "ECG" in texto:
        return "LAUDO ELETROCARDIOGRAMA"
    elif "ESPIROMETRIA" in texto:
        return "LAUDO ESPIROMETRIA"
    
    # Fallback Genérico
    elif "RESULTADO DE EXAMES" in texto or "RESULTADO" in texto or "EXAME" in texto or "LAUDO" in texto:
        return "RESULTADO DE EXAMES"
    else:
        return None

def extrair_nome_colaborador(texto_pagina):
    if not texto_pagina:
        return None
        
    # Padrões ajustados para extrair especificamente o texto limpo digitado
    padroes = [
        r'2-\s*Nome:\s*\n?\s*\|\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'Funcionário:\s*\d*\s*-\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'(?:NOME|COLABORADOR|PACIENTE|CANDIDATO|EMPREGADO|NOME DO TRABALHADOR|SR\(A\)):\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'NOME\s*:\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})'
    ]
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            # Corta termos de cabeçalho comuns na mesma linha
            nome = re.split(r'\b(SEXO|CARGO|CPF|RG|DATA|IDADE|PIS|CTPS|CADASTRO|ATEND|UNIDADE|SETOR)\b', nome, flags=re.IGNORECASE)[0]
            nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)
            nome_final = re.sub(r'\s+', ' ', nome_limpo).upper().strip()
            if len(nome_final) > 3:
                return nome_final
    return None

arquivo_enviado = st.file_uploader("Envie o PDF consolidado do lote", type=["pdf"])

if arquivo_enviado is not None:
    if st.button("Processar e Separar Documentos"):
        reader_pypdf = PdfReader(arquivo_enviado)
        zip_buffer = io.BytesIO()
        
        with pdfplumber.open(arquivo_enviado) as pdf_plumber:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                documento_atual = []
                tipo_doc_atual = None
                nome_colaborador_atual = "COLABORADOR_DESCONHECIDO"
                contadores = {}

                for idx, page_plumber in enumerate(pdf_plumber.pages):
                    texto = extrair_texto_com_ocr(page_plumber)
                    
                    tipo_detectado = classificar_documento(texto)
                    nome_detectado = extrair_nome_colaborador(texto)

                    if nome_detectado:
                        nome_colaborador_atual = nome_detectado

                    if tipo_detectado and tipo_detectado != tipo_doc_atual and documento_atual:
                        writer = PdfWriter()
                        for p in documento_atual:
                            writer.add_page(p)
                        
                        pdf_out = io.BytesIO()
                        writer.write(pdf_out)
                        
                        nome_tipo = tipo_doc_atual if tipo_doc_atual else "DOCUMENTO_SEM_CLASSIFICACAO"
                        chave_base = f"{nome_tipo} - {nome_colaborador_atual}"
                        
                        if chave_base in contadores:
                            contadores[chave_base] += 1
                            nome_final = f"{chave_base}_{contadores[chave_base]}.pdf"
                        else:
                            contadores[chave_base] = 0
                            nome_final = f"{chave_base}.pdf"
                        
                        zip_file.writestr(nome_final, pdf_out.getvalue())
                        documento_atual = []

                    if tipo_detectado:
                        tipo_doc_atual = tipo_detectado

                    documento_atual.append(reader_pypdf.pages[idx])

                if documento_atual:
                    writer = PdfWriter()
                    for p in documento_atual:
                        writer.add_page(p)
                    pdf_out = io.BytesIO()
                    writer.write(pdf_out)
                    
                    nome_tipo = tipo_doc_atual if tipo_doc_atual else "DOCUMENTO_SEM_CLASSIFICACAO"
                    chave_base = f"{nome_tipo} - {nome_colaborador_atual}"
                    
                    if chave_base in contadores:
                        contadores[chave_base] += 1
                        nome_final = f"{chave_base}_{contadores[chave_base]}.pdf"
                    else:
                        nome_final = f"{chave_base}.pdf"
                    
                    zip_file.writestr(nome_final, pdf_out.getvalue())

        st.success("Processamento concluído!")
        st.download_button(
            label="Baixar Todos os Arquivos (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="prontuarios_separados.zip",
            mime="application/zip"
        )
