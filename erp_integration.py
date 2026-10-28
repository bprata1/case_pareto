import os
import re
import json
import csv
import uuid
import unicodedata
import difflib
from datetime import datetime, date

# Obter diretório raiz do projeto e caminho para o dataset
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')

CATEGORIAS_VALIDAS = [
    "GENERICOS",
    "MEDICAMENTOS_REFERENCIA",
    "MIP",
    "HIGIENE_BELEZA",
    "DERMOCOSMETICOS",
    "SUPLEMENTOS",
]

TETOS_CATEGORIA = {
    "GENERICOS": 15.0,
    "MEDICAMENTOS_REFERENCIA": 12.0,
    "MIP": 18.0,
    "HIGIENE_BELEZA": 20.0,
    "DERMOCOSMETICOS": 20.0,
    "SUPLEMENTOS": 20.0,
}

CATEGORIAS_EXCECAO_SAZONAL = {"GENERICOS", "MIP"}
TETO_EXCECAO_SAZONAL = 30.0

STOPWORDS_FORNECEDOR = {
    "ltda", "sa", "s.a", "s.a.", "industria", "farmaceutica", "distribuidora",
    "de", "do", "da", "dos", "das", "produtos", "higiene", "suplementos",
    "alimentares", "laboratorios", "farma", "cosmeticos", "genericos",
    "dermocosmeticos", "comercio", "cia", "empresa", "fornecedor"
}

STOPWORDS_LOJA = {
    "drog", "vitalis", "drogaria", "loja", "lojas", "unidade", "unidades",
    "filial", "filiais", "de", "do", "da", "dos", "das", "no", "na", "em", "rj"
}


def normalizar_texto(texto: str) -> str:
    """Remove acentos, caracteres especiais extras e converte para minúsculas."""
    if not texto:
        return ""
    texto_str = str(texto).strip().lower()
    nfkd = unicodedata.normalize('NFKD', texto_str)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Substituir pontuação como parênteses, barras e hifens por espaço (exceto quando tratado antes)
    limpo = re.sub(r"[^\w\s]", " ", sem_acento)
    limpo = re.sub(r"\s+", " ", limpo).strip()
    return limpo


def carregar_dados_erp():
    """Carrega os arquivos locais (Mock ERP) para a memória usando os.path."""
    fornecedores = {}
    lojas = {}
    extrato = []
    condicoes_vigentes = {}
    schema_post = {}

    try:
        path_fornecedores = os.path.join(DATASET_DIR, 'mock_erp', 'respostas', 'GET_fornecedores.json')
        if not os.path.exists(path_fornecedores):
            path_fornecedores = os.path.join(BASE_DIR, 'data', 'GET_fornecedores.json')
        with open(path_fornecedores, 'r', encoding='utf-8') as f:
            fornecedores = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar fornecedores: {e}")

    try:
        path_lojas = os.path.join(DATASET_DIR, 'mock_erp', 'respostas', 'GET_lojas.json')
        if not os.path.exists(path_lojas):
            path_lojas = os.path.join(BASE_DIR, 'data', 'GET_lojas.json')
        with open(path_lojas, 'r', encoding='utf-8') as f:
            lojas = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar lojas: {e}")

    try:
        path_extrato = os.path.join(DATASET_DIR, 'extrato_erp.csv')
        if not os.path.exists(path_extrato):
            path_extrato = os.path.join(BASE_DIR, 'data', 'extrato_erp.csv')
        with open(path_extrato, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            extrato = list(reader)
    except Exception as e:
        print(f"Erro ao carregar extrato ERP: {e}")

    try:
        path_condicoes = os.path.join(DATASET_DIR, 'mock_erp', 'respostas', 'GET_condicoes.json')
        if os.path.exists(path_condicoes):
            with open(path_condicoes, 'r', encoding='utf-8') as f:
                condicoes_vigentes = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar condicoes vigentes: {e}")

    try:
        path_schema = os.path.join(DATASET_DIR, 'mock_erp', 'schema', 'condicao_post.schema.json')
        if os.path.exists(path_schema):
            with open(path_schema, 'r', encoding='utf-8') as f:
                schema_post = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar schema post: {e}")

    return fornecedores, lojas, extrato, condicoes_vigentes, schema_post


FORNECEDORES_RAW, LOJAS_RAW, EXTRATO_ERP, CONDICOES_VIGENTES_RAW, SCHEMA_POST = carregar_dados_erp()


def obter_data_referencia_erp() -> date:
    """
    Retorna a data de referência do snapshot do ERP (consultado_em: 2026-09-30)
    para validação consistente dos e-mails do dataset.
    """
    try:
        consultado_em = ""
        if isinstance(FORNECEDORES_RAW, dict):
            consultado_em = FORNECEDORES_RAW.get("consultado_em", "")
        if consultado_em and len(consultado_em) >= 10:
            return datetime.strptime(consultado_em[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return date(2026, 9, 30)


def listar_fornecedores_erp() -> list:
    if isinstance(FORNECEDORES_RAW, dict):
        return FORNECEDORES_RAW.get("itens", [])
    elif isinstance(FORNECEDORES_RAW, list):
        return FORNECEDORES_RAW
    return []


def listar_lojas_erp() -> list:
    if isinstance(LOJAS_RAW, dict):
        return LOJAS_RAW.get("itens", [])
    elif isinstance(LOJAS_RAW, list):
        return LOJAS_RAW
    return []


def buscar_fornecedor_detalhado(termo_busca: str) -> dict:
    """
    Realiza busca resiliente de fornecedor (por código FORN-###, CNPJ, razão social,
    tokens principais ou fuzzy matching).
    Retorna dicionário com dados completos, incluindo status ATIVO/INATIVO e motivo.
    """
    if not termo_busca or not str(termo_busca).strip():
        return {
            "encontrado": False,
            "ativo": False,
            "cod_fornecedor": "",
            "razao_social": "",
            "cnpj": "",
            "status": "NAO_ENCONTRADO",
            "erro": "Nome ou código do fornecedor não informado."
        }

    termo_bruto = str(termo_busca).strip()
    lista_fornecedores = listar_fornecedores_erp()

    # 1. Verificar se o termo contém diretamente um código FORN-###
    match_cod = re.search(r"FORN[-_\s]?(\d{3})", termo_bruto.upper())
    if match_cod:
        cod_procurado = f"FORN-{match_cod.group(1)}"
        for f in lista_fornecedores:
            if f.get("cod_fornecedor", "").upper() == cod_procurado:
                return _formatar_retorno_fornecedor(f)

    # 2. Verificar por CNPJ (apenas dígitos)
    digitos_busca = re.sub(r"\D", "", termo_bruto)
    if len(digitos_busca) >= 8:
        for f in lista_fornecedores:
            digitos_cnpj = re.sub(r"\D", "", f.get("cnpj", ""))
            if digitos_busca in digitos_cnpj:
                return _formatar_retorno_fornecedor(f)

    # 3. Normalização textual e remoção de stopwords
    termo_norm = normalizar_texto(termo_bruto)
    tokens_busca = [t for t in termo_norm.split() if t not in STOPWORDS_FORNECEDOR and len(t) >= 2]
    if not tokens_busca:
        tokens_busca = termo_norm.split()

    melhor_cand = None
    melhor_score = 0.0

    for f in lista_fornecedores:
        razao = f.get("razao_social", f.get("nome", ""))
        razao_norm = normalizar_texto(razao)
        tokens_razao = [t for t in razao_norm.split() if t not in STOPWORDS_FORNECEDOR]
        marca_principal = tokens_razao[0] if tokens_razao else (razao_norm.split()[0] if razao_norm else "")

        # Match exato de substring normalizada
        if termo_norm in razao_norm or razao_norm in termo_norm:
            return _formatar_retorno_fornecedor(f)

        # Match da marca principal (ex: "alfa", "beta", "gama", "delta", "nutrivida", "epsilon", "zeta", "omega")
        if marca_principal and marca_principal in tokens_busca:
            return _formatar_retorno_fornecedor(f)

        # Verificar similaridade fuzzy com a marca principal ou razão social
        for tb in tokens_busca:
            if marca_principal:
                sim_marca = difflib.SequenceMatcher(None, tb, marca_principal).ratio()
                if sim_marca > melhor_score:
                    melhor_score = sim_marca
                    melhor_cand = f
            for tr in tokens_razao:
                sim_token = difflib.SequenceMatcher(None, tb, tr).ratio()
                if sim_token > melhor_score:
                    melhor_score = sim_token
                    melhor_cand = f

        sim_full = difflib.SequenceMatcher(None, " ".join(tokens_busca), " ".join(tokens_razao)).ratio()
        if sim_full > melhor_score:
            melhor_score = sim_full
            melhor_cand = f

    if melhor_cand and melhor_score >= 0.72:
        return _formatar_retorno_fornecedor(melhor_cand)

    return {
        "encontrado": False,
        "ativo": False,
        "cod_fornecedor": termo_bruto,
        "razao_social": "",
        "cnpj": "",
        "status": "NAO_ENCONTRADO",
        "erro": f"Fornecedor '{termo_bruto}' não encontrado na base do ERP (`GET_fornecedores.json`)."
    }


def _formatar_retorno_fornecedor(f: dict) -> dict:
    status = f.get("status", "INATIVO").upper()
    ativo = (status == "ATIVO")
    cod = f.get("cod_fornecedor", "")
    razao = f.get("razao_social", f.get("nome", ""))
    data_inat = f.get("data_inativacao")
    motivo_inat = f.get("motivo_inativacao")
    erro = None
    if not ativo:
        erro = (
            f"Fornecedor '{razao}' ({cod}) está com status {status} no ERP"
            + (f" desde {data_inat}" if data_inat else "")
            + (f" — Motivo: {motivo_inat}." if motivo_inat else ".")
        )
    return {
        "encontrado": True,
        "ativo": ativo,
        "cod_fornecedor": cod,
        "razao_social": razao,
        "cnpj": f.get("cnpj", ""),
        "status": status,
        "data_inativacao": data_inat,
        "motivo_inativacao": motivo_inat,
        "erro": erro
    }


def validar_fornecedor(nome_extraido: str):
    """
    Mantém compatibilidade com a assinatura original:
    Retorna (cod_fornecedor, cnpj) se ATIVO.
    Lança ValueError detalhado se INATIVO ou não encontrado.
    """
    info = buscar_fornecedor_detalhado(nome_extraido)
    if not info["encontrado"]:
        raise ValueError(info["erro"])
    if not info["ativo"]:
        raise ValueError(info["erro"])
    return info["cod_fornecedor"], info["cnpj"]


def detectar_referencia_indireta_lojas(texto_loja: str) -> bool:
    """
    Edge Case 5: Detecta quando o campo de lojas contém uma referência indireta
    (ex: 'lojas listadas na planilha anexa', 'conforme anexo', '10 lojas de maior giro').
    """
    if not texto_loja:
        return True
    norm = normalizar_texto(texto_loja)
    termos_indiretos = [
        "planilha", "anexo", "anexa", "listei", "listada", "listadas",
        "arquivo", "csv", "pendente", "definir", "maior giro", "a definir",
        "conforme tabela", "ver anexo", "vide anexo"
    ]
    for t in termos_indiretos:
        if t in norm:
            return True
    return False


def validar_loja(nome_loja: str) -> str:
    """
    Busca a loja no JSON de lojas de forma resiliente (código LOJA-###, REDE,
    nome sem acento, sem parênteses ou fuzzy matching) e retorna 'LOJA-###' ou 'REDE'.
    """
    if not nome_loja or not str(nome_loja).strip():
        raise ValueError("Nome ou código da loja não fornecido.")

    bruto = str(nome_loja).strip()
    norm = normalizar_texto(bruto)

    # Checar se é referência indireta a anexo
    if detectar_referencia_indireta_lojas(bruto):
        raise ValueError(
            f"Referência indireta de lojas detectada ('{bruto}'). "
            "Anexe a planilha correspondente ou informe os códigos das lojas (ex: LOJA-101) / REDE."
        )

    # Checar se representa toda a rede
    if norm in {"rede", "todas", "toda a rede", "todas as lojas", "rede completa", "nacional"} or "toda a rede" in norm or "todas as lojas" in norm:
        return "REDE"

    lista_lojas = listar_lojas_erp()

    # 1. Verificar se já é código LOJA-###
    match_cod = re.search(r"LOJA[-_\s]?(\d{3})", bruto.upper())
    if match_cod:
        cod_proc = f"LOJA-{match_cod.group(1)}"
        for l in lista_lojas:
            if l.get("cod_loja", "").upper() == cod_proc:
                if l.get("status", "ATIVA").upper() != "ATIVA":
                    raise ValueError(f"Loja '{cod_proc}' não está ATIVA no ERP.")
                return cod_proc
        raise ValueError(f"Código de loja '{cod_proc}' não existe no cadastro do ERP.")

    # 2. Normalizar tokens do nome da loja (ex: "Barra (shopping)" -> "barra shopping", "Méier" -> "meier")
    tokens_busca = [t for t in norm.split() if t not in STOPWORDS_LOJA]
    busca_limpa = " ".join(tokens_busca) if tokens_busca else norm

    melhor_loja = None
    melhor_score = 0.0

    for l in lista_lojas:
        nome_erp = l.get("nome", "")
        nome_erp_norm = normalizar_texto(nome_erp)
        tokens_erp = [t for t in nome_erp_norm.split() if t not in STOPWORDS_LOJA]
        erp_limpo = " ".join(tokens_erp)

        if busca_limpa and (busca_limpa == erp_limpo or busca_limpa in erp_limpo or erp_limpo in busca_limpa):
            return l.get("cod_loja")

        # Checar interseção de tokens relevantes
        if tokens_busca and tokens_erp and set(tokens_busca).issubset(set(tokens_erp)):
            return l.get("cod_loja")

        sim = difflib.SequenceMatcher(None, busca_limpa, erp_limpo).ratio()
        if sim > melhor_score:
            melhor_score = sim
            melhor_loja = l

    if melhor_loja and melhor_score >= 0.72:
        return melhor_loja.get("cod_loja")

    raise ValueError(f"Loja '{bruto}' não encontrada na base do ERP (`GET_lojas.json`).")


def resolver_lista_lojas(lojas_input) -> tuple:
    """
    Recebe lista ou string de lojas e retorna:
    (lista_codigos_validados, lista_erros, flag_busca_indireta)
    """
    if not lojas_input:
        return [], ["Nenhuma loja especificada."], True

    if isinstance(lojas_input, list):
        itens_brutos = []
        for x in lojas_input:
            if isinstance(x, str) and ("," in x or ";" in x):
                itens_brutos.extend([p.strip() for p in re.split(r"[,;]", x) if p.strip()])
            elif str(x).strip():
                itens_brutos.append(str(x).strip())
    else:
        texto = str(lojas_input).strip()
        if detectar_referencia_indireta_lojas(texto):
            return [], [
                f"Referência indireta a anexo ou lojas indefinidas detectada: '{texto}'. "
                "Faça upload da planilha anexa (CSV/XLSX) ou preencha as lojas manualmente."
            ], True
        # Separar por vírgula, ponto-e-vírgula ou ' e ' quando não fizer parte de nome composto conhecido
        if "," in texto or ";" in texto:
            itens_brutos = [p.strip() for p in re.split(r"[,;]", texto) if p.strip()]
        elif " e " in texto.lower() and "higiene" not in texto.lower():
            itens_brutos = [p.strip() for p in re.split(r"\s+e\s+", texto, flags=re.IGNORECASE) if p.strip()]
        else:
            itens_brutos = [texto]

    codigos = []
    erros = []
    flag_indireta = False

    for item in itens_brutos:
        if detectar_referencia_indireta_lojas(item):
            flag_indireta = True
        try:
            cod = validar_loja(item)
            if cod == "REDE":
                return ["REDE"], [], False
            if cod not in codigos:
                codigos.append(cod)
        except Exception as e:
            erros.append(str(e))

    return codigos, erros, flag_indireta


def normalizar_categoria(cat_input: str) -> str:
    """Normaliza o nome/código da categoria para o enum oficial do ERP."""
    if not cat_input:
        return ""
    bruto = str(cat_input).strip().upper()
    if bruto in CATEGORIAS_VALIDAS:
        return bruto

    norm = normalizar_texto(cat_input)
    mapa = {
        "generico": "GENERICOS",
        "genericos": "GENERICOS",
        "referencia": "MEDICAMENTOS_REFERENCIA",
        "medicamentos de referencia": "MEDICAMENTOS_REFERENCIA",
        "medicamento de referencia": "MEDICAMENTOS_REFERENCIA",
        "rx": "MEDICAMENTOS_REFERENCIA",
        "mip": "MIP",
        "isento": "MIP",
        "isentos": "MIP",
        "otc": "MIP",
        "higiene": "HIGIENE_BELEZA",
        "beleza": "HIGIENE_BELEZA",
        "higiene e beleza": "HIGIENE_BELEZA",
        "hpc": "HIGIENE_BELEZA",
        "perfumaria": "HIGIENE_BELEZA",
        "dermo": "DERMOCOSMETICOS",
        "dermocosmetico": "DERMOCOSMETICOS",
        "dermocosmeticos": "DERMOCOSMETICOS",
        "suplemento": "SUPLEMENTOS",
        "suplementos": "SUPLEMENTOS",
        "nutricao": "SUPLEMENTOS",
        "vitaminas": "SUPLEMENTOS",
    }
    for chave, valor in mapa.items():
        if chave in norm:
            return valor

    # Fuzzy match contra CATEGORIAS_VALIDAS
    matches = difflib.get_close_matches(bruto, CATEGORIAS_VALIDAS, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return bruto


def validar_vigencia(data_inicio_str: str, data_fim_str: str, data_referencia: date = None) -> dict:
    """
    Edge Case 7 — Regra 6 da Política Comercial:
    - Toda condição deve ter data de início e data de fim definidas.
    - Não é permitido cadastrar condição com data de início anterior à data do cadastro (retroativa).
    - A vigência máxima de uma condição é de 12 (doze) meses.
    """
    if data_referencia is None:
        data_referencia = obter_data_referencia_erp()

    erros = []
    if not data_inicio_str or not str(data_inicio_str).strip() or str(data_inicio_str).strip().lower() == "null":
        erros.append("Data de início é obrigatória (Regra 6).")
    if not data_fim_str or not str(data_fim_str).strip() or str(data_fim_str).strip().lower() == "null":
        erros.append("Data de fim é obrigatória (Regra 6).")

    if erros:
        return {"valido": False, "erros": erros, "dias_vigencia": None}

    try:
        dt_ini = datetime.strptime(str(data_inicio_str).strip()[:10], "%Y-%m-%d").date()
    except Exception:
        erros.append(f"Data de início '{data_inicio_str}' inválida. Use o formato YYYY-MM-DD.")
        dt_ini = None

    try:
        dt_fim = datetime.strptime(str(data_fim_str).strip()[:10], "%Y-%m-%d").date()
    except Exception:
        erros.append(f"Data de fim '{data_fim_str}' inválida. Use o formato YYYY-MM-DD.")
        dt_fim = None

    if not dt_ini or not dt_fim:
        return {"valido": False, "erros": erros, "dias_vigencia": None}

    if dt_fim < dt_ini:
        erros.append(f"Data de fim ({dt_fim}) não pode ser anterior à data de início ({dt_ini}).")

    # Proibição de data retroativa (Regra 6)
    if dt_ini < data_referencia:
        erros.append(
            f"Data de início retroativa proibida pela Regra 6: início em {dt_ini.strftime('%Y-%m-%d')} "
            f"é anterior à data de referência do cadastro ({data_referencia.strftime('%Y-%m-%d')})."
        )

    # Limite máximo de 12 meses (Regra 6)
    # Calculando a data limite exata de 12 meses à frente
    try:
        ano_limite = dt_ini.year + 1
        mes_limite = dt_ini.month
        dia_limite = dt_ini.day
        try:
            dt_limite_12m = date(ano_limite, mes_limite, dia_limite)
        except ValueError:
            # Caso 29 de fevereiro em ano bissexto -> 28 de fevereiro do ano seguinte
            dt_limite_12m = date(ano_limite, mes_limite, 28)
    except Exception:
        dt_limite_12m = dt_ini

    dias_vigencia = (dt_fim - dt_ini).days + 1
    # Nota: De 2026-10-01 a 2027-09-30 são 365 dias (12 meses exatos).
    # De 2026-10-01 a 2027-10-01 seriam 366 dias (1 ano e 1 dia se inclusivo, mas aceitamos até dt_limite_12m).
    if dt_fim > dt_limite_12m:
        erros.append(
            f"Vigência superior a 12 meses proibida pela Regra 6: período de {dt_ini} a {dt_fim} "
            f"({dias_vigencia} dias) ultrapassa o limite máximo de 12 meses ({dt_limite_12m})."
        )

    return {
        "valido": len(erros) == 0,
        "erros": erros,
        "dias_vigencia": dias_vigencia
    }


def verificar_sobreposicao_extrato(
    cod_fornecedor: str,
    cod_categoria: str,
    lojas: list,
    data_inicio_str: str,
    data_fim_str: str,
    cod_condicao_substituida: str = None
) -> dict:
    """
    Edge Case 6 — Regra 9 (Sobreposição Contratual):
    Cruza os parâmetros com `dataset/extrato_erp.csv` (onde STATUS == 'VIGENTE').
    Se o mesmo fornecedor, categoria e loja tiverem datas conflitantes/sobrepostas,
    retorna os detalhes do conflito para barrar o cadastro.
    """
    conflitos = []
    if not cod_fornecedor or not cod_categoria or not lojas or not data_inicio_str or not data_fim_str:
        return {"tem_conflito": False, "conflitos": [], "mensagem": ""}

    try:
        dt_ini_nova = datetime.strptime(str(data_inicio_str).strip()[:10], "%Y-%m-%d").date()
        dt_fim_nova = datetime.strptime(str(data_fim_str).strip()[:10], "%Y-%m-%d").date()
    except Exception:
        return {"tem_conflito": False, "conflitos": [], "mensagem": ""}

    cod_forn_upper = str(cod_fornecedor).strip().upper()
    cod_cat_upper = normalizar_categoria(cod_categoria)
    lojas_upper = [str(l).strip().upper() for l in lojas if str(l).strip()]
    cond_subst_upper = str(cod_condicao_substituida).strip().upper() if cod_condicao_substituida else ""

    conflitos_por_cond = {}

    for row in EXTRATO_ERP:
        status_row = str(row.get("STATUS", "")).strip().upper()
        if status_row != "VIGENTE":
            continue

        forn_row = str(row.get("COD_FORN", "")).strip().upper()
        cat_row = str(row.get("CATEG", "")).strip().upper()
        loja_row = str(row.get("COD_LOJA", "")).strip().upper()
        cond_id = str(row.get("COND_ID", "")).strip().upper()

        # Se o usuário explicitamente informou que esta condição substitui a COND-### vigente, não há conflito com ela
        if cond_subst_upper and cond_id == cond_subst_upper:
            continue

        if forn_row != cod_forn_upper or cat_row != cod_cat_upper:
            continue

        # Verificar sobreposição de loja
        loja_sobrepoe = (
            loja_row == "REDE"
            or "REDE" in lojas_upper
            or loja_row in lojas_upper
        )
        if not loja_sobrepoe:
            continue

        # Converter datas do CSV (YYYYMMDD)
        dt_ini_csv_str = str(row.get("DT_INI", "")).strip()
        dt_fim_csv_str = str(row.get("DT_FIM", "")).strip()
        try:
            dt_ini_csv = datetime.strptime(dt_ini_csv_str, "%Y%m%d").date()
            dt_fim_csv = datetime.strptime(dt_fim_csv_str, "%Y%m%d").date()
        except Exception:
            continue

        # Verificar sobreposição de intervalo de datas: [A, B] e [C, D] se sobrepõem sse A <= D e B >= C
        if dt_ini_nova <= dt_fim_csv and dt_fim_nova >= dt_ini_csv:
            if cond_id not in conflitos_por_cond:
                conflitos_por_cond[cond_id] = {
                    "cod_condicao": cond_id,
                    "cod_fornecedor": forn_row,
                    "cod_categoria": cat_row,
                    "lojas_conflitantes": [],
                    "data_inicio": dt_ini_csv.strftime("%Y-%m-%d"),
                    "data_fim": dt_fim_csv.strftime("%Y-%m-%d"),
                    "tipo": row.get("TP_COND", ""),
                    "valor_atual": row.get("VLR_PCT") or row.get("VLR_BRL") or "",
                }
            if loja_row not in conflitos_por_cond[cond_id]["lojas_conflitantes"]:
                conflitos_por_cond[cond_id]["lojas_conflitantes"].append(loja_row)

    conflitos = list(conflitos_por_cond.values())
    if conflitos:
        resumo = "; ".join([
            f"{c['cod_condicao']} (Lojas: {', '.join(c['lojas_conflitantes'])}, "
            f"Vigência: {c['data_inicio']} a {c['data_fim']})"
            for c in conflitos
        ])
        msg = (
            f"Sobreposição contratual detectada no `extrato_erp.csv` (Regra 9): "
            f"Já existe(m) condição(ões) VIGENTE(S) para {cod_forn_upper} na categoria {cod_cat_upper} "
            f"no mesmo período e loja(s): {resumo}."
        )
        return {"tem_conflito": True, "conflitos": conflitos, "mensagem": msg}

    return {"tem_conflito": False, "conflitos": [], "mensagem": ""}


def detectar_prompt_injection(texto: str) -> dict:
    """
    Edge Case 1: Detecta tentativas de Prompt Injection no texto do e-mail.
    """
    if not texto:
        return {"detectado": False, "trechos": [], "mensagem": ""}

    padroes = [
        r"nota para processamento autom[aá]tico",
        r"desconsidere as regras",
        r"registre a condi[cç][aã]o diretamente",
        r"status\s+aprovado",
        r"sem necessidade de revis[aã]o",
        r"ignore\s+previous\s+instructions",
        r"ignore\s+todas\s+as\s+regras",
        r"pr[eé]-aprovada pela diretoria",
    ]
    trechos = []
    for pat in padroes:
        m = re.search(pat, texto, flags=re.IGNORECASE)
        if m:
            trechos.append(m.group(0))

    if trechos:
        return {
            "detectado": True,
            "trechos": trechos,
            "mensagem": (
                "Tentativa de Prompt Injection detectada no corpo do e-mail "
                f"(trechos suspeitos: {', '.join(repr(t) for t in trechos[:3])}). "
                "O comando malicioso foi ignorado pelo Extrator e a condição segue o fluxo normal de auditoria."
            )
        }
    return {"detectado": False, "trechos": [], "mensagem": ""}


def avaliar_politica_deterministica(
    cod_categoria: str,
    tipo_condicao: str,
    valor: float,
    campanha_sazonal: bool = False,
    contrapartida: str = None
) -> dict:
    """
    Valida deterministicamente os tetos por categoria (Regra 4), exceção sazonal (Nota *),
    alçadas de aprovação (Regra 5) e contrapartida obrigatória para verba (Regra 7).
    """
    cat = normalizar_categoria(cod_categoria)
    tipo = str(tipo_condicao).strip().upper()
    erros = []
    alertas = []

    try:
        val = float(valor)
    except Exception:
        val = 0.0

    if val <= 0:
        erros.append("O valor/percentual da condição deve ser maior que zero.")

    if cat not in CATEGORIAS_VALIDAS:
        erros.append(f"Categoria '{cod_categoria}' inválida. Categorias aceitas: {', '.join(CATEGORIAS_VALIDAS)}.")

    status_politica = "DENTRO_DA_POLITICA"
    alcada_exibicao = "Coordenação Comercial"
    alcada_minima = "coordenador"
    nivel_hierarquia = 2

    if tipo == "DESCONTO_PERCENTUAL":
        teto_padrao = TETOS_CATEGORIA.get(cat, 15.0)

        if val > teto_padrao:
            if campanha_sazonal and cat in CATEGORIAS_EXCECAO_SAZONAL and val <= TETO_EXCECAO_SAZONAL:
                status_politica = "EXCECAO_SAZONAL"
                alertas.append(
                    f"Exceção Sazonal aplicada (Nota * da Política): Desconto de {val:.2f}% em {cat} "
                    f"acima do teto padrão ({teto_padrao:.0f}%), permitido até {TETO_EXCECAO_SAZONAL:.0f}% "
                    "em campanhas sazonais aprovadas pelo Trade Marketing."
                )
            else:
                status_politica = "FORA_DA_POLITICA"
                erros.append(
                    f"Desconto de {val:.2f}% excede o teto permitido de {teto_padrao:.0f}% para a categoria {cat} (Regra 4)."
                )

        # Definir alçada (Regra 5)
        if val <= 10.0:
            alcada_exibicao = "Coordenação Comercial"
            alcada_minima = "coordenador"
            nivel_hierarquia = 2
        elif val <= 20.0:
            alcada_exibicao = "Gerência Comercial"
            alcada_minima = "gerente"
            nivel_hierarquia = 3
        elif val <= 25.0:
            alcada_exibicao = "Diretoria Comercial"
            alcada_minima = "diretor"
            nivel_hierarquia = 4
        elif status_politica == "EXCECAO_SAZONAL" and val <= 30.0:
            # Exceção sazonal entre 25% e 30% (ex: Alfa 28%): permitido pela Nota (*) + Regra 11 (Diretoria Comercial)
            alcada_exibicao = "Diretoria Comercial (Exceção Sazonal / Trade Marketing)"
            alcada_minima = "diretor"
            nivel_hierarquia = 4
        else:
            alcada_exibicao = "VEDADO"
            alcada_minima = "vedado"
            nivel_hierarquia = 99
            status_politica = "FORA_DA_POLITICA"
            if not any("excede o teto" in e for e in erros):
                erros.append(f"Desconto percentual de {val:.2f}% é VEDADO pela Política Comercial (Regra 5).")

    elif tipo == "VERBA_EXPOSICAO":
        # Regra 7: Toda verba de exposição deve estar vinculada a uma contrapartida descrita
        if not contrapartida or not str(contrapartida).strip() or str(contrapartida).strip().lower() == "null":
            erros.append("Toda Verba de Exposição exige uma contrapartida descrita (Regra 7).")

        if val <= 5000.0:
            alcada_exibicao = "Gerência Comercial"
            alcada_minima = "gerente"
            nivel_hierarquia = 3
        elif val <= 20000.0:
            alcada_exibicao = "Diretoria Comercial"
            alcada_minima = "diretor"
            nivel_hierarquia = 4
        else:
            alcada_exibicao = "Comitê Comercial (Diretoria)"
            alcada_minima = "diretor"
            nivel_hierarquia = 4
    else:
        erros.append(f"Tipo de condição '{tipo}' inválido. Use DESCONTO_PERCENTUAL ou VERBA_EXPOSICAO.")

    if erros:
        status_politica = "FORA_DA_POLITICA"

    return {
        "aprovado_politica": status_politica in ["DENTRO_DA_POLITICA", "EXCECAO_SAZONAL"] and len(erros) == 0,
        "status_politica": status_politica,
        "alcada_exibicao": alcada_exibicao,
        "alcada_minima": alcada_minima,
        "nivel_hierarquia": nivel_hierarquia,
        "erros": erros,
        "alertas": alertas,
    }


def construir_payload_erp(
    cod_fornecedor: str,
    cod_categoria: str,
    tipo: str,
    valor: float,
    lojas: list,
    data_inicio: str,
    data_fim: str,
    aprovador_nome: str,
    aprovador_matricula: str = "000000",
    contrapartida: str = None,
    cod_condicao_substituida: str = None,
    origem_referencia: str = "Processamento AI Builder"
) -> dict:
    """
    Constrói o Payload JSON rigorosamente aderente ao `condicao_post.schema.json`.
    """
    tipo_upper = str(tipo).strip().upper()
    payload = {
        "cod_fornecedor": str(cod_fornecedor).strip().upper(),
        "cod_categoria": normalizar_categoria(cod_categoria),
        "tipo": tipo_upper,
        "lojas": [str(l).strip().upper() for l in lojas if str(l).strip()],
        "data_inicio": str(data_inicio).strip()[:10],
        "data_fim": str(data_fim).strip()[:10],
        "aprovador": {
            "matricula": str(aprovador_matricula).strip() or "000000",
            "nome": str(aprovador_nome).strip() or "Pendente Aprovação"
        },
        "origem": {
            "tipo": "EMAIL",
            "referencia": str(origem_referencia).strip() or "Processamento AI Builder"
        }
    }

    val_num = round(float(valor), 2)
    if tipo_upper == "DESCONTO_PERCENTUAL":
        payload["percentual"] = val_num
    else:
        payload["valor"] = val_num

    if contrapartida and str(contrapartida).strip() and str(contrapartida).strip().lower() != "null":
        payload["contrapartida"] = str(contrapartida).strip()[:500]

    if cod_condicao_substituida and str(cod_condicao_substituida).strip() and str(cod_condicao_substituida).strip().lower() != "null":
        payload["cod_condicao_substituida"] = str(cod_condicao_substituida).strip().upper()

    return payload


def validar_schema_payload(payload: dict) -> tuple:
    """
    Valida se o dicionário de payload cumpre todas as regras de `condicao_post.schema.json`.
    Retorna (valido: bool, erros: list).
    """
    erros = []
    obrigatorios = ["cod_fornecedor", "cod_categoria", "tipo", "lojas", "data_inicio", "data_fim", "aprovador", "origem"]
    for campo in obrigatorios:
        if campo not in payload or payload[campo] in [None, "", []]:
            erros.append(f"Campo obrigatório '{campo}' ausente ou vazio no payload.")

    cod_forn = str(payload.get("cod_fornecedor", ""))
    if not re.match(r"^FORN-\d{3}$", cod_forn):
        erros.append(f"cod_fornecedor '{cod_forn}' fora do padrão '^FORN-\\d{{3}}$'.")

    cod_cat = str(payload.get("cod_categoria", ""))
    if cod_cat not in CATEGORIAS_VALIDAS:
        erros.append(f"cod_categoria '{cod_cat}' fora do enum permitido.")

    tipo = str(payload.get("tipo", ""))
    if tipo == "DESCONTO_PERCENTUAL":
        if "percentual" not in payload or payload["percentual"] <= 0 or payload["percentual"] > 100:
            erros.append("Campo 'percentual' (0 < p <= 100) obrigatório para DESCONTO_PERCENTUAL.")
        if "valor" in payload:
            erros.append("Campo 'valor' proibido quando tipo = DESCONTO_PERCENTUAL.")
    elif tipo == "VERBA_EXPOSICAO":
        if "valor" not in payload or payload["valor"] <= 0:
            erros.append("Campo 'valor' (> 0) obrigatório para VERBA_EXPOSICAO.")
        if "percentual" in payload:
            erros.append("Campo 'percentual' proibido quando tipo = VERBA_EXPOSICAO.")
    else:
        erros.append(f"Tipo '{tipo}' inválido.")

    lojas = payload.get("lojas", [])
    if not isinstance(lojas, list) or len(lojas) == 0:
        erros.append("Campo 'lojas' deve ser uma lista não vazia.")
    else:
        for lj in lojas:
            if not re.match(r"^(LOJA-\d{3}|REDE)$", str(lj)):
                erros.append(f"Código de loja '{lj}' fora do padrão '^(LOJA-\\d{{3}}|REDE)$'.")

    if "cod_condicao_substituida" in payload:
        if not re.match(r"^COND-\d{3}$", str(payload["cod_condicao_substituida"])):
            erros.append(f"cod_condicao_substituida '{payload['cod_condicao_substituida']}' fora do padrão '^COND-\\d{{3}}$'.")

    return (len(erros) == 0, erros)


def envelopar_requisicao_post(payload: dict) -> dict:
    """
    Envelopa o body no formato ilustrativo completo de requisição POST /api/v1/condicoes
    (com headers Content-Type e Idempotency-Key UUID v4), conforme `POST_condicoes_request.json`.
    """
    return {
        "metodo": "POST",
        "caminho": "/api/v1/condicoes",
        "headers": {
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4())
        },
        "body": payload
    }
