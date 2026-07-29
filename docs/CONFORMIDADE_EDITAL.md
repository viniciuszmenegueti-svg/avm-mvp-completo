# Matriz de conformidade - CAIXA CR 012/2026

Atualização: 29/07/2026

Esta matriz distingue código executável, dependências externas e obrigações
organizacionais. "Implementado" não significa homologado pela CAIXA nem
substitui validação dos Responsáveis Técnicos.

| Referência | Exigência | Estado verificável | Evidência no projeto |
|---|---|---|---|
| TR 2.2(ii) | Modelo verificável, com critérios e premissas | Parcial | `engine/models/linear_regression_nbr.py` calcula OLS, significância, PRESS/LOOCV, IC80 e gates econômicos; ainda falta registry persistente de datasets/modelos reais |
| TR 2.3 / RF-006 | Entrega PDF e CSV por API | Parcial | Endpoints `report.pdf` e `report.csv`; o PDF ainda não é a peça técnica completa e não possui assinatura |
| TR 2.4, 2.5, 17.11 | LGPD, sigilo e uso exclusivo | Parcial | Dados brutos e documentos são ignorados pelo Git; credenciais ficam no ambiente; faltam política de retenção, direitos dos titulares, criptografia gerenciada e evidências operacionais |
| TR 3 | Conflito de interesses | Parcial | Declaração, recusa `TR_9_5_C` e dossiê persistido; detecção automática depende de bases externas e processo de compliance |
| TR 7.2 / RF-002 | IA para leitura automatizada de matrícula | Não implementado | Falta provedor de IA, upload seguro, classificação do documento, extração por campo e confiança |
| TR 7.5 e 7.7 / RF-003 | Veracidade e consistência dos dados | Parcial | Coerência cidade/UF/IBGE e regras de tipologia implementadas; falta comparação OS x matrícula e validação documental completa |
| TR 7.8 a 7.10 | Menor privilégio, MFA e rastreio de usuário | Parcial | Chaves separadas para integração e administração, identidade vinculada à chave e bloqueio de configuração insegura em produção; falta OIDC/MFA, RBAC completo e ciclo formal de concessão/revogação |
| TR 9.5(a-d), 9.6 | Quatro recusas taxativas e evidência | Implementado no escopo atual | Enums contratuais, dossiê, evidência, transações e histórico; toda nova falha precisa continuar mapeada para um dos quatro motivos |
| TR 9.5(d), Anexo V | Localização e imprecisão máxima de 50 m | Parcial | Coordenadas e precisão declarada; precisão acima de 50 m força recusa (d); falta geocodificador CNEFE/IBGE auditável |
| TR 9.7, 11.1 e 11.2 / RF-004 | Resposta completa em até 5 minutos | Não implementado ponta a ponta | Falta worker assíncrono, deadline persistido, timeout/cancelamento, métricas de percentil e teste de carga |
| TR 17.3 | Entrega digital via API | Parcial | API REST disponível; falta adaptador para o contrato/payload e sandbox oficiais da CAIXA |
| TR 17.4 / Anexo V | Identificação ou certificação digital | Não implementado | Instrumento, titular e fluxo de assinatura ainda dependem de decisão dos RTs/CAIXA |
| TR 19.9 | Relatório do Modelo por cidade/versão | Não implementado | O endpoint de diagnóstico não substitui relatório versionado com EDA, algoritmo, bibliotecas e hiperparâmetros |
| TR 19.10 | Fluxo Pareado | Não implementado | Depende de autorização, parâmetros e massa de testes da CAIXA |
| TR 20.4 a 20.13 | Ingestão de desvios e suspensão | Não implementado | Falta contrato de ingestão, parâmetros configuráveis, alertas, histórico de suspensões e bloqueio automático por cidade |
| TR 20.14 / RNF-004 | Versão e vigência dos modelos por todo o contrato | Parcial | A avaliação guarda a versão; falta persistência imutável dos artefatos, datasets e períodos de vigência |
| RNF-006 | Rastreabilidade | Parcial | Request ID, logs, histórico de status, versão do modelo e evidências de recusa; falta audit log imutável/WORM e identidade em todas as ações |
| Cláusula de pagamento | Fechamento mensal, município, ART/RRT | Não implementado | Falta fechamento, glosas, agrupamento fiscal, anexos e trilha de aprovação contábil |

## Regra de liberação

O modo contratual não pode ser habilitado enquanto houver qualquer um destes
bloqueios:

1. dataset real, verificável, versionado e aprovado pelo RT para a combinação
   cidade x tipologia;
2. modelo persistido, revisado, com Relatório do Modelo aceito e Fluxo Pareado
   concluído;
3. leitura de matrícula e coerência documental funcionando;
4. geocodificação auditável com precisão de até 50 m;
5. PDF/CSV no layout oficial e assinatura exigida;
6. integração oficial da CAIXA, SLA e observabilidade validados;
7. segurança, LGPD, MFA/RBAC e procedimentos operacionais aprovados;
8. faturamento, desvios, suspensão e revisão pós-emissão funcionando.

Até lá, `ALLOW_SYNTHETIC_PRICING=false` é obrigatório e a ausência de modelo
aplicável deve terminar em recusa `TR_9_5_A`.
