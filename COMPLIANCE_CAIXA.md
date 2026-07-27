# Conformidade CAIXA — estado real do projeto

## Classificação desta versão

Este repositório é um **MVP de workflow, persistência, rastreabilidade e aplicação de regras de recusa para AVM**.

Ele não deve ser apresentado como motor estatístico aderente à NBR 14.653-2, pronto para produção contratual, emissão de laudo ou utilização em decisões de crédito.

## Proteção contra precificação sintética

- O cálculo `RULE_BASED_V1` é reconhecido como demonstrativo.
- Por padrão, `ALLOW_SYNTHETIC_PRICING=false`.
- Sem modelo ou dataset estatístico aplicável, a Ordem de Serviço é recusada pelo motivo taxativo `TR_9_5_A`.
- A recusa persiste referência contratual, evidências, instante de detecção e versões de modelo e dataset.
- O modo demonstrativo somente é habilitado por decisão explícita com `ALLOW_SYNTHETIC_PRICING=true`.
- O modo demonstrativo nunca deve ser utilizado para laudo, crédito ou produção contratual.

## Taxonomia contratual de recusas

O sistema implementa os quatro motivos taxativos previstos no TR §9.5.

### TR_9_5_A — modelo não aplicável

A Ordem de Serviço é recusada quando:

- não existe modelo ou dataset aplicável à cidade e à tipologia do imóvel; ou
- somente o mecanismo demonstrativo de preço-base sintético está disponível e `ALLOW_SYNTHETIC_PRICING=false`.

As evidências registradas podem incluir:

- código IBGE;
- tipologia do imóvel;
- método de precificação;
- condição que provocou a recusa;
- versão do modelo;
- versão do dataset;
- indicação de bloqueio do preço sintético.

### TR_9_5_B — inconsistência de dados

A Ordem de Serviço é recusada quando o nome da cidade ou a UF informada não corresponde ao código IBGE registrado.

O dossiê de recusa registra:

- código IBGE informado;
- cidade informada;
- UF informada;
- cidade esperada;
- UF esperada;
- campos considerados inconsistentes.

O fluxo de status registrado é:

1. `RECEIVED → VALIDATING_INPUT`;
2. `VALIDATING_INPUT → REFUSED`.

Esta implementação cobre atualmente a coerência entre cidade, UF e código IBGE. Ela ainda não cobre extração de matrícula, comparação entre Ordem de Serviço e matrícula ou validação documental completa.

### TR_9_5_C — conflito de interesse

A Ordem de Serviço é recusada quando a entrada contém uma declaração explícita de conflito de interesse.

A declaração exige:

- indicação de existência do conflito;
- tipo do conflito;
- descrição objetiva;
- origem ou responsável pela identificação.

O dossiê registra essas informações como evidência da recusa.

A implementação atual não detecta conflito de interesse automaticamente em bases externas. Ela depende de declaração fornecida pelo sistema integrador, área de compliance ou responsável pelo processo.

### TR_9_5_D — localização não confirmada

A Ordem de Serviço é recusada quando a entrada informa que a localização do imóvel não pôde ser confirmada.

A declaração exige:

- indicação de que a localização não foi confirmada;
- motivo da não confirmação;
- origem ou responsável pela verificação.

Também podem ser informados:

- método de confirmação;
- referência da evidência consultada.

O dossiê registra essas informações como evidência da recusa.

A implementação atual não executa geocodificação real, consulta cartográfica, validação de coordenadas ou confirmação automática do endereço. Ela depende de uma declaração de confirmação recebida na Ordem de Serviço.

## Comportamento operacional das recusas

Para as recusas B, C e D, o sistema:

- cria e persiste a Ordem de Serviço;
- altera o status de `RECEIVED` para `VALIDATING_INPUT`;
- cria o dossiê de recusa com referência contratual e evidências;
- altera o status de `VALIDATING_INPUT` para `REFUSED`;
- registra o histórico das duas transições;
- evita criar mais de um dossiê de recusa para a mesma ordem;
- realiza rollback quando ocorre falha durante a persistência transacional da recusa.

A prioridade aplicada na criação de uma ordem é:

1. verificação de identificador externo duplicado;
2. conflito de interesse — `TR_9_5_C`;
3. localização não confirmada — `TR_9_5_D`;
4. inconsistência entre cidade, UF e código IBGE — `TR_9_5_B`;
5. criação normal da ordem.

A recusa `TR_9_5_A` ocorre posteriormente, no momento da tentativa de precificação.

## Validação automatizada atual

Na última validação da branch `develop`, o projeto apresentou:

- 254 testes aprovados;
- cobertura total de 98,84%;
- formatação validada em 146 arquivos;
- Ruff aprovado;
- MyPy aprovado em 67 arquivos.

Esses resultados comprovam o comportamento automatizado coberto pelos testes, mas não substituem homologação funcional, regulatória, estatística, de segurança e de integração com a CAIXA.

## Itens ainda não implementados

1. Motor de regressão aderente à NBR 14.653-2.
2. Seleção, treinamento, validação e governança de modelos estatísticos.
3. Dataset real, versionado, representativo e auditável por cidade e tipologia.
4. LOOCV, PRESS, diagnósticos estatísticos, graus de fundamentação e precisão.
5. Extração de matrícula com confiança por campo.
6. Coerência automatizada entre Ordem de Serviço, matrícula e demais documentos.
7. Geocodificação auditável e confirmação automática da localização.
8. Validação de latitude, longitude, endereço e referências cartográficas.
9. Detecção automática de conflito de interesse em fontes internas ou externas.
10. Laudo PDF e arquivos CSV no formato contratual.
11. Assinatura ICP-Brasil e emissão ou vinculação de ART/RRT.
12. SLA ponta a ponta de cinco minutos.
13. Entrega pela integração oficial da CAIXA.
14. Fechamento, medição e faturamento contratual completos.
15. Controles completos de segurança, privacidade, LGPD e gestão de acessos.
16. Monitoramento operacional, alertas e resposta a incidentes em produção.

## Regra operacional

Na ausência de qualquer elemento necessário para uma avaliação tecnicamente defensável, o sistema deve recusar a Ordem de Serviço conforme um dos quatro motivos taxativos do TR §9.5.

O sistema nunca deve:

- fabricar um valor;
- ocultar a ausência de dados;
- utilizar fallback sintético em produção contratual;
- apresentar o mecanismo demonstrativo como modelo estatístico homologado;
- emitir laudo sem os requisitos técnicos, profissionais e documentais aplicáveis.