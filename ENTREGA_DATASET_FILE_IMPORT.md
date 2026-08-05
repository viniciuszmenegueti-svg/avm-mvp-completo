# Entrega: importação de arquivos de datasets

Implementação do upload controlado e processamento inicial de arquivos CSV vinculados a versões de datasets.

## Recursos

- upload multipart autenticado
- armazenamento em diretório controlado
- limite configurável de tamanho
- validação de extensão, MIME, checksum e tamanho declarado
- proteção contra path traversal e uploads duplicados
- leitura UTF-8 e UTF-8 com BOM
- detecção de delimitador
- validação de cabeçalho e quantidade de campos
- contagem de registros
- transição atômica para PROCESSING
- persistência de COMPLETED ou FAILED
- consulta do resultado da importação

## Configuração

- `DATASET_UPLOAD_DIR`: diretório raiz de armazenamento
- `DATASET_MAX_UPLOAD_BYTES`: limite por arquivo em bytes, padrão 52428800
