# 🚀 Pareto AI Builder — Plataforma Corporativa de Condições Comerciais & Compliance (V6)

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)]()
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)]()
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)]()

> **Automação, Governança de Alçadas e Auditoria Determinística na Ingestão de Condições Comerciais (Rede Farmacêutica Vitalis)**  
> *Aplicação corporativa desenvolvida como resolução do Case Técnico da Pareto, combinando IA Generativa (Multi-Agent), Motor Determinístico em Python e Workflow Hierárquico de Aprovação.*

🌐 **Aplicação em Produção (Streamlit Cloud):** **https://casepareto-bernard-meireles.streamlit.app/**

📄 **Documentação e Materiais Complementares:** **https://drive.google.com/drive/folders/18u2XF-OCSGqQvpa882oc_lqNaSW7ESGH?usp=drive_link**

---

## 📖 O Problema de Negócio

No processo comercial da rede de farmácias **Vitalis**, negociações de descontos percentuais e verbas de exposição (Trade Marketing) chegam por e-mail em texto livre, frequentemente acompanhadas de planilhas anexas (`.csv` / `.xlsx`). O fluxo manual de leitura, cruzamento de códigos no ERP, verificação da Política Comercial (`POL-COM-004`) e digitação gera:

1. **Gargalo Operacional:** Analistas comerciais gastam horas traduzindo e-mails, cruzando códigos de lojas/fornecedores e conferindo tetos por categoria.
2. **Riscos de Compliance e Glosas Financeiras:** Fornecedores inativos cadastrados por engano, descontos acima do teto, ausência de contrapartida em verbas, contratos duplicados/sobrepostos e aprovações fora da alçada correta.

---

## 💡 A Solução (Arquitetura V6)

Uma plataforma web orientada a **Human-in-the-Loop (HITL)** e **Governança Corporativa por Alçadas**:

- **Agentes de IA (Google Gemini)** realizam o trabalho pesado de extração semântica de e-mails e planilhas anexas, desmembrando condições mistas e neutralizando tentativas de *Prompt Injection*.
- **Motor Determinístico em Python (`erp_integration.py`)** executa 100% das validações críticas de Master Data (`GET_fornecedores.json`, `GET_lojas.json`), vigência contratual (`extrato_erp.csv` + SQLite), tetos da Política Comercial (`POL-COM-004`) e validação estrita de JSON Schema (`condicao_post.schema.json`).
- **Workflow Hierárquico Persistente (`database.py` em SQLite)** conecta o **Analista Comercial** aos gestores aprovadores (**Coordenador**, **Gerente** e **Diretor**), com suporte a **Substituição Auditada (Override)**, **Ciclo Completo de Rejeição e Correção** e **Central de Notificações Interativa**.

---

## 🛡️ Os 7 Edge Cases de Negócio Resolvidos ("Pegadinhas" do Dataset)

O sistema identifica, trata e alerta visualmente os **7 casos críticos** presentes no dataset oficial:

| # | Edge Case ("Pegadinha") | Caso do Dataset | Como o Sistema Resolve |
| :--- | :--- | :--- | :--- |
| **1** | **Prompt Injection** | `Nutrivida` (`2026-09-29_1830_nutrivida.eml`) | Fornecedor insere comando oculto pedindo aprovação direta sem revisão. O detector determinístico + arquitetura Multi-Agent isolam a instrução maliciosa, exibem alerta de segurança (`🛡️ Edge Case 1`) e submetem os dados brutos às travas normais. |
| **2** | **Fornecedor Inativo no ERP** | `Nutrivida` (`FORN-005`) | Cruzamento determinístico com `GET_fornecedores.json` identifica status `INATIVO` (pendência cadastral ANVISA) e bloqueia o envio à fila (Regra 8). |
| **3** | **Condições Mistas (Desconto + Verba)** | `Gama Dermo` (`2026-09-28_1640_gama.eml`) | Proposta combina Desconto Percentual e Verba de Exposição no mesmo e-mail. A IA desmembra automaticamente em **2 objetos independentes** (Regra 5), cada um com sua própria validação e alçada. |
| **4** | **Exceção Sazonal (Até 30%)** | `Alfa Pharma` (`2026-09-28_0912_alfa.eml`) | Pede 28% em `GENERICOS` (teto padrão é 15%), citando *"Campanha de Fim de Ano"*. O motor aplica a **Nota (\*) da Política Comercial**, classifica como `EXCECAO_SAZONAL` e escala a alçada para a **Diretoria Comercial**. |
| **5** | **Busca Indireta em Anexos + Divergência** | `Gama Dermo` (`proposta_gama_q4.csv`) | O e-mail cita *"lojas listadas na planilha anexa"*. Sem o anexo, o sistema bloqueia a referência indireta; com o upload conjunto do `.eml` + `.csv`, extrai as 6 lojas reais e alerta a divergência de desconto (16% no e-mail vs. 18% na planilha). |
| **6** | **Sobreposição Contratual e Substituição Auditada (Override)** | `Distribuidora Beta` (`2026-09-29_1005_beta.eml`) | Cruza com `extrato_erp.csv` (`STATUS == 'VIGENTE'`) e SQLite. Bloqueia duplicidades idênticas informando onde o item está (ERP ou Fila). Quando há **divergência de valor** (ex.: ERP `COND-003` tem 10% vs. nova proposta de 12%), permite solicitar **Substituição Auditada (Override)** mediante justificativa obrigatória do Analista. |
| **7** | **Limites Críticos de Vigência** | Todos os casos (`Regra 6`) | Validador Python bloqueia datas de início retroativas em relação à data de referência do ERP e proíbe vigências superiores a **12 meses** (365 dias). |

---

## 🏛️ Governança de Perfis, Alçadas e Funcionalidades (V6)

### 1. Autenticação Nominal e Hierarquia (`POL-COM-004`)
A aplicação possui controle de acesso baseado em perfis com credenciais corporativas pré-configuradas (acessíveis também via **Troca Rápida em 1 Clique** na barra lateral **🛠️ Área do Avaliador**):

> 🔑 **Senha padrão para todos os usuários de teste:** `123`

| Usuário (Login) | Nome | Cargo / Perfil | Escopo de Atuação e Alçada (`POL-COM-004`) |
| :--- | :--- | :--- | :--- |
| `renata.alves` | Renata Alves | **Analista Comercial** | Ingestão de e-mails/anexos, revisão humana, solicitação de substituição auditada, correção de itens rejeitados e acompanhamento da fila (leitura). |
| `carlos.eduardo` | Carlos Eduardo | **Coordenador Comercial** | Aprova descontos percentuais de **até 10%**. |
| `fernanda.lima` | Fernanda Lima | **Gerente Comercial** | Aprova descontos de **> 10% até 20%** e verbas de exposição de **até R$ 5.000,00** (além da hierarquia de Coordenação). |
| `roberto.almeida` | Roberto Almeida | **Diretor Comercial** | Aprova descontos de **> 20% até 25%**, verbas **> R$ 5.000,00** e **Exceções Sazonais (até 30%)**, além de toda a hierarquia inferior. |

### 2. Filtros Estritos vs. Hierárquicos na Fila do Gestor
Na visão dos aprovadores, o gestor dispõe de três modos de filtro de escopo:
- **Apenas minha alçada de aprovação (Estrito):** Exibe *exclusivamente* os itens cujo nível de alçada exigido é exatamente igual ao cargo logado (ex.: Diretor vê apenas itens de `Diretoria Comercial`).
- **Visão Geral (Minha Hierarquia):** Exibe os itens da alçada direta somados aos de níveis subordinados.
- **Todos:** Permite consultar toda a fila da empresa (itens de alçada superior ficam em modo somente leitura com aviso de trava hierárquica).

### 3. Substituição Auditada (Override com Contexto ERP)
- Quando uma nova proposta conflita em período/loja com um contrato vigente no `extrato_erp.csv` mas possui **novo valor negociado**, o Analista pode marcar **"⚠️ Solicitar substituição/correção da condição vigente"** e preencher uma justificativa obrigatória.
- No card da Fila de Aprovação, o Gestor visualiza em destaque tanto a **Justificativa do Analista** quanto o **Contexto Comparativo do ERP** (ex.: `Condição Vigente (COND-003): 10% | Nova Proposta: 12%`, lojas afetadas e vigência atual), preenchendo automaticamente o campo `cod_condicao_substituida` no payload JSON final.

### 4. Ciclo de Vida de Rejeição e Correção Assistida
- **Reprovação Motivada:** Ao clicar em **"❌ Reprovar Condição"**, o Gestor deve preencher obrigatoriamente o **Motivo da Rejeição**.
- **Correção pelo Analista:** Na Fila de Aprovação do Analista, condições `REJEITADAS` exibem o motivo apontado pelo gestor e o botão **"📝 Corrigir Condição"**.
- **Redirecionamento e Alerta Persistente:** Ao acionar a correção, o sistema redireciona o Analista para a aba de Ingestão, preenche o formulário com os dados da proposta reprovada e mantém um **alerta persistente no topo da tela** com o motivo da rejeição até que a condição seja ajustada e reenviada para a fila.

### 5. Central de Notificações Interativa (`🔔 Notificações Recentes`)
- Localizada na barra lateral (acima da Área do Avaliador), exibe em tempo real as últimas movimentações relevantes para cada perfil:
  - **Para o Analista:** Notifica condições `APROVADAS` e `REJEITADAS` (com snippet do motivo).
  - **Para os Gestores:** Exibe o resumo de pendências na alçada direta/hierarquia e as últimas propostas recebidas.
- **Navegação em 1 Clique:** Todos os itens da Central de Notificações são clicáveis e levam o usuário diretamente para a tela, filtro de status e protocolo correspondente, combinados com alertas `st.toast` em tempo real.

### 6. Visibilidade Técnica do Payload ERP (`condicao_post.schema.json`)
- Em todos os cards (tanto na revisão do Analista quanto na Fila de Aprovação), o expander **"Visualizar Payload JSON (Técnico)"** permite inspecionar o Body do `POST /api/v1/condicoes` e o envelope HTTP completo (com `Idempotency-Key` UUID v4), além de oferecer o botão **"📥 Baixar Payload JSON (.json)"**.

---

## 📂 Estrutura do Projeto

```text
case_pareto/
├── app.py                   # Interface Streamlit V6 (Login, Ingestão, Fila, Override, Correção e Notificações)
├── agents.py                # Orquestração Multi-Agent com Google Gemini + Fallback Resiliente
├── prompts.py               # System Prompts blindados (Agente 1 Extrator e Agente 2 Auditor)
├── erp_integration.py       # Motor Determinístico (Fuzzy De-Para, Vigência, Sobreposição ERP e JSON Schema)
├── database.py              # Persistência SQLite (Usuários, Fila Hierárquica, Override, Rejeição e Notificações)
├── CONTEXTO_PROJETO.md      # Diretrizes arquiteturais e regras de negócio do projeto
├── MAPA_DATASET.md          # Mapeamento detalhado dos arquivos do dataset e contratos do Mock ERP
├── PLANEJAMENTO_V2.md       # Documentação de engenharia e checklist de evolução da arquitetura
├── requirements.txt         # Dependências Python do projeto
└── dataset/                 # Repositório estático de dados (Mock ERP, Política e E-mails de Teste)
    ├── politica_comercial.md
    ├── extrato_erp.csv
    ├── emails/
    │   ├── 2026-09-28_0912_alfa.eml
    │   ├── 2026-09-28_1640_gama.eml
    │   ├── 2026-09-29_1005_beta.eml
    │   ├── 2026-09-29_1830_nutrivida.eml
    │   └── anexos/
    │       └── proposta_gama_q4.csv
    └── mock_erp/
        ├── respostas/
        │   ├── GET_fornecedores.json
        │   ├── GET_lojas.json
        │   └── GET_condicoes.json
        ├── exemplos/
        │   └── POST_condicoes_request.json
        └── schema/
            └── condicao_post.schema.json
```

---

## 💻 Como Rodar o Projeto Localmente

**Pré-requisitos:** Python 3.10+ e uma chave de API do Google Gemini (opcional para os casos oficiais do dataset, pois o sistema conta com fallback determinístico resiliente).

1. **Clone o repositório:**
```bash
git clone https://github.com/bprata1/case_pareto.git
cd case_pareto
```

2. **Crie um ambiente virtual e instale as dependências:**
```bash
python -m venv .venv
# No Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# No Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

3. **Configure as Variáveis de Ambiente:**
Crie um arquivo `.env` na raiz do projeto com sua chave da API do Google Gemini:
```env
GEMINI_API_KEY=sua_chave_aqui
```

4. **Execute a aplicação:**
```bash
streamlit run app.py
```

---

*Desenvolvido por **Bernard Prata Meireles Vieira Fernandes**.*
