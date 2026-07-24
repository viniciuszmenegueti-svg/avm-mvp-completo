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
- Registro e consulta de recusas
- Bloqueio de ordens duplicadas
- Cálculo inicial de avaliação AVM
- Persistência do resultado da avaliação
- Consulta da avaliação por Ordem de Serviço
- Faixa estimada de valor mínimo e máximo
- Cálculo do valor por metro quadrado
- Índice de confiança da avaliação
- Idempotência no cálculo da avaliação
- Configuração de preços-base por cidade e tipologia no banco de dados
- Atualização de preços protegida por credenciais administrativas
- Suporte a múltiplos administradores com identidade vinculada à chave
- Histórico de alterações de preços
- Identificação do responsável por cada alteração de preço
- Registro e consulta das versões dos modelos AVM
- Bloqueio da avaliação quando o modelo padrão não está ativo
- Persistência da versão do modelo utilizada em cada avaliação
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

Os preços-base por metro quadrado utilizados atualmente são valores demonstrativos persistidos no banco de dados para validação técnica do fluxo. Eles não devem ser considerados valores reais de mercado nem utilizados para emissão de laudos imobiliários.

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
APP_NAME=AVM Imoveis API
APP_VERSION=0.2.0
APP_ENV=development
APP_DEBUG=false
LOG_LEVEL=INFO

ADMIN_CREDENTIALS_JSON={"admin-local":"change_this_admin_key","pricing-admin":"change_this_pricing_key"}

ADMIN_API_KEY=
ADMIN_ACTOR=

POSTGRES_DB=avm
POSTGRES_USER=avm_app
POSTGRES_PASSWORD=avm_local_password
POSTGRES_PORT=5433

DATABASE_URL=postgresql+psycopg://avm_app:avm_local_password@localhost:5433/avm
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

A atualização do preço-base exige o seguinte cabeçalho:

```text
X-Admin-API-Key: chave administrativa configurada no ambiente
```

As credenciais podem ser configuradas em `ADMIN_CREDENTIALS_JSON`, associando cada chave a uma identidade administrativa. A identidade correspondente à chave utilizada é armazenada como `changed_by` no histórico e não pode ser escolhida pelo cliente.

As variáveis legadas `ADMIN_API_KEY` e `ADMIN_ACTOR` permanecem disponíveis para compatibilidade, mas a configuração com `ADMIN_CREDENTIALS_JSON` é a opção recomendada.

### Ordens de Serviço

```text
POST  /orders
GET   /orders
GET   /orders/{internal_order_id}
GET   /orders/external/{external_order_id}
PATCH /orders/{internal_order_id}/status
GET   /orders/{internal_order_id}/status-history
GET   /orders/{internal_order_id}/refusal
```

### Modelos AVM

```text
GET /models
GET /models/{method}
```

`GET /models` lista somente os modelos ativos. `GET /models/{method}` consulta uma versão registrada pelo método, como `RULE_BASED_V1`.

### Avaliações AVM

```text
POST /orders/{internal_order_id}/valuation
GET  /orders/{internal_order_id}/valuation
```

A criação da avaliação exige que o modelo padrão esteja com status `ACTIVE`. Quando o modelo está desativado ou depreciado, a API responde com HTTP `503` e o código `AVM_MODEL_NOT_ACTIVE`.

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
  "model_version": "1.0.0",
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

A versão do modelo utilizada é persistida em `model_version`, permitindo rastrear exatamente qual implementação produziu o resultado.

Falhas esperadas do motor AVM utilizam exceções específicas, como preço por metro quadrado inválido ou ausência defensiva da área de referência. A API converte essas falhas em HTTP `422` com o código `VALUATION_CALCULATION_ERROR`.

## Consulta da avaliação

```http
GET /orders/{internal_order_id}/valuation
```

## Consulta da recusa

```http
GET /orders/{internal_order_id}/refusal
```

Exemplo de resposta:

```json
{
  "refusal_id": "UUID-DA-RECUSA",
  "internal_order_id": "UUID-DA-ORDEM",
  "reason_code": "MISSING_BASE_PRICE",
  "message": "Não existe preço-base configurado para a cidade e tipologia.",
  "details": {
    "city_ibge_code": "3550308",
    "property_type": "APARTMENT"
  },
  "refused_at": "2026-07-22T20:05:00Z"
}
```

A consulta retorna HTTP `404` com códigos distintos quando a ordem não existe ou quando não possui recusa registrada:

```text
ORDER_NOT_FOUND
ORDER_REFUSAL_NOT_FOUND
```

Os motivos de recusa atualmente suportados são:

```text
MISSING_BASE_PRICE
INSUFFICIENT_MARKET_DATA
UNSUPPORTED_PROPERTY_TYPE
PROPERTY_DATA_INCONSISTENT
LOW_CONFIDENCE
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

O projeto possui atualmente 191 testes automatizados e cobertura superior a 99%.

## Teste de integração

Com o ambiente Docker ativo, execute:

```powershell
python "scripts\integration-test.py"
```

O teste valida:

- Healthchecks
- Lista de cidades
- Bloqueio de atualização sem chave administrativa
- Bloqueio de atualização com chave inválida
- Atualização autorizada de preço-base
- Registro do responsável vinculado à chave administrativa
- Criação da ordem
- Consulta por identificador externo
- Atualização para `VALIDATING_INPUT`
- Cálculo e persistência da avaliação
- Consulta da avaliação
- Atualização automática para `COMPLETED`
- Histórico de status
- Idempotência do cálculo
- Bloqueio de ordem duplicada
- Criação temporária de cidade sem preço-base
- Recusa da ordem com HTTP `409`
- Código de erro `ORDER_REFUSED`
- Persistência do motivo `MISSING_BASE_PRICE`
- Consulta dos detalhes da recusa
- Atualização automática para `REFUSED`
- Histórico de status `VALIDATING_INPUT → REFUSED`
- Limpeza automática da cidade temporária ao final do teste

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

engine/
├── exceptions.py
├── registry.py
└── models/
    └── rule_based_v1.py

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
- Suporte a múltiplas credenciais administrativas
- Identidade administrativa determinada no servidor
- Senha do PostgreSQL fora do código-fonte
- Auditoria de dependências com `pip-audit`
- Usuário não privilegiado na imagem Docker
- Cabeçalhos básicos de segurança
- Request ID para rastreabilidade
- Logs HTTP estruturados
- Tratamento centralizado de erros

## Licença

Projeto em desenvolvimento para fins de estudo, demonstração técnica e evolução de um modelo automatizado de avaliação imobiliária.
