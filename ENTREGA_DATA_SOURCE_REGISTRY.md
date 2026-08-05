# Entrega: Cadastro de Fontes de Dados

## Implementação

- Entidade SQLAlchemy `data_sources` com nome normalizado e único.
- Status `ACTIVE` e `INACTIVE`.
- Campos de tipo, responsável, descrição, data de referência e metadados JSON.
- Repositório com criação, consulta, filtros e paginação.
- Serviço com regras de duplicidade, atualização e transição de status.
- Endpoints administrativos protegidos por `X-Admin-API-Key`.
- Migration Alembic `c9f2a6d4e810` sobre `b7e4c2a9d610`.
- Registro do modelo no metadata do Alembic e no banco de testes.

## Endpoints

- `POST /admin/data-sources`
- `GET /admin/data-sources`
- `GET /admin/data-sources/{data_source_id}`
- `PATCH /admin/data-sources/{data_source_id}`
- `POST /admin/data-sources/{data_source_id}/activate`
- `POST /admin/data-sources/{data_source_id}/deactivate`

## Testes adicionados

- Rotas, autenticação, validação, filtros, paginação e OpenAPI.
- Repositório.
- Metadata SQLAlchemy.
- Estrutura e execução isolada de upgrade, downgrade e reaplicação da migration.

Resultado no ambiente de entrega: 20 testes específicos aprovados.

A suíte completa do ZIP base não pôde ser concluída neste ambiente porque `config/shadow-model-rj.json` referencia um artefato externo por caminho absoluto do computador de origem. Essa limitação já existia no pacote recebido e não é causada pelo módulo de fontes de dados.
