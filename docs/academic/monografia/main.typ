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

// RESUMO-E-ABSTRACT (Task 10)

#titulo-pre[Lista de tabelas]
#outline(title: none, target: figure.where(kind: table))

#titulo-pre[Lista de figuras]
#outline(title: none, target: figure.where(kind: image))

#titulo-pre[Sumário]
#outline(title: none, depth: 3, indent: auto)

#show: textual
#context [#metadata(here().page()) <inicio-textual>]

// CAPÍTULOS (cada task de capítulo acrescenta sua linha de #include aqui, na ordem 1 a 6)
#include "capitulos/03-metodo.typ"

#context [#metadata(here().page()) <fim-textual>]

#bibliography("referencias.bib", title: [Referências], style: "abnt.csl")
// APÊNDICES (Task 9)
