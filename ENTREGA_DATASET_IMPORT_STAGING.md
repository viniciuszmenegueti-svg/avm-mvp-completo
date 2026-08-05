# Entrega: staging e validação de importações

Implementa o staging linha a linha de arquivos CSV já processados por uma versão de dataset.

## Recursos

- execução auditável por versão de dataset
- persistência da linha original e normalizada em JSON
- validação de obrigatoriedade e tipos
- normalização de texto, inteiro, decimal, data e booleano
- detecção de duplicidade dentro do arquivo
- contadores de válidos, inválidos e duplicados
- gravação em lotes configuráveis
- resumo da execução
- paginação das linhas rejeitadas
- reprocessamento explícito e seguro

## Endpoints

- `POST /admin/dataset-versions/{dataset_version_id}/stage-import`
- `GET /admin/dataset-versions/{dataset_version_id}/staging-summary`
- `GET /admin/dataset-versions/{dataset_version_id}/rejected-rows`

## Alembic

Head: `f8d1c5a7e230`
