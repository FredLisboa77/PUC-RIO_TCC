#import "abnt.typ": abnt, titulo-pre, textual, fonte
#show: abnt

// Capa (não contada)
#page[
  #set par(first-line-indent: 0pt)
  #align(center)[
    PONTIFÍCIA UNIVERSIDADE CATÓLICA DO RIO DE JANEIRO \
    Pós-Graduação _Inteligência Artificial Generativa & Large Language Models_
    #v(1fr)
    CARLOS FREDERICO COELHO LISBOA
    #v(1fr)
    *AUDITORIA DE PROJETOS POWER BI*
    #v(2fr)
    Rio de Janeiro \
    2026
  ]
]

// Folha de rosto (primeira página contada)
#page[
  #counter(page).update(1)
  #set par(first-line-indent: 0pt)
  #align(center)[
    CARLOS FREDERICO COELHO LISBOA
    #v(1fr)
    *AUDITORIA DE PROJETOS POWER BI*
    #v(1fr)
  ]
  #align(right, block(width: 8cm, {
    set par(justify: true, leading: 0.5em)
    set text(size: 10pt)
    align(left)[
      Trabalho apresentado ao curso GenAI e LLM MASTER da Pontifícia Universidade Católica do Rio de Janeiro como pré-requisito para conclusão de curso e obtenção de crédito na disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão".

      Orientadora: Evelyn C. S. Batista
    ]
  }))
  #v(2fr)
  #align(center)[Rio de Janeiro \ 2026]
]

#include "capitulos/resumo.typ"

#titulo-pre[Lista de tabelas]
#outline(title: none, target: figure.where(kind: table))

#titulo-pre[Lista de figuras]
#outline(title: none, target: figure.where(kind: image))

#titulo-pre[Lista de abreviaturas e siglas]
#block({
  set par(first-line-indent: 0pt, justify: false)
  grid(columns: (2.2cm, 1fr), row-gutter: 0.8em,
  [ABNT], [Associação Brasileira de Normas Técnicas],
  [ADR], [_Architecture Decision Record_ (registro de decisão de arquitetura)],
  [BM25], [_Best Matching 25_, função de pontuação da busca lexical],
  [BPA], [_Best Practice Analyzer_ (Tabular Editor)],
  [CPU], [_Central Processing Unit_ (processador central)],
  [DAX], [_Data Analysis Expressions_],
  [FN], [Falso negativo],
  [FP], [Falso positivo],
  [GPU], [_Graphics Processing Unit_ (placa de vídeo)],
  [HTML], [_HyperText Markup Language_],
  [IC], [Intervalo de confiança],
  [IEEE], [_Institute of Electrical and Electronics Engineers_],
  [JSON], [_JavaScript Object Notation_],
  [LLM], [_Large Language Model_ (modelo de linguagem de grande porte)],
  [M], [Linguagem de fórmulas do Power Query],
  [MIT], [Licença de código aberto do _Massachusetts Institute of Technology_],
  [MRR], [_Mean Reciprocal Rank_ (média do inverso da posição)],
  [PBIP], [_Power BI Project_],
  [PBIR], [_Power BI Enhanced Report Format_],
  [PBIX], [Arquivo binário de relatório do Power BI Desktop],
  [PDF], [_Portable Document Format_],
  [RAG], [_Retrieval-Augmented Generation_ (geração aumentada por recuperação)],
  [TMDL], [_Tabular Model Definition Language_],
  [TMSL], [_Tabular Model Scripting Language_],
  [VN], [Verdadeiro negativo],
  [VP], [Verdadeiro positivo],
  )
})

#titulo-pre[Sumário]
#outline(title: none, depth: 3, indent: auto)

#show: textual
#context [#metadata(here().page()) <inicio-textual>]

// Parte textual: capítulos 1 a 6
#include "capitulos/01-introducao.typ"
#include "capitulos/02-fundamentacao.typ"
#include "capitulos/03-metodo.typ"
#include "capitulos/04-avaliacao.typ"
#include "capitulos/05-discussao.typ"
#include "capitulos/06-conclusao.typ"

#context [#metadata(here().page()) <fim-textual>]

#bibliography("referencias.bib", title: [Referências], style: "abnt.csl")
#include "capitulos/apendices.typ"
