# Registro de versões de datasets

## Entrega

- Entidade `dataset_versions` vinculada a `datasets`.
- Numeração sequencial por dataset.
- Deduplicação por checksum SHA-256 dentro do dataset.
- Estados `REGISTERED`, `PROCESSING`, `COMPLETED` e `FAILED`.
- Rastreabilidade de arquivo, responsável, período, contagem e falhas.
- Endpoints administrativos protegidos.
- Migration Alembic reversível.
- Testes de rotas, repositório, metadata e migration.
