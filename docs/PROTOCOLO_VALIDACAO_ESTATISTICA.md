# Protocolo de validação estatística

## Objetivo

Avaliar modelos candidatos de forma reproduzível, sem confundir ajuste
estatístico com homologação. O Responsável Técnico continua responsável pela
seleção das variáveis, análise de mercado, enquadramento normativo e aprovação.

## Entrada mínima

- dados de mercado com fonte verificável, data, localização, tipologia,
  características físicas e valor;
- trilha de saneamento com motivo para cada exclusão;
- versão imutável do dataset;
- definição das variáveis, unidades, transformações e sinais economicamente
  esperados;
- combinação única de cidade/região, tipologia e data de referência.

Antes de montar as matrizes numéricas, toda observação deve passar pelo fluxo
descrito em `docs/COLETA_DADOS_INTERNET.md`. O validador preserva rejeições,
impede que preço pedido seja tratado como transação e exige coordenada com
precisão auditável de até 50 m. A saída `model_ready=true` é condição necessária,
mas não suficiente, para executar um candidato.

## Cálculos implementados

O módulo `engine/models/linear_regression_nbr.py` executa:

1. validação de dimensões, finitude, graus de liberdade e posto completo;
2. regressão OLS determinística com intercepto;
3. resíduos, erro padrão, R², R² ajustado e coeficiente de correlação;
4. erros padrão, estatísticas t e significância bilateral dos coeficientes;
5. matriz chapéu, resíduos deletados, PRESS e RMSE de LOOCV;
6. teste F global e p-valor;
7. VIF, teste de normalidade, Breusch-Pagan, Durbin-Watson, resíduos
   padronizados e distância de Cook;
8. estimativa do alvo diagnóstico e intervalo de confiança obrigatório de 80%;
9. itens automáticos de amostra, significância individual, significância global
   e grau de precisão separado;
10. domínio mínimo/máximo de cada variável e bloqueio de extrapolação;
11. gates de coerência de sinal, que reprovam e nunca manipulam coeficientes.

Esses cálculos não cobrem sozinhos a pontuação integral de fundamentação da
NBR. O sistema retorna `overall=null` e identifica somente o
`automatic_fundamentation_gate`. A precisão é recalculada por imóvel e não é
reutilizada a partir do alvo do treinamento.

## Gates

Um candidato não segue para revisão do RT se:

- a matriz for singular ou sem graus de liberdade;
- houver valores não finitos ou valores de mercado não positivos;
- a estimativa do alvo for não positiva;
- algum gate econômico falhar;
- os itens automáticos de amostra e significância não atingirem grau mínimo;
- PRESS/LOOCV indicar generalização inadequada segundo o limiar versionado;
- o dataset não possuir fonte e trilha de saneamento completas.

Na inferência, a OS também é recusada quando estiver fora do domínio observado,
quando o artefato não reproduzir seus hashes ou quando o IC80 individual tiver
amplitude superior a 50%.

## O que o endpoint não faz

`POST /statistical-models/fit` é administrativo e produz diagnóstico de um
candidato. Ele sempre retorna `homologated=false`. Não cadastra dataset, não
ativa cidade, não assina relatório e não autoriza uso em crédito.

## Registro controlado para homologação sombra

`POST /statistical-models/train` calcula o hash no servidor e persiste a matriz,
os valores, a semântica da variável dependente, o domínio, coeficientes,
diagnósticos, vigência e hashes SHA-256. O hash opcional informado pelo cliente
é apenas uma conferência e precisa coincidir. O endpoint de aprovação exige ator
distinto daquele que treinou e promove somente a `HOMOLOGATION_APPROVED`.

Uma avaliação em `HOMOLOGATION_SHADOW` seleciona essa versão pela combinação
cidade, tipologia e vigência, sem novo ajuste durante a avaliação. PDF, CSV e API
registram o modelo e os hashes. O sistema bloqueia a entrega e informa
`contractual_validity=false`. Essa aprovação técnica não representa decisão do
RT, Relatório do Modelo aceito, Fluxo Pareado ou autorização da CAIXA.

`GET /statistical-models/{id}/report.pdf` gera uma minuta separada do Relatório
do Modelo com escopo, dataset, variáveis, coeficientes, domínios, diagnósticos e
gráficos. A minuta permanece sem validade contratual e sem assinatura.

## Testes de admissão antes da produção

- reproduzir laudos aceitos fornecidos pelos RTs dentro da tolerância aprovada;
- validar cálculos contra gabaritos independentes;
- executar testes de estabilidade, influência, resíduos e multicolinearidade;
- registrar decisão do RT e versão exata de código, modelo e dataset;
- gerar Relatório do Modelo e concluir Fluxo Pareado da CAIXA.
