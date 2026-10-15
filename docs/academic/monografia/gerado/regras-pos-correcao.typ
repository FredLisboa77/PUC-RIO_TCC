// Gerado por `python -m academico tabelas`. Nao editar a mao.
#figure(
  table(
    columns: 8,
    align: (left, right, right, right, right, right, right, right),
    table.header([*Regra*], [*VP*], [*FP*], [*FN*], [*Indet.*], [*Precisão*], [*IC 95% (Wilson)*], [*Revocação*]),
    [DAX-001], [6], [0], [0], [0], [1,00], [\[0,61; 1,00\]], [1,00],
    [MOD-001], [1], [0], [0], [1], [1,00], [\[0,21; 1,00\]], [1,00],
    [MOD-002], [0], [0], [0], [0], [—], [—], [—],
    [MOD-003], [1], [2], [0], [0], [0,33], [\[0,06; 0,79\]], [1,00],
    [MOD-005], [0], [0], [0], [7], [—], [—], [—],
    [MOD-006], [3], [0], [0], [0], [1,00], [\[0,44; 1,00\]], [1,00],
    [MOD-007], [1], [0], [0], [0], [1,00], [\[0,21; 1,00\]], [1,00],
    [PERF-001], [24], [2], [0], [5], [0,92], [\[0,76; 0,98\]], [1,00],
    [PERF-003], [16], [0], [0], [0], [1,00], [\[0,81; 1,00\]], [1,00],
    [*Total (micro)*], [52], [4], [0], [13], [0,93], [\[0,83; 0,97\]], [1,00],
  ),
  caption: [Desempenho das regras após a correção da MOD-003 e da PERF-001 (análise de erros)],
) <tab-regras-pos-correcao>
#fonte[Elaborado pelo autor a partir de `regras-2026-10-12-pos-correcao.json`.]
