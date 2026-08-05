import os
import re
from pypdf import PdfReader, PdfWriter

# 1. Caminho base onde estão as pastas dos colaboradores
PASTA_DESTINO_BASE = r"C:\Caminho\Para\Sua\Pasta\Colaboradores"  # Ajuste para o seu caminho da rede/servidor

def classificar_documento(texto_pagina):
    """
    Identifica o tipo de documento pelo cabeçalho ou palavras-chave na página.
    """
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
        return None  # Indica que pode ser uma página de continuação do documento anterior

def extrair_nome_colaborador(texto_pagina):
    """
    Extrai o nome do colaborador da página usando REGEX.
    """
    padroes = [
        r'(?:Nome|COLABORADOR|Paciente|Candidato):\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})',
        r'EMPREGADO:\s*([A-ZÁÉÍÓÚÃÕÇ\s]{3,})'
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto_pagina, re.IGNORECASE)
        if match:
            nome = match.group(1).split('\n')[0].strip()
            # Limpa caracteres inválidos para nomes de arquivos/pastas
            nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)
            return re.sub(r'\s+', ' ', nome_limpo).upper()
            
    return None

def gerar_nome_arquivo_unico(pasta_destino, nome_base):
    """
    Garante a Opção B: Se o arquivo 'ASO - NOME.pdf' já existir,
    cria 'ASO - NOME_1.pdf', 'ASO - NOME_2.pdf', etc.
    """
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
    reader = PdfReader(caminho_pdf_entrada)
    total_paginas = len(reader.pages)
    
    documento_atual = []
    tipo_doc_atual = None
    nome_colaborador_atual = None

    for idx, page in enumerate(reader.pages):
        texto = page.extract_text() or ""
        
        tipo_detectado = classificar_documento(texto)
        nome_detectado = extrair_nome_colaborador(texto)

        # Se detectou um novo tipo de documento (e não é uma página vazia/continuação)
        # ou se o nome do colaborador mudou, salva o documento acumulado anteriormente
        eh_novo_documento = (tipo_detectado is not None and tipo_detectado != tipo_doc_atual) or \
                            (nome_detectado is not None and nome_detectado != nome_colaborador_atual and nome_colaborador_atual is not None)

        if eh_novo_documento and documento_atual:
            salvar_documento(documento_atual, tipo_doc_atual, nome_colaborador_atual)
            documento_atual = []

        # Atualiza o estado
        if tipo_detectado:
            tipo_doc_atual = tipo_detectado
        if nome_detectado:
            nome_colaborador_atual = nome_detectado

        # Adiciona a página ao buffer do documento atual
        documento_atual.append(page)

    # Salva o último documento processado do lote
    if documento_atual:
        salvar_documento(documento_atual, tipo_doc_atual, nome_colaborador_atual)

def salvar_documento(paginas, tipo_doc, nome_colaborador):
    if not nome_colaborador or not tipo_doc:
        print(f"[Aviso] Documento ignorado por falta de Identificação/Nome.")
        return

    # Pasta do colaborador específico
    pasta_colaborador = os.path.join(PASTA_DESTINO_BASE, nome_colaborador)

    # Cria a pasta caso ela ainda não exista
    if not os.path.exists(pasta_colaborador):
        os.makedirs(pasta_colaborador)

    # Define o nome base do arquivo
    nome_base_arquivo = f"{tipo_doc} - {nome_colaborador}"
    
    # Aplica a regra de sufixo (_1, _2) para duplicados
    caminho_final = gerar_nome_arquivo_unico(pasta_colaborador, nome_base_arquivo)

    # Escreve o novo PDF
    writer = PdfWriter()
    for pag in paginas:
        writer.add_page(pag)

    with open(caminho_final, "wb") as output_pdf:
        writer.write(output_pdf)

    print(f"[Sucesso] Arquivo salvo: {caminho_final}")

# --- EXECUÇÃO ---
if __name__ == "__main__":
    pdf_lote = "prontuario_completo.pdf"  # Nome do PDF consolidado a ser lido
    processar_pdf_prontuario(pdf_lote)