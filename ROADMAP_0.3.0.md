# Roadmap AVM Imoveis API v0.3.0

## Objetivo da versão

Evoluir a plataforma AVM de uma API técnica validada para um MVP operacional de avaliação imobiliária, fortalecendo dados, explicabilidade, rastreabilidade e preparação para evolução futura dos modelos.

## Princípios da versão

A evolução deve preservar:

- Separação entre API, serviços, repositórios e engine AVM
- Versionamento dos modelos de avaliação
- Rastreabilidade completa das avaliações realizadas
- Migrations controladas e versionadas
- Testes automatizados como requisito obrigatório

## Escopo planejado

### 1. Dados imobiliários

Objetivo:
Criar uma estrutura preparada para receber dados reais de mercado.

Itens:

- Cadastro de fontes de dados imobiliários
- Estrutura para histórico de imóveis avaliados
- Preparação para integração com dados externos
- Normalização de atributos dos imóveis
- Expansão dos fatores utilizados no cálculo AVM

Critério de aceite:

- Modelo de dados definido
- Migrações versionadas
- Testes automatizados

---

### 2. Evolução do motor AVM

Objetivo:
Evoluir o motor baseado em regras para um modelo mais explicável e preparado para futuras abordagens estatísticas ou Machine Learning.

Itens:

- Estrutura de fatores de ajuste
- Peso por características do imóvel
- Ajuste por localização
- Ajuste por área
- Ajuste por quantidade de quartos e vagas
- Registro dos fatores utilizados na avaliação
- Preparação para futuros modelos preditivos

Critério de aceite:

- Avaliação retorna composição do cálculo
- Fatores utilizados ficam persistidos
- Resultado é reproduzível

---

### 3. Confiança da avaliação

Objetivo:
Criar uma camada de explicabilidade do resultado.

Itens:

- Índice de confiança revisado
- Motivos que aumentam ou reduzem confiança
- Registro dos indicadores utilizados

Critério de aceite:

- API retorna nível de confiança
- Explicação disponível junto da avaliação

---

### 4. Administração e operação

Objetivo:
Melhorar gerenciamento e observabilidade da plataforma.

Itens:

- Endpoint administrativo de diagnóstico
- Melhorias nos logs
- Métricas básicas da aplicação
- Monitoramento de erros

Critério de aceite:

- Informações operacionais disponíveis
- Logs padronizados

---

### 5. Qualidade

Objetivo:
Manter estabilidade durante evolução.

Itens:

- Manter cobertura acima de 95%
- Expandir testes de integração
- Revisar documentação da API
- Atualizar exemplos de uso

Critério de aceite:

- Pipeline CI aprovado
- Documentação atualizada

---

## Fora do escopo da versão 0.3.0

- Treinamento de modelos Machine Learning em produção
- Integrações comerciais com portais imobiliários
- Aplicação web completa
- Aplicativo mobile

---

## Ordem de implementação

1. Estrutura de dados imobiliários
2. Evolução do motor AVM
3. Persistência dos fatores da avaliação
4. Índice de confiança
5. Melhorias operacionais
6. Documentação final

## Meta da versão

Entregar uma arquitetura preparada para receber dados reais, aumentar a explicabilidade das avaliações e criar uma base sólida para evolução futura do AVM baseado em dados.
