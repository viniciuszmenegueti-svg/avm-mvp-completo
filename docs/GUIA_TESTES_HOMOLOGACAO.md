# Guia de testes e homologação

Este guia separa três níveis diferentes de validação. Nenhum deles, isoladamente,
autoriza uso contratual ou substitui a aprovação dos Responsáveis Técnicos.

## 1. Testes automatizados do código

Execute no ambiente virtual:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest
docker compose config --quiet
```

Critérios mínimos:

- todos os testes aprovados;
- cobertura total igual ou superior a 95%;
- nenhuma falha de lint, formatação ou tipagem;
- configuração do Compose válida;
- auditoria de dependências concluída sem vulnerabilidade conhecida aplicável.

## 2. Integração demonstrativa

O ambiente de desenvolvimento permite `RULE_BASED_V1` somente quando
`ALLOW_SYNTHETIC_PRICING=true`. Essa execução valida o fluxo, não o modelo.

```powershell
docker compose up -d --build
python scripts/integration-test.py
docker compose exec -T api alembic check
```

Valide também os relatórios PDF e CSV e arquive a evidência visual do PDF.

## 3. Homologação técnica segura

Copie o exemplo sem versionar o arquivo resultante:

```powershell
Copy-Item ".env.homologation.example" ".env.homologation"
```

Substitua todos os placeholders por segredos aleatórios com pelo menos 24
caracteres. O arquivo deve manter:

```text
APP_ENV=homologation
APP_DEBUG=false
ALLOW_SYNTHETIC_PRICING=false
MODEL_EXECUTION_MODE=HOMOLOGATION_SHADOW
```

O Compose usa portas e nomes próprios, permitindo executar a homologação sem
reutilizar o banco de desenvolvimento:

```powershell
docker compose `
  --project-name avm-homologation `
  --env-file ".env.homologation" `
  up -d --build
```

Confirme migrations e execute o teste automatizado:

```powershell
docker compose `
  --project-name avm-homologation `
  --env-file ".env.homologation" `
  exec -T api alembic check

python scripts/homologation-test.py `
  --env-file ".env.homologation" `
  --base-url "http://localhost:8001"
```

O teste deve comprovar:

- `environment=homologation`;
- `execution_mode=HOMOLOGATION_SHADOW`;
- HTTP 401 sem credencial cliente ou administrativa;
- HTTP 403 com credencial inválida;
- acesso permitido com as credenciais corretas;
- criação persistente de dataset e modelo OLS candidatos, com SHA-256;
- aprovação exclusivamente técnica para homologação sombra;
- avaliação pela versão congelada do modelo, sem recalcular coeficientes;
- emissão de PDF e CSV identificados como sem validade contratual;
- bloqueio da transição para entrega com HTTP 409 e
  `SHADOW_DELIVERY_BLOCKED`;
- evidência JSON em `.audit/homologation-result.json`.

A massa criada pelo script é sintética, identificada como não contratual e serve
somente para provar o funcionamento do pipeline. Ela não pode ser reaproveitada
como amostra de mercado ou aprovação do Responsável Técnico.

Para encerrar sem apagar o banco de homologação:

```powershell
docker compose `
  --project-name avm-homologation `
  --env-file ".env.homologation" `
  down
```

Use `down -v` somente para uma instância comprovadamente descartável.

## 4. Homologação estatística

`POST /statistical-models/fit` continua sendo um diagnóstico não persistente e
sempre retorna `homologated=false`. O fluxo de sombra usa:

- `POST /statistical-models/train` para persistir dataset, matriz, diagnósticos,
  coeficientes, vigência e hashes do candidato;
- `POST /statistical-models/{id}/approve-homologation` para habilitá-lo somente
  em `HOMOLOGATION_SHADOW`;
- seleção automática da versão aprovada pela cidade, tipologia e vigência;
- bloqueio de entrega e marcação `contractual_validity=false`.

Antes de qualquer decisão contratual, são obrigatórios:

- dataset real e imutável por cidade e tipologia;
- fonte e evidência de cada observação;
- trilha de saneamento e exclusões;
- plano de variáveis aprovado;
- amostra suficiente para o grau pretendido;
- análise de resíduos, influência, heterocedasticidade e multicolinearidade;
- PRESS/LOOCV e limiar de aceitação versionado;
- sinais econômicos coerentes;
- intervalo de confiança e grau de precisão;
- reprodução de casos de referência independentes;
- parecer e assinatura do Responsável Técnico.

## 5. Homologação contratual

Mesmo após a aprovação estatística, ainda permanecem como bloqueios:

- leitura e confronto automatizado de matrícula;
- geocodificação auditável com precisão de até 50 metros;
- payload e sandbox oficiais da CAIXA;
- PDF/CSV no layout oficial e assinatura exigida;
- Fluxo Pareado;
- SLA ponta a ponta inferior a cinco minutos sob carga;
- OIDC/MFA, RBAC e gestão de segredos;
- LGPD, retenção, descarte, incidentes e auditoria imutável;
- ingestão de desvios, suspensão de modelos e revisão pós-emissão;
- fechamento mensal, ART/RRT, glosas e evidências fiscais.

## Regra de liberação

`ALLOW_SYNTHETIC_PRICING` deve permanecer `false` em homologação e produção.
`HOMOLOGATION_SHADOW` nunca autoriza entrega. O projeto não disponibiliza endpoint
para transformar um modelo sombra em `CONTRACTUAL_ACTIVE`.
Nenhum modelo pode ser ativado por cidade e tipologia sem dataset versionado,
relatório do modelo, decisão do RT e evidências contratuais correspondentes.
