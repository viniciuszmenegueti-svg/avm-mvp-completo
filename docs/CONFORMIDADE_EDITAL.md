# Conformidade com o Edital CR 012/2026

Atualização: 31/07/2026

A matriz detalhada e vigente está em
[`MATRIZ_HOMOLOGACAO_2026.md`](MATRIZ_HOMOLOGACAO_2026.md). Este arquivo mantém
somente a decisão de liberação para evitar versões contraditórias da mesma
informação.

## Decisão atual

- **testes técnicos controlados:** autorizáveis em
  `MODEL_EXECUTION_MODE=HOMOLOGATION_SHADOW`;
- **homologação formal CAIXA:** não concluída;
- **operação contratual:** bloqueada deliberadamente no código;
- **validade dos PDFs/CSVs de teste:** `contractual_validity=false`;
- **dados sintéticos ou anúncios de internet:** nunca constituem dataset
  contratual sem saneamento, evidência, RT e aceite externo.

## Controles que não podem ser contornados

1. `ALLOW_SYNTHETIC_PRICING=false` em ambiente seguro;
2. duas identidades administrativas distintas para treino e revisão;
3. modelo por cidade, tipologia e vigência, com artefato revalidado por hash;
4. extrapolação bloqueada e precisão IC80 recalculada por imóvel;
5. geocodificação CNEFE vinculada à auditoria real da mesma identidade;
6. entregas contratuais bloqueadas no modo sombra;
7. prazo, ator, request ID, recusa e evidência persistidos;
8. nenhum campo ou teste local pode declarar aceite da CAIXA, assinatura de RT
   ou conclusão do Fluxo Pareado.

## Bloqueadores formais remanescentes

- integração e sandbox oficiais da CAIXA;
- matrícula/IA e confronto documental;
- dataset real e parecer dos Responsáveis Técnicos;
- Relatório do Modelo definitivo por cidade;
- RTs, CREA/CAU, ART/RRT e assinatura;
- Fluxo Pareado de 30 dias e parâmetros oficiais;
- OIDC/MFA, RBAC, TLS/cofre e auditoria WORM;
- desvios/suspensão, revisão pós-emissão e faturamento.

Nenhum resultado de cobertura, PR, PDF demonstrativo ou teste interno substitui
esses marcos.
