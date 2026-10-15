// Gerado por `python -m academico tabelas`. Nao editar a mao.
#import "../abnt.typ": fonte
#figure(
  table(
    columns: 4,
    align: (left, right, right, right),
    table.header([*Item*], [*Sim / n*], [*Proporção*], [*IC 95% (Wilson)*]),
    [Pertinente], [61 / 61], [1,00], [\[0,94; 1,00\]],
    [Fiel], [32 / 61], [0,52], [\[0,40; 0,64\]],
    [Recomendação correta], [47 / 61], [0,77], [\[0,65; 0,86\]],
    [*Utilizável como está*], [23 / 61], [0,38], [\[0,27; 0,50\]],
  ),
  caption: [Rubrica humana das explicações geradas: proporção de "sim" por item],
) <tab-geracao>
#fonte[Elaborado pelo autor a partir de `geracao-2026-10-14.json`.]
