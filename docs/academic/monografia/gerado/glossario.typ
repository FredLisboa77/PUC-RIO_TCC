// Gerado por `python -m academico tabelas`. Nao editar a mao.
#import "../abnt.typ": fonte
#figure(
  table(
    columns: 6,
    align: (left, right, right, right, right, right),
    table.header([*Item*], [*Original*], [*Com glossário*], [*Só original*], [*Só glossário*], [*p (McNemar)*]),
    [Pertinente], [61 \/ 61 (1,00)], [61 \/ 61 (1,00)], [0], [0], [1,000],
    [Fiel], [32 \/ 61 (0,52)], [51 \/ 61 (0,84)], [2], [21], [\<0,001],
    [Recomendação correta], [47 \/ 61 (0,77)], [37 \/ 61 (0,61)], [18], [8], [0,076],
    [*Utilizável como está*], [23 \/ 61 (0,38)], [32 \/ 61 (0,52)], [4], [13], [0,049],
  ),
  caption: [Glossário na instrução, comparação pareada nos 61 achados (análise de erros): vereditos de 14\/10 para as explicações originais e da nova sessão para as com glossário],
) <tab-glossario>
#fonte[Elaborado pelo autor a partir de `glossario-2026-10-15.json`.]
