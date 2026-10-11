# Conjunto de avaliação da recuperação — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a régua da recuperação: o gabarito das 9 regras (página, seção e frase-marca), as 62 consultas geradas e versionadas, e as métricas (acerto@K, Precision@K, MRR@10; macro por regra, micro e por tipo), sem medir nenhum recuperador.

**Architecture:** Três módulos em `rag/`: `texto.py` (normalização), `consulta.py` (a consulta que o pipeline real vai usar) e `avaliacao.py` (modelos, dedução da seção âncora, gerador, métricas e o comando `python -m rag.avaliacao gerar`). Núcleo puro, com a leitura das páginas e dos PBIP injetada; os dados ficam em `eval/recuperacao/`. O arquivo de consultas é gerado e conferido por teste, no padrão do `rag/sources.yaml`.

**Tech Stack:** Python 3.11.9, Pydantic 2.13.5, PyYAML 6.0.3, pytest 9.1.1. Nenhuma dependência nova.

**Spec:** `docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`

## Global Constraints

- Código, nomes, mensagens, testes e commits em **português**.
- Rodar pelo `.venv`: `.\.venv\Scripts\python.exe -m pytest -q`.
- **Nenhum teste usa rede.** Testes de dados reais são pulados quando `rag/store/` ou `data/pbip/` não existe.
- `eval/` **não** vira pacote Python: só dados e documentos. Código vai em `rag/`.
- Arquivos gerados são gravados com `newline="\n"` (o teste compara texto; `core.autocrlf` converte no checkout).
- O P8 fica fora: o dataset de métricas é **P1–P7** (ADR-005).
- K em `(1, 3, 5, 10)`; a busca é feita uma vez com K = 10. A métrica que decide é a **macro por regra**.
- Relevância: o trecho contém a frase-marca, ambos normalizados.
- Pedido do Fred: **salvar cada etapa importante** — commit e push a cada tarefa.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Branch: `fase3-avaliacao-recuperacao`.

## Review Focus

1. **Consulta de uma regra que não tem gabarito chega a `avaliar`** — falha antes de medir qualquer consulta, nunca conta como erro de recuperação. Teste na Task 4.
2. **Recuperador que devolve lista vazia** — a consulta vira "não apareceu", sem `IndexError` ao montar o "primeiro devolvido". Teste na Task 4.
3. **Uma regra falha no runner sobre um dos P1–P7** — o gerador para nomeando projeto e regra, em vez de gerar menos consultas em silêncio. Teste na Task 5.
4. **Frase-marca partida entre dois blocos da mesma seção** (parágrafo seguido de lista) — a dedução une os blocos com espaço e encontra a seção. Teste na Task 3.
5. **Nome de objeto com caracteres especiais** (`Sales[Avg $/Unit LY]`, `Backorder %`, `→` em relacionamento) — a consulta preserva o nome como está e o YAML faz ida e volta sem perda. Testes nas Tasks 2 e 3.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `rag/texto.py` | `normalizar` |
| `rag/consulta.py` | `montar_consulta`, `TIPOS_EM_INGLES` |
| `rag/avaliacao.py` | Caminhos, `ErroDeAvaliacao`, modelos, `ler_frases_marca`, `id_da_pagina`, `deduzir_secao`, `gerar`, `como_yaml`, `ler_conjunto`, `avaliar`, `formatar_relatorio`, `achados_dos_projetos`, `gerar_do_repositorio`, `main` |
| `eval/recuperacao/gabarito.yaml` | Escrito à mão: as 9 frases-marca |
| `eval/recuperacao/consultas.yaml` | Gerado |
| `tests/test_rag_texto.py`, `tests/test_rag_consulta.py`, `tests/test_rag_avaliacao.py`, `tests/test_rag_avaliacao_real.py` | Testes novos |
| `tests/test_rag_store_real.py` | Passa a ler o gabarito e a usar `rag.texto.normalizar` |

---

### Task 1: Normalização e o gabarito das frases-marca

**Files:**
- Create: `rag/texto.py`, `rag/avaliacao.py`, `eval/recuperacao/gabarito.yaml`
- Modify: `tests/test_rag_store_real.py`
- Test: `tests/test_rag_texto.py`, `tests/test_rag_avaliacao.py`

**Interfaces:**
- Consumes: `rag.catalogo.RAIZ` (a pasta `rag/`).
- Produces:
  - `rag.texto.normalizar(texto: str) -> str`
  - `rag.avaliacao`: `RAIZ_REPO: Path`, `PASTA_AVALIACAO = RAIZ_REPO / "eval" / "recuperacao"`, `ARQUIVO_GABARITO`, `ARQUIVO_CONSULTAS`, `class ErroDeAvaliacao(Exception)`, `class FraseMarca(BaseModel)` (`id_regra: str`, `frase_marca: str`), `ler_frases_marca(caminho: Path) -> list[FraseMarca]` (ordenada por `id_regra`)

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_texto.py`:

```python
"""Normalização usada para casar a frase-marca com o texto do Learn."""

from rag.texto import normalizar


def test_aspas_tipograficas_viram_retas():
    assert normalizar("Don’t use “DIVIDE” ‘here’") == "don't use \"divide\" 'here'"


def test_espaco_nao_separavel_e_espacos_repetidos():
    assert normalizar("Auto date/time   option\n\tnow") == "auto date/time option now"


def test_maiusculas_viram_minusculas():
    assert normalizar("Mark Your Date Table") == "mark your date table"
```

Criar `tests/test_rag_avaliacao.py`:

```python
"""Conjunto de avaliação da recuperação: gabarito, consultas e métricas.

Dados sintéticos; os testes sobre a base e os PBIP reais estão em
`test_rag_avaliacao_real.py`.
"""

import pytest

from core.rules.todas import REGISTRO
from rag.avaliacao import (
    ARQUIVO_GABARITO,
    ErroDeAvaliacao,
    FraseMarca,
    ler_frases_marca,
)


def test_ler_frases_marca_ordena_por_regra(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-006\n  frase_marca: b\n- id_regra: MOD-003\n  frase_marca: a\n",
        encoding="utf-8",
    )
    assert ler_frases_marca(arquivo) == [
        FraseMarca(id_regra="MOD-003", frase_marca="a"),
        FraseMarca(id_regra="MOD-006", frase_marca="b"),
    ]


def test_gabarito_ausente_falha(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="não existe"):
        ler_frases_marca(tmp_path / "nao-existe.yaml")


def test_regra_repetida_no_gabarito_falha(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-003\n  frase_marca: a\n- id_regra: MOD-003\n  frase_marca: b\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*mais de uma vez"):
        ler_frases_marca(arquivo)


def test_gabarito_versionado_cobre_exatamente_as_regras_do_registro():
    frases = ler_frases_marca(ARQUIVO_GABARITO)
    assert [f.id_regra for f in frases] == REGISTRO.ids()
    assert all(0 < len(f.frase_marca.split()) <= 12 for f in frases)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_texto.py tests/test_rag_avaliacao.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.texto'` e `'rag.avaliacao'`.

- [ ] **Step 2: Implementar**

Criar `rag/texto.py`:

```python
"""Normalização de texto para comparar trechos do Learn com frases transcritas.

O Learn usa aspas tipográficas (`’`) e espaço não separável; as specs de regras
transcrevem com aspas retas. Sem normalizar, a frase-marca não casaria.
"""

_TROCAS = {
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    " ": " ",
}


def normalizar(texto: str) -> str:
    for de, para in _TROCAS.items():
        texto = texto.replace(de, para)
    return " ".join(texto.lower().split())
```

Criar `rag/avaliacao.py`:

```python
"""Conjunto de avaliação da recuperação (Fase 3).

A régua que decide chunking, embeddings e busca híbrida: o gabarito das regras
(página, seção âncora e frase-marca), as consultas por regra e por achado de
P1–P7, e as métricas. Desenho:
`docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from rag.catalogo import RAIZ

RAIZ_REPO = RAIZ.parent
PASTA_AVALIACAO = RAIZ_REPO / "eval" / "recuperacao"
ARQUIVO_GABARITO = PASTA_AVALIACAO / "gabarito.yaml"
ARQUIVO_CONSULTAS = PASTA_AVALIACAO / "consultas.yaml"


class ErroDeAvaliacao(Exception):
    """O conjunto não pode ser gerado ou medido sem perder algo em silêncio."""


class FraseMarca(BaseModel):
    """Escrita à mão: um trecho curto da passagem que a regra cita."""

    id_regra: str
    frase_marca: str


def ler_frases_marca(caminho: Path) -> list[FraseMarca]:
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"{caminho} não existe")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    frases = [FraseMarca.model_validate(d) for d in dados]
    vistos: set[str] = set()
    for frase in frases:
        if frase.id_regra in vistos:
            raise ErroDeAvaliacao(f"{frase.id_regra} aparece mais de uma vez em {caminho.name}")
        vistos.add(frase.id_regra)
    return sorted(frases, key=lambda f: f.id_regra)
```

Criar `eval/recuperacao/gabarito.yaml` (as frases são as mesmas que hoje estão em `tests/test_rag_store_real.py`):

```yaml
# Frases-marca: um trecho curto (até ~10 palavras) da passagem que cada regra cita,
# transcrito das specs de regras. Escrito à mão. Citação acadêmica com fonte
# (Lei 9.610/98, art. 46), não republicação da página.
# A página e a seção âncora são deduzidas por `python -m rag.avaliacao gerar`.
- id_regra: DAX-001
  frase_marca: use the DIVIDE function whenever the denominator is an expression
- id_regra: MOD-001
  frase_marca: disable the global Auto date/time option
- id_regra: MOD-002
  frase_marca: minimize the use of bi-directional relationships
- id_regra: MOD-003
  frase_marca: the right number of tables with the right relationships
- id_regra: MOD-005
  frase_marca: mark your date table as a date table
- id_regra: MOD-006
  frase_marca: the benefits of a single model table outweigh the benefits
- id_regra: MOD-007
  frase_marca: avoid creating one-to-one model relationships
- id_regra: PERF-001
  frase_marca: preference creating custom columns in Power Query
- id_regra: PERF-003
  frase_marca: calculations that sum the values of a column of Decimal number
```

- [ ] **Step 3: Verificar os testes novos**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_texto.py tests/test_rag_avaliacao.py -q`
Expected: 7 passam.

- [ ] **Step 4: O teste de dados reais passa a ler o gabarito**

Em `tests/test_rag_store_real.py`:
- Acrescentar aos imports (os demais, `import yaml` inclusive, ficam como estão):

```python
from rag.avaliacao import ARQUIVO_GABARITO, ler_frases_marca
from rag.texto import normalizar
```

- Trocar o dicionário `FRASES_MARCA = {...}` e sua docstring por:

```python
FRASES_MARCA = {f.id_regra: f.frase_marca for f in ler_frases_marca(ARQUIVO_GABARITO)}
"""As frases-marca vivem em `eval/recuperacao/gabarito.yaml`."""
```

- Apagar a função `_normalizar` e, em `test_a_passagem_citada_pela_regra_esta_no_texto_extraido`, trocar as duas chamadas `_normalizar(` por `normalizar(`.

`yaml` continua importado: `test_toda_pagina_do_catalogo_foi_coletada_e_extraida` usa.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_store_real.py -q`
Expected: 11 passam (com `rag/store/` presente).
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam (365 + 7).

- [ ] **Step 5: Commit e push**

```bash
git add rag/texto.py rag/avaliacao.py eval/recuperacao/gabarito.yaml tests/test_rag_texto.py tests/test_rag_avaliacao.py tests/test_rag_store_real.py
git commit -m "feat(rag): normalizacao compartilhada e gabarito das frases-marca em eval/recuperacao

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 2: A consulta do pipeline

**Files:**
- Create: `rag/consulta.py`
- Test: `tests/test_rag_consulta.py`

**Interfaces:**
- Consumes: `core.rules.base.RegraMeta`, `Achado`, `Evidencia`; `core.rules.todas.REGISTRO`.
- Produces: `rag.consulta.TIPOS_EM_INGLES: dict[str, str]`; `montar_consulta(meta: RegraMeta, achado: Achado | None = None) -> str`.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_consulta.py`:

```python
"""A consulta que o pipeline manda ao índice: termos da regra, em inglês, mais
o contexto do achado. A mesma função alimenta o conjunto de avaliação."""

import pytest

from core.rules.base import Achado, Evidencia
from core.rules.todas import REGISTRO
from rag.consulta import TIPOS_EM_INGLES, montar_consulta

METAS = {m.id: m for m in REGISTRO.metas()}


def _achado(id_regra, tipo, objeto):
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(tipo_objeto=tipo, objeto=objeto),
        mensagem="mensagem em português que não entra na consulta",
    )


def test_consulta_por_regra_une_os_termos():
    assert montar_consulta(METAS["MOD-003"]) == (
        "star schema model relationships; dimension table fact table; "
        "table not related; filter propagation"
    )


def test_consulta_por_achado_acrescenta_tipo_e_objeto():
    achado = _achado("MOD-003", "tabela", "Date Role")
    assert montar_consulta(METAS["MOD-003"], achado) == (
        "star schema model relationships; dimension table fact table; "
        "table not related; filter propagation | table Date Role"
    )


@pytest.mark.parametrize(
    "objeto",
    ["Sales[Avg $/Unit LY]", "Backorder Percentage[Backorder %]", "Sales Order[K] → Sales[K]"],
)
def test_nome_do_objeto_e_preservado_como_esta(objeto):
    consulta = montar_consulta(METAS["DAX-001"], _achado("DAX-001", "medida", objeto))
    assert consulta.endswith(f" | measure {objeto}")


def test_mensagem_e_trecho_ficam_de_fora():
    achado = Achado(
        id_regra="DAX-001",
        evidencia=Evidencia(tipo_objeto="medida", objeto="T[M]", trecho="DIVIDE([A], [B])"),
        mensagem="divide com o operador",
    )
    consulta = montar_consulta(METAS["DAX-001"], achado)
    assert "operador" not in consulta and "[A]" not in consulta


def test_todo_tipo_de_objeto_tem_traducao():
    assert TIPOS_EM_INGLES == {
        "tabela": "table",
        "coluna": "column",
        "medida": "measure",
        "relacionamento": "relationship",
        "particao": "partition",
        "modelo": "model",
    }


def test_mesma_entrada_mesma_saida():
    achado = _achado("PERF-003", "coluna", "Sales[Unit Price]")
    assert montar_consulta(METAS["PERF-003"], achado) == montar_consulta(METAS["PERF-003"], achado)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_consulta.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.consulta'`.

- [ ] **Step 2: Implementar**

Criar `rag/consulta.py`:

```python
"""A consulta de recuperação de um achado (Fase 3).

É a função que o pipeline real chama, e também a que gera as consultas do
conjunto de avaliação: o conjunto mede a consulta que será usada. Os termos
são os da regra, em inglês, porque o `bge-small-en-v1.5` é monolíngue (ADR-002,
revisão C-6). A `mensagem` do achado, em português, e o trecho de DAX ou M
ficam de fora.
"""

from core.rules.base import Achado, RegraMeta

TIPOS_EM_INGLES = {
    "tabela": "table",
    "coluna": "column",
    "medida": "measure",
    "relacionamento": "relationship",
    "particao": "partition",
    "modelo": "model",
}


def montar_consulta(meta: RegraMeta, achado: Achado | None = None) -> str:
    texto = "; ".join(meta.termos_consulta)
    if achado is None:
        return texto
    tipo = TIPOS_EM_INGLES[achado.evidencia.tipo_objeto]
    return f"{texto} | {tipo} {achado.evidencia.objeto}"
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_consulta.py -q`
Expected: 8 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/consulta.py tests/test_rag_consulta.py
git commit -m "feat(rag): consulta de recuperacao montada a partir da regra e do achado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 3: Dedução da seção âncora, gerador e o arquivo de consultas

**Files:**
- Modify: `rag/avaliacao.py` (acrescentar)
- Test: `tests/test_rag_avaliacao.py` (acrescentar)

**Interfaces:**
- Consumes: Task 1 (`FraseMarca`, `ErroDeAvaliacao`); Task 2 (`montar_consulta`); `rag.texto.normalizar`; `rag.extracao.PaginaExtraida`; `rag.urls.normalizar_url`, `caminho_sem_idioma`; `core.rules.base.RegraMeta`, `Achado`.
- Produces (`rag/avaliacao.py`):
  - `class Gabarito(FraseMarca)`: `id_pagina: str`, `ancora: str`
  - `class Consulta(BaseModel)`: `id: str`, `tipo: Literal["regra", "achado"]`, `projeto: str | None = None`, `id_regra: str`, `objeto: str | None = None`, `texto: str`
  - `class ConjuntoAvaliacao(BaseModel)`: `gabaritos: list[Gabarito]`, `consultas: list[Consulta]`
  - `CABECALHO_CONSULTAS: str`
  - `id_da_pagina(url: str) -> str`
  - `deduzir_secao(pagina: PaginaExtraida, frase_marca: str, id_regra: str) -> str`
  - `gerar(*, metas: list[RegraMeta], frases: list[FraseMarca], ler_pagina: Callable[[str], PaginaExtraida], achados_por_projeto: dict[str, list[Achado]]) -> ConjuntoAvaliacao`
  - `como_yaml(conjunto: ConjuntoAvaliacao) -> str`; `ler_conjunto(caminho: Path) -> ConjuntoAvaliacao`

- [ ] **Step 1: Testes que falham**

Em `tests/test_rag_avaliacao.py`, acrescentar ao import de `rag.avaliacao`: `ConjuntoAvaliacao`, `Consulta`, `Gabarito`, `como_yaml`, `deduzir_secao`, `gerar`, `id_da_pagina`, `ler_conjunto`. Acrescentar também:

```python
from core.rules.base import Achado, Evidencia
from rag.consulta import montar_consulta
from rag.extracao import VERSAO_EXTRATOR, Bloco, PaginaExtraida, Secao
```

No fim do arquivo:

```python
METAS = {m.id: m for m in REGISTRO.metas()}
STAR = "learn:power-bi/guidance/star-schema"
FRASES = [
    FraseMarca(id_regra="MOD-003", frase_marca="right number of tables"),
    FraseMarca(id_regra="MOD-006", frase_marca="a single model table"),
]


def _pagina(id_pagina, secoes):
    """`secoes`: lista de (ancora, [textos dos blocos])."""
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_pagina,
        url="https://learn.microsoft.com/en-us/x",
        titulo="T",
        secoes=[
            Secao(
                ancora=ancora,
                titulo=ancora,
                nivel=2,
                caminho=ancora,
                blocos=[Bloco(tipo="paragrafo", texto=t) for t in textos],
            )
            for ancora, textos in secoes
        ],
        secoes_excluidas=[],
    )


PAGINA_STAR = _pagina(
    STAR,
    [
        ("relevance", ["Use the Right Number of Tables here."]),
        ("snowflake-dimensions", ["Usually A single model table is better."]),
        ("outra", ["nada a ver"]),
    ],
)


def _achado(id_regra, objeto, tipo="tabela"):
    return Achado(id_regra=id_regra, evidencia=Evidencia(tipo_objeto=tipo, objeto=objeto), mensagem="m")


def _gerar(achados=None, frases=FRASES, paginas=None):
    paginas = paginas or {STAR: PAGINA_STAR}
    return gerar(
        metas=[METAS["MOD-003"], METAS["MOD-006"]],
        frases=frases,
        ler_pagina=lambda id_pagina: paginas[id_pagina],
        achados_por_projeto=achados or {},
    )


def test_id_da_pagina_vem_da_url_canonica():
    assert id_da_pagina(METAS["MOD-003"].url_canonica) == STAR


def test_deduz_a_secao_de_cada_regra():
    assert _gerar().gabaritos == [
        Gabarito(id_regra="MOD-003", frase_marca="right number of tables", id_pagina=STAR, ancora="relevance"),
        Gabarito(
            id_regra="MOD-006",
            frase_marca="a single model table",
            id_pagina=STAR,
            ancora="snowflake-dimensions",
        ),
    ]


def test_frase_partida_entre_dois_blocos_da_mesma_secao_e_encontrada():
    pagina = _pagina(STAR, [("s", ["the right number", "of tables matters"])])
    assert deduzir_secao(pagina, "right number of tables", "MOD-003") == "s"


def test_frase_em_nenhuma_secao_falha_nomeando_a_regra():
    pagina = _pagina(STAR, [("s", ["nada"])])
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*nenhuma seção.*star-schema"):
        deduzir_secao(pagina, "right number of tables", "MOD-003")


def test_frase_em_mais_de_uma_secao_falha_nomeando_as_secoes():
    pagina = _pagina(STAR, [("a", ["right number of tables"]), ("b", ["Right number of tables"])])
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*mais de uma seção.*a, b"):
        deduzir_secao(pagina, "right number of tables", "MOD-003")


def test_regra_sem_gabarito_e_gabarito_sem_regra_falham():
    with pytest.raises(ErroDeAvaliacao, match="sem gabarito: MOD-006"):
        _gerar(frases=FRASES[:1])
    with pytest.raises(ErroDeAvaliacao, match="regra inexistente: XXX-999"):
        _gerar(frases=[*FRASES, FraseMarca(id_regra="XXX-999", frase_marca="x")])


def test_consultas_por_regra_e_por_achado_com_ids_estaveis():
    achados = {
        "P2": [_achado("MOD-003", "Toggle A"), _achado("MOD-003", "Toggle B")],
        "P1": [_achado("MOD-006", "Product")],
    }
    conjunto = _gerar(achados)
    assert [(c.id, c.tipo, c.projeto, c.objeto) for c in conjunto.consultas] == [
        ("REGRA/MOD-003", "regra", None, None),
        ("REGRA/MOD-006", "regra", None, None),
        ("P1/MOD-006/1", "achado", "P1", "Product"),
        ("P2/MOD-003/1", "achado", "P2", "Toggle A"),
        ("P2/MOD-003/2", "achado", "P2", "Toggle B"),
    ]
    assert conjunto.consultas[0].texto == montar_consulta(METAS["MOD-003"])
    assert conjunto.consultas[2].texto == montar_consulta(METAS["MOD-006"], achados["P1"][0])


def test_achado_de_regra_fora_do_registro_falha():
    with pytest.raises(ErroDeAvaliacao, match="P1.*XXX-999"):
        _gerar({"P1": [_achado("XXX-999", "T")]})


def test_yaml_faz_ida_e_volta_com_nomes_especiais(tmp_path):
    achados = {"P5": [_achado("MOD-003", "Sales[Avg $/Unit LY] → % 'x'", tipo="medida")]}
    conjunto = _gerar(achados)
    texto = como_yaml(conjunto)
    assert texto.startswith("# Gerado por `python -m rag.avaliacao gerar`")
    arquivo = tmp_path / "consultas.yaml"
    arquivo.write_text(texto, encoding="utf-8", newline="\n")
    assert ler_conjunto(arquivo) == conjunto
    assert b"\r\n" not in arquivo.read_bytes()


def test_ler_conjunto_ausente_falha_indicando_o_gerador(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="rag.avaliacao gerar"):
        ler_conjunto(tmp_path / "nao-existe.yaml")
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py -q`
Expected: `ImportError: cannot import name 'ConjuntoAvaliacao'`.

- [ ] **Step 2: Implementar**

Em `rag/avaliacao.py`, os imports passam a ser:

```python
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from core.rules.base import Achado, RegraMeta
from rag.catalogo import RAIZ
from rag.consulta import montar_consulta
from rag.extracao import PaginaExtraida
from rag.texto import normalizar
from rag.urls import caminho_sem_idioma, normalizar_url
```

E acrescentar no fim:

```python
CABECALHO_CONSULTAS = (
    "# Gerado por `python -m rag.avaliacao gerar` — não editar à mão.\n"
    "# Frases-marca: eval/recuperacao/gabarito.yaml. Desenho:\n"
    "# docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md\n"
)


class Gabarito(FraseMarca):
    """A frase-marca com a página e a seção âncora deduzidas da base extraída."""

    id_pagina: str
    ancora: str


class Consulta(BaseModel):
    id: str
    tipo: Literal["regra", "achado"]
    projeto: str | None = None
    id_regra: str
    objeto: str | None = None
    texto: str


class ConjuntoAvaliacao(BaseModel):
    gabaritos: list[Gabarito]
    consultas: list[Consulta]


def id_da_pagina(url: str) -> str:
    """`https://learn.microsoft.com/en-us/power-bi/guidance/star-schema` →
    `learn:power-bi/guidance/star-schema`, o id do catálogo."""
    return "learn:" + caminho_sem_idioma(normalizar_url(url))


def deduzir_secao(pagina: PaginaExtraida, frase_marca: str, id_regra: str) -> str:
    """A única seção cujo texto contém a frase-marca. Os blocos da seção são
    unidos com espaço: a frase pode começar num parágrafo e terminar numa lista."""
    alvo = normalizar(frase_marca)
    achadas = [
        secao.ancora
        for secao in pagina.secoes
        if alvo in normalizar(" ".join(bloco.texto for bloco in secao.blocos))
    ]
    if not achadas:
        raise ErroDeAvaliacao(f"{id_regra}: frase-marca em nenhuma seção de {pagina.id}")
    if len(achadas) > 1:
        raise ErroDeAvaliacao(
            f"{id_regra}: frase-marca em mais de uma seção de {pagina.id}: {', '.join(achadas)}"
        )
    return achadas[0]


def gerar(
    *,
    metas: list[RegraMeta],
    frases: list[FraseMarca],
    ler_pagina: Callable[[str], PaginaExtraida],
    achados_por_projeto: dict[str, list[Achado]],
) -> ConjuntoAvaliacao:
    """Gabaritos deduzidos e consultas: uma por regra, depois uma por achado,
    projeto a projeto em ordem e, dentro do projeto, na ordem do runner."""
    por_id = {meta.id: meta for meta in metas}
    frase_de = {frase.id_regra: frase for frase in frases}
    sem_gabarito = sorted(set(por_id) - set(frase_de))
    if sem_gabarito:
        raise ErroDeAvaliacao(f"regra(s) sem gabarito: {', '.join(sem_gabarito)}")
    sem_regra = sorted(set(frase_de) - set(por_id))
    if sem_regra:
        raise ErroDeAvaliacao(f"gabarito de regra inexistente: {', '.join(sem_regra)}")

    gabaritos = []
    for id_regra in sorted(por_id):
        frase = frase_de[id_regra]
        id_pagina = id_da_pagina(por_id[id_regra].url_canonica)
        ancora = deduzir_secao(ler_pagina(id_pagina), frase.frase_marca, id_regra)
        gabaritos.append(
            Gabarito(
                id_regra=id_regra, frase_marca=frase.frase_marca, id_pagina=id_pagina, ancora=ancora
            )
        )

    consultas = [
        Consulta(id=f"REGRA/{id_regra}", tipo="regra", id_regra=id_regra, texto=montar_consulta(por_id[id_regra]))
        for id_regra in sorted(por_id)
    ]
    for projeto in sorted(achados_por_projeto):
        contagem: Counter[str] = Counter()
        for achado in achados_por_projeto[projeto]:
            meta = por_id.get(achado.id_regra)
            if meta is None:
                raise ErroDeAvaliacao(f"{projeto}: achado de regra fora do registro: {achado.id_regra}")
            contagem[achado.id_regra] += 1
            consultas.append(
                Consulta(
                    id=f"{projeto}/{achado.id_regra}/{contagem[achado.id_regra]}",
                    tipo="achado",
                    projeto=projeto,
                    id_regra=achado.id_regra,
                    objeto=achado.evidencia.objeto,
                    texto=montar_consulta(meta, achado),
                )
            )
    return ConjuntoAvaliacao(gabaritos=gabaritos, consultas=consultas)


def como_yaml(conjunto: ConjuntoAvaliacao) -> str:
    corpo = yaml.safe_dump(
        conjunto.model_dump(mode="json"), allow_unicode=True, sort_keys=False, width=1000
    )
    return CABECALHO_CONSULTAS + corpo


def ler_conjunto(caminho: Path) -> ConjuntoAvaliacao:
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"{caminho} não existe — rode `python -m rag.avaliacao gerar`")
    return ConjuntoAvaliacao.model_validate(yaml.safe_load(caminho.read_text(encoding="utf-8")))
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py -q`
Expected: todos passam (4 da Task 1 + 10 novos).
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/avaliacao.py tests/test_rag_avaliacao.py
git commit -m "feat(rag): gerador do conjunto de avaliacao — secao ancora deduzida e consultas por regra e por achado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 4: Métricas e relatório

**Files:**
- Modify: `rag/avaliacao.py` (acrescentar)
- Test: `tests/test_rag_avaliacao.py` (acrescentar)

**Interfaces:**
- Consumes: Task 3 (`ConjuntoAvaliacao`, `Consulta`, `Gabarito`); `rag.texto.normalizar`.
- Produces (`rag/avaliacao.py`):
  - `KS = (1, 3, 5, 10)`; `K_MAX = 10`
  - `class Trecho(BaseModel)`: `texto: str`, `id_pagina: str`, `ancora: str | None = None`
  - `Buscador = Callable[[str, int], list[Trecho]]`
  - `class ResultadoConsulta(BaseModel)`: `id`, `id_regra`, `tipo`, `posicao: int | None`, `relevantes_ate: dict[int, int]`, `primeiro_devolvido: str | None`
  - `class Metricas(BaseModel)`: `consultas: int`, `acerto: dict[int, float]`, `precisao: dict[int, float]`, `mrr: float`
  - `class RelatorioRecuperacao(BaseModel)`: `macro: Metricas`, `micro: Metricas`, `por_tipo: dict[str, Metricas]`, `por_regra: dict[str, Metricas]`, `resultados: list[ResultadoConsulta]`; propriedade `erros -> list[ResultadoConsulta]`
  - `avaliar(buscar: Buscador, conjunto: ConjuntoAvaliacao) -> RelatorioRecuperacao`
  - `formatar_relatorio(relatorio: RelatorioRecuperacao) -> str`

Contas do caso sintético abaixo, feitas à mão: regra R1 com duas consultas (primeiro acerto nas posições 1 e 3) e regra R2 com uma (sem acerto).
- Micro: acerto@1 = 1/3, acerto@3 = 2/3, MRR = (1 + 1/3 + 0)/3 = 4/9, Precision@3 = (1 + 1 + 0)/(3 × 3) = 2/9.
- R1: acerto@1 = 1/2, acerto@3 = 1, MRR = 2/3. R2: tudo 0.
- Macro: acerto@1 = 1/4, acerto@3 = 1/2, MRR = 1/3.
- Por tipo: `regra` (c1, c3) acerto@1 = 1/2; `achado` (c2) acerto@1 = 0, acerto@3 = 1.

- [ ] **Step 1: Testes que falham**

Acrescentar ao import de `rag.avaliacao`: `K_MAX`, `Trecho`, `avaliar`, `formatar_relatorio`. No fim:

```python
RELEVANTE = Trecho(texto="Text with “Alpha” Beta here.", id_pagina="p", ancora="a")
OUTRO = Trecho(texto="other", id_pagina="q", ancora="b")

CONJUNTO = ConjuntoAvaliacao(
    gabaritos=[
        Gabarito(id_regra="R1", frase_marca='"alpha" beta', id_pagina="p", ancora="a"),
        Gabarito(id_regra="R2", frase_marca="gamma", id_pagina="p", ancora="c"),
    ],
    consultas=[
        Consulta(id="REGRA/R1", tipo="regra", id_regra="R1", texto="q1"),
        Consulta(id="P1/R1/1", tipo="achado", projeto="P1", id_regra="R1", objeto="T", texto="q2"),
        Consulta(id="REGRA/R2", tipo="regra", id_regra="R2", texto="q3"),
    ],
)

RESPOSTAS = {"q1": [RELEVANTE, OUTRO, OUTRO], "q2": [OUTRO, OUTRO, RELEVANTE], "q3": []}


def _buscar(texto, k):
    return RESPOSTAS[texto][:k]


def test_metricas_micro_contadas_a_mao():
    micro = avaliar(_buscar, CONJUNTO).micro
    assert micro.consultas == 3
    assert micro.acerto[1] == pytest.approx(1 / 3)
    assert micro.acerto[3] == pytest.approx(2 / 3)
    assert micro.mrr == pytest.approx(4 / 9)
    assert micro.precisao[3] == pytest.approx(2 / 9)


def test_macro_e_a_media_das_regras_e_difere_da_micro():
    relatorio = avaliar(_buscar, CONJUNTO)
    assert relatorio.por_regra["R1"].acerto[1] == pytest.approx(1 / 2)
    assert relatorio.por_regra["R1"].mrr == pytest.approx(2 / 3)
    assert relatorio.por_regra["R2"].acerto[10] == 0
    assert relatorio.macro.acerto[1] == pytest.approx(1 / 4)
    assert relatorio.macro.acerto[3] == pytest.approx(1 / 2)
    assert relatorio.macro.mrr == pytest.approx(1 / 3)
    assert relatorio.macro.mrr != pytest.approx(relatorio.micro.mrr)


def test_corte_por_tipo():
    por_tipo = avaliar(_buscar, CONJUNTO).por_tipo
    assert por_tipo["regra"].consultas == 2 and por_tipo["regra"].acerto[1] == pytest.approx(1 / 2)
    assert por_tipo["achado"].acerto[1] == 0 and por_tipo["achado"].acerto[3] == 1


def test_erros_listam_posicao_e_primeiro_devolvido():
    erros = avaliar(_buscar, CONJUNTO).erros
    assert [(e.id, e.posicao, e.primeiro_devolvido) for e in erros] == [
        ("P1/R1/1", 3, "q#b"),
        ("REGRA/R2", None, None),
    ]


def test_aspas_tipograficas_casam_com_aspas_retas():
    assert avaliar(_buscar, CONJUNTO).resultados[0].posicao == 1


def test_consulta_de_regra_sem_gabarito_falha_antes_de_medir():
    chamadas = []

    def buscar(texto, k):
        chamadas.append(texto)
        return []

    conjunto = CONJUNTO.model_copy(
        update={"consultas": [*CONJUNTO.consultas, Consulta(id="REGRA/R9", tipo="regra", id_regra="R9", texto="q9")]}
    )
    with pytest.raises(ErroDeAvaliacao, match="R9"):
        avaliar(buscar, conjunto)
    assert chamadas == []


def test_recuperador_que_devolve_mais_que_k_falha():
    with pytest.raises(ErroDeAvaliacao, match="REGRA/R1.*11"):
        avaliar(lambda texto, k: [OUTRO] * (K_MAX + 1), CONJUNTO)


def test_conjunto_sem_consultas_falha():
    with pytest.raises(ErroDeAvaliacao, match="nenhuma consulta"):
        avaliar(_buscar, CONJUNTO.model_copy(update={"consultas": []}))


def test_relatorio_formatado():
    texto = formatar_relatorio(avaliar(_buscar, CONJUNTO))
    assert "Macro por regra (decide)" in texto
    assert "MRR@10 0.333" in texto
    assert "Micro (3 consultas)" in texto
    assert "P1/R1/1: primeiro acerto na posição 3" in texto
    assert "REGRA/R2: não apareceu" in texto
    assert "Precision@K" in texto
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py -q`
Expected: `ImportError: cannot import name 'K_MAX'`.

- [ ] **Step 2: Implementar**

Acrescentar no fim de `rag/avaliacao.py`:

```python
KS = (1, 3, 5, 10)
K_MAX = 10


class Trecho(BaseModel):
    """O que um recuperador devolve. A régua não sabe de chunking nem de índice."""

    texto: str
    id_pagina: str
    ancora: str | None = None


Buscador = Callable[[str, int], list[Trecho]]


class ResultadoConsulta(BaseModel):
    id: str
    id_regra: str
    tipo: Literal["regra", "achado"]
    posicao: int | None
    """Posição (a partir de 1) do primeiro trecho relevante; `None` se não houve até K_MAX."""
    relevantes_ate: dict[int, int]
    primeiro_devolvido: str | None
    """`id_pagina#ancora` do primeiro trecho devolvido, para explicar o erro."""


class Metricas(BaseModel):
    consultas: int
    acerto: dict[int, float]
    precisao: dict[int, float]
    mrr: float


class RelatorioRecuperacao(BaseModel):
    macro: Metricas
    micro: Metricas
    por_tipo: dict[str, Metricas]
    por_regra: dict[str, Metricas]
    resultados: list[ResultadoConsulta]

    @property
    def erros(self) -> list[ResultadoConsulta]:
        return [r for r in self.resultados if r.posicao is None or r.posicao > 1]


def _metricas(resultados: list[ResultadoConsulta]) -> Metricas:
    n = len(resultados)
    return Metricas(
        consultas=n,
        acerto={k: sum(1 for r in resultados if r.posicao is not None and r.posicao <= k) / n for k in KS},
        precisao={k: sum(r.relevantes_ate[k] for r in resultados) / (k * n) for k in KS},
        mrr=sum(1 / r.posicao for r in resultados if r.posicao is not None) / n,
    )


def _media(metricas: list[Metricas]) -> Metricas:
    n = len(metricas)
    return Metricas(
        consultas=sum(m.consultas for m in metricas),
        acerto={k: sum(m.acerto[k] for m in metricas) / n for k in KS},
        precisao={k: sum(m.precisao[k] for m in metricas) / n for k in KS},
        mrr=sum(m.mrr for m in metricas) / n,
    )


def avaliar(buscar: Buscador, conjunto: ConjuntoAvaliacao) -> RelatorioRecuperacao:
    """Mede um recuperador sobre o conjunto. A busca é feita uma vez por consulta,
    com K_MAX; os cortes menores saem da mesma lista."""
    if not conjunto.consultas:
        raise ErroDeAvaliacao("nenhuma consulta no conjunto")
    frases = {g.id_regra: normalizar(g.frase_marca) for g in conjunto.gabaritos}
    sem_gabarito = sorted({c.id_regra for c in conjunto.consultas} - set(frases))
    if sem_gabarito:
        raise ErroDeAvaliacao(f"consulta(s) de regra sem gabarito: {', '.join(sem_gabarito)}")

    resultados = []
    for consulta in conjunto.consultas:
        trechos = buscar(consulta.texto, K_MAX)
        if len(trechos) > K_MAX:
            raise ErroDeAvaliacao(
                f"{consulta.id}: o recuperador devolveu {len(trechos)} trechos para K = {K_MAX}"
            )
        relevante = [frases[consulta.id_regra] in normalizar(t.texto) for t in trechos]
        resultados.append(
            ResultadoConsulta(
                id=consulta.id,
                id_regra=consulta.id_regra,
                tipo=consulta.tipo,
                posicao=next((i + 1 for i, r in enumerate(relevante) if r), None),
                relevantes_ate={k: sum(relevante[:k]) for k in KS},
                primeiro_devolvido=(
                    f"{trechos[0].id_pagina}#{trechos[0].ancora or ''}" if trechos else None
                ),
            )
        )

    regras = sorted({r.id_regra for r in resultados})
    por_regra = {regra: _metricas([r for r in resultados if r.id_regra == regra]) for regra in regras}
    por_tipo = {
        tipo: _metricas([r for r in resultados if r.tipo == tipo])
        for tipo in ("regra", "achado")
        if any(r.tipo == tipo for r in resultados)
    }
    return RelatorioRecuperacao(
        macro=_media(list(por_regra.values())),
        micro=_metricas(resultados),
        por_tipo=por_tipo,
        por_regra=por_regra,
        resultados=resultados,
    )


def _linha(rotulo: str, m: Metricas) -> str:
    acertos = " · ".join(f"acerto@{k} {m.acerto[k]:.3f}" for k in KS)
    return f"{rotulo}: {acertos} · MRR@10 {m.mrr:.3f}"


def formatar_relatorio(relatorio: RelatorioRecuperacao) -> str:
    linhas = [
        _linha("Macro por regra (decide)", relatorio.macro),
        _linha(f"Micro ({relatorio.micro.consultas} consultas)", relatorio.micro),
        *(
            _linha(f"Tipo {tipo} ({m.consultas} consultas)", m)
            for tipo, m in relatorio.por_tipo.items()
        ),
        "Por regra:",
        *(_linha(f"  {regra} ({m.consultas})", m) for regra, m in relatorio.por_regra.items()),
        "Precision@K (micro): "
        + " · ".join(f"@{k} {relatorio.micro.precisao[k]:.3f}" for k in KS)
        + " — com uma só passagem relevante por consulta, tende a acerto@K / K.",
        f"Consultas fora da posição 1: {len(relatorio.erros)}",
    ]
    for erro in relatorio.erros:
        onde = (
            f"primeiro acerto na posição {erro.posicao}" if erro.posicao is not None else "não apareceu"
        )
        linhas.append(f"  {erro.id}: {onde} — primeiro devolvido: {erro.primeiro_devolvido or '(nada)'}")
    return "\n".join(linhas)
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/avaliacao.py tests/test_rag_avaliacao.py
git commit -m "feat(rag): metricas da recuperacao — acerto@K, Precision@K e MRR, macro por regra, micro e por tipo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 5: Comando, geração real e registros

**Files:**
- Modify: `rag/avaliacao.py` (acrescentar)
- Create: `eval/recuperacao/consultas.yaml` (gerado), `tests/test_rag_avaliacao_real.py`
- Test: `tests/test_rag_avaliacao.py` (acrescentar)
- Modify: `README.md`, `docs/project/status.md`, `docs/project/progress-log.md`
- Republicar: a página do orientador (artifact `https://claude.ai/code/artifact/476dde6e-9da2-4871-8cfc-afc67784f0c0`; fonte no scratchpad da sessão em `orientador/andamento.html`; se tiver sumido, baixar com Artifact `read_file`, path `index.html`, tirar o esqueleto até `<title>` e republicar com `url`)

**Interfaces:**
- Consumes: Tasks 1–4; `core.ingest.abrir_pbip`; `core.parser_bim.ler_modelo`; `core.rules.runner.avaliar` (importado como `avaliar_regras`, para não colidir com a métrica); `core.rules.todas.REGISTRO`; `rag.extracao.PASTA_TEXTOS`, `caminho_do_texto`.
- Produces (`rag/avaliacao.py`):
  - `PASTA_PBIP = RAIZ_REPO / "data" / "pbip"`; `PROJETOS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")`
  - `achados_dos_projetos(pasta: Path, auditar: Callable[[Path], ResultadoRegras] | None = None) -> dict[str, list[Achado]]`
  - `ler_pagina_extraida(id_pagina: str, pasta_textos: Path = PASTA_TEXTOS) -> PaginaExtraida`
  - `gerar_do_repositorio() -> ConjuntoAvaliacao`
  - `resumo_conjunto(conjunto: ConjuntoAvaliacao) -> str`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Testes que falham**

Acrescentar ao import de `rag.avaliacao` em `tests/test_rag_avaliacao.py`: `achados_dos_projetos`, `ler_pagina_extraida`, `main`, `resumo_conjunto`. Acrescentar `from core.rules.runner import FalhaDeRegra, ResultadoRegras` e `from rag import avaliacao as modulo_avaliacao`. No fim:

```python
def _projetos(tmp_path, codigos):
    for codigo in codigos:
        (tmp_path / f"{codigo}_Projeto {codigo}").mkdir()
    return tmp_path


def test_achados_dos_projetos_roda_os_sete_em_ordem(tmp_path):
    vistos = []

    def auditar(caminho):
        vistos.append(caminho.name)
        return ResultadoRegras(achados=[_achado("MOD-003", caminho.name)], regras_executadas=9)

    achados = achados_dos_projetos(_projetos(tmp_path, [f"P{i}" for i in range(1, 9)]), auditar)
    assert list(achados) == ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    assert vistos == [f"P{i}_Projeto P{i}" for i in range(1, 8)]


def test_projeto_ausente_falha_nomeando_o_projeto(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="P4"):
        achados_dos_projetos(_projetos(tmp_path, ["P1", "P2", "P3"]), lambda c: ResultadoRegras())


def test_regra_com_falha_num_projeto_para_o_gerador(tmp_path):
    def auditar(caminho):
        return ResultadoRegras(regras_com_falha=[FalhaDeRegra(id_regra="DAX-001", erro="boom")])

    with pytest.raises(ErroDeAvaliacao, match="P1.*DAX-001"):
        achados_dos_projetos(_projetos(tmp_path, [f"P{i}" for i in range(1, 8)]), auditar)


def test_pagina_extraida_ausente_indica_coleta_e_extracao(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="rag.coleta.*rag.extracao"):
        ler_pagina_extraida(STAR, tmp_path)


def test_resumo_conta_consultas_por_tipo_e_por_regra():
    texto = resumo_conjunto(_gerar({"P1": [_achado("MOD-006", "Product")]}))
    assert "Consultas: 3 (2 por regra, 1 por achado)" in texto
    assert "MOD-006 → learn:power-bi/guidance/star-schema#snowflake-dimensions" in texto
    assert "MOD-006: 2 consulta(s)" in texto


def test_main_sem_dados_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_avaliacao, "PASTA_PBIP", tmp_path / "nao-existe")
    assert main(["gerar"]) == 1
    assert "P1" in capsys.readouterr().err
```

Criar `tests/test_rag_avaliacao_real.py`:

```python
"""O conjunto de avaliação versionado, conferido contra a base e os PBIP reais.

O teste de congelamento é pulado sem `rag/store/` e `data/pbip/`, que não são
versionados. A coerência entre os dois arquivos versionados roda sempre.
"""

import pytest

from rag.avaliacao import (
    ARQUIVO_CONSULTAS,
    ARQUIVO_GABARITO,
    PASTA_PBIP,
    como_yaml,
    gerar_do_repositorio,
    ler_conjunto,
    ler_frases_marca,
)
from rag.coleta import ARQUIVO_REGISTRO

dados_reais = pytest.mark.skipif(
    not (ARQUIVO_REGISTRO.is_file() and PASTA_PBIP.is_dir()),
    reason="rag/store/ ou data/pbip/ ausente (não são versionados)",
)


def test_consultas_versionadas_usam_as_frases_do_gabarito():
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    frases = {f.id_regra: f.frase_marca for f in ler_frases_marca(ARQUIVO_GABARITO)}
    assert {g.id_regra: g.frase_marca for g in conjunto.gabaritos} == frases


def test_contagem_do_conjunto_versionado():
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    assert len(conjunto.gabaritos) == 9
    assert len(conjunto.consultas) == 62
    assert sum(c.tipo == "regra" for c in conjunto.consultas) == 9
    assert len({c.id for c in conjunto.consultas}) == 62


def test_mod003_e_mod006_caem_em_secoes_diferentes_da_mesma_pagina():
    gabaritos = {g.id_regra: g for g in ler_conjunto(ARQUIVO_CONSULTAS).gabaritos}
    assert gabaritos["MOD-003"].id_pagina == gabaritos["MOD-006"].id_pagina
    assert gabaritos["MOD-003"].ancora != gabaritos["MOD-006"].ancora


@dados_reais
def test_consultas_versionadas_sao_o_que_o_gerador_produz():
    assert ARQUIVO_CONSULTAS.read_text(encoding="utf-8") == como_yaml(gerar_do_repositorio()), (
        "eval/recuperacao/consultas.yaml divergiu — rode `python -m rag.avaliacao gerar` e revise o diff"
    )
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py tests/test_rag_avaliacao_real.py -q`
Expected: `ImportError: cannot import name 'achados_dos_projetos'` e `'PASTA_PBIP'`.

- [ ] **Step 2: Implementar**

Em `rag/avaliacao.py`, acrescentar aos imports:

```python
import argparse
import sys

from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.runner import ResultadoRegras
from core.rules.runner import avaliar as avaliar_regras
from core.rules.todas import REGISTRO
from rag.extracao import PASTA_TEXTOS, caminho_do_texto
```

Logo abaixo de `ARQUIVO_CONSULTAS`:

```python
PASTA_PBIP = RAIZ_REPO / "data" / "pbip"
PROJETOS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
"""O dataset de métricas. O P8 é estudo de caso (ADR-005) e fica fora."""
```

E no fim do arquivo:

```python
def _auditar_padrao(caminho: Path) -> ResultadoRegras:
    return avaliar_regras(ler_modelo(abrir_pbip(caminho).model_bim), REGISTRO)


def achados_dos_projetos(
    pasta: Path, auditar: Callable[[Path], ResultadoRegras] | None = None
) -> dict[str, list[Achado]]:
    """Roda as regras sobre P1–P7, na ordem. Uma regra com falha para tudo: gerar
    menos consultas em silêncio mudaria a régua sem aviso."""
    auditar = auditar or _auditar_padrao
    saida: dict[str, list[Achado]] = {}
    for codigo in PROJETOS:
        candidatos = sorted(pasta.glob(f"{codigo}_*")) if pasta.is_dir() else []
        if not candidatos:
            raise ErroDeAvaliacao(f"{codigo} não encontrado em {pasta} (data/ não é versionado)")
        resultado = auditar(candidatos[0])
        if resultado.regras_com_falha:
            falhas = ", ".join(f"{f.id_regra} ({f.erro})" for f in resultado.regras_com_falha)
            raise ErroDeAvaliacao(f"{codigo}: regra(s) com falha: {falhas}")
        saida[codigo] = resultado.achados
    return saida


def ler_pagina_extraida(id_pagina: str, pasta_textos: Path = PASTA_TEXTOS) -> PaginaExtraida:
    caminho = caminho_do_texto(pasta_textos, id_pagina)
    if not caminho.is_file():
        raise ErroDeAvaliacao(
            f"{id_pagina}: página não extraída — rode `python -m rag.coleta` e `python -m rag.extracao`"
        )
    return PaginaExtraida.model_validate_json(caminho.read_text(encoding="utf-8"))


def gerar_do_repositorio() -> ConjuntoAvaliacao:
    return gerar(
        metas=REGISTRO.metas(),
        frases=ler_frases_marca(ARQUIVO_GABARITO),
        ler_pagina=ler_pagina_extraida,
        achados_por_projeto=achados_dos_projetos(PASTA_PBIP),
    )


def resumo_conjunto(conjunto: ConjuntoAvaliacao) -> str:
    por_regra = Counter(c.id_regra for c in conjunto.consultas)
    n_regra = sum(c.tipo == "regra" for c in conjunto.consultas)
    return "\n".join(
        [
            f"Gabaritos: {len(conjunto.gabaritos)}",
            *(f"  {g.id_regra} → {g.id_pagina}#{g.ancora}" for g in conjunto.gabaritos),
            f"Consultas: {len(conjunto.consultas)} ({n_regra} por regra, "
            f"{len(conjunto.consultas) - n_regra} por achado)",
            *(f"  {regra}: {n} consulta(s)" for regra, n in sorted(por_regra.items())),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.avaliacao",
        description="Conjunto de avaliação da recuperação.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="deduz os gabaritos e gera eval/recuperacao/consultas.yaml")
    parser.parse_args(argv)
    try:
        conjunto = gerar_do_repositorio()
    except ErroDeAvaliacao as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    ARQUIVO_CONSULTAS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CONSULTAS.write_text(como_yaml(conjunto), encoding="utf-8", newline="\n")
    print(resumo_conjunto(conjunto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`gerar_do_repositorio` lê `PASTA_PBIP` e `ARQUIVO_GABARITO` como globais do módulo no momento da chamada, o que permite ao teste trocá-los com `monkeypatch`.

- [ ] **Step 3: Gerar o arquivo real**

Run: `.\.venv\Scripts\python.exe -m rag.avaliacao gerar`
Expected:
```
Gabaritos: 9
  DAX-001 → learn:dax/best-practices/dax-divide-function-operator#recommendations
  MOD-001 → learn:power-bi/guidance/auto-date-time#recommendations
  MOD-002 → learn:power-bi/guidance/relationships-bidirectional-filtering#bi-directional-relationship-guidance
  MOD-003 → learn:power-bi/guidance/star-schema#star-schema-relevance-to-power-bi-semantic-models
  MOD-005 → learn:power-bi/transform-model/desktop-date-tables#set-and-use-date-tables-in-power-bi-desktop
  MOD-006 → learn:power-bi/guidance/star-schema#snowflake-dimensions
  MOD-007 → learn:power-bi/guidance/relationships-one-to-one#recommendations
  PERF-001 → learn:power-bi/guidance/import-modeling-data-reduction#preference-for-custom-columns
  PERF-003 → learn:power-bi/transform-model/desktop-data-types#accuracy-of-number-type-calculations
Consultas: 62 (9 por regra, 53 por achado)
  DAX-001: 7 consulta(s)
  MOD-001: 2 consulta(s)
  MOD-002: 1 consulta(s)
  MOD-003: 8 consulta(s)
  MOD-005: 1 consulta(s)
  MOD-006: 4 consulta(s)
  MOD-007: 2 consulta(s)
  PERF-001: 20 consulta(s)
  PERF-003: 17 consulta(s)
```
Se algum número divergir: **parar** e investigar antes de seguir (superpowers:systematic-debugging) — a régua é o que se congela aqui.
Abrir `eval/recuperacao/consultas.yaml` e conferir à mão duas consultas: `P5/DAX-001/1` e `P1/MOD-007/1` (o `→` do relacionamento preservado).

- [ ] **Step 4: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao.py tests/test_rag_avaliacao_real.py -q`
Expected: todos passam (o de congelamento roda, porque os dados estão presentes).
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 5: Commit e push do código e do conjunto**

```bash
git add rag/avaliacao.py eval/recuperacao/consultas.yaml tests/test_rag_avaliacao.py tests/test_rag_avaliacao_real.py
git commit -m "feat(rag): python -m rag.avaliacao gerar e o conjunto congelado — 9 gabaritos, 62 consultas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

- [ ] **Step 6: Registros**

- `README.md`, na seção "Catálogo de fontes da RAG", depois do bloco de `rag.extracao`:

````markdown
```powershell
python -m rag.avaliacao gerar     # gera eval/recuperacao/consultas.yaml (precisa de rag/store/ e data/pbip/)
```

`eval/recuperacao/gabarito.yaml` (frases-marca) é escrito à mão; `consultas.yaml` é gerado — não editar à mão.
````

- `docs/project/status.md`:
  - Seção 3, tabela "O que já funciona": acrescentar `| Conjunto de avaliação da recuperação (`python -m rag.avaliacao gerar`) | 9 gabaritos com a seção âncora deduzida da base, 62 consultas (9 por regra, 53 por achado de P1–P7) congeladas em `eval/recuperacao/consultas.yaml`; métricas acerto@K, Precision@K e MRR@10, com a macro por regra como número que decide |`.
  - Seção 8, passo 1: `| 1 | **Medir chunking e embeddings com o conjunto de avaliação** | A régua está congelada (11/10/2026). A medição decide o chunking, o tamanho do trecho e se a busca híbrida entra no MVP (emenda de 09/10 da ADR-002) |`.
  - Número de testes nas seções 1, 3 e 9: o da última execução.
- `docs/project/progress-log.md`: nova entrada "11/10/2026 — Fase 3 — conjunto de avaliação da recuperação" com: as 4 decisões do Fred (consulta montada pelo pipeline, relevância pela frase-marca, escopo conjunto + métricas, gerador versionado); a tabela de seções âncora deduzidas; as 62 consultas por regra e por tipo; MOD-002 e MOD-005 só com a consulta por regra; a macro por regra como número que decide; o número de testes; e **Próximo passo:** brainstorming da medição de chunking e embeddings.
- Página do orientador: na seção 5, um parágrafo curto "A régua da recuperação, congelada em 11/10" (o gabarito deduzido, as 62 consultas, a macro por regra e por que ela decide); na seção 9, passo 1 vira "Medir chunking e embeddings com a régua"; contagem de testes no meta-row, no cartão de números e na seção 10. Republicar no mesmo endereço.

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

```bash
git add README.md docs/project
git commit -m "docs: conjunto de avaliacao da recuperacao congelado — 9 gabaritos, 62 consultas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```
