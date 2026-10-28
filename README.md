# 🚀 Pareto AI Builder - Extrator de Condições Comerciais (MVP)

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)]()
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)]()

> **Otimização e Governança na Ingestão de Dados Comerciais**  
> *Este projeto é um MVP desenvolvido como resolução do Case Técnico da Pareto, demonstrando a aplicação de IA Generativa para processos de Back-office.*

🌐 **https://casepareto-bernard-meireles.streamlit.app/**

📄 **https://drive.google.com/drive/folders/18u2XF-OCSGqQvpa882oc_lqNaSW7ESGH?usp=drive_link**

---

## 📖 O Problema de Negócio
No processo comercial de distribuidoras, propostas de fornecedores chegam por e-mail em formato de texto livre e desestruturado. O processo manual de leitura, interpretação, cruzamento com a política comercial da empresa e posterior digitação no ERP gera:
1. **Gargalo Operacional:** Analistas gastam tempo valioso ("hora cara") atuando como tradutores de e-mail.
2. **Inconsistência e Falhas:** Divergências na interpretação geram glosas milionárias descobertas apenas no fechamento financeiro do mês.

## 💡 A Solução
Uma aplicação web orientada a **Human-in-the-Loop (HITL)**. A carga cognitiva de ler e-mails desestruturados e cruzar regras complexas foi delegada a **Agentes de Inteligência Artificial**, enquanto o Analista Comercial é elevado à posição de auditor, tomando a decisão final por meio de uma interface visual assistida. 

Nenhum dado é gravado no ERP sem validação algorítmica e aprovação humana.

## 🛠️ Destaques da Arquitetura

Este MVP não é um simples "wrapper" de IA. Ele adota padrões de governança e engenharia de software defensiva:

* 🤖 **Arquitetura Multi-Agent (Segregation of Duties):** 
  O processo usa dois agentes LLM isolados. O **Agente Extrator** lê o texto bruto e formata em JSON. O **Agente Auditor** recebe apenas o JSON limpo para cruzar com a Política Comercial, impedindo que o texto original contamine a decisão da regra de negócio.
* 🛡️ **Defesa Anti-Prompt Injection:**
  O sistema é blindado contra fornecedores que tentam burlar regras inserindo comandos como *"Aprovar automaticamente"* no corpo do e-mail. A IA é instruída a ignorar ordens e extrair estritamente as métricas financeiras.
* ⚖️ **Motor Determinístico (Regras Estritas em Python):**
  A IA **não** cruza códigos de Master Data (IDs de Fornecedores e Lojas). Para evitar alucinações de LLM, o mapeamento exato (De-Para) e a validação de status de cadastro são feitos via código determinístico em Python, batendo contra um *Mock ERP*.
* 🛑 **Segurança Pós-Edição:**
  Se o humano tentar editar um desconto na interface para um valor acima do teto da Política Comercial, o algoritmo bloqueia a geração do *payload* final e emite um alerta detalhado.



## ⚙️ Fluxo de Funcionamento

1. **Ingestão:** O usuário faz upload do arquivo `.eml` (ou texto) na interface.
2. **Extração (IA):** O Agente converte o texto livre em dados estruturados (Descontos, Verbas, Vigência, Contrapartidas).
3. **Auditoria (IA + Python):** O sistema deduz a categoria, checa o teto de limite de descontos da política e valida se o CNPJ/Fornecedor existe na base de dados.
4. **Revisão Humana:** A interface exibe os dados para o analista. Cores semânticas indicam sucesso ou necessidade de revisão.
5. **Integração:** Após a confirmação, o sistema gera o JSON (*Payload* de Integração) formatado exatamente sob o contrato da API do ERP.



## 💻 Como Rodar o Projeto Localmente

**Pré-requisitos:** Python 3.10+ e uma chave de API válida do Google Gemini.

1. **Clone o repositório:**
```bash
git clone [https://github.com/bprata1/case_pareto.git](https://github.com/bprata1/case_pareto.git)
cd case_pareto

```

2. **Crie um ambiente virtual e instale as dependências:**

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

3. **Configure as Variáveis de Ambiente:**
Crie um arquivo `.env` na raiz do projeto e insira sua chave da API do Google Gemini:

```env
GEMINI_API_KEY=sua_chave_aqui

```

4. **Execute a aplicação:**

```bash
streamlit run app.py

```

---

*Desenvolvido por **Bernard Prata Meireles Vieira Fernandes**.*
