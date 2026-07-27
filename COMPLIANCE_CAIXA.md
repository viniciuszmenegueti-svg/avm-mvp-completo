# Conformidade CAIXA — estado real do projeto

## Classificação desta versão

Este repositório é um **MVP de workflow e persistência para AVM**. Ele não deve ser apresentado como motor estatístico NBR 14.653-2 pronto para produção.

## Proteção implementada nesta revisão

- O cálculo `RULE_BASED_V1` é reconhecido como demonstrativo.
- Por padrão, `ALLOW_SYNTHETIC_PRICING=false`.
- Sem modelo/dataset estatístico aplicável, a OS é recusada pelo motivo taxativo `TR_9_5_A`.
- A recusa persiste referência contratual, evidências, instante de detecção e versões de modelo/dataset.
- O modo demonstrativo só é habilitado por decisão explícita com `ALLOW_SYNTHETIC_PRICING=true`; nunca deve ser usado para laudo, crédito ou produção contratual.

## Itens ainda não implementados

1. Motor de regressão aderente à NBR 14.653-2 e seleção/validação de modelos.
2. Dataset real, versionado e auditável por cidade e tipologia.
3. LOOCV/PRESS, diagnósticos, graus de fundamentação e precisão.
4. Extração de matrícula com confiança por campo e coerência OS × matrícula.
5. Geocodificação auditável e regra de convicção de localização.
6. Laudo PDF, CSV, assinatura ICP-Brasil e ART/RRT.
7. SLA ponta a ponta de cinco minutos e entrega pela integração CAIXA.
8. Fechamento/faturamento contratual completo.

## Regra operacional

Na ausência de qualquer elemento necessário a uma avaliação defensável, o sistema deve recusar segundo um dos quatro motivos do TR §9.5; nunca deve fabricar valor ou utilizar fallback sintético.
