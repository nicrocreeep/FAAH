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
    # Se o texto for muito curto, provavelmente é imagem ou OCR falhou parcialmente
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
    # PRIORIDADE 1: DOCUMENTOS ESTRUTURAIS/FICHAS
    # (Devem vir antes porque contêm listas de exames solicitados)
    # ============================================
    if "FICHA CLÍNICA" in texto or "FICHA CLINICA" in texto or \
       ("ANTECEDENTES FAMILIARES" in texto and "ANTECEDENTES PESSOAIS" in texto):
        return "FICHA CLÍNICA"
    
    if "ATESTADO DE SAÚDE OCUPACIONAL" in texto or "ATESTADO DE SAUDE OCUPACIONAL" in texto:
        return "ASO"
    
    # ============================================
    # PRIORIDADE 2: AVALIAÇÕES ESPECÍFICAS
    # ============================================
    if "AVALIAÇÃO PSICOLÓGICA" in texto or "AVALIACAO PSICOLOGICA" in texto or \
       "PROTOCOLO MÉDICO COMPLEMENTAR PARA AVALIAÇÃO PSICOSOCIAL" in texto or \
       "AVALIAÇÃO PSICOSOCIAL" in texto or "AVALIACAO PSICOSSOCIAL" in texto or \
       "QUESTIONÁRIO SRQ-20" in texto:
        return "AVALIAÇÃO PSICOLÓGICA"

    # NOVO: Avaliação do Equilíbrio / Vestibular / Cerebelar (inclui Romberg, VPPB, etc.)
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
    # PRIORIDADE 3: EXAMES VISUAIS
    # ============================================
    if "ACUIDADE VISUAL" in texto or "OD:20/" in texto or "OE:20/" in texto or \
       "SNELLEN" in texto or "EYETEST" in texto:
        return "EXAME ACUIDADE VISUAL"
    if "ISHIHARA" in texto or "JAEGER" in texto or "SENSIBILIDADE DE CONTRASTE" in texto:
        return "EXAME SENSIBILIDADE E CORES"
    
    # ============================================
    # PRIORIDADE 4: EXAMES DE IMAGEM / LAUDOS ESPECÍFICOS
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
    # PRIORIDADE 5: EXAMES TOXICOLÓGICOS / URINA
    # ============================================
    if any(x in texto for x in [
        "ÁCIDO HIPÚRICO", "ACIDO HIPURICO", "ÁCIDO METIL HIPÚRICO", 
        "ACIDO METIL HIPURICO", "METILHIPÚRICO", "METILHIPURICO", "HIPÚRICO", "HIPURICO"
    ]):
        return "EXAME TOXICOLÓGICO ÁCIDOS"
    
    if "CREATININA" in texto and ("G/G" in texto or "G/G CREATININA" in texto):
        return "EXAME TOXICOLÓGICO ÁCIDOS"
    
    # ============================================
    # PRIORIDADE 6: EXAMES LABORATORIAIS SANGUÍNEOS
    # ============================================
    # Hemograma completo (evita falso positivo em fichas clínicas que listam exames)
    if "HEMOGRAMA COMPLETO" in texto or \
       ("HEMOGRAMA" in texto and any(x in texto for x in [
           "HEMACIAS", "HEMOGLOBINA", "HEMATOCRITO", "HEMATÓCRITO",
           "LEUCOCITOS", "LEUCÓCITOS", "PLAQUETAS", "V.C.M", "H.C.M", "RDW"
       ])):
        return "EXAME HEMOGRAMA"
    
    # Bioquímica sanguínea (GAMA GT, TGO, TGP, Glicose) - mas sem Hemograma
    if any(x in texto for x in [
        "GAMA GT", "GAMA-GLUTAMIL", "GGT", "GLUTAMILTRANSFERASE", "GLUTAMIL TRANSFERASE",
        "TGO", "TRANSAMINASE OXALACETICA", "TRANSAMINASE OXALACÉTICA", "ASPARTATO AMINOTRANSFERASE",
        "TGP", "TRANSAMINASE PIRUVICA", "TRANSAMINASE PIRÚVICA", "ALANINA AMINOTRANSFERASE",
        "GLICOSE", "GLICOSE JEJUM", "CREATININA", "UREIA", "ÁCIDO ÚRICO"
    ]):
        return "EXAME BIOQUÍMICA SANGUÍNEA"
    
    # ============================================
    # PRIORIDADE 7: ENCAMINHAMENTOS E GENÉRICOS
    # ============================================
    if "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL" in texto or \
       ("ENCAMINHAMENTO" in texto and "MEDICINA" in texto):
        return "ENCAMINHAMENTO DA MEDICINA OCUPACIONAL"
    
    if "RESULTADO DE EXAMES" in texto:
        return "RESULTADO DE EXAMES"
    
    # Fallback
    if "EXAME" in texto or "LAUDO" in texto:
        return "RESULTADO DE EXAMES"
    
    return None

def extrair_subtipo_exame(texto_pagina):
    """Extrai o subtipo específico do exame para quebrar laboratoriais separados."""
    if not texto_pagina:
        return None
    texto = texto_pagina.upper()
    
    if "HEMOGRAMA COMPLETO" in texto or ("HEMOGRAMA" in texto and "HEMACIAS" in texto):
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
    if "GRUPO SANGUINEO" in texto or "GRUPO SANGUÍNEO" in texto or ("ABO" in texto and "RH" in texto):
        return "TIPAGEM_SANGUINEA"
    return None

def extrair_nome_colaborador(texto_pagina):
    if not texto_pagina:
        return None
        
    texto = texto_pagina.upper()
    
    # Padroes melhorados e ordenados por especificidade
    padroes = [
        # Avaliação Psicológica / Equilíbrio: AVALIADO: Carlos Gabriel Jesus dos Santos
        r'AVALIADO[:\s]+([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|CARGO|CPF|RG|$)',
        
        # Audiometria: Funcionário/Paciente: CARLOS GABRIEL JESUS DOS SANTOS
        r'FUNCIONÁRIO/PACIENTE[:\s]+([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|IDADE|SEXO|EMPRESA|$)',
        
        # Formato: Funcionário (Código / Nome) \n 193 / Antonio Marcos...
        r'FUNCIONÁRIO\s*\(CÓDIGO\s*/\s*NOME\)\s*\n?\s*\d+\s*/\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|EMPRESA|RG|CPF|$)',
        
        # Formato: Funcionário: 193 - Antonio Marcos...
        r'FUNCIONÁRIO:\s*\d+\s*-\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|UNIDADE|CNPJ|RG|CPF|$)',
        
        # Formato SOC/Labs: Nome........:134497-ANTONIO MARCOS SIQUEIRA DE SOUZA
        r'NOME\.{2,}\s*:\s*\d*[-–]?\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|DATA|SEXO|$)',
        
        # Formato simples: Nome: ANTONIO MARCOS...
        r'NOME\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|RG|DATA|SEXO|EMPRESA|$)',
        
        # Genéricos
        r'(?:COLABORADOR|PACIENTE|CANDIDATO|EMPREGADO|NOME DO TRABALHADOR|SR\(A\))\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|CPF|RG|DATA|SEXO|$)',
        
        # Laudo médico: Paciente : CARLOS GABRIEL JESUS DOS SANTOS
        r'PACIENTE\s*:\s*([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,60})(?=\n|DATA|CPF|RG|IDADE|SEXO|$)',
        
        # Cabeçalho ECG/EEG: ANTONIO MARCOS SIQUEIRA DE SOUZA - Código do exame
        r'^([A-ZÁÉÍÓÚÃÕÇÂÊÎÔÛ\s]{3,50})\s*-\s*CÓDIGO\s+DO\s+EXAME',
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE | re.MULTILINE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            # Remove sujeira comum que vem grudada no nome
            stops = ['SEXO', 'CARGO', 'CPF', 'RG', 'DATA', 'IDADE', 'PIS', 'CTPS', 
                     'CADASTRO', 'ATEND', 'UNIDADE', 'SETOR', 'EMPRESA', 'CNPJ', 
                     'MÉDICO', 'MEDICO', 'PROTOCOLO', 'CONVÊNIO', 'CONVENIO']
            for stop in stops:
                nome = re.split(rf'\\b{stop}\\b', nome, flags=re.IGNORECASE)[0]
            nome_limpo = re.sub(r'[\\\\/*?:"<>|]', '', nome)
            nome_final = re.sub(r'\\s+', ' ', nome_limpo).upper().strip()
            # Remove números/códigos soltos no início (ex: 134497-)
            nome_final = re.sub(r'^\\d+[\\s\\-–]+', '', nome_final)
            if len(nome_final) > 3:
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

                    # Propaga nome do colaborador
                    if nome_detectado:
                        nome_colaborador_atual = nome_detectado

                    # ==========================================
                    # LÓGICA DE QUEBRA DE DOCUMENTO
                    # ==========================================
                    deve_quebrar = False
                    
                    if documento_atual:
                        # 1. Mudou o tipo principal detectado
                        if tipo_detectado and tipo_doc_atual and tipo_detectado != tipo_doc_atual:
                            deve_quebrar = True
                        
                        # 2. Mudou o subtipo dentro de exames laboratoriais
                        # (ex: Hemograma -> GAMA GT, ou Tipagem -> Hemograma)
                        elif (tipo_detectado and tipo_doc_atual and 
                              tipo_detectado == tipo_doc_atual and
                              tipo_detectado in ["EXAME HEMOGRAMA", "EXAME BIOQUÍMICA SANGUÍNEA", 
                                                "EXAME TOXICOLÓGICO ÁCIDOS", "LAUDO TIPAGEM SANGUINEA"]):
                            if subtipo_detectado and subtipo_atual and subtipo_detectado != subtipo_atual:
                                deve_quebrar = True
                        
                        # 3. Mudou o nome do colaborador no meio do lote (novo funcionário)
                        #    Exceto para documentos que podem ter referências a médicos/avalistas
                        elif (nome_detectado and 
                              nome_detectado != nome_colaborador_atual and
                              tipo_doc_atual not in ["ASO", "FICHA CLÍNICA", "AVALIAÇÃO PSICOLÓGICA"]):
                            deve_quebrar = True
                        
                        # 4. Página parece ser cabeçalho de novo documento de lab/imagem
                        #    (tem nome + tipo próprio, e o documento atual já tem páginas)
                        elif (nome_detectado and tipo_detectado and 
                              tipo_doc_atual and tipo_detectado != tipo_doc_atual):
                            deve_quebrar = True

                    if deve_quebrar:
                        # ---- SALVAR DOCUMENTO ANTERIOR ----
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
                        
                        # ---- RESETAR ESTADO PARA NOVO DOCUMENTO ----
                        documento_atual = []
                        tipo_doc_atual = None
                        subtipo_atual = None
                        # nome_colaborador_atual mantém para propagação, 
                        # mas será sobrescrito se nome_detectado na próxima página

                    # Atualiza tipo e subtipo se detectados nesta página
                    if tipo_detectado:
                        tipo_doc_atual = tipo_detectado
                    if subtipo_detectado:
                        subtipo_atual = subtipo_detectado

                    documento_atual.append(reader_pypdf.pages[idx])

                # ---- FECHA ÚLTIMO DOCUMENTO ----
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
