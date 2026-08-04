# Matriz de prontidão para homologação AVM — 2026

Data de corte: 31/07/2026
Versão da aplicação: 0.3.1
Escopo liberado: testes técnicos controlados em `HOMOLOGATION_SHADOW`

## 1. Regra de interpretação

Esta matriz usa o Edital CR 012/2026 republicado e seus anexos como fonte
vinculante principal. As NBR 14653-1:2019 e 14653-2:2011 são as fontes
normativas para o trabalho avaliatório e a regressão linear. Os demais
documentos fornecidos foram usados como especificação, orientação, exemplo ou
evidência histórica conforme sua natureza.

Documentos marcados como externos/confidenciais não são copiados para este
repositório. Regras presentes apenas em versão histórica de manual não foram
transformadas em obrigação fixa. Parâmetros que a CAIXA ainda fornecerá — por
exemplo, massa mínima e limites de desvio — permanecem configuráveis e
bloqueados até confirmação oficial.

As classificações abaixo significam:

- **Implementado para teste**: existe código e teste automatizado, sem afirmar
  aceite externo;
- **Parcial**: existe controle útil, mas falta elemento técnico, profissional ou
  externo;
- **Dependência externa**: não pode ser concluído unilateralmente pelo software;
- **Bloqueador formal**: impede homologação CAIXA ou operação contratual.

## 2. Resultado executivo

| Marco | Decisão | Justificativa |
|---|---|---|
| Desenvolvimento local | APTO | suíte automatizada, análise estática e fluxo demonstrativo |
| Homologação técnica interna controlada | APTO COM RESSALVAS | modo sombra, dados não contratuais, rastreabilidade e entregas bloqueadas |
| Apresentação como candidato à integração CAIXA | CONDICIONAL | exige fechar matrícula/IA, segurança corporativa, RTs e documentação do modelo real |
| Fluxo Pareado oficial | NÃO INICIADO | depende de convocação, massa, parâmetros e autorização CAIXA |
| Homologação formal | NÃO APROVADO | nenhum teste interno substitui o aceite da CAIXA |
| Produção contratual | BLOQUEADA NO CÓDIGO | `CONTRACTUAL` não possui chave local de liberação |

## 3. Obrigações do edital e estado verificável

| ID | Obrigação | Referência documental | Estado | Evidência/pendência |
|---|---|---|---|---|
| AVM-01 | Receber OS por integração | Edital pp. 28–30; RF-001 | Parcial | API/OpenAPI e autenticação existem; falta contrato e sandbox oficiais |
| AVM-02 | Preservar identificador externo | Edital pp. 29–30 | Implementado para teste | texto de até 100 caracteres, unicidade e idempotência |
| AVM-03 | Receber dados cadastrais e matrícula | Edital p. 28; RF-001 | Parcial | imóvel/endereço são validados; ingestão segura da matrícula ainda falta |
| AVM-04 | Leitura automatizada de matrícula por IA | Edital pp. 28 e 53; RF-002 | Bloqueador formal | faltam upload, classificação, extração por campo, confiança, páginas e revisão |
| AVM-05 | Conferir consistência e veracidade | Edital pp. 28 e 30; RF-003 | Parcial | cidade/UF/IBGE, tipologia, áreas e geocodificação; falta confronto OS × matrícula |
| AVM-06 | Não presumir localização pelo endereço | Edital p. 30 | Implementado para teste | endereço CNEFE é sugestão; precisão permanece declarada/comprovada pelo processo |
| AVM-07 | Latitude/longitude com imprecisão máxima de 50 m | Edital p. 53 | Parcial | auditoria CNEFE vinculada por FK e evidência; protocolo métrico/RT por cidade falta |
| AVM-08 | Recusar em até cinco minutos | Edital p. 30 | Implementado para teste | deadline/resposta persistidos, timeout e testes; callback oficial ainda depende da CAIXA |
| AVM-09 | Cancelar demanda sem resposta no limite | Edital p. 30; RF-004 | Parcial | decisão fail-closed local; falta protocolo oficial e execução distribuída |
| AVM-10 | Concorrência e filas simultâneas | Edital pp. 30–31; RNF-007 | Parcial | locks/índices/idempotência e testes locais; falta ensaio de carga no ambiente-alvo |
| AVM-11 | Usar somente modelo autorizado por cidade/tipologia/vigência | Edital pp. 34–36 | Implementado para teste | fail-closed e modelo sombra; autorização contratual permanece externa |
| AVM-12 | Critérios, premissas e procedimentos verificáveis | Edital p. 24 | Parcial | matriz, semântica, coeficientes, diagnósticos, domínio e hashes persistidos; RT falta |
| AVM-13 | Versionar modelo durante todo o contrato | Edital p. 36 | Parcial | versão/vigência/hash imutável na base; retenção WORM externa ainda falta |
| AVM-14 | Relatório do Modelo por cidade/região | Edital p. 34 | Parcial | endpoint gera minuta com EDA, diagnósticos, gráficos e hashes; falta peça assinada/aceita |
| AVM-15 | Novo relatório a cada atualização | Edital p. 34 | Parcial | cada versão possui ID/hash próprios; falta workflow documental assinado |
| AVM-16 | Validação estatística e mercadológica | Edital pp. 34–36; NBR 14653-2 | Parcial | OLS, F, t, PRESS/LOOCV, IC80, VIF, normalidade, heterocedasticidade e influência; faltam parecer RT, validação real e espacial quando aplicável |
| AVM-17 | Delimitar mercado, localização e tipologia | Edital pp. 34–36 | Parcial | chave cidade × tipologia e bloqueio de domínio; segmentação real depende da amostra |
| AVM-18 | Resultado equivalente em API, PDF e CSV | Edital p. 24; RF-006 | Implementado para teste | rotas testadas, cabeçalhos/hash e CSV neutralizado; layout oficial ainda não recebido |
| AVM-19 | Informar valor, características e responsáveis | Edital p. 24 | Parcial | valor/atributos/modelo presentes; RTs/registro/assinatura continuam ausentes |
| AVM-20 | Preservar auditoria | Edital p. 47 | Parcial | request ID, ator, status, recusa, CNEFE e hashes; falta armazenamento WORM corporativo |
| AVM-21 | PDF técnico legível e preservável | Edital pp. 24 e 53 | Parcial | PDF válido e QA visual; PDF/A depende de confirmação do fluxo definitivo |
| AVM-22 | Identificação e assinatura digital | Edital pp. 23, 33 e 53 | Bloqueador formal | não é permitido simular assinatura profissional |
| AVM-23 | Preservar peça assinada | referência de fluxo digital fornecida | Dependência externa | requer provedor de assinatura e cofre documental homologados |
| AVM-24 | Disponibilizar artefatos históricos | Edital pp. 34 e 36 | Parcial | exportação, hashes, backup/restauração; retenção contratual deve ser aprovada |

## 4. Recusas e decisão segura

Os quatro motivos taxativos do item 9.5 do Termo de Referência permanecem a
taxonomia externa. Códigos internos mais específicos são guardados como
condição/evidência e mapeados para um desses motivos, sem inventar uma quinta
categoria contratual.

| Condição interna | Destino contratual | Controle |
|---|---|---|
| modelo ausente, suspenso, incompatível ou fora do domínio | 9.5(a) | recusa, modelo consultado, versão e causa |
| dados/documentos incoerentes ou insuficientes | 9.5(b) | campos comparados, regra e evidência |
| conflito ou impedimento | 9.5(c) | declaração, tipo, responsável e dossiê |
| localização não confirmada ou acima de 50 m | 9.5(d) | endereço, fonte, audit ID, coordenadas e precisão |
| prazo excedido | cancelamento/recusa conforme protocolo oficial | deadline, elapsed time, ator e request ID |

Toda decisão deve ser terminal, idempotente e reproduzível. O dossiê conserva
entrada analisada, regra, evidência, processo decisor, timestamps e request ID.

## 5. Controles estatísticos

O sistema calcula separadamente:

1. item de quantidade de dados `N/(k+1)`;
2. significância bilateral de cada regressor;
3. significância global do modelo pelo teste F;
4. precisão da estimativa individual pelo IC de 80%;
5. diagnósticos de generalização, resíduos, multicolinearidade e influência.

O mínimo dos três primeiros itens é chamado apenas de **gate automático de
fundamentação**. Ele não é o grau global da NBR. A precisão não é misturada com
a fundamentação. A pontuação integral, a coerência, a elasticidade, o conteúdo
do laudo e o parecer do RT continuam necessários.

Na inferência, o sistema:

- recalcula o IC80 e a precisão para cada imóvel;
- recusa amplitude superior a 50%;
- bloqueia qualquer variável fora do mínimo/máximo observado;
- recomputa os hashes do dataset, da matriz e do artefato;
- aceita somente `usable_market_value_brl`, unidade BRL e transformação `NONE`
  nesta versão;
- exige variáveis disponíveis e compatíveis com a tipologia.

## 6. Geocodificação

Uma importação CNEFE passa por `LOADING`, `ACTIVE` ou `FAILED`. Apenas a versão
ativa mais recente de cada município participa da consulta. Falha após lote
parcial não torna os registros visíveis.

Quando o método é `CNEFE_IBGE`, a ordem só é criada se o servidor confirmar:

- auditoria existente e resultado `MATCHED`;
- mesmo ator de integração;
- dataset ainda ativo;
- endereço normalizado idêntico;
- coordenadas idênticas ao registro selecionado;
- referência explícita ao audit ID.

O CNEFE não informa automaticamente erro métrico individual. Por isso o
resultado não presume atendimento a 50 m: evidência de precisão e responsável
continuam obrigatórios.

## 7. Segurança e operação

Implementado no escopo local:

- credenciais distintas para cliente, treinador e revisor;
- rejeição de placeholders, segredos duplicados e senha PostgreSQL fraca;
- segregação entre treino e revisão do modelo;
- configuração contratual bloqueada;
- cabeçalhos CSP, frame, MIME, referrer, permissions e HSTS somente em HTTPS;
- neutralização de fórmulas no CSV;
- vínculo de ator/request ID nas mutações de OS;
- backup, validação e restauração ensaiados.

Ainda obrigatórios antes da homologação formal:

- OIDC/MFA, RBAC por papel/escopo e ciclo de revogação;
- TLS e cofre de segredos no ambiente-alvo;
- criptografia/retenção, resposta a incidentes e governança LGPD;
- auditoria append-only/WORM externa;
- observabilidade, alertas e ensaio de carga no ambiente contratado.

## 8. Dependências que nenhum código local pode declarar concluídas

- três Responsáveis Técnicos, vínculos, diplomas e CREA/CAU válidos;
- ART/RRT e assinatura eletrônica aplicável;
- dataset real, plano de variáveis e parecer mercadológico aprovados;
- dez cidades/regiões inicialmente escolhidas e autorizadas;
- contrato/payload/sandbox oficiais da API CAIXA;
- Relatório do Modelo definitivo de cada localidade;
- quantidade mínima e limites de desempenho fornecidos pela CAIXA;
- Fluxo Pareado de 30 dias por localidade, sem remuneração;
- autorização expressa da CAIXA;
- ingestão oficial de desvios, suspensão e reincidência;
- revisão pós-emissão, medição, glosas, faturamento e ART/RRT mensal.

## 9. Critério de saída desta fase

O pacote pode ser entregue para **testes técnicos internos** quando todos os
comandos abaixo passarem no mesmo commit e a evidência for arquivada:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pip check
alembic check
python scripts/homologation-test.py --env-file .env.homologation --base-url http://localhost:8001
```

Mesmo com resultado verde, o status formal permanece **não homologado** até que
as dependências externas da seção 8 sejam comprovadas.
