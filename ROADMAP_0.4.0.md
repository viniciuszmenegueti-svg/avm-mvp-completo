Roadmap AVM Imóveis API v0.4.0



Objetivo da versão



Preparar o AVM para trabalhar com dados imobiliários reais, versionados e auditáveis, substituindo gradualmente a dependência de preços-base demonstrativos por uma camada estruturada de dados de mercado.



A versão 0.4.0 não terá como objetivo declarar aderência completa à NBR 14.653-2 nem disponibilizar um modelo estatístico para produção contratual. O foco será construir a base de dados, governança, validação e rastreabilidade necessária para uma evolução estatística posterior.



Escopo planejado



1\. Cadastro de fontes de dados



entidade de fonte de dados;



nome, tipo, responsável e descrição;



situação ativa ou inativa;



data de referência e metadados de rastreabilidade;



endpoints administrativos protegidos.



2\. Versionamento de datasets



vínculo obrigatório com uma fonte;



identificador de versão;



período de referência;



cidade, UF e tipologia abrangidas;



estados DRAFT, ACTIVE, DEPRECATED e REJECTED;



quantidade de registros;



identificador de integridade;



apenas um dataset ativo por recorte aplicável.



3\. Registro de dados de mercado



fonte e dataset;



tipologia, cidade, UF e código IBGE;



endereço normalizado;



áreas e características do imóvel;



valor observado e data da observação;



natureza do valor, como oferta ou transação;



latitude e longitude opcionais;



indicador de qualidade;



prevenção de duplicidades.



4\. Importação controlada por CSV



validação de cabeçalho e tipos;



processamento transacional;



relatório de registros aceitos e rejeitados;



erros por linha;



prevenção de duplicidades;



limite configurável de tamanho;



associação obrigatória a dataset DRAFT.



5\. Qualidade dos dados



coerência entre cidade, UF e código IBGE;



valores e áreas positivos;



campos obrigatórios;



valores extremos por regras configuráveis;



métricas de completude, duplicidade e consistência;



bloqueio de ativação em falhas críticas.



6\. Aplicabilidade do dataset



seleção por cidade, UF, código IBGE e tipologia;



quantidade mínima configurável de registros;



persistência da versão selecionada;



recusa TR\_9\_5\_A quando não houver dataset aplicável;



ausência de fallback silencioso.



7\. Observabilidade e administração



fontes e datasets por situação;



registros por cidade e tipologia;



últimas importações;



falhas de validação;



métricas administrativas;



logs estruturados.



8\. Documentação e qualidade



documentação dos novos endpoints;



exemplo de CSV;



ciclo de vida do dataset;



atualização do README e dos documentos de conformidade;



testes de integração;



cobertura mínima de 95%;



CI aprovado.



Fora do escopo da versão 0.4.0



aderência completa à NBR 14.653-2;



emissão de laudo técnico;



modelo estatístico homologado para crédito;



treinamento de Machine Learning em produção;



extração automática de matrícula;



assinatura ICP-Brasil;



ART/RRT;



integração oficial com a CAIXA;



aplicação web completa;



aplicativo mobile.



Ordem de implementação



fontes de dados;



datasets versionados;



dados de mercado;



importação CSV;



qualidade e ativação;



seleção de dataset;



integração com avaliação e recusa;



observabilidade;



documentação final.



Meta da versão



Entregar uma camada de dados imobiliários reais, versionados, auditáveis e selecionáveis por cidade e tipologia, criando a base técnica necessária para futuros modelos estatísticos sem fabricar valores nem ocultar ausência de dados.

