# Relatório de Implementação — AVM MVP v0.3.0

## Base recebida

A base recebida já possuía FastAPI, SQLAlchemy, Alembic, PostgreSQL, cadastro de
ordens, preços-base, avaliação determinística, histórico, recusas, autenticação
administrativa e API inicial de imóveis.

## Implementações realizadas

### Imóveis persistentes

- Campo de complemento incorporado ao ativo imobiliário.
- Tipos monetários e de área mantidos como `Decimal` no domínio.
- Listagem paginada com filtro por código IBGE.
- Atualização parcial via `PATCH`.
- Detecção de duplicidade por tipologia, cidade, CEP, logradouro, número e complemento.
- Resposta HTTP 409 estruturada para duplicidades.

### Integração entre imóvel e ordem

- Chave estrangeira opcional `orders.property_asset_id`.
- Endpoint `POST /orders/from-property-asset`.
- Conversão do ativo persistente para o snapshot imutável usado pela ordem.
- Preservação da compatibilidade com o endpoint original `POST /orders`.

### Explicabilidade do AVM

- Persistência de fatores de cálculo em JSON.
- Persistência dos motivos do índice de confiança.
- Retorno dos fatores e motivos na API de avaliação.
- Resultado continua determinístico e reproduzível pela versão do modelo.

### Operação

- Endpoint protegido `GET /admin/diagnostics`.
- Contagens de ordens, imóveis e avaliações.
- Distribuição das ordens por status.
- Verificação de conectividade com o banco.

### Banco de dados

Foram adicionadas três migrations sequenciais:

1. `81e4b0f7c2a1_expande_property_assets.py`
2. `b2c9a134e7d5_adiciona_explicabilidade_avaliacoes.py`
3. `c8d7e6f5a4b3_vincula_ordens_a_imoveis.py`

## Limites do MVP

O modelo continua utilizando preços-base demonstrativos. O projeto está preparado
para homologação técnica, mas não deve emitir laudos ou sustentar decisões de
crédito sem dados reais, calibração estatística e validação independente.
