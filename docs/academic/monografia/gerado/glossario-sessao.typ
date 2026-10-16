// Gerado por `python -m academico tabelas`. Nao editar a mao.
#import "../abnt.typ": fonte
#figure(
  table(
    columns: 6,
    align: (left, right, right, right, right, right),
    table.header([*Item*], [*Concordância*], [*Kappa*], [*Original reanotada*], [*Com glossário*], [*p (McNemar)*]),
    [Pertinente], [1,00], [—], [20 \/ 20], [20 \/ 20], [1,000],
    [Fiel], [0,70], [0,43], [15 \/ 20], [14 \/ 20], [1,000],
    [Recomendação correta], [0,75], [0,43], [13 \/ 20], [11 \/ 20], [0,727],
    [*Utilizável como está*], [0,65], [0,30], [10 \/ 20], [8 \/ 20], [0,727],
  ),
  caption: [Os 20 achados reanotados: consistência do anotador entre 14\/10 e a nova sessão, e comparação das duas versões só com vereditos da nova sessão (análise exploratória, fora do protocolo)],
) <tab-glossario-sessao>
#fonte[Elaborado pelo autor a partir de `glossario-2026-10-15.json`.]
