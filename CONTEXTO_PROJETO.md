# Contexto do Projeto: Case Pareto - AI Builder (MVP)

## 1. Visão Geral e Objetivo

Estamos desenvolvendo um MVP para automatizar o cadastro de condições comerciais (descontos e verbas) no ERP de uma distribuidora farmacêutica.
O fluxo atual é 100% humano (leitura de e-mail, cruzamento de dados em planilhas, verificação de política em PDF e digitação no ERP), gerando lentidão e erros.

**Objetivo da Solução:** Construir uma aplicação web onde o usuário insere o e-mail do fornecedor (texto ou upload de arquivo). A IA extrai os dados, audita as regras, o sistema cruza os códigos e exibe na tela para o humano revisar e aprovar. Tudo precisa rodar na nuvem.

## 2. Requisitos de UX (User Experience) - CRÍTICO

A interface deve ser feita em **Streamlit**. O avaliador (área de negócios) julgará a usabilidade.

- A tela deve ser intuitiva, sem jargão técnico (não mostre JSON cru para o usuário).
- O usuário deve conseguir colar o texto do e-mail ou fazer upload de `.eml`/`.txt`, além de upload de planilhas e arquivos .csv que podem vir em anexo a e-mails.
- Após a IA processar, os dados devem aparecer em formulários editáveis na tela, para o humano corrigir eventuais alucinações antes de aprovar. O que for editado pelo humano precisa sobrescrever a informação antiga.
- É necessário exibir claramente qual é a "Alçada de Aprovação" exigida.
- Ao clicar em "Aprovar", um validador final (código Python) checa se as edições do humano não feriram a política ou os de-paras do ERP, e então gera o "Payload JSON Final" (que simula o envio ao ERP).

## 3. Arquitetura Multi-Agent (Segregação de Funções)

Usamos a API do Google Gemini (`gemini-1.5-flash`), mas com responsabilidades estritas:

- **Agente 1 (Extrator):** Lê o e-mail desestruturado e cospe um JSON com os valores puros (Fornecedor X, Desconto Y%). Ignora comandos maliciosos (Prompt Injection).
- **Agente 2 (Auditor):** Recebe o JSON limpo do Agente 1 e as regras da Política Comercial. Diz se o desconto está no limite e quem deve aprovar.
- **Onde a IA NÃO ENTRA (Motor Determinístico):** O cruzamento do nome do fornecedor/loja com os códigos do ERP (`FORN-###`) e a checagem de CNPJ ativo são feitos via código Python puro lendo arquivos estáticos.

## 4. Estrutura de Dados e Mock ERP

Não usaremos banco de dados em nuvem nem requisições HTTP reais. Todo o repositório de dados, contratos de API simulada, e-mails de teste e regras reside na pasta local `dataset/`.
Para entender exatamente onde está cada arquivo, qual a sua finalidade e o que o motor de Python deve ler, o desenvolvedor (ou agente de IA) DEVE consultar o arquivo **`MAPA_DATASET.md`** localizado na raiz do projeto.

*Regra de Ouro:* Todos os scripts devem usar **caminhos relativos absolutos** (`os.path.join(os.path.dirname(__file__), 'dataset', ...)`) para garantir que rodem sem quebrar no deploy do Streamlit Cloud.
