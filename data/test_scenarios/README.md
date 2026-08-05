# Massa adversa de testes — Anexo III

Esta pasta contém somente dados **sintéticos** para validar contratos de API,
regras de recusa, limites, codificação Unicode e fluxos operacionais nas dez
localidades do Anexo III.

Nenhum registro representa imóvel real, evidência de mercado, geocodificação
auditável ou transação. Por isso, todos os cenários possuem
`synthetic=true` e `contract_eligible=false` e são proibidos em treinamento,
ajuste, homologação estatística ou emissão contratual.

## Cobertura

- 10 localidades e respectivos códigos IBGE;
- apartamentos, casas e terrenos;
- entradas nominais e limites de 0 a 50 m;
- precisão acima de 50 m e localização não confirmada;
- inconsistência cidade/UF/IBGE;
- conflito de interesse;
- áreas inválidas e coordenadas fora da faixa;
- Unicode, campos extensos, contagens zero e máximas.

Cada combinação cidade × tipologia contém 24 cenários. O manifesto informa a
quantidade total, a distribuição e o SHA-256 canônico.

## Regeneração

```powershell
python scripts/generate-order-test-dataset.py
```

Arquivos gerados:

- `avm-order-scenarios-annex-iii.csv`: inspeção e planilha;
- `avm-order-scenarios-annex-iii.jsonl`: automação e execução em lote;
- `MANIFEST.json`: finalidade, contagens e integridade lógica.
