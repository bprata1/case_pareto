import os
import json
import csv

# Obter diretório raiz do projeto e caminho para o dataset
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')

def carregar_dados_erp():
    """Carrega os arquivos locais (Mock ERP) para a memória."""
    fornecedores = []
    lojas = []
    extrato = []

    # Carregar fornecedores
    try:
        path_fornecedores = os.path.join(DATASET_DIR, 'mock_erp', 'respostas', 'GET_fornecedores.json')
        # Verifica se o arquivo existe na estrutura original caso não tenha sido movido corretamente
        if not os.path.exists(path_fornecedores):
            path_fornecedores = os.path.join(BASE_DIR, 'data', 'GET_fornecedores.json')
        
        with open(path_fornecedores, 'r', encoding='utf-8') as f:
            fornecedores = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar fornecedores: {e}")

    # Carregar lojas
    try:
        path_lojas = os.path.join(DATASET_DIR, 'mock_erp', 'respostas', 'GET_lojas.json')
        if not os.path.exists(path_lojas):
            path_lojas = os.path.join(BASE_DIR, 'data', 'GET_lojas.json')
            
        with open(path_lojas, 'r', encoding='utf-8') as f:
            lojas = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar lojas: {e}")

    # Carregar extrato
    try:
        path_extrato = os.path.join(DATASET_DIR, 'extrato_erp.csv')
        if not os.path.exists(path_extrato):
            path_extrato = os.path.join(BASE_DIR, 'data', 'extrato_erp.csv')
            
        with open(path_extrato, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            extrato = list(reader)
    except Exception as e:
        print(f"Erro ao carregar extrato ERP: {e}")

    return fornecedores, lojas, extrato

# Carregamento inicial em memória
FORNECEDORES, LOJAS, EXTRATO_ERP = carregar_dados_erp()

def validar_fornecedor(nome_extraido: str):
    """
    Busca o fornecedor (nome_extraido) via semelhança simples (lower case) no JSON de fornecedores.
    Retorna (cod_fornecedor, cnpj) se ATIVO.
    Lança ValueError se inativo ou não encontrado.
    """
    if not nome_extraido:
        raise ValueError("Nome do fornecedor não fornecido.")
        
    nome_busca = nome_extraido.strip().lower()
    
    for f in FORNECEDORES:
        nome_forn = f.get('nome', '').strip().lower()
        if nome_busca in nome_forn or nome_forn in nome_busca:
            if f.get('status') == 'ATIVO':
                return f.get('cod_fornecedor'), f.get('cnpj')
            else:
                raise ValueError(f"Fornecedor '{nome_extraido}' encontrado, mas está INATIVO.")
                
    raise ValueError(f"Fornecedor '{nome_extraido}' não encontrado na base do ERP.")

def validar_loja(nome_loja: str):
    """
    Busca a loja no JSON de lojas e retorna o código LOJA-###.
    Lança ValueError se não encontrada.
    """
    if not nome_loja:
        raise ValueError("Nome da loja não fornecido.")
        
    nome_busca = nome_loja.strip().lower()
    
    # LOJAS pode ser uma lista ou um dict dependendo de como o JSON está estruturado
    # Assumindo que é uma lista de dicts com 'nome' ou 'filial' e 'codigo' ou 'id'
    # Vamos tratar como uma lista de chaves/valores ou iterar de acordo
    if isinstance(LOJAS, dict):
        for codigo, nome in LOJAS.items():
            if isinstance(nome, str) and (nome_busca in nome.strip().lower() or nome.strip().lower() in nome_busca):
                return codigo
    elif isinstance(LOJAS, list):
        for l in LOJAS:
            nome = l.get('nome', l.get('filial', '')).strip().lower()
            if nome_busca in nome or nome in nome_busca:
                return l.get('codigo', l.get('id', l.get('cod_loja', '')))
                
    raise ValueError(f"Loja '{nome_loja}' não encontrada na base do ERP.")
