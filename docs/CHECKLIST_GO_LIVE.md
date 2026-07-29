# Checklist de go-live

Nenhum item deve ser presumido. Cada marcação exige evidência arquivada.

## Dados e modelo

- [ ] dataset real e versionado por cidade x tipologia;
- [ ] fonte verificável e saneamento auditável;
- [ ] amostra suficiente para o grau pretendido;
- [ ] goldens aprovados pelos RTs;
- [ ] Relatório do Modelo entregue;
- [ ] Fluxo Pareado aprovado;
- [ ] versão/vigência ativada somente para a localidade autorizada.

## Pipeline contratual

- [ ] payload e autenticação do sandbox CAIXA validados;
- [ ] matrícula classificada e extraída por campo, com confiança;
- [ ] comparação OS x matrícula;
- [ ] geocodificação CNEFE/IBGE com precisão declarada de até 50 m;
- [ ] PDF e CSV no layout oficial;
- [ ] assinatura/identificação do RT validada;
- [ ] todas as falhas mapeadas para recusa (a), (b), (c) ou (d);
- [ ] prazo ponta a ponta abaixo de 5 minutos sob carga e falhas.

## Segurança e operação

- [ ] PostgreSQL gerenciado, backups e restauração testados;
- [ ] segredos em cofre, rotação e revogação;
- [ ] OIDC/MFA e menor privilégio;
- [ ] logs sem dados pessoais e auditoria imutável;
- [ ] criptografia em trânsito e repouso;
- [ ] política LGPD, retenção, descarte e incidentes;
- [ ] monitoramento, alertas, plantão e runbooks;
- [ ] fechamento mensal, município, ART/RRT e glosas;
- [ ] ingestão de desvios e suspensão por cidade;
- [ ] revisão pós-emissão e versionamento da peça.
