# Relatório de implementação: importação de arquivos de datasets

## Escopo concluído

- upload administrativo multipart de CSV
- armazenamento em diretório controlado e configurável
- validação de nome, extensão, MIME, tamanho e SHA-256
- escrita temporária e movimentação atômica do arquivo
- bloqueio de upload duplicado
- proteção contra path traversal
- limite de tamanho configurável
- processamento CSV com UTF-8 e UTF-8 BOM
- detecção de delimitador entre vírgula, ponto e vírgula, tabulação e barra vertical
- validação de cabeçalho vazio ou duplicado
- validação da quantidade de campos por linha
- contagem de registros
- transição atômica de REGISTERED para PROCESSING
- persistência dos estados COMPLETED e FAILED
- consulta do resultado da importação
- autenticação administrativa nos endpoints

## Endpoints

- `POST /admin/dataset-versions/{dataset_version_id}/file`
- `POST /admin/dataset-versions/{dataset_version_id}/process-file`
- `GET /admin/dataset-versions/{dataset_version_id}/import-result`

## Configuração

- `DATASET_UPLOAD_DIR`: raiz dos arquivos enviados
- `DATASET_MAX_UPLOAD_BYTES`: limite por arquivo, padrão de 50 MiB

## Validação

- 15 testes específicos aprovados
- compilação Python aprovada
- Alembic permanece com um único head: `e6c3b9a2f410`

A suíte completa foi iniciada, mas os testes antigos do modelo sombra dependem de um artefato externo indicado por caminho absoluto em `config/shadow-model-rj.json`. Esse artefato não estava no ZIP-base recebido. A primeira falha reproduzida foi `ShadowValuationServiceError: Arquivo não encontrado` para `model-artifact-v3.json`.
