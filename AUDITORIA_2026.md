# Auditoria técnica de 29/07/2026

Foram adicionados:

- motor OLS determinístico com significância, IC80, PRESS/LOOCV, graus
  objetivos e gates de coerência econômica;
- endpoint administrativo `POST /statistical-models/fit`, que nunca declara
  homologação automática;
- exportação de cada avaliação por
  `GET /orders/{id}/valuation/report.pdf` e `report.csv`;
- coordenadas com precisão declarada e gate contratual de 50 m;
- autenticação separada de integração e bloqueio de configuração insegura em
  produção;
- matriz de conformidade, protocolo estatístico e checklist de go-live em
  `docs/`.

Este repositório permanece uma base técnica segura, não um sistema já
homologado. Consulte `docs/CONFORMIDADE_EDITAL.md` antes de qualquer uso
contratual. A ausência de dataset/modelo real aplicável continua provocando
recusa `TR_9_5_A`; o sistema não fabrica valor.
