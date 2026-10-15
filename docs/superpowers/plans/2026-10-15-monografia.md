# Monografia e README de entrega — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produzir a monografia do TCC em PDF nas normas ABNT, composta em Typst a partir de fontes versionadas, com toda tabela de resultado gerada dos JSON de `eval/results`, e reescrever o `README.md` no modelo de entrega da PUC-Rio.

**Architecture:** um pacote Python `academico/` com três responsabilidades isoladas — compilar e medir o documento (`compilacao.py`), gerar as tabelas `.typ` e os blocos do README a partir dos resultados (`tabelas.py`) e conferir citações contra o `.bib` (`citacoes.py`) — e uma CLI `python -m academico tabelas|pdf|paginas`. O texto fica em `docs/academic/monografia/` (`main.typ`, `abnt.typ`, um arquivo por capítulo). Os capítulos são redigidos pelo Claude e aprovados pelo Fred um a um.

**Tech Stack:** Python 3.11, pacote `typst==0.15.0` do pip (compilador embutido), pytest, estilo bibliográfico ABNT embutido no Typst.

**Spec:** `docs/superpowers/specs/2026-10-15-monografia-design.md`

## Global Constraints

- Tudo em português: texto, nomes de função, de teste, mensagens de commit.
- Título: "Auditoria de projetos Power BI". Autor: Carlos Frederico Coelho Lisboa. Orientadora: Evelyn C. S. Batista (sem link de GitHub). Matrícula: 251.100.867. Repositório: https://github.com/FredLisboa77/PUC-RIO_TCC
- Curso: Pós-Graduação *Inteligência Artificial Generativa & Large Language Models* (GenAI e LLM MASTER), PUC-Rio; disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão".
- ABNT: A4; margens 3 cm superior e esquerda, 2 cm inferior e direita; fonte 12 pt (10 pt em tabelas, legendas e notas); espaçamento 1,5; recuo de primeira linha 1,25 cm; páginas contadas a partir da folha de rosto e numeradas (canto superior direito) a partir da Introdução; legenda de tabela acima, "Fonte:" abaixo.
- Extensão: 30 a 50 páginas textuais (Introdução até o fim da Conclusão); alvo 42. Orçamento: cap. 1 = 4, cap. 2 = 8, cap. 3 = 11, cap. 4 = 12, cap. 5 = 5, cap. 6 = 2.
- Fonte única dos números de resultado: `eval/results/consolidado-2026-10-14.json`. Tabela de resultado só entra pelos arquivos de `docs/academic/monografia/gerado/`, nunca digitada. Número no texto corrido é conferido contra o JSON antes do commit.
- Referência só entra no `.bib` depois de aberta e conferida na fonte (autor, ano, título, local). Inverificável não entra, e o Fred é avisado.
- Decisões já tomadas não são reabertas: um anotador só, P9 não acionado, BM25 mantido, MVP sem regras de M.
- Capítulo só é dado como aprovado quando o Fred disser. Cada capítulo: commit + push na `fase5-monografia`.
- Saídas de console da CLI só em ASCII (o console do Windows deste projeto não garante UTF-8; ver `_ascii` em `avaliacao_geracao/__main__.py`).
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Arquivo gerado editado à mão ou desatualizado** — se alguém mexer num `gerado/*.typ` ou o JSON mudar, a suíte tem de falhar apontando o arquivo (teste de sincronia, Task 2).
2. **Valor ausente no JSON** (`precisao.principal = null`, `wilson = null`, como em MOD-002 e MOD-005) — a tabela mostra "—", não "None" nem quebra (Task 2).
3. **Texto com caractere especial do Typst** (`*`, `_`, `#`, `@`, `<`, `$`) vindo do JSON ou do registro de regras — sai literal, não vira marcação nem referência quebrada (Task 2).
4. **Citação sem entrada no `.bib` ou entrada sem citação** — a suíte falha nomeando a chave; rótulos de tabela e de seção (`@tab-regras`, `@sec-metodo`) não contam como citação (Task 3).
5. **Erro de compilação do Typst** (arquivo incluído que não existe, sintaxe inválida) — vira `ErroDeCompilacao` com a mensagem do Typst e a CLI sai com código 1, sem traceback (Task 1).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | + `typst==0.15.0` |
| `academico/__init__.py` | docstring do pacote |
| `academico/compilacao.py` | caminhos, `compilar`, `paginas_textuais`, `ErroDeCompilacao` |
| `academico/tabelas.py` | formatação pt-BR, escape Typst, uma função por tabela, `gerar_todas`, `escrever`, blocos Markdown do README |
| `academico/citacoes.py` | extrai citações e chaves do `.bib`, `verificar` |
| `academico/__main__.py` | CLI `tabelas`, `pdf`, `paginas` |
| `docs/academic/monografia/abnt.typ` | regras de estilo ABNT e funções `abnt`, `textual`, `fonte` |
| `docs/academic/monografia/main.typ` | capa, folha de rosto, resumo/abstract, listas, sumário, inclusões, marcadores de página |
| `docs/academic/monografia/capitulos/*.typ` | um arquivo por capítulo + `apendices.typ` + `resumo.typ` |
| `docs/academic/monografia/gerado/*.typ` | tabelas geradas — não editar |
| `docs/academic/monografia/referencias.bib` | referências conferidas |
| `docs/academic/monografia.pdf` | PDF versionado |
| `docs/project/ambiente.md` | conteúdo técnico que sai do README |
| `README.md` | modelo da PUC-Rio |
| `tests/test_academico_compilacao.py`, `tests/test_academico_tabelas.py`, `tests/test_academico_citacoes.py` | testes |

---

### Task 1: Typst, estilo ABNT, pré-textuais e compilação

**Files:**
- Modify: `requirements.txt`
- Create: `academico/__init__.py`, `academico/compilacao.py`, `academico/__main__.py`
- Create: `docs/academic/monografia/abnt.typ`, `docs/academic/monografia/main.typ`
- Delete: `docs/academic/.gitkeep`
- Test: `tests/test_academico_compilacao.py`

**Interfaces:**
- Produces: `academico.compilacao.RAIZ_REPO: Path`, `PASTA_MONOGRAFIA: Path`, `PRINCIPAL: Path`, `PDF: Path`, `class ErroDeCompilacao(Exception)`, `compilar(principal: Path = PRINCIPAL) -> bytes`, `paginas_textuais(principal: Path = PRINCIPAL) -> int`; `academico.__main__.main(argv: list[str] | None = None) -> int` com subcomando `pdf` e `paginas`. Em `main.typ`: rótulos `<inicio-textual>` e `<fim-textual>`; `abnt.typ` exporta `abnt`, `textual`, `fonte`.

- [ ] **Step 1: Instalar o Typst e conferir o compilador e o estilo ABNT**

Acrescentar ao fim de `requirements.txt`:

```
# Fase 5 - monografia (compilador Typst embutido na roda)
typst==0.15.0
```

Run: `.\.venv\Scripts\python.exe -m pip install typst==0.15.0`
Expected: `Successfully installed typst-0.15.0`. Se falhar por TLS, conferir `.venv/pip.ini` (já aponta o certificado do Norton) e repetir; se continuar falhando, parar e avisar o Fred (risco da spec, seção 7).

Conferir o estilo bibliográfico ABNT embutido, num arquivo do scratchpad:

```typst
#set text(lang: "pt", region: "br")
Teste @x.
#bibliography(bytes("@article{x, author={Sadowski, Caitlin}, title={T}, journal={J}, year={2018}}"), style: "associacao-brasileira-de-normas-tecnicas")
```

Run: `.\.venv\Scripts\python.exe -c "import typst,sys; open(sys.argv[2],'wb').write(typst.compile(sys.argv[1])); print('ok')" <scratchpad>\abnt-teste.typ <scratchpad>\abnt-teste.pdf`
Expected: `ok`, e o PDF mostra "(SADOWSKI, 2018)" e a entrada em ABNT. Se o nome do estilo não existir, o Typst lista os estilos válidos no erro: usar o de ABNT que aparecer; se nenhum aparecer, baixar o CSL "associacao-brasileira-de-normas-tecnicas.csl" do repositório oficial `citation-style-language/styles`, salvar como `docs/academic/monografia/abnt.csl` e usar `style: "abnt.csl"` daqui em diante (registrar no progress-log).

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_academico_compilacao.py`:

```python
"""Compilação da monografia pelo Typst do pip."""

from pathlib import Path

import pytest

from academico.__main__ import main
from academico.compilacao import PRINCIPAL, ErroDeCompilacao, compilar, paginas_textuais

DOC_COM_MARCADORES = """
#set page(paper: "a4")
Capa
#pagebreak()
#context [#metadata(here().page()) <inicio-textual>]
Primeira página textual
#pagebreak()
Segunda
#pagebreak()
Terceira
#context [#metadata(here().page()) <fim-textual>]
"""


def _escrever(pasta: Path, texto: str) -> Path:
    arquivo = pasta / "doc.typ"
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


def test_compilar_devolve_pdf(tmp_path):
    pdf = compilar(_escrever(tmp_path, "Olá"))
    assert pdf.startswith(b"%PDF")


def test_compilar_converte_erro_do_typst(tmp_path):
    with pytest.raises(ErroDeCompilacao, match="nao-existe.typ"):
        compilar(_escrever(tmp_path, '#include "nao-existe.typ"'))


def test_paginas_textuais_conta_do_inicio_ao_fim(tmp_path):
    assert paginas_textuais(_escrever(tmp_path, DOC_COM_MARCADORES)) == 3


def test_paginas_textuais_sem_marcador_e_erro(tmp_path):
    with pytest.raises(ErroDeCompilacao, match="inicio-textual"):
        paginas_textuais(_escrever(tmp_path, "Sem marcadores"))


def test_monografia_compila():
    assert compilar(PRINCIPAL).startswith(b"%PDF")


def test_cli_erro_de_compilacao_sai_com_1_sem_traceback(tmp_path, capsys):
    codigo = main(["pdf", "--principal", str(_escrever(tmp_path, '#include "nao-existe.typ"')), "--saida", str(tmp_path / "x.pdf")])
    assert codigo == 1
    saida = capsys.readouterr()
    assert "Traceback" not in saida.err
    assert "nao-existe.typ" in saida.err


def test_cli_pdf_grava_arquivo_e_informa_paginas(tmp_path, capsys):
    destino = tmp_path / "saida.pdf"
    codigo = main(["pdf", "--principal", str(_escrever(tmp_path, DOC_COM_MARCADORES)), "--saida", str(destino)])
    assert codigo == 0
    assert destino.read_bytes().startswith(b"%PDF")
    assert "3 paginas textuais" in capsys.readouterr().out
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_compilacao.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'academico'`.

- [ ] **Step 4: Implementar `academico/`**

`academico/__init__.py`:

```python
"""A monografia do TCC: compilação em Typst, tabelas geradas dos resultados e conferência de citações."""
```

`academico/compilacao.py`:

```python
"""Compilação da monografia com o Typst instalado pelo pip.

O Typst vem embutido na roda `typst`, sem instalação no sistema. As páginas
textuais (da Introdução ao fim da Conclusão) são medidas por dois marcadores
que `main.typ` grava com o número da página em que caem.
"""

import json
from pathlib import Path

import typst

RAIZ_REPO = Path(__file__).resolve().parent.parent
PASTA_MONOGRAFIA = RAIZ_REPO / "docs" / "academic" / "monografia"
PRINCIPAL = PASTA_MONOGRAFIA / "main.typ"
PDF = RAIZ_REPO / "docs" / "academic" / "monografia.pdf"

_ERROS_DO_TYPST = tuple({RuntimeError, getattr(typst, "TypstError", RuntimeError)})


class ErroDeCompilacao(Exception):
    """O Typst recusou o documento; a mensagem é a dele."""


def compilar(principal: Path = PRINCIPAL) -> bytes:
    """Compila `principal` e devolve o PDF."""
    try:
        return typst.compile(str(principal), root=str(principal.parent))
    except _ERROS_DO_TYPST as erro:
        raise ErroDeCompilacao(str(erro)) from erro


def _pagina_do_marcador(principal: Path, rotulo: str) -> int:
    try:
        bruto = typst.query(str(principal), f"<{rotulo}>", field="value", one=True, root=str(principal.parent))
    except _ERROS_DO_TYPST as erro:
        raise ErroDeCompilacao(f"marcador <{rotulo}>: {erro}") from erro
    return int(json.loads(bruto))


def paginas_textuais(principal: Path = PRINCIPAL) -> int:
    """Páginas da Introdução ao fim da Conclusão, contando as duas."""
    inicio = _pagina_do_marcador(principal, "inicio-textual")
    return _pagina_do_marcador(principal, "fim-textual") - inicio + 1
```

`academico/__main__.py`:

```python
"""`python -m academico tabelas|pdf|paginas`."""

import argparse
import sys
from pathlib import Path

from academico.compilacao import PDF, PRINCIPAL, ErroDeCompilacao, compilar, paginas_textuais


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pdf(principal: Path, saida: Path) -> int:
    conteudo = compilar(principal)
    saida.write_bytes(conteudo)
    print(f"{_ascii(saida.name)}: {paginas_textuais(principal)} paginas textuais")
    return 0


def _paginas(principal: Path) -> int:
    print(f"{paginas_textuais(principal)} paginas textuais (alvo 42, limite 30 a 50)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m academico")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_pdf = sub.add_parser("pdf", help="compila a monografia em PDF")
    p_pdf.add_argument("--principal", type=Path, default=PRINCIPAL)
    p_pdf.add_argument("--saida", type=Path, default=PDF)
    p_pag = sub.add_parser("paginas", help="conta as paginas textuais")
    p_pag.add_argument("--principal", type=Path, default=PRINCIPAL)
    args = parser.parse_args(argv)
    try:
        if args.comando == "pdf":
            return _pdf(args.principal, args.saida)
        return _paginas(args.principal)
    except ErroDeCompilacao as erro:
        print(_ascii(f"erro de compilacao: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Escrever o estilo e o documento principal**

`docs/academic/monografia/abnt.typ`:

```typst
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
  show figure.where(kind: table): set figure.caption(position: top)
  set figure.caption(separator: [ -- ])
  show figure.caption: set text(size: 10pt)
  show figure: set block(breakable: true)
  show table: set text(size: 10pt)
  show table: set par(justify: false, first-line-indent: 0pt, leading: 0.5em)
  set table(stroke: 0.5pt, inset: 4pt)
  show raw: set text(size: 10pt)
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
```

`docs/academic/monografia/main.typ`:

```typst
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
  #align(right, block(width: 8cm, align(left, par(justify: true, leading: 0.5em)[
    #text(size: 10pt)[Trabalho apresentado ao curso GenAI e LLM MASTER da Pontifícia Universidade Católica do Rio de Janeiro como pré-requisito para conclusão de curso e obtenção de crédito na disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão".

    Orientadora: Evelyn C. S. Batista]
  ])))
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

#context [#metadata(here().page()) <fim-textual>]

// BIBLIOGRAFIA E APÊNDICES (Tasks 4 e 9)
```

Os dois comentários em maiúsculas marcam onde as tasks seguintes inserem conteúdo; não aparecem no PDF.

Apagar `docs/academic/.gitkeep`.

- [ ] **Step 6: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_compilacao.py -q`
Expected: `7 passed`. Se `test_paginas_textuais_conta_do_inicio_ao_fim` falhar porque a consulta não acha metadado criado dentro de `context`, trocar os dois marcadores (no teste e no `main.typ`) por `#context { let p = here().page(); [#metadata(p) <inicio-textual>] }` e repetir.

- [ ] **Step 7: Gerar o PDF e inspecionar**

Run: `.\.venv\Scripts\python.exe -m academico pdf`
Expected: `monografia.pdf: 1 paginas textuais` (só a página vazia da parte textual). Abrir `docs/academic/monografia.pdf` e conferir: capa sem número, folha de rosto com a natureza do trabalho à direita, listas e sumário com título centralizado, nenhuma página com número antes da parte textual.

- [ ] **Step 8: Rodar a suíte inteira e commitar**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passando (877 + 7).

```bash
git add requirements.txt academico tests/test_academico_compilacao.py docs/academic
git commit -m "feat(academico): compilacao da monografia em Typst com estilo ABNT e pre-textuais"
git push
```

---

### Task 2: Tabelas geradas dos resultados

**Files:**
- Create: `academico/tabelas.py`
- Modify: `academico/__main__.py` (subcomando `tabelas`)
- Create (gerados): `docs/academic/monografia/gerado/{regras,regras-pos-correcao,recuperacao,complementares,geracao,geracao-por-regra,concordancia,catalogo}.typ`
- Test: `tests/test_academico_tabelas.py`

**Interfaces:**
- Consumes: `academico.compilacao.RAIZ_REPO`, `PASTA_MONOGRAFIA`; `core.rules.todas.REGISTRO.metas()` (cada meta tem `id`, `titulo`, `categoria`, `severidade`, `url_canonica`).
- Produces: `academico.tabelas.CONSOLIDADO: Path`, `PASTA_GERADO: Path`, `num(valor: float | None, casas: int = 2) -> str`, `faixa(par: list[float] | None) -> str`, `escapar(texto: str) -> str`, `carregar(caminho: Path = CONSOLIDADO) -> dict`, `gerar_todas(consolidado: dict) -> dict[str, str]` (nome do arquivo → conteúdo), `escrever(tabelas: dict[str, str], pasta: Path = PASTA_GERADO) -> None`. Rótulos Typst: `<tab-regras>`, `<tab-regras-pos-correcao>`, `<tab-recuperacao>`, `<tab-complementares>`, `<tab-geracao>`, `<tab-geracao-por-regra>`, `<tab-concordancia>`, `<tab-catalogo>`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_academico_tabelas.py`:

```python
"""Tabelas da monografia geradas de eval/results."""

from academico.compilacao import compilar
from academico.tabelas import (
    PASTA_GERADO,
    carregar,
    escapar,
    faixa,
    gerar_todas,
    num,
    tabela_concordancia,
    tabela_geracao,
    tabela_regras,
)

BLOCO_REGRAS = {
    "origem": "regras-x.json",
    "por_regra": {
        "MOD-002": {
            "matriz": {"vp": 0, "fp": 0, "fn": 0, "vn": 45, "ind_marcados": 0, "ind_nao_marcados": 0},
            "taxas": {"precisao": {"principal": None}, "recall": {"principal": None}},
            "wilson": {"precisao": None, "recall": None},
        },
        "DAX-001": {
            "matriz": {"vp": 6, "fp": 0, "fn": 0, "vn": 4, "ind_marcados": 1, "ind_nao_marcados": 2},
            "taxas": {"precisao": {"principal": 1.0}, "recall": {"principal": 1.0}},
            "wilson": {"precisao": [0.6096, 0.99999], "recall": [0.6096, 0.99999]},
        },
    },
    "total_micro": {
        "matriz": {"vp": 6, "fp": 0, "fn": 0, "vn": 49, "ind_marcados": 1, "ind_nao_marcados": 2},
        "taxas": {"precisao": {"principal": 1.0}, "recall": {"principal": 1.0}},
        "wilson": {"precisao": [0.6096, 0.99999], "recall": [0.6096, 0.99999]},
    },
}


def test_num_usa_virgula_e_traco_para_ausente():
    assert num(0.8846) == "0,88"
    assert num(-0.0796) == "-0,08"
    assert num(None) == "—"
    assert num(0.61296, 3) == "0,613"


def test_faixa_wilson():
    assert faixa([0.6096, 0.99999]) == "[0,61; 1,00]"
    assert faixa(None) == "—"


def test_escapar_neutraliza_marcacao_do_typst():
    assert escapar("a*b_c#d@e<f>$g") == r"a\*b\_c\#d\@e\<f\>\$g"
    assert escapar(r"x\y") == r"x\\y"


def test_tabela_regras_ordena_mostra_ausente_e_total():
    texto = tabela_regras(BLOCO_REGRAS, "tab-x", "Legenda")
    assert texto.index("[DAX-001]") < texto.index("[MOD-002]")
    assert "[MOD-002], [0], [0], [0], [0], [—], [—], [—]" in texto
    assert r"[DAX-001], [6], [0], [0], [3], [1,00], [\[0,61; 1,00\]], [1,00]" in texto
    assert "[*Total (micro)*]" in texto
    assert texto.rstrip().endswith("`regras-x.json`.]")
    assert "<tab-x>" in texto


def test_tabela_geracao_conta_n_com_indeterminados():
    bloco = {
        "origem": "g.json",
        "itens": {
            nome: {"total": {"n": {"sim": 2, "nao": 1, "indeterminado": 1}, "principal": 0.5, "wilson": [0.1, 0.9]}}
            for nome in ("pertinente", "fiel", "recomendacao_correta")
        },
        "utilizavel": {"total": {"n": {"sim": 1, "nao": 3, "indeterminado": 0}, "principal": 0.25, "wilson": [0.05, 0.7]}},
    }
    texto = tabela_geracao(bloco)
    assert r"[Fiel], [2 / 4], [0,50], [\[0,10; 0,90\]]" in texto
    assert r"[*Utilizável como está*], [1 / 4], [0,25], [\[0,05; 0,70\]]" in texto


def test_tabela_concordancia_explica_as_celulas():
    bloco = {
        "origem": "g.json",
        "concordancia": {
            "pertinente": {"tabela": {"a": 60, "b": 0, "c": 1, "d": 0}, "n": 61, "concordancia": 0.9836, "kappa": 0.0},
            "fiel": {"tabela": {"a": 24, "b": 24, "c": 8, "d": 5}, "n": 61, "concordancia": 0.4754, "kappa": -0.0796},
        },
    }
    texto = tabela_concordancia(bloco)
    assert "[Fiel], [Sem aviso de números ou nomes], [24], [24], [8], [5], [0,48], [-0,08]" in texto


def test_arquivos_gerados_em_dia_com_o_consolidado():
    esperadas = gerar_todas(carregar())
    assert sorted(p.name for p in PASTA_GERADO.glob("*.typ")) == sorted(esperadas)
    for nome, conteudo in esperadas.items():
        assert (PASTA_GERADO / nome).read_text(encoding="utf-8") == conteudo, (
            f"{nome} desatualizado: rode `python -m academico tabelas`"
        )


def test_cada_tabela_gerada_compila(tmp_path):
    abnt = (PASTA_GERADO.parent / "abnt.typ").read_text(encoding="utf-8")
    (tmp_path / "abnt.typ").write_text(abnt, encoding="utf-8")
    for nome, conteudo in gerar_todas(carregar()).items():
        doc = tmp_path / "doc.typ"
        doc.write_text('#import "abnt.typ": abnt, fonte\n#show: abnt\n' + conteudo, encoding="utf-8")
        assert compilar(doc).startswith(b"%PDF"), nome
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_tabelas.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'academico.tabelas'`.

- [ ] **Step 3: Implementar `academico/tabelas.py`**

```python
"""Tabelas da monografia geradas a partir dos resultados em `eval/results`.

Nenhum número de resultado é digitado na monografia: cada tabela sai daqui,
lida do consolidado, e um teste falha se o arquivo em `gerado/` divergir do
que este módulo produz.
"""

import json
from pathlib import Path

from academico.compilacao import PASTA_MONOGRAFIA, RAIZ_REPO
from core.rules.todas import REGISTRO

CONSOLIDADO = RAIZ_REPO / "eval" / "results" / "consolidado-2026-10-14.json"
PASTA_GERADO = PASTA_MONOGRAFIA / "gerado"
AUSENTE = "—"
_ESPECIAIS = "\\*_#@<>$`[]~"

ROTULOS_GERACAO = {
    "pertinente": "Pertinente",
    "fiel": "Fiel",
    "recomendacao_correta": "Recomendação correta",
}
CRITERIO_AUTOMATICO = {
    "pertinente": "Cita a seção âncora",
    "fiel": "Sem aviso de números ou nomes",
}
ROTULOS_ESTRATEGIA = {"bm25": "BM25", "densa": "Densa (bge-small)", "hibrida": "Híbrida"}
ROTULOS_CONFIGURACAO = {"secao": "seção", "bm25": "BM25", "completo": "completo"}


def num(valor: float | None, casas: int = 2) -> str:
    """Número no padrão brasileiro; ausente vira travessão."""
    if valor is None:
        return AUSENTE
    return f"{valor:.{casas}f}".replace(".", ",")


def faixa(par: list[float] | None) -> str:
    """Intervalo de Wilson como `[piso; teto]`."""
    if par is None:
        return AUSENTE
    return f"[{num(par[0])}; {num(par[1])}]"


def escapar(texto: str) -> str:
    """Texto literal dentro de conteúdo Typst."""
    for caractere in _ESPECIAIS:
        texto = texto.replace(caractere, "\\" + caractere)
    return texto


def carregar(caminho: Path = CONSOLIDADO) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _celula(texto: str) -> str:
    return f"[{escapar(texto)}]"


def _negrito(texto: str) -> str:
    return f"[*{escapar(texto)}*]"


def _figura(rotulo: str, legenda: str, cabecalho: list[str], linhas: list[list[str]], alinhamento: list[str], origem: str) -> str:
    """Uma tabela ABNT: legenda acima, fonte abaixo. `linhas` já vem em células Typst."""
    partes = [
        "// Gerado por `python -m academico tabelas`. Nao editar a mao.",
        "#figure(",
        "  table(",
        f"    columns: {len(cabecalho)},",
        f"    align: ({', '.join(alinhamento)}),",
        f"    table.header({', '.join(_negrito(c) for c in cabecalho)}),",
    ]
    partes += [f"    {', '.join(linha)}," for linha in linhas]
    partes += [
        "  ),",
        f"  caption: [{escapar(legenda)}],",
        f") <{rotulo}>",
        f"#fonte[Elaborado pelo autor a partir de `{origem}`.]",
        "",
    ]
    return "\n".join(partes)


def _linha_regra(nome: str, dados: dict, negrito: bool = False) -> list[str]:
    m = dados["matriz"]
    rotulo = _negrito(nome) if negrito else _celula(nome)
    return [
        rotulo,
        _celula(str(m["vp"])),
        _celula(str(m["fp"])),
        _celula(str(m["fn"])),
        _celula(str(m["ind_marcados"] + m["ind_nao_marcados"])),
        _celula(num(dados["taxas"]["precisao"]["principal"])),
        _celula(faixa((dados.get("wilson") or {}).get("precisao"))),
        _celula(num(dados["taxas"]["recall"]["principal"])),
    ]


def tabela_regras(bloco: dict, rotulo: str, legenda: str) -> str:
    linhas = [_linha_regra(regra, bloco["por_regra"][regra]) for regra in sorted(bloco["por_regra"])]
    linhas.append(_linha_regra("Total (micro)", bloco["total_micro"], negrito=True))
    return _figura(
        rotulo,
        legenda,
        ["Regra", "VP", "FP", "FN", "Indet.", "Precisão", "IC 95% (Wilson)", "Revocação"],
        linhas,
        ["left"] + ["right"] * 7,
        bloco["origem"],
    )


def tabela_recuperacao(bloco: dict) -> str:
    macro = bloco["macro"]
    linhas = [
        [_celula(k), _celula(num(macro["acerto"][k])), _celula(num(macro["precisao"][k]))]
        for k in ("1", "3", "5", "10")
    ]
    linhas.append([_celula("MRR@10"), _celula(num(macro["mrr"])), _celula(AUSENTE)])
    cfg = bloco["configuracao"]
    legenda = (
        f"Recuperação vencedora (fragmento por {ROTULOS_CONFIGURACAO.get(cfg['chunking'], cfg['chunking'])}, "
        f"busca {ROTULOS_CONFIGURACAO.get(cfg['busca'], cfg['busca'])}, corpus {ROTULOS_CONFIGURACAO.get(cfg['corpus'], cfg['corpus'])}): "
        f"médias macro por regra em {macro['consultas']} consultas"
    )
    return _figura("tab-recuperacao", legenda, ["K", "Acerto@K", "Precisão@K"], linhas, ["left", "right", "right"], bloco["origem"])


def tabela_complementares(bloco: dict) -> str:
    linhas = [
        [_celula(ROTULOS_ESTRATEGIA.get(nome, nome)), _celula(num(v["principal"])), _celula(num(v["piso"])), _celula(num(v["teto"]))]
        for nome, v in bloco["macro"].items()
    ]
    return _figura(
        "tab-complementares",
        "Pertinência dos trechos complementares por estratégia de busca (média macro)",
        ["Estratégia", "Principal", "Piso", "Teto"],
        linhas,
        ["left", "right", "right", "right"],
        bloco["origem"],
    )


def _sim_de_n(contagem: dict) -> str:
    n = contagem["sim"] + contagem["nao"] + contagem["indeterminado"]
    return f"{contagem['sim']} / {n}"


def _linha_item(rotulo: str, total: dict, negrito: bool = False) -> list[str]:
    return [
        _negrito(rotulo) if negrito else _celula(rotulo),
        _celula(_sim_de_n(total["n"])),
        _celula(num(total["principal"])),
        _celula(faixa(total["wilson"])),
    ]


def tabela_geracao(bloco: dict) -> str:
    linhas = [_linha_item(ROTULOS_GERACAO[nome], bloco["itens"][nome]["total"]) for nome in ROTULOS_GERACAO]
    linhas.append(_linha_item("Utilizável como está", bloco["utilizavel"]["total"], negrito=True))
    return _figura(
        "tab-geracao",
        "Rubrica humana das explicações geradas: proporção de \"sim\" por item",
        ["Item", "Sim / n", "Proporção", "IC 95% (Wilson)"],
        linhas,
        ["left", "right", "right", "right"],
        bloco["origem"],
    )


def tabela_geracao_por_regra(bloco: dict) -> str:
    regras = sorted(bloco["itens"]["fiel"]["por_regra"])
    linhas = []
    for regra in regras:
        fiel = bloco["itens"]["fiel"]["por_regra"][regra]["n"]
        recomendacao = bloco["itens"]["recomendacao_correta"]["por_regra"][regra]["n"]
        utilizavel = bloco["utilizavel"]["por_regra"][regra]["n"]
        n = fiel["sim"] + fiel["nao"] + fiel["indeterminado"]
        linhas.append([_celula(regra), _celula(str(n)), _celula(_sim_de_n(fiel)), _celula(_sim_de_n(recomendacao)), _celula(_sim_de_n(utilizavel))])
    return _figura(
        "tab-geracao-por-regra",
        "Rubrica humana das explicações por regra",
        ["Regra", "Achados", "Fiel", "Recomendação correta", "Utilizável"],
        linhas,
        ["left"] + ["right"] * 4,
        bloco["origem"],
    )


def tabela_concordancia(bloco: dict) -> str:
    linhas = []
    for nome, automatico in CRITERIO_AUTOMATICO.items():
        c = bloco["concordancia"][nome]
        t = c["tabela"]
        linhas.append([
            _celula(ROTULOS_GERACAO[nome]),
            _celula(automatico),
            _celula(str(t["a"])),
            _celula(str(t["b"])),
            _celula(str(t["c"])),
            _celula(str(t["d"])),
            _celula(num(c["concordancia"])),
            _celula(num(c["kappa"])),
        ])
    return _figura(
        "tab-concordancia",
        "Concordância entre a leitura humana e a conferência automática "
        "(a: ambos sim; b: só o automático diz sim; c: só o humano diz sim; d: ambos não)",
        ["Item humano", "Critério automático", "a", "b", "c", "d", "Concordância", "Kappa"],
        linhas,
        ["left", "left"] + ["right"] * 6,
        bloco["origem"],
    )


def tabela_catalogo() -> str:
    linhas = [
        [_celula(m.id), _celula(m.titulo), _celula(m.categoria), _celula(m.severidade), f'[#link("{m.url_canonica}")[{escapar(m.url_canonica)}]]']
        for m in REGISTRO.metas()
    ]
    return _figura(
        "tab-catalogo",
        "Catálogo das regras e a página do Microsoft Learn que ancora cada uma",
        ["ID", "Regra", "Categoria", "Severidade", "Âncora"],
        linhas,
        ["left"] * 5,
        "core/rules/todas.py",
    )


def gerar_todas(consolidado: dict) -> dict[str, str]:
    regras = consolidado["regras"]
    pos = consolidado["regras_pos_correcao"]
    return {
        "regras.typ": tabela_regras(regras, "tab-regras", f"Desempenho das regras contra o gabarito em P1–P7 ({regras['rotulo']})"),
        "regras-pos-correcao.typ": tabela_regras(pos, "tab-regras-pos-correcao", f"Desempenho das regras após a correção da MOD-003 e da PERF-001 ({pos['rotulo']})"),
        "recuperacao.typ": tabela_recuperacao(consolidado["recuperacao"]),
        "complementares.typ": tabela_complementares(consolidado["complementares"]),
        "geracao.typ": tabela_geracao(consolidado["geracao"]),
        "geracao-por-regra.typ": tabela_geracao_por_regra(consolidado["geracao"]),
        "concordancia.typ": tabela_concordancia(consolidado["geracao"]),
        "catalogo.typ": tabela_catalogo(),
    }


def escrever(tabelas: dict[str, str], pasta: Path = PASTA_GERADO) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in tabelas.items():
        (pasta / nome).write_text(conteudo, encoding="utf-8", newline="\n")
```

- [ ] **Step 4: Ligar o subcomando `tabelas` na CLI**

Em `academico/__main__.py`, acrescentar o import e a função, e o subparser:

```python
from academico.tabelas import CONSOLIDADO, PASTA_GERADO, carregar, escrever, gerar_todas


def _tabelas() -> int:
    tabelas = gerar_todas(carregar(CONSOLIDADO))
    escrever(tabelas, PASTA_GERADO)
    print(f"{len(tabelas)} tabelas geradas em docs/academic/monografia/gerado")
    return 0
```

```python
    sub.add_parser("tabelas", help="gera as tabelas a partir de eval/results")
```

e no despacho, antes do `pdf`: `if args.comando == "tabelas": return _tabelas()`.

- [ ] **Step 5: Gerar os arquivos e rodar os testes**

Run: `.\.venv\Scripts\python.exe -m academico tabelas`
Expected: `8 tabelas geradas em docs/academic/monografia/gerado`

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_tabelas.py -q`
Expected: `8 passed`.

Conferir à mão em `gerado/regras.typ`: linha total com precisão `0,88`; em `gerado/geracao.typ`: `[Fiel], [32 / 61], [0,52]` e utilizável `[23 / 61], [0,38]`; em `gerado/concordancia.typ`: kappa `-0,08`. Esses são os números do progress-log de 14/10.

- [ ] **Step 6: Suíte inteira e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passando.

```bash
git add academico tests/test_academico_tabelas.py docs/academic/monografia/gerado
git commit -m "feat(academico): tabelas da monografia geradas do consolidado"
git push
```

---

### Task 3: Conferência de citações

**Files:**
- Create: `academico/citacoes.py`
- Modify: `academico/__main__.py` (o `pdf` confere citações antes de compilar)
- Test: `tests/test_academico_citacoes.py`

**Interfaces:**
- Consumes: `academico.compilacao.PASTA_MONOGRAFIA`.
- Produces: `academico.citacoes.BIB: Path`, `chaves_do_bib(texto: str) -> set[str]`, `citacoes(textos: list[str]) -> set[str]`, `class Verificacao(NamedTuple): sem_entrada: list[str]; nao_citadas: list[str]`, `verificar(pasta: Path = PASTA_MONOGRAFIA) -> Verificacao`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_academico_citacoes.py`:

```python
"""Toda citação tem entrada no .bib e toda entrada é citada."""

from academico.citacoes import chaves_do_bib, citacoes, verificar

BIB = """
@article{sadowski2018,
  author = {Sadowski, Caitlin},
  year = {2018},
}
@online{learn-pbip, title = {PBIP}}
"""


def test_chaves_do_bib():
    assert chaves_do_bib(BIB) == {"sadowski2018", "learn-pbip"}


def test_citacoes_ignora_rotulos_de_tabela_e_secao():
    texto = """
    == Método <sec-metodo>
    Ver @sec-metodo e @tab-regras, segundo @sadowski2018 e #cite(<learn-pbip>, form: "prose").
    Contato: fred@exemplo.com. Escapado: \\@naocita.
    """
    tabela = "#figure(table())<tab-regras>"
    assert citacoes([texto, tabela]) == {"sadowski2018", "learn-pbip"}


def test_verificar_aponta_os_dois_sentidos(tmp_path):
    (tmp_path / "capitulos").mkdir()
    (tmp_path / "capitulos" / "c.typ").write_text("Segundo @sadowski2018 e @fantasma.", encoding="utf-8")
    (tmp_path / "referencias.bib").write_text(BIB, encoding="utf-8")
    v = verificar(tmp_path)
    assert v.sem_entrada == ["fantasma"]
    assert v.nao_citadas == ["learn-pbip"]


def test_verificar_sem_bib_e_sem_citacao_e_vazio(tmp_path):
    (tmp_path / "main.typ").write_text("Sem citações.", encoding="utf-8")
    assert verificar(tmp_path) == ([], [])


def test_monografia_sem_citacao_orfa():
    v = verificar()
    assert v.sem_entrada == [], f"citações sem entrada no .bib: {v.sem_entrada}"
    assert v.nao_citadas == [], f"entradas do .bib nunca citadas: {v.nao_citadas}"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_citacoes.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'academico.citacoes'`.

- [ ] **Step 3: Implementar `academico/citacoes.py`**

```python
"""Conferência das citações da monografia contra `referencias.bib`.

No Typst, `@chave` serve tanto para citar quanto para referenciar um rótulo
do próprio texto (`@tab-regras`, `@sec-metodo`). É citação o que não for
rótulo definido em algum `.typ` da monografia.
"""

import re
from pathlib import Path
from typing import NamedTuple

from academico.compilacao import PASTA_MONOGRAFIA

BIB = PASTA_MONOGRAFIA / "referencias.bib"

_REFERENCIA = re.compile(r"(?<![\w\\])@([A-Za-z][\w:-]*[\w])")
_CITE = re.compile(r"cite\(<([A-Za-z][\w:.-]*)>")
_ROTULO = re.compile(r"(?<!cite\()<([A-Za-z][\w:.-]*)>")
_CHAVE_BIB = re.compile(r"^\s*@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


class Verificacao(NamedTuple):
    sem_entrada: list[str]
    nao_citadas: list[str]


def chaves_do_bib(texto: str) -> set[str]:
    return set(_CHAVE_BIB.findall(texto))


def citacoes(textos: list[str]) -> set[str]:
    rotulos = {r for t in textos for r in _ROTULO.findall(t)}
    referencias = {r for t in textos for r in _REFERENCIA.findall(t)}
    explicitas = {c for t in textos for c in _CITE.findall(t)}
    return (referencias - rotulos) | explicitas


def verificar(pasta: Path = PASTA_MONOGRAFIA) -> Verificacao:
    textos = [p.read_text(encoding="utf-8") for p in sorted(pasta.rglob("*.typ"))]
    bib = pasta / "referencias.bib"
    chaves = chaves_do_bib(bib.read_text(encoding="utf-8")) if bib.exists() else set()
    citadas = citacoes(textos)
    return Verificacao(sorted(citadas - chaves), sorted(chaves - citadas))
```

O teste de e-mail passa porque `_REFERENCIA` exige que o `@` não venha depois de letra ou dígito (`fred@exemplo.com`) nem de barra invertida (`\@naocita`).

- [ ] **Step 4: O `pdf` recusa citação sem entrada**

Em `academico/__main__.py`, no início de `_pdf`:

```python
from academico.citacoes import verificar
```

```python
def _pdf(principal: Path, saida: Path) -> int:
    if principal == PRINCIPAL:
        conferencia = verificar()
        if conferencia.sem_entrada:
            print(f"citacoes sem entrada no .bib: {', '.join(conferencia.sem_entrada)}", file=sys.stderr)
            return 1
    conteudo = compilar(principal)
    ...
```

(As entradas não citadas não impedem o PDF; o teste da suíte as acusa.)

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_academico_citacoes.py tests/test_academico_compilacao.py -q`
Expected: todos passando (5 + 7).

- [ ] **Step 6: Suíte inteira, commit e registro**

Run: `.\.venv\Scripts\python.exe -m pytest -q` — todos passando.

Acrescentar ao fim de `docs/project/progress-log.md` uma entrada "## 15/10/2026 — Monografia: infraestrutura pronta" com: Typst 0.15.0 do pip (e qual estilo ABNT foi usado, do Step 1 da Task 1), os três módulos de `academico/`, as 8 tabelas geradas, a contagem de testes, e "**Próximo passo:** capítulo 3 (Método e arquitetura)".

```bash
git add academico tests/test_academico_citacoes.py docs/project/progress-log.md
git commit -m "feat(academico): conferencia das citacoes contra o .bib"
git push
```

---

## Tasks de capítulo (4 a 9): procedimento comum

Cada task de capítulo segue **estes passos**, além do conteúdo próprio descrito nela:

- [ ] **A. Ler as fontes listadas** na task, inteiras ou nas seções indicadas. Não escrever de memória.
- [ ] **B. Escrever** `docs/academic/monografia/capitulos/<arquivo>.typ` em Typst: capítulo com `= Título <cap-x>`, seções com `== Título <sec-x>`; citações `@chave`; tabelas só com `#include "../gerado/<nome>.typ"` e chamadas no texto como `@tab-<nome>`; termos técnicos em itálico na primeira ocorrência; siglas por extenso na primeira ocorrência. Prosa corrida, não listas de tópicos, salvo enumeração genuína.
- [ ] **C. Referências:** para cada fonte externa citada, abrir a fonte (WebFetch/WebSearch, ou o arquivo local), conferir autor, ano, título e local, e só então acrescentar a entrada em `docs/academic/monografia/referencias.bib`. Microsoft Learn: `@online` com `title`, `organization = {Microsoft}`, `url`, `urldate = {2026-10-15}` (ou a data da coleta, se a página vier da base RAG). Fonte inverificável: não citar e avisar o Fred na entrega.
- [ ] **D. Incluir** o capítulo em `main.typ`, na posição do comentário `// CAPÍTULOS`, mantendo a ordem 1→6 (`#include "capitulos/<arquivo>.typ"`).
- [ ] **E. Conferir números:** listar todo número de resultado do texto corrido e conferir cada um contra o JSON indicado (ou a tabela gerada). Os números de referência estão na própria task.
- [ ] **F. Compilar e medir:** `.\.venv\Scripts\python.exe -m academico pdf` e `.\.venv\Scripts\python.exe -m academico paginas`. O capítulo deve ficar dentro de ±1 página do orçamento; se passar, cortar antes de entregar.
- [ ] **G. Testes:** `.\.venv\Scripts\python.exe -m pytest tests/test_academico_citacoes.py tests/test_academico_tabelas.py tests/test_academico_compilacao.py -q` — todos passando.
- [ ] **H. Commit e push:** `git add docs/academic` e `git commit -m "docs(monografia): capitulo N - <titulo>"`; `git push`.
- [ ] **I. Entregar ao Fred e PARAR:** informar as páginas do capítulo, as referências acrescentadas (e as recusadas por não verificáveis), e o caminho `docs/academic/monografia.pdf`. Esperar as correções. Aplicar, recompilar, commitar `docs(monografia): capitulo N revisado`. O capítulo só está aprovado quando o Fred disser.

---

### Task 4: Capítulo 3 — Método e arquitetura (11 páginas)

**Files:**
- Create: `docs/academic/monografia/capitulos/03-metodo.typ`, `docs/academic/monografia/referencias.bib`
- Modify: `docs/academic/monografia/main.typ`

**Interfaces:**
- Consumes: nada gerado. O catálogo das regras entra no Apêndice A (Task 9); até lá, o texto remete a ele como "Apêndice A", sem `@tab-catalogo`, para não quebrar a compilação.
- Produces: rótulos `<cap-metodo>`, `<sec-criterio>`, `<sec-regras>`, `<sec-pipeline>`, `<sec-rag>`, `<sec-geracao>`, `<sec-dataset>`; o bloco de bibliografia em `main.typ`.

**Fontes:** `docs/adr/ADR-001` a `ADR-005` (inteiros, com emendas); `docs/project/fase1-viabilidade-e-planejamento.md` (escopo e limites declarados); specs `2026-10-06-motor-de-regras-estruturais-design.md`, `2026-10-08-regras-de-dax-e-varredura-textual-design.md` (terceiro teste do critério), `2026-10-09-catalogo-de-fontes-rag-design.md`, `2026-10-09-coleta-da-base-rag-design.md`, `2026-10-11-medicao-da-recuperacao-design.md`, `2026-10-11-geracao-com-citacao-design.md`; `docs/project/backlog.md` (decisão D-1, candidatas recusadas); docstring de `core/rules/referencias.py` (PERF-005); `python -m core.rules.catalogo`.

**Roteiro:**
1. Visão geral (1 p.): ferramenta em três camadas — leitura do PBIP, detecção determinística, explicação com RAG e LLM local; por que o LLM explica e não detecta (ADR-003).
2. Leitura do PBIP (1 p.): estrutura PBIP, `model.bim` em TMSL (ADR-001), modelo interno normalizado; o lexer de DAX e a cobertura medida (137 de 137 expressões tokenizadas, 105 de 105 em escopo, 0 lacunas, no P8).
3. Critério de detectabilidade (2 p.) `<sec-criterio>`: os três testes e o caso da PERF-005 (precisão entre ~15% e ~91% contra limiar 0,7 — números da docstring de `core/rules/referencias.py`), a contagem como resultado (D-1).
4. As 9 regras (1,5 p.) `<sec-regras>`: agrupadas por categoria (modelagem, performance, DAX), cada uma ancorada numa página do Microsoft Learn; remete ao Apêndice A.
5. Pipeline (1 p.) `<sec-pipeline>`: orquestração sequencial, isolamento de erro por regra, figura do fluxo — uma `#figure(kind: image, ...)` desenhada com `grid` de `box`es e setas, legenda "Fluxo da auditoria", fonte "Elaborado pelo autor".
6. Base RAG e recuperação (2 p.) `<sec-rag>`: catálogo de 1.420 páginas do Learn, coleta e extração por seção (ADR-004); seleção da recuperação por medição — 24 combinações, regra de decisão fixada antes, vencedora "seção + BM25 sobre o corpus completo" (detalhe numérico fica no cap. 4).
7. Geração com citação obrigatória (1,5 p.) `<sec-geracao>`: `qwen2.5:7b` no Ollama local, temperatura 0, a citação obrigatória e a conferência automática de números e nomes; o cache das respostas.
8. Dataset (1 p.) `<sec-dataset>`: P1–P7 públicos (MIT) para métricas; P8 como estudo de caso não reprodutível por terceiros (ADR-005, 2ª emenda); gabarito anotado pelo autor, tag `regras-gt`.

**Bibliografia em `main.typ`:** neste capítulo entram as primeiras citações (páginas do Learn das âncoras e da documentação do PBIP/TMSL). Substituir o comentário `// BIBLIOGRAFIA E APÊNDICES (Tasks 4 e 9)` por:

```typst
#bibliography("referencias.bib", title: [Referências], style: "associacao-brasileira-de-normas-tecnicas")
// APÊNDICES (Task 9)
```

(Se no Step 1 da Task 1 o estilo tiver sido o `abnt.csl`, usar `style: "abnt.csl"`.) O título da bibliografia não é numerado: acrescentar em `abnt.typ`, dentro de `abnt`, `show bibliography: set heading(numbering: none)`.

**Números de referência a conferir:** 9 regras; 1.420 páginas; 137/137 e 105/105 (status.md, seção 3); 24 combinações (`rag/medicao` no progress-log de 11/10); faixa ~15%–~91% e limiar 0,7 (`core/rules/referencias.py`).

Executar os passos comuns A–I.

---

### Task 5: Capítulo 4 — Avaliação (12 páginas)

**Files:**
- Create: `docs/academic/monografia/capitulos/04-avaliacao.typ`
- Modify: `docs/academic/monografia/main.typ`, `docs/academic/monografia/referencias.bib` (se citar)

**Interfaces:**
- Consumes: `gerado/regras.typ`, `gerado/regras-pos-correcao.typ`, `gerado/recuperacao.typ`, `gerado/complementares.typ`, `gerado/geracao.typ`, `gerado/geracao-por-regra.typ`, `gerado/concordancia.typ`; rótulos `<sec-criterio>`, `<sec-rag>`, `<sec-geracao>`, `<sec-dataset>` do cap. 3.
- Produces: `<cap-avaliacao>`, `<sec-aval-regras>`, `<sec-aval-recuperacao>`, `<sec-aval-geracao>`, `<sec-caso-p8>`.

**Fontes:** `eval/results/consolidado-2026-10-14.json`; progress-log nas entradas de 12/10 (gabarito, precisão 0,88, análise de erros da MOD-003 e da PERF-001, divergências), 11/10 (medição da recuperação, efeito teto), 12/10 (complementares), 14/10 (rubrica: padrões dos "não"); `docs/project/status.md` seção 3 (P8: 15 de 15, 8,1 s por achado, 123 s; cache 165,6 s → 1,5 s); specs `2026-10-11-gabarito-das-regras-design.md`, `2026-10-12-correcao-mod003-perf001-design.md`, `2026-10-13-avaliacao-da-geracao-design.md`.

**Roteiro:**
1. Desenho da avaliação (1 p.): três perguntas (as regras acertam? a recuperação acha a passagem certa? a explicação é utilizável?), um conjunto de medidas por pergunta, intervalo de Wilson, regra de decisão fixada antes de medir.
2. Regras (3,5 p.) `<sec-aval-regras>`: `#include "../gerado/regras.typ"`; precisão micro 0,88, macro 0,88; R-03 acionado só pela MOD-003; os 6 FP da MOD-003 (tabelas desconectadas de propósito) e os 6 FN da PERF-001; correção como análise de erros, não resultado oficial — `#include "../gerado/regras-pos-correcao.typ"`; o gatilho do R-12 (46 VP ≥ 40).
3. Recuperação (2,5 p.) `<sec-aval-recuperacao>`: `#include "../gerado/recuperacao.typ"`; acerto@5 = 1,00 com efeito teto declarado; complementares — `#include "../gerado/complementares.typ"`, BM25 mantido por margem de 0,10.
4. Geração (4 p.) `<sec-aval-geracao>`: `#include "../gerado/geracao.typ"` e `#include "../gerado/geracao-por-regra.typ"`; padrões dos "não" (PERF-001 "compreende"/"descompressão", DAX-001 tratando BLANK como problema, sintaxe DAX no Power Query, MOD-003 relacionando tabelas desconectadas); `#include "../gerado/concordancia.typ"` — kappa 0,00 por prevalência e −0,08 na fidelidade: a conferência automática não mede fidelidade; consequência na ferramenta (aviso renomeado para "Números ou nomes sem origem nos trechos").
5. Estudo de caso P8 e desempenho (1 p.) `<sec-caso-p8>`: 15 achados; tempo por achado; cache.

**Números de referência a conferir** (contra o consolidado e o progress-log): precisão micro 0,88 (46 VP, 6 FP); macro 0,88; pertinente 61/61; fiel 32/61 = 0,52; recomendação 47/61 = 0,77; utilizável 23/61 = 0,38; kappa 0,00 e −0,08; acerto@5 1,00; MRR 0,61; complementares 0,62 × 0,67; P8 15/15, 8,1 s, 123 s, 165,6 s → 1,5 s.

Ao fim dos passos comuns, acrescentar entrada curta ao progress-log ("capítulos 3 e 4 escritos e aprovados", páginas) no commit de aprovação.

Executar os passos comuns A–I.

---

### Task 6: Capítulo 2 — Fundamentação e trabalhos relacionados (8 páginas)

**Files:**
- Create: `docs/academic/monografia/capitulos/02-fundamentacao.typ`
- Modify: `docs/academic/monografia/main.typ`, `docs/academic/monografia/referencias.bib`

**Interfaces:**
- Produces: `<cap-fundamentacao>`.

**Fontes:** `docs/project/backlog.md` (referência a Sadowski et al., 2018); `docs/project/fase1-viabilidade-e-planejamento.md`; specs da RAG; pesquisa externa verificada.

**Roteiro:**
1. Power BI, modelo semântico e PBIP (1,5 p.): modelo tabular, VertiPaq, TMSL, o formato PBIP — documentação da Microsoft.
2. Boas práticas de modelagem (1,5 p.): esquema estrela (Kimball; orientação do Learn "Understand star schema"), colunas calculadas × Power Query, tabelas de data.
3. Análise estática e falsos positivos (1,5 p.): Sadowski et al. (2018), "Lessons from building static analysis tools at Google", CACM — por que a precisão importa mais que a cobertura; ligação com o critério de detectabilidade.
4. RAG e LLM local (2 p.): Lewis et al. (2020) (RAG); BM25 (Robertson e Zaragoza, 2009); modelos densos de sentença; fidelidade/alucinação em geração ancorada (um levantamento verificado, p.ex. Ji et al., 2023, ACM Computing Surveys); LLM local e privacidade dos modelos dos clientes.
5. Ferramentas existentes (1,5 p.): Best Practice Analyzer do Tabular Editor e regras da Microsoft para ele; outras ferramentas que a pesquisa confirmar. Posicionar a contribuição: regras ancoradas + explicação com citação verificável, avaliada com gabarito.

**Regra deste capítulo:** cada referência acima é **candidata**; só entra a que for conferida no passo C. As referências citadas aqui são as que o README listará em "Trabalhos relacionados" (Task 11) — anotar quais são ferramentas/trabalhos comparáveis.

Executar os passos comuns A–I.

---

### Task 7: Capítulo 5 — Discussão e ameaças à validade (5 páginas)

**Files:**
- Create: `docs/academic/monografia/capitulos/05-discussao.typ`
- Modify: `docs/academic/monografia/main.typ`

**Interfaces:**
- Consumes: rótulos dos caps. 3 e 4.
- Produces: `<cap-discussao>`.

**Fontes:** `docs/project/riscos.md` (R-03, R-12 e os demais); progress-log (decisão de um anotador; P9 não acionado; efeito teto e decisão por uma consulta, emenda de 11/10 da ADR-002; não determinismo do Ollama com temperatura 0; PERF-001 sem complementar pertinente; `filterExpression` de RLS pendente de verificação no Desktop); `fase1-viabilidade-e-planejamento.md` (limites declarados: F17 TMDL, F19 camada de relatório, F24 PBIX; grupo 4 de regras de M fora do MVP).

**Roteiro:**
1. O que os resultados dizem (1,5 p.): método de regras se sustenta; recuperação não é o gargalo; geração do 7B é; a conferência automática é insuficiente.
2. Ameaças à validade interna (1,5 p.): um anotador, gabarito pelo próprio autor, cegueira da planilha aos sinais automáticos como mitigação; não determinismo.
3. Ameaças à validade externa (1 p.): sete projetos públicos, n pequeno por regra (Wilson largo), P8 fora das métricas.
4. Escopo (1 p.): o que a ferramenta não lê e por quê.

Executar os passos comuns A–I.

---

### Task 8: Capítulo 1 — Introdução (4 páginas)

**Files:**
- Create: `docs/academic/monografia/capitulos/01-introducao.typ`
- Modify: `docs/academic/monografia/main.typ`

**Interfaces:**
- Produces: `<cap-introducao>`.

**Fontes:** `docs/project/fase1-viabilidade-e-planejamento.md` (problema e objetivo); `docs/project/status.md`; os caps. 2–5 já aprovados.

**Roteiro:** contexto (1 p.); problema (0,75 p.); objetivo geral e específicos (0,75 p.); contribuições — o critério de detectabilidade, a ferramenta, a avaliação com gabarito e rubrica (0,75 p.); organização do texto, um parágrafo por capítulo com `@cap-x` (0,75 p.).

Executar os passos comuns A–I.

---

### Task 9: Capítulo 6 — Conclusão — e apêndices

**Files:**
- Create: `docs/academic/monografia/capitulos/06-conclusao.typ`, `docs/academic/monografia/capitulos/apendices.typ`
- Modify: `docs/academic/monografia/main.typ`, `docs/academic/monografia/capitulos/03-metodo.typ` (trocar a menção ao "Apêndice A" por `@tab-catalogo`)

**Interfaces:**
- Consumes: `gerado/catalogo.typ`.
- Produces: `<cap-conclusao>`, `<apendice-a>`, `<apendice-b>`, `<apendice-c>`.

**Fontes:** todos os capítulos aprovados; `docs/superpowers/specs/2026-10-13-avaliacao-da-geracao-design.md` (texto da rubrica); README atual, seções Ambiente, Avaliação da geração e Testes (comandos de reprodução).

**Conclusão (2 p.):** retomar o objetivo, responder às três perguntas da avaliação com os números principais, trabalhos futuros (regras de M, TMDL, camada de relatório, modelo maior ou ajuste para a geração, consulta da PERF-001, segundo anotador).

**Apêndices:** em `main.typ`, substituir `// APÊNDICES (Task 9)` por `#include "capitulos/apendices.typ"`. Em `apendices.typ`:

```typst
#set heading(numbering: (..n) => "APÊNDICE " + numbering("A", n.pos().first()) + " –", supplement: [Apêndice])
#counter(heading).update(0)

= Catálogo das regras <apendice-a>
#include "../gerado/catalogo.typ"

= Rubrica da avaliação da geração <apendice-b>
// texto da rubrica: os três itens, os vereditos sim/não/indeterminado e o critério de "utilizável como está", transcritos da spec de 13/10

= Como reproduzir os resultados <apendice-c>
// comandos, na ordem: ambiente, tabelas (`python -m academico tabelas`), regras, recuperação, geração com cache, consolidado
```

Os dois comentários acima marcam o que escrever; substituí-los pelo texto antes do commit. Os apêndices ficam fora da contagem de páginas textuais (estão depois de `<fim-textual>`).

Executar os passos comuns A–I.

---

### Task 10: Resumo e abstract

**Files:**
- Create: `docs/academic/monografia/capitulos/resumo.typ`
- Modify: `docs/academic/monografia/main.typ`

**Interfaces:**
- Produces: o texto do resumo e do abstract, que a Task 11 copia no README.

- [ ] **Step 1: Escrever `resumo.typ`**

```typst
#import "../abnt.typ": titulo-pre

#titulo-pre[Resumo]
#par(first-line-indent: 0pt)[ /* resumo: um parágrafo, 150 a 500 palavras (NBR 6028) — objetivo, método, resultados com os números principais, conclusão */ ]

#v(1em)
#par(first-line-indent: 0pt)[*Palavras-chave:* Power BI. Análise estática. Geração aumentada por recuperação. Modelos de linguagem. Auditoria de modelos semânticos.]

#titulo-pre[Abstract]
#par(first-line-indent: 0pt)[ /* tradução fiel do resumo */ ]

#v(1em)
#par(first-line-indent: 0pt)[*Keywords:* Power BI. Static analysis. Retrieval-augmented generation. Language models. Semantic model auditing.]
```

Substituir os dois comentários `/* */` pelos textos. Números do resumo: precisão 0,88; pertinente 61/61; fiel 0,52; utilizável 0,38; 9 regras; 7 projetos.

- [ ] **Step 2:** Em `main.typ`, substituir `// RESUMO-E-ABSTRACT (Task 10)` por `#include "capitulos/resumo.typ"`.

- [ ] **Step 3:** Compilar (`python -m academico pdf`), conferir que resumo e abstract cabem cada um em uma página, rodar os testes de `academico`, commitar `docs(monografia): resumo e abstract`, push, entregar ao Fred e PARAR até a aprovação.

---

### Task 11: README no modelo da PUC-Rio e `ambiente.md`

**Files:**
- Create: `docs/project/ambiente.md`
- Modify: `README.md`, `academico/tabelas.py`, `academico/__main__.py`
- Test: `tests/test_academico_tabelas.py`

**Interfaces:**
- Consumes: `tabela_regras`, `tabela_recuperacao`, `tabela_geracao` (dados), `carregar`.
- Produces: `academico.tabelas.README: Path`, `blocos_markdown(consolidado: dict) -> dict[str, str]`, `atualizar_readme(texto: str, blocos: dict[str, str]) -> str`.

- [ ] **Step 1: Testes que falham** (acrescentar a `tests/test_academico_tabelas.py`):

```python
from academico.tabelas import README, atualizar_readme, blocos_markdown


def test_atualizar_readme_substitui_so_o_miolo_do_bloco():
    texto = "antes\n<!-- tabela:regras -->\nvelho\n<!-- /tabela -->\ndepois\n"
    novo = atualizar_readme(texto, {"regras": "| a |\n|---|\n| 1 |"})
    assert novo == "antes\n<!-- tabela:regras -->\n| a |\n|---|\n| 1 |\n<!-- /tabela -->\ndepois\n"


def test_atualizar_readme_bloco_ausente_e_erro():
    import pytest

    with pytest.raises(KeyError, match="geracao"):
        atualizar_readme("sem blocos", {"geracao": "x"})


def test_blocos_markdown_numeros_em_portugues():
    blocos = blocos_markdown(carregar())
    assert set(blocos) == {"regras", "recuperacao", "geracao"}
    assert "| **Total (micro)** | 46 | 6 | 6 |" in blocos["regras"]
    assert "| Fiel | 32 / 61 | 0,52 |" in blocos["geracao"]


def test_readme_em_dia_com_o_consolidado():
    texto = README.read_text(encoding="utf-8")
    assert atualizar_readme(texto, blocos_markdown(carregar())) == texto, "rode `python -m academico tabelas`"
```

- [ ] **Step 2:** Rodar e ver falhar (`ImportError`).

- [ ] **Step 3: Implementar** em `academico/tabelas.py`:

```python
README = RAIZ_REPO / "README.md"


def _md(cabecalho: list[str], linhas: list[list[str]]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(linha) + " |" for linha in linhas]
    return "\n".join(saida)


def blocos_markdown(consolidado: dict) -> dict[str, str]:
    """As três tabelas principais, em Markdown, para a seção Resultados do README."""
    regras = consolidado["regras"]
    linhas_regras = []
    for regra in sorted(regras["por_regra"]):
        d = regras["por_regra"][regra]
        m = d["matriz"]
        linhas_regras.append([regra, str(m["vp"]), str(m["fp"]), str(m["fn"]), num(d["taxas"]["precisao"]["principal"]), faixa(d["wilson"]["precisao"])])
    t = regras["total_micro"]
    linhas_regras.append(["**Total (micro)**", str(t["matriz"]["vp"]), str(t["matriz"]["fp"]), str(t["matriz"]["fn"]), num(t["taxas"]["precisao"]["principal"]), faixa(t["wilson"]["precisao"])])

    rec = consolidado["recuperacao"]["macro"]
    linhas_rec = [[k, num(rec["acerto"][k]), num(rec["precisao"][k])] for k in ("1", "3", "5", "10")]
    linhas_rec.append(["MRR@10", num(rec["mrr"]), AUSENTE])

    ger = consolidado["geracao"]
    linhas_ger = [[ROTULOS_GERACAO[n], _sim_de_n(ger["itens"][n]["total"]["n"]), num(ger["itens"][n]["total"]["principal"]), faixa(ger["itens"][n]["total"]["wilson"])] for n in ROTULOS_GERACAO]
    u = ger["utilizavel"]["total"]
    linhas_ger.append(["**Utilizável como está**", _sim_de_n(u["n"]), num(u["principal"]), faixa(u["wilson"])])

    return {
        "regras": _md(["Regra", "VP", "FP", "FN", "Precisão", "IC 95% (Wilson)"], linhas_regras),
        "recuperacao": _md(["K", "Acerto@K", "Precisão@K"], linhas_rec),
        "geracao": _md(["Item", "Sim / n", "Proporção", "IC 95% (Wilson)"], linhas_ger),
    }


def atualizar_readme(texto: str, blocos: dict[str, str]) -> str:
    """Troca o miolo de cada bloco `<!-- tabela:nome -->` … `<!-- /tabela -->`."""
    for nome, conteudo in blocos.items():
        abertura = f"<!-- tabela:{nome} -->\n"
        inicio = texto.find(abertura)
        if inicio < 0:
            raise KeyError(f"bloco <!-- tabela:{nome} --> ausente do README")
        miolo = inicio + len(abertura)
        fim = texto.index("<!-- /tabela -->", miolo)
        texto = texto[:miolo] + conteudo + "\n" + texto[fim:]
    return texto
```

Em `academico/__main__.py`, `_tabelas` passa a também atualizar o README:

```python
    texto = README.read_text(encoding="utf-8")
    README.write_text(atualizar_readme(texto, blocos_markdown(consolidado)), encoding="utf-8", newline="\n")
```

(com `consolidado = carregar(CONSOLIDADO)` reaproveitado e `README`, `atualizar_readme`, `blocos_markdown` importados).

- [ ] **Step 4: Mover o conteúdo técnico para `docs/project/ambiente.md`.** Copiar do README atual, sem alterar o conteúdo, as seções "Estado atual", "Decisões de arquitetura", "Escopo", "Stack", "Estrutura", "Ambiente" (com todas as subseções), "Testes" e "Nota sobre dados", com cabeçalho `# Ambiente, estrutura e comandos` e uma linha dizendo que o conteúdo veio do README em 15/10/2026. Conferir com `git diff --stat` que nenhuma seção ficou para trás.

- [ ] **Step 5: Reescrever `README.md`** no modelo da PUC-Rio, sem os comentários de orientação:

```markdown
# Auditoria de projetos Power BI

#### Aluno: [Carlos Frederico Coelho Lisboa](https://github.com/FredLisboa77)
#### Orientadora: Evelyn C. S. Batista

---

Trabalho apresentado ao curso [GenAI e LLM MASTER](https://ica.ele.puc-rio.br/cursos/ia-generativa-large-language-models/) como pré-requisito para conclusão de curso e obtenção de crédito na disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão".

- [Link para o código](https://github.com/FredLisboa77/PUC-RIO_TCC).

- [Link para a monografia](docs/academic/monografia.pdf).

- Trabalhos relacionados:
    - (os trabalhos/ferramentas comparáveis citados no capítulo 2, com link — se nenhum, remover este item)

---

### Resumo

(texto do resumo, idêntico ao de `capitulos/resumo.typ`)

### Abstract

(texto do abstract, idêntico)

### 1. Introdução
### 2. Modelagem
### 3. Resultados

<!-- tabela:regras -->
<!-- /tabela -->

<!-- tabela:recuperacao -->
<!-- /tabela -->

<!-- tabela:geracao -->
<!-- /tabela -->

### 4. Conclusões
### 5. Referências
### 6. Instalação
### 7. Como executar

---

Matrícula: 251.100.867

Pontifícia Universidade Católica do Rio de Janeiro

Curso de Pós Graduação *Inteligência Artificial Generativa & Large Language Models*
```

Os parênteses acima indicam o conteúdo a escrever, não texto a manter. Conteúdo de cada seção:
- **1. Introdução** — condensação do cap. 1, 3 a 4 parágrafos.
- **2. Modelagem** — condensação do cap. 3, 4 a 6 parágrafos (leitura do PBIP, critério de detectabilidade, regras, RAG, geração com citação, dataset).
- **3. Resultados** — 3 a 5 parágrafos do cap. 4 intercalados com os três blocos de tabela.
- **4. Conclusões** — condensação dos caps. 5 e 6.
- **5. Referências** — as obras citadas no README, em ABNT, copiadas da lista de referências do PDF.
- **6. Instalação** — Python 3.11, venv, `pip install -r requirements.txt`, Ollama com `qwen2.5:7b`, e um link para `docs/project/ambiente.md` (certificado do Norton, `HF_HUB_OFFLINE` etc.).
- **7. Como executar** — auditoria pela CLI (`python -m core.auditoria <pasta-pbip>`), interface (`streamlit run app/streamlit_app.py`), relatório (`python -m reports ...`), testes (`pytest`), e a monografia (`python -m academico tabelas` e `python -m academico pdf`).

Os números escritos nos parágrafos seguem as regras das tasks de capítulo (conferidos contra o JSON).

- [ ] **Step 6:** `.\.venv\Scripts\python.exe -m academico tabelas` (preenche os blocos) e `.\.venv\Scripts\python.exe -m pytest -q` — todos passando.

- [ ] **Step 7:** Commit `docs: README no modelo de entrega da PUC-Rio e ambiente.md`, push, entregar ao Fred (com o link do README na branch no GitHub) e PARAR até a aprovação.

---

### Task 12: Revisão de consistência, PDF final e merge

**Files:**
- Modify: `docs/academic/monografia/**`, `docs/academic/monografia.pdf`, `docs/project/progress-log.md`, `docs/project/status.md`

- [ ] **Step 1: Consistência.** Ler o PDF inteiro de ponta a ponta e conferir: nomes de regra iguais aos do registro; termos uniformes (achado, regra, âncora, trecho, explicação, revocação); todo número do texto corrido contra o JSON (refazer a lista do passo E de cada capítulo); toda tabela e figura chamada no texto antes de aparecer; siglas por extenso na primeira ocorrência; nenhum comentário `//` ou `/* */` de instrução remanescente (`git grep -n "Task\|/\*" docs/academic/monografia`).
- [ ] **Step 2: Extensão.** `python -m academico paginas` entre 30 e 50.
- [ ] **Step 3: PDF final.** `python -m academico tabelas`, `python -m academico pdf`, `.\.venv\Scripts\python.exe -m pytest -q` — todos passando.
- [ ] **Step 4: Registro.** Entrada no progress-log ("Monografia concluída": páginas, referências, testes; **Próximo passo:** demonstração, subprojeto 3) e `status.md` atualizado (posição, F5). Oferecer ao Fred a atualização da página do orientador.
- [ ] **Step 5: Commit e push** `docs(monografia): versao final`.
- [ ] **Step 6: Merge.** Perguntar ao Fred se o merge na `main` é local (como na F4/F5) ou por PR, e seguir superpowers:finishing-a-development-branch.
