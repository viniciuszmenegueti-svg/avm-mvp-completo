# Relatório de validação

## Resultado específico

- 13 testes aprovados
- compilação Python aprovada
- migration com upgrade e downgrade em SQLite aprovada
- Alembic com um único head: `f8d1c5a7e230`

## Cobertura funcional

- metadata e índices dos modelos
- encadeamento e execução da migration
- staging de linhas válidas, inválidas e duplicadas
- normalização de tipos
- paginação e filtro de rejeitados
- autenticação administrativa
- validação de colunas configuradas
- bloqueio de reprocessamento sem autorização explícita
- reprocessamento com `force_reprocess`

## Suíte completa

A suíte completa foi iniciada. Os primeiros erros são de testes antigos do modelo sombra porque `config/shadow-model-rj.json` referencia `model-artifact-v3.json` por um caminho absoluto do computador de origem. O artefato não está presente no ZIP-base recebido. Os testes específicos desta entrega passaram integralmente.
