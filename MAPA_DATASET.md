# Mapa do Diretório de Dados (`dataset/`)

Este projeto não utiliza banco de dados externo. Todo o insumo (regras, histórico e mock de APIs) está contido na pasta `dataset/`. O backend (Python) deve usar caminhos relativos (ex: `os.path.join(..., 'dataset', ...)`) para ler esses arquivos.

## Estrutura e Finalidade dos Arquivos

### Insumos de Entrada (Para Teste no Streamlit)

- `dataset/emails/`: Contém os arquivos `.eml` originais dos fornecedores (texto livre com a negociação). O usuário fará upload desses arquivos pela interface.
- `dataset/emails/anexos/`: Planilhas citadas nos e-mails.

### Bases de Dados Mockadas (O "ERP Local")

- `dataset/extrato_erp.csv`: Export de condições comerciais do ERP (separador `;`). Útil para checar sobreposições de condições antigas.
- `dataset/mock_erp/respostas/GET_fornecedores.json`: Simula o banco de dados de fornecedores. Contém `cod_fornecedor`, `nome` e `status` (ATIVO/INATIVO).
- `dataset/mock_erp/respostas/GET_lojas.json`: Simula o banco de dados de lojas. Contém o "de-para" de nomes das filiais para o código `LOJA-###`.
- `dataset/mock_erp/respostas/GET_condicoes.json`: Simula as condições vigentes em tempo real.

### Regras e Contratos

- `dataset/mock_erp/README.md`: Documentação simulada da API do ERP. Define as regras de rate limit (10 req/min) e comportamentos de erro.
- `dataset/mock_erp/schema/condicao_post.schema.json`: O formato EXATO do JSON que a nossa aplicação precisa cuspir no final do fluxo para o cadastro ter sucesso.
- `dataset/Politica_Comercial.pdf`: As regras de negócio (tetos de desconto, alçadas). *Nota: Para otimizar o código, o texto deste PDF foi transcrito para a variável Python no arquivo `politica_comercial.py` na raiz do projeto.*
- `dataset/Instrucoes_case_tecnico_Pareto.docx`: Documento original com as instruções gerais do case.
