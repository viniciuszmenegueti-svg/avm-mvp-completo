# AVM Imóveis API

[![CI](https://github.com/viniciuszmenegueti-svg/avm/actions/workflows/ci.yml/badge.svg)](https://github.com/viniciuszmenegueti-svg/avm/actions/workflows/ci.yml)

API para recebimento, validação, processamento e avaliação automatizada de imóveis por meio de Ordens de Serviço.

## Tecnologias

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
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
- Cálculo inicial de avaliação AVM
- Persistência do resultado da avaliação
- Consulta da avaliação por Ordem de Serviço
- Faixa estimada de valor mínimo e máximo
- Cálculo do valor por metro quadrado
- Índice de confiança da avaliação
- Idempotência no cálculo da avaliação
- Transações atômicas no banco de dados
- Healthchecks de vida e prontidão
- Request ID por requisição
- Logs HTTP
- Tratamento padronizado de erros
- Cabeçalhos básicos de segurança
- Testes automatizados com cobertura mínima de 95%
- Teste de integração com API e PostgreSQL reais
- Pipeline de integração contínua no GitHub Actions

## Aviso sobre o modelo AVM

O método `RULE_BASED_V1` é uma implementação inicial e demonstrativa.

Os preços-base por metro quadrado utilizados atualmente são valores configurados no código para validação técnica do fluxo. Eles não devem ser considerados valores reais de mercado nem utilizados para emissão de laudos imobiliários.

Uma versão futura poderá utilizar:

- Imóveis comparáveis
- Dados históricos de transações
- Características de localização
- Modelos estatísticos
- Algoritmos de aprendizado de máquina
- Métricas de erro e validação por cidade

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

## Fluxo de processamento

O fluxo principal de uma avaliação é:

```text
RECEIVED
    |
    v
VALIDATING_INPUT
    |
    v
COMPLETED
```

Uma ordem também pode ser movida de `VALIDATING_INPUT` para `REFUSED`.

O cálculo AVM somente pode ser executado quando a ordem estiver no status:

```text
VALIDATING_INPUT
```

Após o cálculo e a persistência da avaliação, a ordem é atualizada automaticamente para:

```text
COMPLETED
```

## Configuração do ambiente

Crie o arquivo `.env` a partir do exemplo:

```powershell
Copy-Item ".env.example" ".env"
```

Exemplo de configuração:

```env
POSTGRES_PASSWORD=avm_local_password
APP_NAME=AVM Imoveis API
APP_VERSION=0.1.0
APP_ENV=development
APP_DEBUG=false
LOG_LEVEL=INFO
```

O arquivo `.env` não deve ser enviado para o repositório.

## Execução com Docker

Construa e inicie a aplicação:

```powershell
docker compose up -d --build
```

Confira os containers:

```powershell
docker compose ps
```

A API estará disponível em:

```text
http://localhost:8000
```

A documentação Swagger estará disponível em:

```text
http://localhost:8000/docs
```

Para encerrar o ambiente:

```powershell
docker compose down
```

Para encerrar e remover os volumes:

```powershell
docker compose down -v
```

## Execução local sem Docker

Crie o ambiente virtual:

```powershell
python -m venv ".venv"
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
python -m pip install --upgrade pip
python -m pip install -r "requirements-dev.txt"
```

Execute as migrations:

```powershell
alembic upgrade head
```

Inicie a API:

```powershell
uvicorn app.main:app --reload
```

## Endpoints principais

### Sistema

```text
GET /
GET /health
GET /health/live
GET /health/ready
```

### Cidades

```text
GET   /cities
GET   /cities/{city_ibge_code}/valuation-prices
GET   /cities/{city_ibge_code}/valuation-prices/{property_type}/history
PATCH /cities/{city_ibge_code}/valuation-prices/{property_type}
```

### Ordens de Serviço

```text
POST  /orders
GET   /orders
GET   /orders/{internal_order_id}
GET   /orders/external/{external_order_id}
PATCH /orders/{internal_order_id}/status
GET   /orders/{internal_order_id}/status-history
```

### Avaliações AVM

```text
POST /orders/{internal_order_id}/valuation
GET  /orders/{internal_order_id}/valuation
```

## Exemplo de criação de ordem

Requisição:

```http
POST /orders
Content-Type: application/json
```

```json
{
  "external_order_id": "CX-2026-000001",
  "property": {
    "property_type": "APARTMENT",
    "state": "SP",
    "city": "São Paulo",
    "city_ibge_code": "3550308",
    "postal_code": "01001-000",
    "neighborhood": "Centro",
    "street": "Rua de Teste",
    "number": "100",
    "complement": "Apartamento 10",
    "private_area_m2": 70,
    "built_area_m2": 80,
    "land_area_m2": null,
    "bedrooms": 2,
    "bathrooms": 2,
    "parking_spaces": 1
  }
}
```

Resposta esperada:

```json
{
  "internal_order_id": "UUID-GERADO-PELA-API",
  "external_order_id": "CX-2026-000001",
  "status": "RECEIVED",
  "received_at": "2026-07-22T20:00:00Z",
  "property": {
    "property_type": "APARTMENT",
    "state": "SP",
    "city": "São Paulo",
    "city_ibge_code": "3550308",
    "postal_code": "01001-000",
    "neighborhood": "Centro",
    "street": "Rua de Teste",
    "number": "100",
    "complement": "Apartamento 10",
    "private_area_m2": 70,
    "built_area_m2": 80,
    "land_area_m2": null,
    "bedrooms": 2,
    "bathrooms": 2,
    "parking_spaces": 1
  }
}
```

## Atualização para validação

Antes de calcular a avaliação, atualize a ordem:

```http
PATCH /orders/{internal_order_id}/status
Content-Type: application/json
```

```json
{
  "status": "VALIDATING_INPUT"
}
```

## Cálculo da avaliação AVM

Requisição:

```http
POST /orders/{internal_order_id}/valuation
```

Exemplo de resposta:

```json
{
  "valuation_id": "UUID-DA-AVALIACAO",
  "internal_order_id": "UUID-DA-ORDEM",
  "method": "RULE_BASED_V1",
  "estimated_value": "735000.00",
  "minimum_value": "661500.00",
  "maximum_value": "808500.00",
  "price_per_m2": "10500.00",
  "reference_area_m2": "70.00",
  "confidence_score": "0.8000",
  "calculated_at": "2026-07-22T20:05:00Z"
}
```

O endpoint é idempotente. Chamadas repetidas para a mesma ordem retornam a avaliação já existente.

## Consulta da avaliação

```http
GET /orders/{internal_order_id}/valuation
```

## Tipologias aceitas

```text
APARTMENT
HOUSE
LAND
```

Regras de áreas:

- `APARTMENT` exige `private_area_m2` e não aceita `land_area_m2`.
- `HOUSE` exige `built_area_m2` e `land_area_m2`.
- `LAND` exige `land_area_m2` e não aceita `private_area_m2` nem `built_area_m2`.

## Validação completa do projeto

Execute:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts\check.ps1"
```

O script executa:

1. Auditoria das dependências de produção
2. Verificação de qualidade com Ruff
3. Verificação de formatação
4. Análise de tipos com MyPy
5. Testes automatizados com cobertura

## Testes

Execute toda a suíte:

```powershell
python -m pytest
```

Execute sem relatório de cobertura:

```powershell
python -m pytest --no-cov
```

Execute um arquivo específico:

```powershell
python -m pytest "tests\test_valuation_routes.py" --no-cov -v
```

O projeto possui atualmente mais de 100 testes automatizados e cobertura integral do código da aplicação.

## Teste de integração

Com o ambiente Docker ativo, execute:

```powershell
python "scripts\integration-test.py"
```

O teste valida:

- Healthchecks
- Lista de cidades
- Criação da ordem
- Consulta por identificador externo
- Atualização para `VALIDATING_INPUT`
- Cálculo e persistência da avaliação
- Consulta da avaliação
- Atualização automática para `COMPLETED`
- Histórico de status
- Idempotência do cálculo
- Bloqueio de ordem duplicada

## Migrations

Aplicar todas as migrations:

```powershell
alembic upgrade head
```

Consultar a migration atual:

```powershell
alembic current
```

Verificar alterações de schema ainda não migradas:

```powershell
alembic check
```

Criar uma nova migration:

```powershell
alembic revision --autogenerate -m "descricao da alteracao"
```

Reverter uma migration:

```powershell
alembic downgrade -1
```

## Integração contínua

O GitHub Actions executa automaticamente:

- Auditoria de dependências
- Ruff
- Verificação de formatação
- MyPy
- Testes com cobertura
- Validação do Docker Compose
- Construção da imagem Docker
- Inicialização da API e do PostgreSQL
- Verificação das migrations
- Teste de integração completo
- Encerramento do ambiente Docker

## Estrutura principal

```text
app/
├── api/
│   └── routes/
├── core/
├── domain/
├── infrastructure/
├── repositories/
├── schemas/
├── services/
└── main.py

migrations/
├── versions/
└── env.py

scripts/
├── check.ps1
├── integration-test.py
└── smoke-test.ps1

tests/
```

## Segurança

O projeto inclui:

- Variáveis de ambiente para configurações sensíveis
- Senha do PostgreSQL fora do código-fonte
- Auditoria de dependências com `pip-audit`
- Usuário não privilegiado na imagem Docker
- Cabeçalhos básicos de segurança
- Request ID para rastreabilidade
- Logs HTTP estruturados
- Tratamento centralizado de erros

## Licença

Projeto em desenvolvimento para fins de estudo, demonstração técnica e evolução de um modelo automatizado de avaliação imobiliária.