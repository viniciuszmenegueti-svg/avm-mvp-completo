# Entrega: Cadastro de Datasets

Módulo administrativo para cadastrar datasets vinculados a fontes de dados.

## Recursos

- vínculo obrigatório com `data_sources`
- nome único por fonte
- estados `ACTIVE`, `INACTIVE` e `ARCHIVED`
- período de referência e metadados JSON
- filtros, paginação e trilha de atores
- criação, consulta, atualização e transições de status
- dataset arquivado imutável
- migration Alembic e testes de upgrade/downgrade

## Endpoints

- `POST /admin/datasets`
- `GET /admin/datasets`
- `GET /admin/datasets/{dataset_id}`
- `PATCH /admin/datasets/{dataset_id}`
- `POST /admin/datasets/{dataset_id}/activate`
- `POST /admin/datasets/{dataset_id}/deactivate`
- `POST /admin/datasets/{dataset_id}/archive`
