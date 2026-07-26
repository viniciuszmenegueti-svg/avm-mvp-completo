# Guia de Homologação do MVP

## Sequência recomendada

1. Consultar `GET /health/ready`.
2. Cadastrar um imóvel em `POST /property-assets`.
3. Consultar o imóvel pelo ID.
4. Confirmar que o mesmo endereço retorna 409 ao tentar cadastrar novamente.
5. Criar ordem em `POST /orders/from-property-asset`.
6. Alterar a ordem para `VALIDATING_INPUT`.
7. Executar `POST /orders/{id}/valuation`.
8. Verificar `factors`, `confidence_score` e `confidence_reasons`.
9. Consultar `GET /admin/diagnostics` com chave administrativa.

## Critérios de aceite

- Nenhum endpoint retorna erro 500 no fluxo nominal.
- IDs são UUIDs válidos.
- Valores monetários preservam duas casas decimais.
- A segunda avaliação da mesma ordem retorna o resultado persistido.
- O status final da ordem é `COMPLETED`.
- O diagnóstico apresenta as contagens esperadas.

## Não validar como preço de mercado

A homologação deve avaliar o fluxo técnico e a rastreabilidade. Os preços-base são
demonstrativos; a acurácia comercial só poderá ser avaliada após ingestão de dados
reais e definição de métricas como MdAPE, MAPE, erro por faixa e cobertura regional.
