import os
import re
import io
import zipfile
import streamlit as st
from pypdf import PdfReader, PdfWriter

st.title("Separador e Renomeador de Prontuários SST")

def classificar_documento(texto_pagina):
    texto = texto_pagina.upper()
    if "ASO - ATESTADO DE SAÚDE OCUPACIONAL" in texto or "ATESTADO DE SAUDE OCUPACIONAL" in texto:
        return "ASO"
    elif "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL" in texto:
        return "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"
    elif "FICHA CLÍNICA" in texto or "FICHA CLINICA" in texto:
        return "FICHA CLÍNICA"
    elif "AVALIAÇÃO PSICOLÓGICA" in texto or "AVALIACAO PSICOLOGICA" in texto:
        return "AVALIAÇÃO PSICOLÓGICA"
    elif "AUDIOMÉTRICO" in texto or "AUDIOMETRIA" in texto:
        return "LAUDO AUDIOMÉTRICO"
    elif "ELETROENCEFALOGRAMA" in texto:
        return "LAUDO ELETROENCEFALOGRAMA"
    elif "ELETROCARDIOGRAMA" in texto:
        return "LAUDO ELETROCARDIOGRAMA"
    elif "ESPIROMETRIA" in texto:
        return "LAUDO ESPIROMETRIA"
    elif "HEMOGRAMA" in texto:
        return "EXAME HEMOGRAMA"
    elif "RESULTADO DE EXAMES" in texto or "LAUDO DE" in texto:
        return "RESULTADO DE EXAMES"
    else:
        return None

def extrair_nome_colaborador(texto_pagina):
    padroes = [
        r'(?:Nome|COLABORADOR|Paciente|Candidato):\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'EMPREGADO:\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})'
    ]
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)
            return re.sub(r'\s+', ' ', nome_limpo).upper()
    return None

arquivo_enviado = st.file_uploader("Envie o PDF consolidado do lote", type=["pdf"])

if arquivo_enviado is not None:
    if st.button("Processar e Separar Documentos"):
        reader = PdfReader(arquivo_enviado)
        
        # Buffer para criar o arquivo .ZIP na memória
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            documento_atual = []
            tipo_doc_atual = None
            nome_colaborador_atual = None
            contadores = {}

            for page in reader.pages:
                texto = page.extract_text() or ""
                tipo_detectado = classificar_documento(texto)
                nome_detectado = extrair_nome_colaborador(texto)

                eh_novo = (tipo_detectado is not None and tipo_detectado != tipo_doc_atual) or \
                          (nome_detectado is not None and nome_detectado != nome_colaborador_atual and nome_colaborador_atual is not None)

                if eh_novo and documento_atual and tipo_doc_atual and nome_colaborador_atual:
                    writer = PdfWriter()
                    for p in documento_atual:
                        writer.add_page(p)
                    
                    pdf_out = io.BytesIO()
                    writer.write(pdf_out)
                    
                    chave_base = f"{tipo_doc_atual} - {nome_colaborador_atual}"
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
                if nome_detectado:
                    nome_colaborador_atual = nome_detectado

                documento_atual.append(page)

            # Salva o último documento processado
            if documento_atual and tipo_doc_atual and nome_colaborador_atual:
                writer = PdfWriter()
                for p in documento_atual:
                    writer.add_page(p)
                pdf_out = io.BytesIO()
                writer.write(pdf_out)
                
                chave_base = f"{tipo_doc_atual} - {nome_colaborador_atual}"
                if chave_base in contadores:
                    contadores[chave_base] += 1
                    nome_final = f"{chave_base}_{contadores[chave_base]}.pdf"
                else:
                    nome_final = f"{chave_base}.pdf"
                
                zip_file.writestr(nome_final, pdf_out.getvalue())

        st.success("Documentos separados com sucesso!")
        st.download_button(
            label="Baixar Todos os Arquivos (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="prontuarios_separados.zip",
            mime="application/zip"
        )
