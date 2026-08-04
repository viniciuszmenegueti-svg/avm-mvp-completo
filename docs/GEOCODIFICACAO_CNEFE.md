# Geocodificação auditável CNEFE/IBGE

## Objetivo e limite de conformidade

O Cockpit pode sugerir latitude e longitude a partir do endereço informado,
sem transmitir o endereço para um serviço público externo. A pesquisa ocorre
na cópia local de um CSV municipal oficial do CNEFE/IBGE.

A sugestão não comprova sozinha a imprecisão máxima de 50 m. O CNEFE publica o
nível de obtenção da coordenada (`NV_GEO_COORD`), não uma medida individual de
erro em metros para cada registro. Por isso, o campo de imprecisão permanece
vazio e a OS só pode ser aceita em ambiente seguro depois de serem informados:

- precisão numérica menor ou igual a 50 m;
- evidência arquivada que sustente essa precisão;
- pessoa ou processo responsável pela conferência.

O fluxo permanece classificado como **parcial** até a importação controlada das
bases municipais, aprovação do protocolo de precisão pelo RT e homologação.

## Regras do resolver

O endpoint protegido `POST /geocoding/resolve`:

1. confere a coerência entre cidade, UF e código IBGE;
2. normaliza acentos, caixa, espaços, CEP e número;
3. busca correspondência exata por município + CEP + logradouro + número;
4. permite sugestão apenas quando existe um único registro de nível 1 ou 2;
5. bloqueia múltiplos registros como `AMBIGUOUS`;
6. bloqueia níveis 3 a 6 como `INSUFFICIENT_POSITIONAL_QUALITY`;
7. não usa aproximação por bairro, centróide, face, localidade ou setor;
8. não retorna nem presume `accuracy_meters`;
9. registra toda tentativa na tabela `geocoding_audits`.

Significado preservado de `NV_GEO_COORD`:

| Nível | Origem posicional | Uso automático |
|---|---|---|
| 1 | coordenada original do endereço no Censo 2022 | sugestão permitida |
| 2 | endereço ajustado por agrupamento do mesmo número | sugestão permitida |
| 3 | endereço estimado | bloqueado |
| 4 | face de quadra | bloqueado |
| 5 | localidade | bloqueado |
| 6 | setor censitário | bloqueado |

Mesmo nos níveis 1 e 2, a precisão em metros continua pendente de confirmação.

## Obter a fonte oficial

Baixe o CSV da cidade ou UF somente da página/FTP oficial do IBGE e preserve o
arquivo original fora do Git. Registre a data da obtenção e a edição indicada
pelo IBGE. Não altere o CSV antes do cálculo do hash.

Antes da importação, confirme que a cidade existe em `GET /cities` e execute as
migrações:

```powershell
docker compose exec -T api alembic upgrade head
```

## Importar um CSV municipal

O exemplo abaixo usa São Paulo. Substitua caminho e versão pela fonte realmente
baixada:

```powershell
& ".\.venv\Scripts\python.exe" `
  "scripts\import-cnefe.py" `
  "C:\CAMINHO-SEGURO\CNEFE_3550308.csv" `
  --dataset-version "CNEFE-CENSO-2022-EDICAO-20240521" `
  --city-ibge-code "3550308" `
  --state "SP"
```

O importador:

- exige CSV delimitado por ponto e vírgula;
- valida município, coordenadas e nível posicional;
- calcula e persiste o SHA-256 do arquivo-fonte;
- preserva o identificador único do endereço e a versão declarada;
- é idempotente para o mesmo registro, versão, endereço e coordenadas;
- interrompe a operação quando encontra uma linha estruturalmente inválida.

O arquivo-fonte, seu hash e o log da importação devem ser arquivados na pasta
operacional de homologação e incluídos no processo de backup validado.

## Testar pelo Cockpit

1. abra `http://localhost:8000/cockpit`;
2. preencha cidade, CEP, logradouro e número;
3. clique em **Localizar pelo endereço**;
4. confira coordenadas, qualidade CNEFE e `audit_id`;
5. informe a imprecisão comprovada, a referência da evidência e o verificador;
6. só então crie a ordem.

Se o endereço for alterado após a busca, o Cockpit bloqueia o envio até uma
nova geocodificação. O relatório PDF/CSV preserva método, coordenadas, precisão,
evidência combinada e responsável declarados na ordem.

## Itens necessários antes da homologação contratual

- importar os arquivos oficiais das dez localidades do Anexo III;
- reconciliar contagem de linhas, rejeições e SHA-256 com as fontes;
- documentar e aprovar pelo RT o protocolo que mede a precisão em metros;
- testar amostras conhecidas, duplicidades, homônimos, números sem complemento,
  CEP divergente e endereços limítrofes;
- controlar acesso, retenção, backup e restauração das bases e auditorias;
- anexar as evidências ao dossiê de homologação.
