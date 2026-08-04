# Coleta auditável de dados públicos de mercado

## Situação desta entrega

Este fluxo é uma base de **teste e saneamento**, não um dataset homologado. A
pesquisa de 31/07/2026 registrou metadados públicos mínimos de anúncios de
apartamentos em São Paulo/SP. Descrições, fotografias, telefones e dados de
contato não foram copiados.

Os anúncios são evidências de **preço pedido** (`OFFER`). Eles não demonstram o
preço de uma transação e não recebem automaticamente
`usable_market_value_brl`. Qualquer tratamento de oferta, transformação ou
fator de negociação depende de metodologia versionada e aprovação expressa do
Responsável Técnico (RT).

Arquivos desta entrega:

- `data/templates/market_observations.template.csv`: leiaute vazio;
- `data/samples/internet_market_observations_sp_2026.csv`: pequena amostra
  pública para testar rejeições e rastreabilidade;
- `scripts/validate-market-dataset.py`: validador em lote;
- `POST /statistical-models/datasets/assess`: o mesmo gate pela API;
- `engine/datasets/market_observations.py`: regras determinísticas e auditáveis.

## Importações VivaReal fornecidas em XLSX

O comando abaixo concilia as duas exportações, calcula o SHA-256 de cada
arquivo, desduplica por URL e por impressão digital física, preserva todas as
exclusões em CSV e registra um candidato estatístico de **pesquisa**:

```powershell
& ".\.venv\Scripts\python.exe" `
  "scripts\train-vivareal-research-model.py" `
  "C:\CAMINHO\dataset_vivareal.xlsx" `
  "C:\CAMINHO\dataset_vivareal 2.xlsx" `
  --env-file ".env.homologation" `
  --base-url "http://localhost:8001"
```

Os dois arquivos conhecidos contêm as mesmas 600 URLs e, portanto, **não**
são concatenados como 1.200 observações. O script também exclui a oferta de
locação e linhas sem todas as variáveis do ajuste. Telefones, imagens,
descrições e dados do anunciante não são copiados para os artefatos de
auditoria.

Como a variável observada é `asking_price_brl`, o artefato permanece
obrigatoriamente `CANDIDATE`, com classificação `RESEARCH_ONLY`. A API rejeita
sua aprovação de homologação e a inferência AVM. O treino serve para testar
leitura, saneamento, regressão, diagnósticos, persistência e emissão do
Relatório do Modelo sem converter preço pedido em valor de mercado.

## Requisitos aplicados

O edital exige longitude e latitude com imprecisão máxima de 50 metros. Os
documentos técnicos também exigem fonte verificável, data, localização,
tipologia, características, valor, contemporaneidade, representatividade e
registro de toda exclusão.

O validador separa dois conceitos:

1. `collection_valid`: a linha tem origem, URL, identificador, captura, escopo,
   tipologia, área e preço compatíveis com a evidência declarada;
2. `model_eligible`: além do anterior, a linha tem data exata e contemporânea,
   endereço completo, CEP, coordenadas, precisão declarada de até 50 m,
   método/fonte/verificador da geocodificação, evidência com SHA-256 e valor de
   mercado utilizável aprovado pelo RT.

Uma linha reprovada nunca é apagada. Ela permanece no CSV com códigos de
motivo, eventual referência de duplicidade e impressão digital da fonte.

## Fontes pesquisadas

| Fonte | Uso permitido neste fluxo | Limitação observada na pesquisa |
|---|---|---|
| Imovelweb | página individual e preço pedido | parte dos anúncios oculta endereço; mapa não comprova precisão |
| Chaves na Mão | página individual e preço pedido | muitos registros têm apenas logradouro ou “endereço indisponível” |
| QuintoAndar | página individual e preço pedido | número do imóvel foi ocultado no exemplo pesquisado; data relativa |
| Lello Imóveis | página individual e preço pedido | exemplos sem número e sem data exata de referência |
| Lopes | página individual e preço pedido | exemplos sem número e sem data exata de referência |
| ZAP Imóveis | descoberta de candidatos | card de categoria agrega anúncios e não serve como evidência individual |
| OLX | descoberta de candidatos | card de categoria não preserva endereço/URL individual suficiente |
| Viva Real | fonte prevista | requer captura individual estável antes de incluir uma linha |
| Mercado Livre | fonte prevista | requer captura individual estável antes de incluir uma linha |

Outros portais podem ser usados com o mesmo leiaute. O nome do portal não torna
o dado válido: cada linha precisa passar pelos mesmos gates.

## Regras de coleta

1. Conferir termos de uso, `robots.txt`, licença e limites da fonte antes de
   qualquer automação. Não contornar login, CAPTCHA, bloqueio ou limitação.
2. Preferir coleta manual assistida ou integração autorizada. Guardar somente
   os campos necessários para avaliação e a evidência permitida.
3. Usar URL individual estável e identificador do anúncio. Página de busca ou
   card de categoria serve apenas para triagem.
4. Registrar `captured_at` com fuso e a data exata do anúncio/atualização em
   `source_reference_date`. Data inferida ou somente a data de captura recebe
   precisão diferente de `EXACT` e não entra no modelo.
5. Classificar `evidence_type` como `OFFER` ou `TRANSACTION`. Nunca preencher
   `transaction_price_brl` a partir de anúncio.
6. Não interpretar “sem informação de vaga” como zero. Zero só é válido quando
   a fonte declarar expressamente que não há vaga.
7. Distinguir área privativa, construída, total e de terreno. Um card que exibe
   faixa ou área ambígua deve ser conferido na página individual.
8. Preservar a evidência autorizada em diretório operacional fora do Git e
   registrar seu caminho relativo e SHA-256. Não versionar imagens, documentos
   ou dados pessoais em repositório público.
9. Detectar replicações entre portais. Duplicatas permanecem no dataset, mas
   somente uma ocorrência pode ser candidata ao ajuste.
10. Encaminhar todas as inclusões, ajustes de oferta e exclusões ao RT.

## Geolocalização

O endereço anunciado e o ponto exibido por um portal não demonstram, por si
sós, precisão de até 50 metros. Para cada observação candidata devem existir:

- endereço padronizado e seus componentes conferidos;
- latitude e longitude em graus decimais;
- `location_accuracy_meters` numérico e menor ou igual a 50;
- método de geocodificação;
- referência de evidência e versão da base;
- identificador do processo ou pessoa que verificou o resultado.

O CNEFE do IBGE é a fonte oficial prioritária deste projeto porque contém
endereços e coordenadas geográficas. O pareamento deve registrar o identificador
único do endereço, a edição da base, os componentes coincidentes e o sistema de
referência. Um pareamento CNEFE não autoriza presumir `accuracy_meters=50`: a
imprecisão declarada precisa vir de protocolo de qualidade documentado e
validado pelo RT.

O endpoint `POST /geocoding/resolve` implementa esse pareamento contra a base
local. Ele exige cidade/UF/IBGE coerentes e correspondência exata de CEP,
logradouro e número. Uma sugestão automática somente é devolvida quando há um
único registro e `NV_GEO_COORD` é 1 ou 2. Mais de um candidato, ausência de
registro ou níveis 3 a 6 bloqueiam o preenchimento automático. Toda tentativa
gera `audit_id`, hash da consulta normalizada, identidade cliente, Request ID,
versão e SHA-256 da fonte. Consulte `docs/GEOCODIFICACAO_CNEFE.md`.

O Nominatim público não é solução de produção ou de geocodificação em lote. Sua
[política de uso](https://operations.osmfoundation.org/policies/nominatim/)
limita chamadas, exige identificação/atribuição e desencoraja consultas em
massa. Se for utilizado em ensaio pontual, o resultado deve ser tratado como
referência secundária e nunca como prova automática do limiar contratual.

Quando a localização não puder ser confirmada, a observação é excluída do
modelo. Para uma OS, a consequência contratual é a recusa por falta de
convicção sobre a localização, não uma coordenada estimada sem prova.

## Tratamento de preço

Para `OFFER`, preencher apenas `asking_price_brl`. Para torná-la candidata ao
modelo, o RT deve aprovar um tratamento e registrar:

- `usable_market_value_brl`;
- `market_value_basis=RT_APPROVED_OFFER_ADJUSTMENT`;
- `market_adjustment_reference` com fórmula, versão, período e evidências;
- `rt_review_reference` com a decisão assinada ou formalmente registrada.

Para `TRANSACTION`, registrar evidência verificável do negócio, preencher
`transaction_price_brl`, usar `market_value_basis=CONFIRMED_TRANSACTION` e
registrar a conferência do RT. Opinião de corretor ou imobiliária não deve ser
classificada como transação.

## Amostra e representatividade

Para o candidato atual com `k=7`, o gate calcula:

- Grau I: 24 observações válidas;
- Grau II: 32 observações válidas;
- Grau III: 48 observações válidas.

O plano recomenda pelo menos 72 válidas após saneamento e cerca de 90 brutas.
Quantidade não substitui cobertura espacial, temporal e por faixa de valor. O
validador também reprova a prontidão quando uma única fonte supera 50% das
observações elegíveis; o limite é configurável e ainda depende de decisão do
RT. Anúncios replicados não contam como fontes independentes.

## Executar a amostra de pesquisa

Na raiz do projeto:

```powershell
New-Item -ItemType Directory -Force ".audit\market-data" | Out-Null

& ".\.venv\Scripts\python.exe" `
  "scripts\validate-market-dataset.py" `
  "data\samples\internet_market_observations_sp_2026.csv" `
  --reference-date "2026-07-31" `
  --variable-count 7 `
  --output-csv ".audit\market-data\internet-sp-auditado.csv" `
  --manifest ".audit\market-data\internet-sp-manifest.json"
```

O resultado esperado é `model_ready=false`. Isso é intencional: a amostra testa
os gates com anúncios reais, mas não possui evidências arquivadas, transações ou
geolocalização comprovada. Não use `--require-model-ready` nessa demonstração;
essa opção existe para pipelines de homologação e retorna código 2 quando algum
gate impedir o ajuste.

## Gate pela API

`POST /statistical-models/datasets/assess` exige a chave administrativa. O
payload contém `policy` e `observations` no mesmo formato lógico do CSV. A
resposta inclui contagens, códigos de exclusão, duplicidades, concentração por
fonte, grau amostral e SHA-256 canônico do conjunto.

O endpoint não persiste dados, não ajusta modelo, não homologa dataset e não
substitui a revisão do RT. Somente observações com `model_eligible=true` podem
ser transformadas em matrizes para `POST /statistical-models/fit`.

## Critério para avançar à homologação estatística

Avançar apenas quando:

- todas as evidências autorizadas estiverem preservadas e verificadas;
- houver valor utilizável aprovado pelo RT;
- localização e precisão estiverem comprovadas;
- exclusões e duplicidades estiverem justificadas;
- a versão do dataset e seu SHA-256 estiverem congelados;
- `model_ready=true` para o grau definido;
- EDA, resíduos, influência, heterocedasticidade, VIF, PRESS/LOOCV e coerência
  econômica tiverem sido revisados;
- o RT tiver assinado o plano, o relatório do modelo e a decisão de uso.
