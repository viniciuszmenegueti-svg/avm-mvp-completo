# Massa adversa e Cockpit AVM — Anexo III

Atualização: 31/07/2026

## Objetivo

Este pacote amplia a validação de software para as dez localidades informadas
no Anexo III, sem criar a falsa impressão de que dados sintéticos são dados de
mercado. A massa testa entrada, persistência, recusas contratuais, limites e
interface. Ela não testa acurácia de valor.

As localidades cobertas são Rio de Janeiro/RJ, São Paulo/SP, Brasília/DF,
Salvador/BA, Belo Horizonte/MG, Curitiba/PR, Recife/PE, Fortaleza/CE,
Goiânia/GO e Porto Alegre/RS.

## Separação obrigatória de dados

Há três classes diferentes no projeto:

1. **Cenários sintéticos de sistema**: os 720 registros desta entrega. Servem
   somente a testes de software e possuem `synthetic=true` e
   `contract_eligible=false`.
2. **Pesquisa pública de anúncios**: observações de preço pedido que precisam
   de fonte, evidência, saneamento, geolocalização e revisão. Não são
   transações confirmadas.
3. **Dataset estatístico homologável**: ainda depende de dados reais,
   verificáveis, imutáveis, suficientes e aprovados pelo Responsável Técnico
   para cada cidade × tipologia.

É proibido mover registros da primeira classe para a terceira. O sistema deve
manter `ALLOW_SYNTHETIC_PRICING=false` em homologação e produção.

## Composição da massa

O gerador cria 24 cenários para cada uma das 30 combinações de cidade e
tipologia, totalizando 720:

| Família | Quantidade | Verificação |
|---|---:|---|
| Nominal | 270 | Payload completo, endereço sintético e geolocalização declarada |
| Limites | 240 | Precisão entre 0 e 50 m, contagens mínimas/máximas e campos-limite |
| Unicode | 30 | Acentuação, símbolos e serialização UTF-8 |
| Recusa de localização | 60 | Acima de 50 m ou localização não confirmada; `TR_9_5_D` |
| Recusa de inconsistência | 30 | Cidade/UF incompatíveis com IBGE; `TR_9_5_B` |
| Recusa por conflito | 30 | Conflito declarado e dossiê; `TR_9_5_C` |
| Erro de esquema | 60 | Área zero ou latitude fora da faixa; HTTP 422 |

Dos 720 cenários, 660 esperam HTTP 201. Isso inclui ordens `RECEIVED` e ordens
`REFUSED`, porque uma recusa contratual válida é persistida com dossiê. Os
outros 60 esperam HTTP 422 e não devem ser persistidos.

## Arquivos

- `engine/testing/order_scenarios.py`: catálogo, gerador e SHA-256 canônico;
- `scripts/generate-order-test-dataset.py`: exportação reproduzível;
- `data/test_scenarios/avm-order-scenarios-annex-iii.csv`: análise tabular;
- `data/test_scenarios/avm-order-scenarios-annex-iii.jsonl`: automação;
- `data/test_scenarios/MANIFEST.json`: finalidade, contagens e integridade;
- `tests/test_order_test_scenarios.py`: equilíbrio, esquema, cidades e recusas;
- `tests/test_secure_location_requirement.py`: bloqueio geográfico reforçado;
- `app/static/`: Cockpit AVM sem dependência externa de frontend.

## Regenerar e verificar

```powershell
python scripts/generate-order-test-dataset.py
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

O `MANIFEST.json` deve continuar indicando 720 cenários, 10 localidades, 3
tipologias e `contract_eligible=false`. Uma alteração legítima da massa muda o
SHA-256; a mudança deve ser revisada e registrada no pull request.

## Cockpit AVM

Com a API disponível, abra:

```text
http://localhost:8000/cockpit
```

O fluxo guiado é:

1. informar a chave de integração e testar o acesso;
2. criar a OS selecionando uma das cidades habilitadas;
3. preencher endereço, áreas e tipologia;
4. informar método, evidência, verificador, coordenadas e precisão de até 50 m;
5. declarar eventual conflito de interesse;
6. validar, processar e baixar PDF/CSV;
7. revisar os documentos, hashes, backup e aprovação técnica.

A chave fica somente na memória da página. Não é gravada em `localStorage` ou
`sessionStorage`. A página usa apenas HTML, CSS e JavaScript locais, possui CSP
restritiva e não carrega bibliotecas, fontes ou métricas de terceiros.

## Endurecimento de geolocalização

Em `homologation`, `staging` e `production`, uma localização confirmada só é
aceita quando contém:

- latitude e longitude em faixas válidas;
- imprecisão declarada de 0 a 50 m;
- método de confirmação;
- referência da evidência;
- responsável ou processo verificador.

Ausência de qualquer item resulta em ordem recusada por `TR_9_5_D`, com a
condição `LOCATION_NOT_AUDITABLE`. O desenvolvimento mantém compatibilidade
com testes legados, mas o Cockpit sempre exige o conjunto completo.

## Cenários improváveis adicionais recomendados

Os testes automatizados já cobrem áreas nulas/zero, coordenadas inválidas,
Unicode, limites de contagens e recusas taxativas. Na homologação integrada,
também devem ser executados e arquivados:

- repetição da mesma OS e concorrência na criação;
- transições de status proibidas e repetidas;
- UUID malformado ou inexistente;
- banco indisponível durante criação e emissão;
- timeout e reinício da API durante processamento;
- arquivo de matrícula corrompido, protegido ou de tipo inesperado;
- evidência ausente, hash divergente e documento alterado após coleta;
- geocodificação parcial, divergente ou com precisão exatamente 50,00/50,01 m;
- perda de uma fonte e concentração excessiva em um portal;
- relatório solicitado antes da conclusão;
- credencial ausente, inválida, revogada e rotacionada;
- carga concorrente com medição do prazo ponta a ponta de cinco minutos.

## Limites que permanecem

O Cockpit simplifica o uso do que está implementado, mas não transforma itens
externos em código concluído. Permanecem bloqueios de go-live: dataset real e
aprovado por cidade × tipologia, IA de matrícula, confronto OS × matrícula,
geocodificador CNEFE/IBGE auditável, modelo homologado, Relatório do Modelo,
Fluxo Pareado, assinatura/ART/RRT, integração e sandbox CAIXA, MFA/RBAC, LGPD,
auditoria imutável, desvios/suspensão, fechamento mensal e aceite dos RTs.
