// Estilo ABNT (NBR 14724) da monografia.

#let abnt(corpo) = {
  set page(paper: "a4", margin: (top: 3cm, left: 3cm, bottom: 2cm, right: 2cm), header: none)
  set text(font: ("Times New Roman", "Liberation Serif"), size: 12pt, lang: "pt", region: "br")
  set par(justify: true, leading: 1em, spacing: 1em, first-line-indent: (amount: 1.25cm, all: true))
  set heading(numbering: "1.1")
  show heading: set text(size: 12pt)
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    block(above: 0pt, below: 2em, text(weight: "bold", upper(it)))
  }
  show heading.where(level: 2): it => block(above: 1.5em, below: 1em, text(weight: "regular", upper(it)))
  show heading.where(level: 3): it => block(above: 1.5em, below: 1em, text(weight: "bold", it))
  set figure.caption(position: top)
  set figure.caption(separator: [ -- ])
  show figure.caption: set text(size: 10pt)
  show table: set text(size: 10pt)
  show table: set par(justify: false, first-line-indent: 0pt, leading: 0.5em)
  set table(stroke: 0.5pt, inset: 4pt)
  show bibliography: set heading(numbering: none)
  show bibliography: set par(first-line-indent: 0pt, justify: false, leading: 0.5em, spacing: 1.2em)
  corpo
}

// Pré-textuais: título centralizado, sem número, fora do sumário.
#let titulo-pre(texto) = {
  pagebreak(weak: true)
  align(center, block(below: 2em, text(weight: "bold", upper(texto))))
}

// Parte textual: número da página no canto superior direito.
#let textual(corpo) = {
  set page(header: context align(right, text(size: 10pt, counter(page).display())))
  corpo
}

#let fonte(texto) = block(above: 0.5em, below: 1.5em, align(left, text(size: 10pt)[Fonte: #texto]))
