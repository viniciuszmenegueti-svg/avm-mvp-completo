\# AVM Imóveis API



API para recebimento, validação e processamento de Ordens de Serviço de avaliação imobiliária.



\## Tecnologias



\- Python 3.12

\- FastAPI

\- SQLAlchemy

\- PostgreSQL

\- Alembic

\- Pytest

\- Docker

\- Docker Compose



\## Funcionalidades atuais



\- Criação e consulta de Ordens de Serviço

\- Consulta por identificador interno e externo

\- Listagem paginada e filtro por status

\- Validação de cidade, UF e código IBGE

\- Atualização e histórico de status

\- Healthchecks de vida e prontidão

\- Request ID e logs HTTP

\- Tratamento padronizado de erros

\- Cabeçalhos básicos de segurança



\## Execução com Docker



Crie o arquivo local de configuração:



```powershell

Copy-Item ".env.example" ".env"

