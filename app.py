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
    if len(texto.strip()) < 80:
        try:
            img = page_plumber.to_image(resolution=300).original
            texto_ocr = pytesseract.image_to_string(img, lang="por")
            if len(texto_ocr.strip()) > len(texto.strip()):
                texto = texto_ocr
        except Exception:
            pass
    return texto

def classificar_documento(texto_pagina):
    if not texto_pagina:
        return None
        
    texto = texto_pagina.upper()
    
    # ============================================
    # PRIORIDADE 1: ASO vs AVALIAÇÃO PSICOLÓGICA (A SOLUÇÃO DO CONFLITO)
    # ============================================
    # Regra do ASO: Tem o título de ASO, MAS a frase "finalidade o atestado" (típica do laudo psicológico) 
    # NÃO pode estar presente. Assim, o laudo não é "roubado" pelo ASO.
    if ("ATESTADO DE SAÚDE OCUPACIONAL" in texto or "ATESTADO DE SAUDE OCUPACIONAL" in texto) and \
       "FINALIDADE O ATESTADO" not in texto and \
       "FINALIDADE DE ATESTADO" not in texto:
        return "ASO"

    # Regra da Avaliação: Fica logo abaixo. Se for um ASO de verdade, já foi pego no if acima 
    # e não vai ser afetado pelo "Aval. Psicológica Psicossocial" no meio dos exames.
    if "AVALIAÇÃO PSICOLÓGICA" in texto or "AVALIACAO PSICOLOGICA" in texto or \
       "PROTOCOLO MÉDICO COMPLEMENTAR PARA AVALIAÇÃO PSICOSOCIAL" in texto or \
       "AVALIAÇÃO PSICOSOCIAL" in texto or "AVALIACAO PSICOSSOCIAL" in texto or \
       "QUESTIONÁRIO SRQ-20" in texto or "AVAL. PSICOLÓGICA" in texto:
        return "AVALIAÇÃO PSICOLÓGICA"

    # ============================================
    # PRIORIDADE 2: DOCUMENTOS ESTRUTURAIS/FICHAS
    # ============================================
    if "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL" in texto or \
       ("ENCAMINHAMENTO" in texto and "MEDICINA" in texto) or \
       ("ENCAMINHAMENTO" in texto and "PASS AÚRA" in texto) or \
       ("RELAÇÃO DE EXAMES" in texto and "ENCAMINHAMENTO" in texto):
        return "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"

    if "FICHA CLÍNICA" in texto or "FICHA CLINICA" in texto or \
       ("ANTECEDENTES FAMILIARES" in texto and "ANTECEDENTES PESSOAIS" in texto):
        return "FICHA CLÍNICA"
    
    # ============================================
    # PRIORIDADE 3: AVALIAÇÕES ESPECÍFICAS
    # ============================================
    if any(x in texto for x in [
        "AVALIAÇÃO DO EQUILÍBRIO", "AVALIACAO DO EQUILIBRIO",
        "FUNÇÃO CEREBELAR", "FUNCAO CEREBELAR",
        "VERTIGEM POSICIONAL PAROXÍSTICA BENIGNA", "VERTIGEM POSICIONAL PAROXISTICA BENIGNA",
        "VPPB", "PESQUISA VPPB",
        "PROVA DE UNTERBERGER", "PROVA DE INDEX", "DIACOCINESIA",
        "PROVA DE ROMBERG", "TESTE DE ROMBERG"
    ]):
        return "EXAME AVALIAÇÃO DO EQUILÍBRIO"
    
    # ============================================
    # PRIORIDADE 4: EXAMES VISUAIS
    # ============================================
    if "ACUIDADE VISUAL" in texto or "OD:20/" in texto or "OE:20/" in texto or \
       "SNELLEN" in texto or "EYETEST" in texto:
        return "EXAME ACUIDADE VISUAL"
    if "ISHIHARA" in texto or "JAEGER" in texto or "SENSIBILIDADE DE CONTRASTE" in texto:
        return "EXAME SENSIBILIDADE E CORES"
    
    # ============================================
    # PRIORIDADE 5: EXAMES DE IMAGEM / LAUDOS ESPECÍFICOS
    # ============================================
    if "ELETROENCEFALOGRAMA" in texto or "EEG" in texto or \
       "ELETROENCEFALOGRAFIA" in texto or \
       ("RITMO DE BASE" in texto and "HIPERPNEIA" in texto) or \
       ("HIPERPNEIA" in texto and "POTENCIAIS" in texto):
        return "LAUDO ELETROENCEFALOGRAMA"
    
    if "ELETROCARDIOGRAMA" in texto or "ECG" in texto or \
       "LAUDO DE ELETROCARDIOGRAMA" in texto or \
       ("RITMO SINUSAL" in texto and "EIXO QRS" in texto) or \
       ("ECG DE REPOUSO" in texto):
        return "LAUDO ELETROCARDIOGRAMA"
    
    if "PNEUMOCONIOSE" in texto or "RAIO X DO TORAX PA-OIT" in texto or \
       "RADIOLÓGICA" in texto or "RADIOGRAFIA" in texto or \
       "RADIOGRÁFICO" in texto or "RAIO X" in texto or "RAIO-X" in texto or "RX " in texto:
        return "LAUDO RAIO X TORAX OIT"
    
    if "AUDIOMÉTRICO" in texto or "AUDIOMETRIA" in texto or "AUDIOGRAMA" in texto or \
       "AVALIAÇÃO AUDIOLÓGICA" in texto or "LIMIARES AUDITIVOS" in texto or \
       "AUDIOMETRIA TONAL" in texto:
        return "LAUDO AUDIOMÉTRICO"
    
    if "ESPIROMETRIA" in texto or ("FEV1" in texto and "FVC" in texto):
        return "LAUDO ESPIROMETRIA"
    
    if "TIPAGEM SANGUÍNEA" in texto or "TIPAGEM SANGUINEA" in texto or \
       "GRUPO SANGUÍNEO" in texto or "GRUPO SANGUINEO" in texto or \
       ("ABO" in texto and "RH" in texto and ("FATOR" in texto or "TIPO" in texto)):
        return "LAUDO TIPAGEM SANGUINEA"
    
    # ============================================
    # PRIORIDADE 6: EXAMES LABORATORIAIS (HEMOGRAMA / BIOQUÍMICA / TOXICOLÓGICO)
    # ============================================
    if any(x in texto for x in [
        "HEMOGRAMA", "ERITOGRAMA", "LEUCOGRAMA",
        "SÉRIE VERMELHA", "SERIE VERMELHA",
        "SÉRIE BRANCA", "SERIE BRANCA"
    ]) or (any(x in texto for x in ["HEMÁCIAS", "HEMACIAS", "HEMATÓCRITO", "HEMATOCRITO"]) and 
           any(y in texto for y in ["LEUCÓCITOS", "LEUCOCITOS", "PLAQUETAS"])):
        return "EXAME HEMOGRAMA"

    if any(x in texto for x in [
        "ÁCIDO HIPÚRICO", "ACIDO HIPURICO", "ÁCIDO METIL HIPÚRICO", 
        "ACIDO METIL HIPURICO", "METILHIPÚRICO", "METILHIPURICO", "HIPÚRICO", "HIPURICO",
        "CROMO", "MANGANÊS", "MANGANES", "CHUMBO", "COBALTO", "CADMIO", "CÁDMIO",
        "MERCÚRIO", "MERCURIO", "ARSÊNICO", "ARSENICO", "NÍQUEL", "NIQUEL",
        "FENOL", "FÊNOL", "TRICLOROCOMPOSTOS"
    ]) or ("CREATININA" in texto and ("G/G" in texto or "INÍCIO DE JORNADA" in texto or "INICIO DE JORNADA" in texto)):
        return "EXAME TOXICOLÓGICO ÁCIDOS E METAIS"
    
    if any(x in texto for x in [
        "GAMA GT", "GAMA-GLUTAMIL", "GGT", "GLUTAMILTRANSFERASE", "GLUTAMIL TRANSFERASE",
        "TGO", "TRANSAMINASE OXALACETICA", "TRANSAMINASE OXALACÉTICA", "ASPARTATO AMINOTRANSFERASE",
        "TGP", "TRANSAMINASE PIRUVICA", "TRANSAMINASE PIRÚVICA", "ALANINA AMINOTRANSFERASE",
        "GLICOSE", "GLICOSE JEJUM", "CREATININA", "UREIA", "ÁCIDO ÚRICO", "ACIDO URICO"
    ]):
        return "EXAME BIOQUÍMICA SANGUÍNEA"
    
    # ============================================
    # PRIORIDADE 7: GENÉRICOS DE EXAMES
    # ============================================
    if "RESULTADO DE EXAMES" in texto or "LAUDO DE EXAME" in texto:
        return "RESULTADO DE EXAMES"
    
    if "EXAME" in texto or "LAUDO" in texto:
        return "RESULTADO DE EXAMES"
    
    return None

def extrair_subtipo_exame(texto_pagina):
    if not texto_pagina:
        return None
    texto = texto_pagina.upper()
    
    if any(x in texto for x in ["HEMOGRAMA", "ERITOGRAMA", "LEUCOGRAMA", "SÉRIE VERMELHA", "SERIE VERMELHA"]):
        return "HEMOGRAMA"
    if "GAMA GT" in texto or "GGT" in texto:
        return "GAMA_GT"
    if "TGO" in texto or "TRANSAMINASE OXALACETICA" in texto or "TRANSAMINASE OXALACÉTICA" in texto:
        return "TGO"
    if "TGP" in texto or "TRANSAMINASE PIRUVICA" in texto or "TRANSAMINASE PIRÚVICA" in texto:
        return "TGP"
    if "GLICOSE JEJUM" in texto:
        return "GLICOSE_JEJUM"
    if "GLICOSE" in texto:
        return "GLICOSE"
    if any(x in texto for x in ["ACIDO HIPURICO", "ÁCIDO HIPÚRICO", "METILHIPURICO", "METILHIPÚRICO"]):
        return "ACIDOS_HIPURICOS"
    if "CROMO" in texto:
        return "CROMO"
    if "MANGANÊS" in texto or "MANGANES" in texto:
        return "MANGANES"
    if "GRUPO SANGUINEO" in texto or "GRUPO SANGUÍNEO" in texto or ("ABO" in texto and "RH" in texto):
        return "TIPAGEM_SANGUINEA"
    return None

def extrair_nome_colaborador(texto_pagina):
    if not texto_pagina:
        return None
        
    texto = texto_pagina.upper()
    
    padroes = [
        r'AVALIADO\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|CARGO|CPF|RG|\.|$)',
        r'PACIENTE\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|CPF|RG|IDADE|SEXO|CONVÊNIO|CONVENIO|\.|$)',
        r'NOME\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|RG|DATA|SEXO|EMPRESA|\.|$)',
        r'NOME\.{2,}\s*:\s*\d*[-–]?\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|DATA|SEXO|\.|$)',
        r'FUNCIONÁRIO/PACIENTE\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|IDADE|SEXO|EMPRESA|\.|$)',
        r'FUNCIONÁRIO\s*\(CÓDIGO\s*/\s*NOME\)\s*\n?\s*\d+\s*/\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|EMPRESA|RG|CPF|\.|$)',
        r'FUNCIONÁRIO:\s*\d+\s*-\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|UNIDADE|CNPJ|RG|CPF|\.|$)',
        r'(?:COLABORADOR|CANDIDATO|EMPREGADO|NOME DO TRABALHADOR|SR\(A\))\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|RG|DATA|SEXO|\.|$)',
        r'^([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,50})\s*-\s*CÓDIGO\s+DO\s+EXAME',
    ]
    
    palavras_proibidas = [
        "APRESENTOU", "DESEMPENHO", "RESULTADO", "EXAME", "DENTRO", "SOLICITANTE", 
        "RELATOR", "LAUDO", "DECLARA", "AVALIADO", "CONCLUSAO", "CONCLUSÃO", "PROTOCOLO"
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE | re.MULTILINE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            stops = ['SEXO', 'CARGO', 'CPF', 'RG', 'DATA', 'IDADE', 'PIS', 'CTPS', 
                     'CADASTRO', 'ATEND', 'UNIDADE', 'SETOR', 'EMPRESA', 'CNPJ', 
                     'MÉDICO', 'MEDICO', 'PROTOCOLO', 'CONVÊNIO', 'CONVENIO', 'EMISSÃO', 'EMISSAO']
            for stop in stops:
                nome = re.split(rf'\b{stop}\b', nome, flags=re.IGNORECASE)[0]
            nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)
            nome_final = re.sub(r'\s+', ' ', nome_limpo).upper().strip()
            nome_final = re.sub(r'^\d+[\s\-–]+', '', nome_final)
            
            if len(nome_final) > 3 and not any(p in nome_final for p in palavras_proibidas):
                return nome_final
                
    return None

# ============================================
# INTERFACE STREAMLIT
# ============================================
arquivo_enviado = st.file_uploader("Envie o PDF consolidado do lote", type=["pdf"])

if arquivo_enviado is not None:
    if st.button("Processar e Separar Documentos"):
        reader_pypdf = PdfReader(arquivo_enviado)
        zip_buffer = io.BytesIO()
        
        with pdfplumber.open(arquivo_enviado) as pdf_plumber:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                documento_atual = []
                tipo_doc_atual = None
                subtipo_atual = None
                nome_colaborador_atual = "COLABORADOR_DESCONHECIDO"
                contadores = {}

                for idx, page_plumber in enumerate(pdf_plumber.pages):
                    texto = extrair_texto_com_ocr(page_plumber)
                    
                    tipo_detectado = classificar_documento(texto)
                    nome_detectado = extrair_nome_colaborador(texto)
                    subtipo_detectado = extrair_subtipo_exame(texto)

                    if nome_detectado:
                        nome_colaborador_atual = nome_detectado

                    deve_quebrar = False
                    
                    if documento_atual:
                        if tipo_detectado and tipo_doc_atual and tipo_detectado != tipo_doc_atual:
                            deve_quebrar = True
                        
                        elif (tipo_detectado and tipo_doc_atual and 
                              tipo_detectado == tipo_doc_atual and
                              tipo_detectado in ["EXAME HEMOGRAMA", "EXAME BIOQUÍMICA SANGUÍNEA", 
                                                "EXAME TOXICOLÓGICO ÁCIDOS E METAIS", "LAUDO TIPAGEM SANGUINEA"]):
                            if subtipo_detectado and subtipo_atual and subtipo_detectado != subtipo_atual:
                                deve_quebrar = True
                        
                        elif (nome_detectado and 
                              nome_detectado != nome_colaborador_atual and
                              tipo_doc_atual not in ["ASO", "FICHA CLÍNICA", "AVALIAÇÃO PSICOLÓGICA", "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"]):
                            deve_quebrar = True

                    if deve_quebrar:
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
                        tipo_doc_atual = None
                        subtipo_atual = None

                    if tipo_detectado:
                        tipo_doc_atual = tipo_detectado
                    if subtipo_detectado:
                        subtipo_atual = subtipo_detectado

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
