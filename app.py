import os
import re
from pypdf import PdfReader, PdfWriter

# Pasta única onde os arquivos divididos e renomeados serão salvos
PASTA_SAIDA = r"./documentos_separados"

def classificar_documento(texto_pagina):
    """Identifica o tipo de documento pelas palavras-chave."""
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
        return None  # Continuação do documento anterior

def extrair_nome_colaborador(texto_pagina):
    """Extrai o nome do colaborador via Regex."""
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

def gerar_nome_arquivo_unico(pasta_destino, nome_base):
    """Aplica o sufixo (_1, _2) para vias repetidas do mesmo documento."""
    caminho_completo = os.path.join(pasta_destino, f"{nome_base}.pdf")
    if not os.path.exists(caminho_completo):
        return caminho_completo

    contador = 1
    while True:
        novo_caminho = os.path.join(pasta_destino, f"{nome_base}_{contador}.pdf")
        if not os.path.exists(novo_caminho):
            return novo_caminho
        contador += 1

def processar_pdf_prontuario(caminho_pdf_entrada):
    # Cria a pasta local de saída se ela ainda não existir
    if not os.path.exists(PASTA_SAIDA):
        os.makedirs(PASTA_SAIDA)

    reader = PdfReader(caminho_pdf_entrada)
    
    documento_atual = []
    tipo_doc_atual = None
    nome_colaborador_atual = None

    for page in reader.pages:
        texto = page.extract_text() or ""
        
        tipo_detectado = classificar_documento(texto)
        nome_detectado = extrair_nome_colaborador(texto)

        # Identifica se começou um novo documento
        eh_novo_documento = (tipo_detectado is not None and tipo_detectado != tipo_doc_atual) or \
                            (nome_detectado is not None and nome_detectado != nome_colaborador_atual and nome_colaborador_atual is not None)

        if eh_novo_documento and documento_atual:
            salvar_documento(documento_atual, tipo_doc_atual, nome_colaborador_atual)
            documento_atual = []

        if tipo_detectado:
            tipo_doc_atual = tipo_detectado
        if nome_detectado:
            nome_colaborador_atual = nome_detectado

        documento_atual.append(page)

    # Salva o último documento acumulado
    if documento_atual:
        salvar_documento(documento_atual, tipo_doc_atual, nome_colaborador_atual)

def salvar_documento(paginas, tipo_doc, nome_colaborador):
    if not nome_colaborador or not tipo_doc:
        print("[Aviso] Página ignorada ou não identificada.")
        return

    # Padrão do nome: TIPO DE DOCUMENTO - NOME DO COLABORADOR.pdf
    nome_base_arquivo = f"{tipo_doc} - {nome_colaborador}"
    caminho_final = gerar_nome_arquivo_unico(PASTA_SAIDA, nome_base_arquivo)

    writer = PdfWriter()
    for pag in paginas:
        writer.add_page(pag)

    with open(caminho_final, "wb") as output_pdf:
        writer.write(output_pdf)

    print(f"[Sucesso] Arquivo separado gerado: {caminho_final}")

# --- EXECUÇÃO ---
if __name__ == "__main__":
    pdf_lote = "prontuario_completo.pdf"  # Caminho do arquivo PDF completo
    processar_pdf_prontuario(pdf_lote)