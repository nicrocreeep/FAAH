import os
import re
import io
import zipfile
import streamlit as st
import pdfplumber
from pypdf import PdfReader, PdfWriter

st.title("Separador e Renomeador de Prontuários SST")

def classificar_documento(texto_pagina):
    if not texto_pagina:
        return None
    
    texto = texto_pagina.upper()
    
    if "ATESTADO DE SAÚDE" in texto or "ATESTADO DE SAUDE" in texto or "ASO" in texto:
        return "ASO"
    elif "ENCAMINHAMENTO" in texto:
        return "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"
    elif "FICHA CLÍNICA" in texto or "FICHA CLINICA" in texto or "ANAMNESE" in texto:
        return "FICHA CLÍNICA"
    elif "PSICOLÓGICA" in texto or "PSICOLOGICA" in texto:
        return "AVALIAÇÃO PSICOLÓGICA"
    elif "AUDIOMÉTRICO" in texto or "AUDIOMETRIA" in texto or "AUDIOGRAMA" in texto:
        return "LAUDO AUDIOMÉTRICO"
    elif "ELETROENCEFALOGRAMA" in texto or "EEG" in texto:
        return "LAUDO ELETROENCEFALOGRAMA"
    elif "ELETROCARDIOGRAMA" in texto or "ECG" in texto:
        return "LAUDO ELETROCARDIOGRAMA"
    elif "ESPIROMETRIA" in texto:
        return "LAUDO ESPIROMETRIA"
    elif "HEMOGRAMA" in texto or "LABORATORIAL" in texto:
        return "EXAME HEMOGRAMA"
    elif "RESULTADO" in texto or "EXAME" in texto or "LAUDO" in texto:
        return "RESULTADO DE EXAMES"
    else:
        return None

def extrair_nome_colaborador(texto_pagina):
    if not texto_pagina:
        return None
        
    padroes = [
        r'(?:NOME|COLABORADOR|PACIENTE|CANDIDATO|EMPREGADO|NOME DO TRABALHADOR):\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'NOME\s*:\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})'
    ]
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)
            nome_final = re.sub(r'\s+', ' ', nome_limpo).upper()
            if len(nome_final) > 3:
                return nome_final
    return None

arquivo_enviado = st.file_uploader("Envie o PDF consolidado do lote", type=["pdf"])

if arquivo_enviado is not None:
    if st.button("Processar e Separar Documentos"):
        # Carrega o PDF via pypdf para manipulação de páginas
        reader_pypdf = PdfReader(arquivo_enviado)
        
        # Buffer do arquivo .ZIP
        zip_buffer = io.BytesIO()
        
        with pdfplumber.open(arquivo_enviado) as pdf_plumber:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                documento_atual = []
                tipo_doc_atual = None
                nome_colaborador_atual = "COLABORADOR_DESCONHECIDO"
                contadores = {}

                for idx, page_plumber in enumerate(pdf_plumber.pages):
                    texto = page_plumber.extract_text() or ""
                    
                    tipo_detectado = classificar_documento(texto)
                    nome_detectado = extrair_nome_colaborador(texto)

                    if nome_detectado:
                        nome_colaborador_atual = nome_detectado

                    # Se detectou um NOVO tipo de documento, quebra o arquivo anterior
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

                    # Adiciona a página correspondente no pypdf
                    documento_atual.append(reader_pypdf.pages[idx])

                # Grava as páginas finais restantes
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
