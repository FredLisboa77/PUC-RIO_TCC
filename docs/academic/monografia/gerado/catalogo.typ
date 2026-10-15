// Gerado por `python -m academico tabelas`. Nao editar a mao.
#import "../abnt.typ": fonte
#figure(
  table(
    columns: 5,
    align: (left, left, left, left, left),
    table.header([*ID*], [*Regra*], [*Categoria*], [*Severidade*], [*Âncora*]),
    [DAX-001], [Divisão com o operador onde o denominador pode ser zero], [DAX], [média], [#link("https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator")[https:\/\/learn.microsoft.com\/en-us\/dax\/best-practices\/dax-divide-function-operator]],
    [MOD-001], [Tempo automático de data\/hora está ligado], [modelagem], [alta], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/auto-date-time]],
    [MOD-002], [Relacionamento com filtro bidirecional], [modelagem], [alta], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/relationships-bidirectional-filtering]],
    [MOD-003], [Tabela sem relacionamento com o resto do modelo], [modelagem], [baixa], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/star-schema")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/star-schema]],
    [MOD-005], [Dimensão de data não está marcada como tabela de data], [modelagem], [média], [#link("https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-date-tables")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/transform-model\/desktop-date-tables]],
    [MOD-006], [Dimensão em floco de neve], [modelagem], [baixa], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/star-schema")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/star-schema]],
    [MOD-007], [Relacionamento um-para-um], [modelagem], [média], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/relationships-one-to-one")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/relationships-one-to-one]],
    [PERF-001], [Coluna calculada em DAX], [desempenho], [média], [#link("https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/guidance\/import-modeling-data-reduction]],
    [PERF-003], [Coluna de ponto flutuante somada], [desempenho], [baixa], [#link("https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-data-types")[https:\/\/learn.microsoft.com\/en-us\/power-bi\/transform-model\/desktop-data-types]],
  ),
  caption: [Catálogo das regras e a página do Microsoft Learn que ancora cada uma],
) <tab-catalogo>
#fonte[Elaborado pelo autor a partir de `core/rules/todas.py`.]
