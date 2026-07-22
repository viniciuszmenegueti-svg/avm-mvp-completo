# AVM Imóveis API

[![CI](https://github.com/viniciuszmenegueti-svg/avm/actions/workflows/ci.yml/badge.svg)](https://github.com/viniciuszmenegueti-svg/avm/actions/workflows/ci.yml)

API para recebimento, validação e processamento de Ordens de Serviço de avaliação imobiliária.

## Tecnologias

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pytest
- Ruff
- MyPy
- pip-audit
- Docker
- Docker Compose
- GitHub Actions

## Funcionalidades atuais

- Criação e consulta de Ordens de Serviço
- Consulta por identificador interno e externo
- Listagem paginada de ordens
- Filtro por status
- Validação de cidade, UF e código IBGE
- Atualização controlada de status
- Histórico de alterações de status
- Bloqueio de ordens duplicadas
- Transações atômicas no banco de dados
- Healthchecks de vida e prontidão
- Request ID por requisição
- Logs HTTP
- Tratamento padronizado de erros
- Cabeçalhos básicos de segurança
- Testes automatizados com cobertura mínima de 95%
- Teste de integração com API e PostgreSQL reais

## Cidades habilitadas

- Belo Horizonte/MG
- Brasília/DF
- Curitiba/PR
- Fortaleza/CE
- Goiânia/GO
- Porto Alegre/RS
- Recife/PE
- Rio de Janeiro/RJ
- Salvador/BA
- São Paulo/SP

## Configuração do ambiente

Crie o arquivo `.env` a partir do exemplo:

```powershell
Copy-Item ".env.example" ".env"