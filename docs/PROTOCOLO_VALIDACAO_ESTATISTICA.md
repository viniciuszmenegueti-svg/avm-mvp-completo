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

## Cálculos implementados

O módulo `engine/models/linear_regression_nbr.py` executa:

1. validação de dimensões, finitude, graus de liberdade e posto completo;
2. regressão OLS determinística com intercepto;
3. resíduos, erro padrão, R², R² ajustado e coeficiente de correlação;
4. erros padrão, estatísticas t e significância bilateral dos coeficientes;
5. matriz chapéu, resíduos deletados, PRESS e RMSE de LOOCV;
6. estimativa do imóvel-alvo e intervalo de confiança configurável, com padrão
   de 80%;
7. enquadramento objetivo de amostra por `N/(k+1)` e gates de significância e
   amplitude;
8. gates de coerência de sinal, que apenas reprovam o candidato e nunca alteram
   coeficientes.

## Gates

Um candidato não segue para revisão do RT se:

- a matriz for singular ou sem graus de liberdade;
- houver valores não finitos ou valores de mercado não positivos;
- a estimativa do alvo for não positiva;
- algum gate econômico falhar;
- amostra, significância ou precisão não atingirem o grau mínimo definido para
  a cidade/tipologia;
- PRESS/LOOCV indicar generalização inadequada segundo o limiar versionado;
- o dataset não possuir fonte e trilha de saneamento completas.

## O que o endpoint não faz

`POST /statistical-models/fit` é administrativo e produz diagnóstico de um
candidato. Ele sempre retorna `homologated=false`. Não cadastra dataset, não
ativa cidade, não assina relatório e não autoriza uso em crédito.

## Testes de admissão antes da produção

- reproduzir laudos aceitos fornecidos pelos RTs dentro da tolerância aprovada;
- validar cálculos contra gabaritos independentes;
- executar testes de estabilidade, influência, resíduos e multicolinearidade;
- registrar decisão do RT e versão exata de código, modelo e dataset;
- gerar Relatório do Modelo e concluir Fluxo Pareado da CAIXA.
