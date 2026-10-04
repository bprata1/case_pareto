import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Carregar variáveis de ambiente (GEMINI_API_KEY)
load_dotenv()

# Importações locais
from politica_comercial import TEXTO_POLITICA
from prompts import PROMPT_EXTRATOR, PROMPT_AUDITOR

# Instanciar o client do Gemini
client = genai.Client()

def extrair_condicoes(texto_email: str) -> dict:
    """
    Agente 1 (Extrator): Lê o e-mail desestruturado e retorna um JSON
    com os valores puros extraídos da negociação.
    """
    try:
        config = types.GenerateContentConfig(
            system_instruction=PROMPT_EXTRATOR,
            response_mime_type="application/json"
        )
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=texto_email,
            config=config
        )
        
        # Faz o parse da resposta em texto para um dicionário Python
        return json.loads(response.text)
    except Exception as e:
        print(f"Erro no Agente 1 (Extrator): {e}")
        return {"erro": "Falha na comunicação com a IA."}


def auditar_condicoes(condicoes_extraidas_json: str) -> dict:
    """
    Agente 2 (Auditor): Recebe o JSON limpo do Agente 1 e as regras da Política Comercial,
    avaliando se o desconto está no limite e definindo quem deve aprovar.
    """
    try:
        # Monta o input unindo as condições extraídas com o texto da política
        input_ia = f"""
Condições Extraídas (JSON):
{condicoes_extraidas_json}

=============================

Política Comercial Vigente:
{TEXTO_POLITICA}
"""
        
        config = types.GenerateContentConfig(
            system_instruction=PROMPT_AUDITOR,
            response_mime_type="application/json"
        )
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=input_ia,
            config=config
        )
        
        # Faz o parse da resposta em texto para um dicionário Python
        return json.loads(response.text)
    except Exception as e:
        print(f"Erro no Agente 2 (Auditor): {e}")
        return {"erro": "Falha na comunicação com a IA."}
