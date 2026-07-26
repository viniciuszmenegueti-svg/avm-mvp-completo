# Relatório de Testes — AVM MVP v0.3.0

## Resultado

- Testes coletados e aprovados: **227**
- Cobertura total: **99,02%**
- Cobertura mínima exigida: **95%**
- Compilação Python: aprovada
- Cadeia de migrations do Alembic: íntegra, com `c8d7e6f5a4b3` como `head`

## Cenários novos validados

- Listagem e filtro de imóveis.
- Atualização parcial de imóvel.
- Detecção de imóvel duplicado.
- Atualização de imóvel inexistente.
- Criação de ordem a partir de imóvel cadastrado.
- Imóvel inexistente ao criar ordem.
- Identificador externo duplicado.
- Persistência e retorno dos fatores de avaliação.
- Retorno dos motivos do índice de confiança.
- Diagnóstico administrativo autenticado.

## Comandos usados

```powershell
python -m compileall -q app engine migrations tests
alembic history
python -m pytest -q
```

## Observação de ambiente

O binário Ruff não estava disponível no ambiente de empacotamento sem acesso ao
índice de pacotes. O projeto mantém Ruff e pre-commit nas dependências de
desenvolvimento; execute `python -m ruff check .` no ambiente local após instalar
`requirements-dev.txt`.
