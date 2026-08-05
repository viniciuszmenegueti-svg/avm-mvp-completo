# Entrega: Versionamento de Datasets e Registro de Importações

## Implementação

- Cadastro de versões vinculadas a datasets ativos.
- Numeração sequencial independente por dataset.
- Deduplicação por checksum SHA-256 dentro do mesmo dataset.
- Rastreabilidade de nome, caminho lógico, tamanho, MIME, período e responsável.
- Estados `REGISTERED`, `PROCESSING`, `COMPLETED` e `FAILED`.
- Registro de início e término do processamento, contagem de registros e mensagem de erro.
- Filtros administrativos por dataset, status, responsável, checksum e período.
- Migration Alembic reversível `e6c3b9a2f410`.

## Validação

- 22 testes específicos aprovados.
- Compilação Python aprovada.
- Alembic com um único head: `e6c3b9a2f410`.
- A suíte completa foi iniciada, mas os testes antigos do modelo sombra dependem de um artefato externo apontado por caminho absoluto em `config/shadow-model-rj.json`. O arquivo não fazia parte do ZIP-base recebido.
