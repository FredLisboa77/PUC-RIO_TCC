// Gerado por `python -m academico tabelas`. Nao editar a mao.
#import "../abnt.typ": fonte
#figure(
  table(
    columns: 9,
    align: (left, right, right, right, right, right, right, right, right),
    table.header([*Regra*], [*VP*], [*FP*], [*FN*], [*Ind. M*], [*Ind. NM*], [*Precisão (piso–teto)*], [*IC 95% (Wilson)*], [*Revocação (piso–teto)*]),
    [DAX-001], [6], [0], [0], [0], [0], [1,00], [\[0,61; 1,00\]], [1,00],
    [MOD-001], [1], [0], [0], [0], [1], [1,00], [\[0,21; 1,00\]], [1,00 (0,50–1,00)],
    [MOD-002], [0], [0], [0], [0], [0], [—], [—], [—],
    [MOD-003], [1], [6], [0], [0], [0], [0,14], [\[0,03; 0,51\]], [1,00],
    [MOD-005], [0], [0], [0], [0], [0], [—], [—], [—],
    [MOD-006], [3], [0], [0], [0], [0], [1,00], [\[0,44; 1,00\]], [1,00],
    [MOD-007], [1], [0], [0], [0], [0], [1,00], [\[0,21; 1,00\]], [1,00],
    [PERF-001], [18], [0], [6], [1], [4], [1,00 (0,95–1,00)], [\[0,82; 1,00\]], [0,75 (0,64–0,76)],
    [PERF-003], [16], [0], [0], [0], [0], [1,00], [\[0,81; 1,00\]], [1,00],
    [*Total (micro)*], [46], [6], [6], [1], [5], [0,88 (0,87–0,89)], [\[0,77; 0,95\]], [0,88 (0,81–0,89)],
  ),
  caption: [Desempenho das regras contra o gabarito em P1–P7 (resultado oficial, regras da tag regras-gt)],
) <tab-regras>
#fonte[Elaborado pelo autor a partir de `regras-2026-10-15.json`.]
