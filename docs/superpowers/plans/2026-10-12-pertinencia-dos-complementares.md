# Pertinência dos complementares e a escolha da busca — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** medir a pertinência dos trechos complementares que BM25, densa e combinada entregam ao LLM, com uma planilha cega julgada pelo Fred, e escolher a busca por uma regra fixada antes de medir.

**Architecture:** a seleção de complementares sai de `montar_contexto` para uma função pura reusada pela medição. `rag/complementares.py` simula as três buscas sobre os trechos do índice, forma o *pool* por (regra, seção), calcula a precisão e decide. `rag/pertinencia.py` grava e lê a planilha e o CSV. `rag/indice.py construir` ganha `--busca`, que só vale se casar com a decisão mais recente.

**Tech Stack:** Python 3.11, Pydantic 2, numpy, rank-bm25, sentence-transformers (`bge-small-en-v1.5`, offline), openpyxl, pytest.

**Spec:** `docs/superpowers/specs/2026-10-12-pertinencia-dos-complementares-design.md`

## Global Constraints

- Tudo em português do Brasil: código, nomes, testes, mensagens, commits.
- Nenhuma dependência nova.
- Seleção dos complementares idêntica à da geração: `K_BUSCA = 10`, `MAX_COMPLEMENTARES = 4`, `ORCAMENTO_PALAVRAS = 1800` (`core/analise/contexto.py`).
- Chave do pool: `<id_regra>|<id_pagina>#<ancora>`.
- Vereditos exatamente: `pertinente`, `não pertinente`, `indeterminado`; justificativa obrigatória em `indeterminado`.
- Planilha em `eval/gabarito/pertinencia-complementares.xlsx` (fora do Git); CSV em `eval/recuperacao/pertinencia.csv` (versionado); resultado em `eval/results/complementares-<AAAA-MM-DD>.json`.
- Regra de decisão: densa ou combinada vence só com macro ≥ macro do BM25 + `MARGEM = 0.10`; se as duas passarem, maior macro; empate pela ordem `bm25`, `densa`, `hibrida`.
- Complementar sem julgamento no CSV → erro, sem métrica.
- Saída de console em ASCII.
- Rodar o que carrega o modelo com `HF_HUB_OFFLINE=1` e `HF_HOME=D:\dev\hf-cache`.
- Testes: `.\.venv\Scripts\python.exe -m pytest -q`; os que dependem da base coletada são pulados sem ela.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push autorizado na branch `fase3-busca-complementares`.

## Review Focus

- **Seção dividida em várias partes** (vários trechos com o mesmo `id_pagina#ancora`) — vira uma única linha do pool, e qualquer parte dela conta com o veredito da seção (teste na Tarefa 2).
- **Consulta cujos 10 resultados estouram o orçamento ou são só a âncora** — zero complementares; não entra na média e é contada à parte, sem divisão por zero (teste na Tarefa 3).
- **Veredito digitado com variação** (`Pertinente`, ` pertinente `) — recusado com aba e linha, sem normalizar (teste na Tarefa 4).
- **`--busca` que não casa com a decisão mais recente, ou sem resultado de complementares** — `construir` recusa com mensagem, sem tocar no índice (teste na Tarefa 6).
- **Cache de embeddings ausente ou de outros textos** — `medir` e `gerar` falham indicando `python -m rag.medicao`, sem recalcular os vetores em silêncio (teste na Tarefa 5).

---

### Task 1: `escolher_complementares` — a seleção da geração como função pura

**Files:**
- Modify: `core/analise/contexto.py`
- Test: `tests/test_analise_contexto.py` (acrescentar)

**Interfaces:**
- Consumes: `TrechoIndexado` (`rag.chunking`).
- Produces: `escolher_complementares(ancora: TrechoIndexado, resultados: list[TrechoIndexado]) -> list[TrechoIndexado]` (só os complementares, sem a âncora).

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_analise_contexto.py`, trocar o import de `core.analise.contexto` por `from core.analise.contexto import ErroDeContexto, carregar_gabaritos, escolher_complementares, montar_contexto, verificar_ancoras` e acrescentar ao fim:

```python
def test_escolher_complementares_pula_a_ancora_e_para_em_quatro():
    outros = [trecho_indexado(f"learn:p{i}", f"texto {i}") for i in range(6)]
    escolhidos = escolher_complementares(TRECHO_ANCORA, [TRECHO_ANCORA, *outros])
    assert escolhidos == outros[:4]


def test_escolher_complementares_respeita_o_orcamento_contando_a_ancora():
    grande = trecho_indexado("learn:grande", "x " * 1790)
    pequeno = trecho_indexado("learn:pequeno", "y z")
    escolhidos = escolher_complementares(TRECHO_ANCORA, [grande, pequeno])
    assert escolhidos == [pequeno]


def test_escolher_complementares_sem_resultado_util_devolve_lista_vazia():
    assert escolher_complementares(TRECHO_ANCORA, [TRECHO_ANCORA]) == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_contexto.py -q`
Expected: erro de coleta — `ImportError: cannot import name 'escolher_complementares'`.

- [ ] **Step 3: Implementar**

Em `core/analise/contexto.py`, acrescentar antes de `montar_contexto`:

```python
def escolher_complementares(ancora: TrechoIndexado, resultados: list[TrechoIndexado]) -> list[TrechoIndexado]:
    """Os complementares que entram no contexto, na ordem da busca: sem a âncora, até
    `MAX_COMPLEMENTARES`, e só os que cabem no orçamento junto com ela. É a mesma função
    que a medição dos complementares usa — a régua mede o que o modelo recebe."""
    escolhidos: list[TrechoIndexado] = []
    total = _palavras(ancora)
    for trecho in resultados:
        if len(escolhidos) >= MAX_COMPLEMENTARES:
            break
        if trecho.id == ancora.id or total + _palavras(trecho) > ORCAMENTO_PALAVRAS:
            continue
        escolhidos.append(trecho)
        total += _palavras(trecho)
    return escolhidos
```

E trocar o corpo de `montar_contexto` por:

```python
def montar_contexto(meta: RegraMeta, achado: Achado, base: BaseRag, gabarito: Gabarito) -> list[TrechoDeContexto]:
    ancora = _trecho_ancora(base, gabarito)
    escolhidos = [ancora, *escolher_complementares(ancora, base.buscar(montar_consulta(meta, achado), K_BUSCA))]
    return [
        _para_contexto(t, numero, "ancora" if numero == 1 else "busca")
        for numero, t in enumerate(escolhidos, start=1)
    ]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_contexto.py tests/test_auditoria.py -q`
Expected: todos passam — os testes antigos de `montar_contexto` (no máximo quatro, orçamento, âncora não repetida) continuam verdes.

- [ ] **Step 5: Commit**

```bash
git add core/analise/contexto.py tests/test_analise_contexto.py
git commit -m "refactor(analise): escolher_complementares como funcao pura"
```

---

### Task 2: As três buscas e o pool por (regra, seção)

**Files:**
- Create: `rag/complementares.py`
- Test: `tests/test_rag_complementares.py`

**Interfaces:**
- Consumes: `escolher_complementares`, `K_BUSCA` (Tarefa 1); `Consulta` (`rag.avaliacao`); `TrechoIndexado`.
- Produces: `Ranqueador = Callable[[str, int], list[int]]`; `TIPOS = ("bm25", "densa", "hibrida")`; `ErroDeComplementares`; `id_da_secao(id_regra: str, t: TrechoIndexado) -> str`; `ConsultaMedida(id: str, id_regra: str, secoes: list[str])`; `ItemPool(id: str, id_regra: str, trecho: TrechoIndexado)`; `complementares_por_busca(consultas: list[Consulta], ancoras: dict[str, TrechoIndexado], trechos: list[TrechoIndexado], ranqueadores: dict[str, Ranqueador]) -> dict[str, list[ConsultaMedida]]`; `formar_pool(...)` com a mesma assinatura, devolvendo `list[ItemPool]` ordenada por `id`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_rag_complementares.py`:

```python
"""Complementares: as três buscas, o pool, a precisão e a decisão."""

from fabricas_analise import trecho_indexado

from rag.avaliacao import Consulta
from rag.complementares import complementares_por_busca, formar_pool, id_da_secao

ANCORA = trecho_indexado("learn:ancora", "auto date time")
TRECHOS = [
    ANCORA,
    trecho_indexado("learn:a", "a", ancora="s1", parte=1),
    trecho_indexado("learn:a", "a2", ancora="s1", parte=2),
    trecho_indexado("learn:b", "b"),
    trecho_indexado("learn:c", "c"),
]
CONSULTAS = [
    Consulta(id="REGRA/MOD-001", tipo="regra", id_regra="MOD-001", texto="q1"),
    Consulta(id="P1/MOD-001/1", tipo="achado", projeto="P1", id_regra="MOD-001", objeto="X", texto="q2"),
]


def _fixo(ordem):
    return lambda consulta, k: ordem[:k]


RANQUEADORES = {"bm25": _fixo([0, 1, 2]), "densa": _fixo([3, 0]), "hibrida": _fixo([4, 1])}


def test_id_da_secao_junta_regra_pagina_e_ancora():
    assert id_da_secao("MOD-001", TRECHOS[1]) == "MOD-001|learn:a#s1"


def test_complementares_por_busca_usa_a_selecao_da_geracao():
    medidas = complementares_por_busca(CONSULTAS, {"MOD-001": ANCORA}, TRECHOS, RANQUEADORES)
    assert [m.secoes for m in medidas["bm25"]] == [["MOD-001|learn:a#s1", "MOD-001|learn:a#s1"]] * 2
    assert [m.secoes for m in medidas["densa"]] == [["MOD-001|learn:b#s"]] * 2


def test_pool_tem_uma_linha_por_secao_mesmo_com_varias_partes():
    pool = formar_pool(CONSULTAS, {"MOD-001": ANCORA}, TRECHOS, RANQUEADORES)
    assert [p.id for p in pool] == ["MOD-001|learn:a#s1", "MOD-001|learn:b#s", "MOD-001|learn:c#s"]
    assert pool[0].trecho.id == "learn:a#s1/1"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.complementares'`.

- [ ] **Step 3: Implementar**

`rag/complementares.py`:

```python
"""Pertinência dos trechos complementares e a escolha da busca (semana 8).

Desenho: `docs/superpowers/specs/2026-10-12-pertinencia-dos-complementares-design.md`.
A régua de 11/10 mede se a âncora é recuperada; desde a semana 7 a âncora entra no
contexto sem depender da busca. Esta régua mede o que sobra para a busca: se os trechos
2 a 5 que o LLM recebe são pertinentes ao achado.
"""

from collections.abc import Callable

from pydantic import BaseModel

from core.analise.contexto import K_BUSCA, escolher_complementares
from rag.avaliacao import Consulta
from rag.chunking import TrechoIndexado

Ranqueador = Callable[[str, int], list[int]]
"""Consulta e k → índices em `trechos`, do mais ao menos relevante."""
TIPOS = ("bm25", "densa", "hibrida")


class ErroDeComplementares(Exception):
    """A medição não pode seguir sem perder algo em silêncio."""


class ConsultaMedida(BaseModel):
    id: str
    id_regra: str
    secoes: list[str]
    """Uma entrada por complementar entregue, na ordem; partes da mesma seção repetem o id."""


class ItemPool(BaseModel):
    id: str
    id_regra: str
    trecho: TrechoIndexado
    """A primeira parte da seção que alguma busca trouxe: é o que a planilha mostra."""


def id_da_secao(id_regra: str, t: TrechoIndexado) -> str:
    return f"{id_regra}|{t.id_pagina}#{t.ancora}"


def _escolhidos(
    consulta: Consulta, ancoras: dict[str, TrechoIndexado], trechos: list[TrechoIndexado], ranquear: Ranqueador
) -> list[TrechoIndexado]:
    resultados = [trechos[i] for i in ranquear(consulta.texto, K_BUSCA)]
    return escolher_complementares(ancoras[consulta.id_regra], resultados)


def complementares_por_busca(
    consultas: list[Consulta],
    ancoras: dict[str, TrechoIndexado],
    trechos: list[TrechoIndexado],
    ranqueadores: dict[str, Ranqueador],
) -> dict[str, list[ConsultaMedida]]:
    return {
        tipo: [
            ConsultaMedida(
                id=c.id,
                id_regra=c.id_regra,
                secoes=[id_da_secao(c.id_regra, t) for t in _escolhidos(c, ancoras, trechos, ranquear)],
            )
            for c in consultas
        ]
        for tipo, ranquear in ranqueadores.items()
    }


def formar_pool(
    consultas: list[Consulta],
    ancoras: dict[str, TrechoIndexado],
    trechos: list[TrechoIndexado],
    ranqueadores: dict[str, Ranqueador],
) -> list[ItemPool]:
    """União, por regra, das seções que as buscas escolhem — o *pooling* do TREC."""
    pool: dict[str, ItemPool] = {}
    for ranquear in ranqueadores.values():
        for c in consultas:
            for t in _escolhidos(c, ancoras, trechos, ranquear):
                chave = id_da_secao(c.id_regra, t)
                pool.setdefault(chave, ItemPool(id=chave, id_regra=c.id_regra, trecho=t))
    return [pool[chave] for chave in sorted(pool)]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add rag/complementares.py tests/test_rag_complementares.py
git commit -m "feat(rag): complementares das tres buscas e pool por secao"
```

---

### Task 3: Precisão dos complementares e a regra de decisão

**Files:**
- Modify: `rag/complementares.py`
- Test: `tests/test_rag_complementares.py` (acrescentar)

**Interfaces:**
- Consumes: `ConsultaMedida`, `TIPOS` (Tarefa 2).
- Produces: `MARGEM = 0.10`; `Precisao(principal, piso, teto: float | None)`; `MedidaBusca(macro: Precisao, micro: Precisao, por_regra: dict[str, Precisao], sem_complementar: int)`; `medir_busca(medidas: list[ConsultaMedida], julgamentos: dict[str, str]) -> MedidaBusca`; `DecisaoBusca(vencedora: str, justificativa: str)`; `decidir_busca(macros: dict[str, float | None]) -> DecisaoBusca`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao import de `rag.complementares` em `tests/test_rag_complementares.py`: `ConsultaMedida, ErroDeComplementares, decidir_busca, medir_busca`; acrescentar `import pytest` no topo; e ao fim:

```python
JULGAMENTOS = {"A|p#1": "pertinente", "A|p#2": "não pertinente", "A|p#3": "indeterminado", "B|p#1": "pertinente"}


def _m(id_, regra, secoes):
    return ConsultaMedida(id=id_, id_regra=regra, secoes=secoes)


def test_precisao_por_consulta_regra_macro_e_micro():
    medidas = [
        _m("1", "A", ["A|p#1", "A|p#2"]),           # 1/2
        _m("2", "A", ["A|p#1", "A|p#1", "A|p#3"]),  # principal 2/2; piso 2/3; teto 3/3
        _m("3", "B", ["B|p#1"]),                    # 1/1
    ]
    r = medir_busca(medidas, JULGAMENTOS)
    assert r.por_regra["A"].principal == pytest.approx((0.5 + 1.0) / 2)
    assert r.por_regra["A"].piso == pytest.approx((0.5 + 2 / 3) / 2)
    assert r.por_regra["A"].teto == pytest.approx((0.5 + 1.0) / 2)
    assert r.macro.principal == pytest.approx((0.75 + 1.0) / 2)
    assert r.micro.principal == pytest.approx(4 / 5)


def test_consulta_sem_complementar_nao_entra_na_media_e_e_contada():
    r = medir_busca([_m("1", "A", []), _m("2", "A", ["A|p#1"])], JULGAMENTOS)
    assert r.sem_complementar == 1
    assert r.por_regra["A"].principal == 1.0


def test_regra_so_com_consultas_vazias_fica_none_e_macro_a_ignora():
    r = medir_busca([_m("1", "A", []), _m("2", "B", ["B|p#1"])], JULGAMENTOS)
    assert r.por_regra["A"].principal is None
    assert r.macro.principal == 1.0


def test_complementar_sem_julgamento_aborta():
    with pytest.raises(ErroDeComplementares, match="A\\|p#9"):
        medir_busca([_m("1", "A", ["A|p#9"])], JULGAMENTOS)


@pytest.mark.parametrize(
    ("macros", "vencedora"),
    [
        ({"bm25": 0.50, "densa": 0.59, "hibrida": 0.55}, "bm25"),
        ({"bm25": 0.50, "densa": 0.55, "hibrida": 0.62}, "hibrida"),
        ({"bm25": 0.50, "densa": 0.70, "hibrida": 0.65}, "densa"),
        ({"bm25": 0.50, "densa": 0.65, "hibrida": 0.65}, "densa"),
        ({"bm25": 0.50, "densa": 0.60, "hibrida": None}, "densa"),
    ],
)
def test_regra_de_decisao(macros, vencedora):
    assert decidir_busca(macros).vencedora == vencedora


def test_decisao_sem_macro_do_bm25_aborta():
    with pytest.raises(ErroDeComplementares, match="bm25"):
        decidir_busca({"bm25": None, "densa": 0.9, "hibrida": 0.9})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares.py -q`
Expected: erro de coleta — `cannot import name 'decidir_busca'`.

- [ ] **Step 3: Implementar**

Acrescentar ao fim de `rag/complementares.py` (e `from statistics import mean` aos imports):

```python
MARGEM = 0.10
"""Fixada antes de medir: uma alternativa só substitui o BM25 se ganhar por isto na macro."""
_EPS = 1e-9


class Precisao(BaseModel):
    principal: float | None
    piso: float | None
    teto: float | None


class MedidaBusca(BaseModel):
    macro: Precisao
    micro: Precisao
    por_regra: dict[str, Precisao]
    sem_complementar: int
    """Consultas sem nenhum complementar: não entram na média, mas aparecem."""


class DecisaoBusca(BaseModel):
    vencedora: str
    justificativa: str


def _contagem(secoes: list[str], julgamentos: dict[str, str]) -> tuple[int, int, int]:
    faltando = sorted({s for s in secoes if s not in julgamentos})
    if faltando:
        raise ErroDeComplementares(
            f"complementar sem julgamento — o pool mudou desde a planilha: {', '.join(faltando)}"
        )
    vereditos = [julgamentos[s] for s in secoes]
    return vereditos.count("pertinente"), vereditos.count("não pertinente"), vereditos.count("indeterminado")


def _precisao(pert: int, nao: int, ind: int) -> Precisao:
    total = pert + nao + ind
    return Precisao(
        principal=pert / (pert + nao) if pert + nao else None,
        piso=pert / total if total else None,
        teto=(pert + ind) / total if total else None,
    )


def _media(valores: list[float | None]) -> float | None:
    presentes = [v for v in valores if v is not None]
    return mean(presentes) if presentes else None


def _media_precisoes(precisoes: list[Precisao]) -> Precisao:
    return Precisao(
        principal=_media([p.principal for p in precisoes]),
        piso=_media([p.piso for p in precisoes]),
        teto=_media([p.teto for p in precisoes]),
    )


def medir_busca(medidas: list[ConsultaMedida], julgamentos: dict[str, str]) -> MedidaBusca:
    por_consulta: dict[str, list[Precisao]] = {}
    soma = [0, 0, 0]
    vazias = 0
    for m in medidas:
        por_consulta.setdefault(m.id_regra, [])
        if not m.secoes:
            vazias += 1
            continue
        contagem = _contagem(m.secoes, julgamentos)
        soma = [a + b for a, b in zip(soma, contagem)]
        por_consulta[m.id_regra].append(_precisao(*contagem))
    por_regra = {regra: _media_precisoes(lista) for regra, lista in sorted(por_consulta.items())}
    return MedidaBusca(
        macro=_media_precisoes(list(por_regra.values())),
        micro=_precisao(*soma),
        por_regra=por_regra,
        sem_complementar=vazias,
    )


def decidir_busca(macros: dict[str, float | None]) -> DecisaoBusca:
    base = macros.get("bm25")
    if base is None:
        raise ErroDeComplementares("sem macro do bm25 — nada contra o que comparar")
    candidatas = [
        t for t in ("densa", "hibrida") if macros.get(t) is not None and macros[t] >= base + MARGEM - _EPS
    ]
    if not candidatas:
        return DecisaoBusca(
            vencedora="bm25",
            justificativa=f"nenhuma alternativa supera a macro do bm25 ({base:.3f}) por {MARGEM:.2f}; fica o bm25",
        )
    vencedora = max(candidatas, key=lambda t: (round(macros[t], 9), -TIPOS.index(t)))
    return DecisaoBusca(
        vencedora=vencedora,
        justificativa=(
            f"{vencedora} ({macros[vencedora]:.3f}) supera a macro do bm25 ({base:.3f}) por {MARGEM:.2f} ou mais"
            + ("; empate resolvido pela mais simples" if len(candidatas) == 2 and abs(macros["densa"] - macros["hibrida"]) < _EPS else "")
        ),
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares.py -q`
Expected: 13 passed (3 da Tarefa 2 + 10 novos, contando os 5 parametrizados).

- [ ] **Step 5: Commit**

```bash
git add rag/complementares.py tests/test_rag_complementares.py
git commit -m "feat(rag): precisao dos complementares e regra de decisao da busca"
```

---

### Task 4: Planilha cega de pertinência e o CSV

**Files:**
- Create: `rag/pertinencia.py`
- Test: `tests/test_rag_pertinencia.py`

**Interfaces:**
- Consumes: `ItemPool`, `ErroDeComplementares` (Tarefa 2).
- Produces: `VEREDITOS = ("pertinente", "não pertinente", "indeterminado")`; `PERGUNTA: str`; `LINHA_CABECALHO = 6`; `LinhaPertinencia(id, id_regra, id_pagina, ancora, veredito, justificativa)`; `Problema(aba: str, linha: int | None, id: str, motivo: str)`; `gerar_planilha(pool: list[ItemPool], ancoras: dict[str, TrechoIndexado], destino: Path) -> None`; `ler_planilha(caminho: Path) -> list[tuple[str, int, LinhaPertinencia]]`; `validar(lidas, pool: list[ItemPool], parcial: bool) -> list[Problema]`; `progresso(lidas) -> dict[str, tuple[int, int]]`; `gravar_csv(linhas: list[LinhaPertinencia], destino: Path) -> None`; `ler_csv(caminho: Path) -> dict[str, str]` (id → veredito).

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_rag_pertinencia.py`:

```python
"""Planilha cega de pertinência dos complementares."""

import pytest
from fabricas_analise import trecho_indexado
from openpyxl import load_workbook

from rag.complementares import ErroDeComplementares, ItemPool
from rag.pertinencia import LINHA_CABECALHO, gerar_planilha, gravar_csv, ler_csv, ler_planilha, progresso, validar

ANCORAS = {"PERF-001": trecho_indexado("learn:reducao", "Prefer custom columns in Power Query.")}
POOL = [
    ItemPool(id="PERF-001|dax:rankx#s", id_regra="PERF-001", trecho=trecho_indexado("dax:rankx", "RANKX returns...")),
    ItemPool(id="PERF-001|learn:pq#s", id_regra="PERF-001", trecho=trecho_indexado("learn:pq", "=Custom column " + "z" * 900)),
]


def _gerar(tmp_path):
    destino = tmp_path / "p.xlsx"
    gerar_planilha(POOL, ANCORAS, destino)
    return destino


def _preencher(destino, vereditos):
    livro = load_workbook(destino)
    aba = livro["PERF-001"]
    cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
    cv = cabecalho.index("veredito") + 1
    for r in range(LINHA_CABECALHO + 1, aba.max_row + 1):
        id_ = aba.cell(row=r, column=1).value
        if id_ in vereditos:
            aba.cell(row=r, column=cv).value = vereditos[id_][0]
            aba.cell(row=r, column=cv + 1).value = vereditos[id_][1]
    livro.save(destino)


def test_uma_aba_por_regra_com_a_ancora_no_topo_e_cega(tmp_path):
    livro = load_workbook(_gerar(tmp_path))
    assert livro.sheetnames == ["Instruções", "PERF-001"]
    aba = livro["PERF-001"]
    assert "Prefer custom columns" in aba["A3"].value
    textos = " ".join(str(c.value).lower() for linha in aba.iter_rows() for c in linha if c.value)
    for proibido in ("bm25", "densa", "hibrida", "híbrida", "combinada"):
        assert proibido not in textos


def test_texto_que_comeca_com_igual_fica_texto_e_inicio_e_cortado(tmp_path):
    aba = load_workbook(_gerar(tmp_path))["PERF-001"]
    cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
    celula = aba.cell(row=LINHA_CABECALHO + 2, column=cabecalho.index("inicio_do_texto") + 1)
    assert celula.data_type == "s" and celula.value.startswith("=Custom")
    assert len(celula.value) <= 600 + len(" […]")


def test_recusa_sobrescrever(tmp_path):
    destino = _gerar(tmp_path)
    with pytest.raises(ErroDeComplementares, match="já existe"):
        gerar_planilha(POOL, ANCORAS, destino)


def test_completa_valida_e_csv_ida_e_volta(tmp_path):
    destino = _gerar(tmp_path)
    _preencher(destino, {POOL[0].id: ("não pertinente", None), POOL[1].id: ("pertinente", None)})
    lidas = ler_planilha(destino)
    assert validar(lidas, POOL, parcial=False) == []
    csv = tmp_path / "pertinencia.csv"
    gravar_csv([l for _, _, l in lidas], csv)
    assert ler_csv(csv) == {POOL[0].id: "não pertinente", POOL[1].id: "pertinente"}


@pytest.mark.parametrize("valor", ["Pertinente", " pertinente ", "talvez"])
def test_veredito_fora_da_lista_e_problema(tmp_path, valor):
    destino = _gerar(tmp_path)
    _preencher(destino, {POOL[0].id: (valor, None), POOL[1].id: ("pertinente", None)})
    assert [(p.id, "fora da lista" in p.motivo) for p in validar(ler_planilha(destino), POOL, parcial=False)] == [(POOL[0].id, True)]


def test_indeterminado_exige_justificativa_e_parcial_mostra_progresso(tmp_path):
    destino = _gerar(tmp_path)
    _preencher(destino, {POOL[0].id: ("indeterminado", None)})
    lidas = ler_planilha(destino)
    assert [(p.id, p.motivo) for p in validar(lidas, POOL, parcial=True)] == [(POOL[0].id, "sem justificativa")]
    assert progresso(lidas) == {"PERF-001": (1, 2)}


def test_id_faltando_e_sobrando(tmp_path):
    destino = _gerar(tmp_path)
    _preencher(destino, {POOL[0].id: ("pertinente", None), POOL[1].id: ("pertinente", None)})
    novo = ItemPool(id="PERF-001|learn:x#s", id_regra="PERF-001", trecho=trecho_indexado("learn:x", "x"))
    motivos = {(p.id, p.motivo) for p in validar(ler_planilha(destino), [POOL[0], novo], parcial=False)}
    assert motivos == {(POOL[1].id, "não está mais no pool"), (novo.id, "seção ausente da planilha")}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_pertinencia.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.pertinencia'`.

- [ ] **Step 3: Implementar**

`rag/pertinencia.py`:

```python
"""A planilha cega de pertinência dos complementares e o CSV oficial.

Mesmo formato do gabarito das regras (`gabarito/planilha.py`): uma aba por regra,
protegida, com só as colunas de anotação livres e lista suspensa no veredito. Nenhuma
célula diz qual busca trouxe a seção.
"""

import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import BaseModel

from rag.chunking import TrechoIndexado
from rag.complementares import ErroDeComplementares, ItemPool

VEREDITOS = ("pertinente", "não pertinente", "indeterminado")
PERGUNTA = "Esta seção ajuda a explicar o problema da regra ou a corrigi-lo, na mesma linha da âncora?"
LINHA_CABECALHO = 6
COLUNAS = ("id", "pagina", "secao", "titulo", "caminho", "inicio_do_texto", "url", "veredito", "justificativa")
EDITAVEIS = ("veredito", "justificativa")
LIMITE_ANCORA = 1500
LIMITE_INICIO = 600
LARGURAS = {"id": 40, "pagina": 30, "secao": 22, "titulo": 30, "caminho": 30, "inicio_do_texto": 80, "url": 30,
            "veredito": 16, "justificativa": 50}
CAMPOS_CSV = ("id", "id_regra", "id_pagina", "ancora", "veredito", "justificativa")
INSTRUCOES = [
    "Pertinência dos trechos complementares — protocolo de anotação",
    "",
    "1. Em cada aba, a âncora da regra está no topo: é a passagem que sustenta o achado.",
    "2. Julgue cada seção pela pergunta da aba: ela ajuda a explicar ou corrigir o problema da regra, na mesma linha da âncora?",
    "3. veredito: 'pertinente', 'não pertinente' ou 'indeterminado' (use a lista suspensa).",
    "4. 'indeterminado' pede justificativa.",
    "5. A planilha não diz qual busca trouxe a seção, de propósito: o julgamento é cego.",
    "6. Para conferir o andamento: python -m rag.complementares importar --parcial",
]


class LinhaPertinencia(BaseModel):
    id: str
    id_regra: str
    id_pagina: str
    ancora: str
    veredito: str | None = None
    justificativa: str | None = None


class Problema(BaseModel):
    aba: str
    linha: int | None
    id: str
    motivo: str


def _cortar(texto: str, limite: int) -> str:
    return texto if len(texto) <= limite else texto[:limite] + " […]"


def _escrever(aba, linha: int, coluna: int, valor: str):
    celula = aba.cell(row=linha, column=coluna, value=ILLEGAL_CHARACTERS_RE.sub("", valor))
    celula.data_type = "s"  # texto, sempre: um trecho que começa com `=` viraria fórmula
    celula.alignment = Alignment(wrap_text=True, vertical="top")
    return celula


def _aba(livro: Workbook, id_regra: str, itens: list[ItemPool], ancora: TrechoIndexado) -> None:
    aba = livro.create_sheet(id_regra)
    aba["A1"] = PERGUNTA
    aba["A1"].font = Font(bold=True)
    aba["A2"] = f"Âncora: {ancora.titulo_pagina} › {ancora.caminho} ({ancora.url})"
    _escrever(aba, 3, 1, _cortar(ancora.texto, LIMITE_ANCORA))
    for coluna, nome in enumerate(COLUNAS, start=1):
        aba.cell(row=LINHA_CABECALHO, column=coluna, value=nome).font = Font(bold=True)
        aba.column_dimensions[aba.cell(row=LINHA_CABECALHO, column=coluna).column_letter].width = LARGURAS[nome]
    for linha, item in enumerate(itens, start=LINHA_CABECALHO + 1):
        t = item.trecho
        valores = (item.id, t.id_pagina, t.ancora, t.titulo_pagina, t.caminho, _cortar(t.texto, LIMITE_INICIO), t.url)
        for coluna, valor in enumerate(valores, start=1):
            _escrever(aba, linha, coluna, valor)
        for nome in EDITAVEIS:
            aba.cell(row=linha, column=COLUNAS.index(nome) + 1).protection = Protection(locked=False)
    if itens:
        letra = aba.cell(row=LINHA_CABECALHO, column=COLUNAS.index("veredito") + 1).column_letter
        validacao = DataValidation(type="list", formula1=f'"{",".join(VEREDITOS)}"', allow_blank=True)
        validacao.add(f"{letra}{LINHA_CABECALHO + 1}:{letra}{LINHA_CABECALHO + len(itens)}")
        aba.add_data_validation(validacao)
    aba.freeze_panes = aba.cell(row=LINHA_CABECALHO + 1, column=2)
    aba.protection.formatColumns = False
    aba.protection.formatRows = False
    aba.protection.sheet = True


def gerar_planilha(pool: list[ItemPool], ancoras: dict[str, TrechoIndexado], destino: Path) -> None:
    if destino.exists():
        raise ErroDeComplementares(f"{destino} já existe e pode ter vereditos — apague ou renomeie antes de gerar outra")
    livro = Workbook()
    instrucoes = livro.active
    instrucoes.title = "Instruções"
    for i, linha in enumerate(INSTRUCOES, start=1):
        instrucoes.cell(row=i, column=1, value=linha)
    for id_regra in sorted({item.id_regra for item in pool}):
        _aba(livro, id_regra, [item for item in pool if item.id_regra == id_regra], ancoras[id_regra])
    destino.parent.mkdir(parents=True, exist_ok=True)
    livro.save(destino)


def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor)
    return texto if texto.strip() else None


def ler_planilha(caminho: Path) -> list[tuple[str, int, LinhaPertinencia]]:
    livro = load_workbook(caminho, read_only=True)
    lidas: list[tuple[str, int, LinhaPertinencia]] = []
    for aba in livro.worksheets[1:]:
        linhas = list(aba.iter_rows(min_row=LINHA_CABECALHO, values_only=True))
        if not linhas:
            continue
        cabecalho = list(linhas[0])
        faltando = [nome for nome in COLUNAS if nome not in cabecalho]
        if faltando:
            livro.close()
            raise ErroDeComplementares(f"aba {aba.title}: coluna(s) ausente(s) no cabeçalho: {', '.join(faltando)}")
        pos = {nome: cabecalho.index(nome) for nome in COLUNAS}
        for numero, valores in enumerate(linhas[1:], start=LINHA_CABECALHO + 1):
            if valores[pos["id"]] is None:
                continue
            lidas.append((aba.title, numero, LinhaPertinencia(
                id=str(valores[pos["id"]]),
                id_regra=aba.title,
                id_pagina=str(valores[pos["pagina"]]),
                ancora=str(valores[pos["secao"]]),
                veredito=_texto(valores[pos["veredito"]]),
                justificativa=_texto(valores[pos["justificativa"]]),
            )))
    livro.close()
    return lidas


def validar(lidas: list[tuple[str, int, LinhaPertinencia]], pool: list[ItemPool], parcial: bool) -> list[Problema]:
    """Não normaliza: um veredito fora da lista é apontado, não corrigido em silêncio."""
    problemas: list[Problema] = []
    for aba, numero, linha in lidas:
        if linha.veredito is None:
            if not parcial:
                problemas.append(Problema(aba=aba, linha=numero, id=linha.id, motivo="sem veredito"))
            continue
        if linha.veredito not in VEREDITOS:
            problemas.append(Problema(aba=aba, linha=numero, id=linha.id, motivo=f"veredito fora da lista: {linha.veredito!r}"))
        elif linha.veredito == "indeterminado" and linha.justificativa is None:
            problemas.append(Problema(aba=aba, linha=numero, id=linha.id, motivo="sem justificativa"))
    na_planilha = {linha.id: (aba, numero) for aba, numero, linha in lidas}
    atuais = {item.id: item for item in pool}
    for id_, (aba, numero) in na_planilha.items():
        if id_ not in atuais:
            problemas.append(Problema(aba=aba, linha=numero, id=id_, motivo="não está mais no pool"))
    for id_, item in atuais.items():
        if id_ not in na_planilha:
            problemas.append(Problema(aba=item.id_regra, linha=None, id=id_, motivo="seção ausente da planilha"))
    return problemas


def progresso(lidas: list[tuple[str, int, LinhaPertinencia]]) -> dict[str, tuple[int, int]]:
    contagem: dict[str, tuple[int, int]] = {}
    for aba, _, linha in lidas:
        julgadas, total = contagem.get(aba, (0, 0))
        contagem[aba] = (julgadas + (linha.veredito is not None), total + 1)
    return contagem


def gravar_csv(linhas: list[LinhaPertinencia], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV, lineterminator="\n")
        escritor.writeheader()
        for linha in sorted(linhas, key=lambda l: l.id):
            escritor.writerow({campo: getattr(linha, campo) or "" for campo in CAMPOS_CSV})


def ler_csv(caminho: Path) -> dict[str, str]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return {linha["id"]: linha["veredito"] for linha in csv.DictReader(arquivo)}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_pertinencia.py -q`
Expected: 9 passed (contando os 3 parametrizados).

- [ ] **Step 5: Commit**

```bash
git add rag/pertinencia.py tests/test_rag_pertinencia.py
git commit -m "feat(rag): planilha cega de pertinencia dos complementares"
```

---

### Task 5: Comando `python -m rag.complementares gerar | importar [--parcial] | medir`

**Files:**
- Modify: `rag/complementares.py` (ambiente real, resultado e `main`)
- Test: `tests/test_rag_complementares_comando.py`

**Interfaces:**
- Consumes: Tarefas 2–4; `BaseRag.carregar()`, `carregar_gabaritos`, `ler_conjunto`, `ARQUIVO_CONSULTAS`, `avaliar` (régua antiga), `IndiceBm25`, `ranquear`, `fundir_rrf`, `K_FUSAO`, `EmbedderBge`, `ler_cache`, `PASTA_EMBEDDINGS`.
- Produces: `Ambiente(consultas, ancoras, trechos, ranqueadores)` (dataclass); `carregar_ambiente() -> Ambiente`; constantes `ARQUIVO_PLANILHA`, `ARQUIVO_CSV`, `PASTA_RESULTADOS`; `ResultadoComplementares(por_busca: dict[str, MedidaBusca], decisao: DecisaoBusca, regua_antiga: dict[str, dict[str, float]], ambiente: dict)`; `formatar(r) -> str`; `main(argv) -> int`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_rag_complementares_comando.py`:

```python
"""O comando python -m rag.complementares, com um ambiente sintético."""

import json

import pytest
from fabricas_analise import trecho_indexado
from openpyxl import load_workbook

from rag import complementares as comando
from rag.avaliacao import Consulta
from rag.pertinencia import LINHA_CABECALHO

ANCORA = trecho_indexado("learn:ancora", "auto date time")
TRECHOS = [ANCORA, trecho_indexado("learn:a", "a"), trecho_indexado("learn:b", "b")]


def _ambiente():
    return comando.Ambiente(
        consultas=[Consulta(id="REGRA/MOD-001", tipo="regra", id_regra="MOD-001", texto="q")],
        ancoras={"MOD-001": ANCORA},
        trechos=TRECHOS,
        ranqueadores={
            "bm25": lambda q, k: [0, 2][:k],
            "densa": lambda q, k: [1, 0][:k],
            "hibrida": lambda q, k: [1, 2][:k],
        },
    )


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "ARQUIVO_PLANILHA", tmp_path / "gabarito" / "p.xlsx")
    monkeypatch.setattr(comando, "ARQUIVO_CSV", tmp_path / "pertinencia.csv")
    monkeypatch.setattr(comando, "PASTA_RESULTADOS", tmp_path / "results")
    monkeypatch.setattr(comando, "carregar_ambiente", _ambiente)
    return tmp_path


def _julgar(caminho, vereditos):
    livro = load_workbook(caminho)
    aba = livro["MOD-001"]
    cab = [c.value for c in aba[LINHA_CABECALHO]]
    for r in range(LINHA_CABECALHO + 1, aba.max_row + 1):
        aba.cell(row=r, column=cab.index("veredito") + 1).value = vereditos[aba.cell(row=r, column=1).value]
    livro.save(caminho)


def test_fluxo_completo_decide_e_grava_json(ambiente, capsys):
    assert comando.main(["gerar"]) == 0
    _julgar(ambiente / "gabarito" / "p.xlsx", {"MOD-001|learn:a#s": "pertinente", "MOD-001|learn:b#s": "não pertinente"})
    assert comando.main(["importar"]) == 0
    assert comando.main(["medir"]) == 0
    dados = json.loads(next((ambiente / "results").glob("complementares-*.json")).read_text(encoding="utf-8"))
    assert dados["por_busca"]["bm25"]["macro"]["principal"] == 0.0
    assert dados["por_busca"]["densa"]["macro"]["principal"] == 1.0
    assert dados["decisao"]["vencedora"] == "densa"
    capsys.readouterr().out.encode("ascii")


def test_importar_incompleto_nao_grava(ambiente, capsys):
    comando.main(["gerar"])
    assert comando.main(["importar"]) == 1
    assert "sem veredito" in capsys.readouterr().err
    assert not (ambiente / "pertinencia.csv").exists()


def test_medir_sem_csv_indica_importar(ambiente, capsys):
    assert comando.main(["medir"]) == 1
    assert "importar" in capsys.readouterr().err


def test_sem_cache_de_embeddings_indica_a_medicao(monkeypatch, capsys):
    def sem_cache():
        raise comando.ErroDeComplementares("sem cache de embeddings para secao-sem - rode `python -m rag.medicao`")

    monkeypatch.setattr(comando, "carregar_ambiente", sem_cache)
    assert comando.main(["gerar"]) == 1
    assert "rag.medicao" in capsys.readouterr().err
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares_comando.py -q`
Expected: falham com `AttributeError: module 'rag.complementares' has no attribute 'ARQUIVO_PLANILHA'` (ou `Ambiente`).

- [ ] **Step 3: Implementar**

Em `rag/complementares.py`, acrescentar aos imports do topo `import argparse`, `import hashlib`, `import sys`, `from dataclasses import dataclass` e `from datetime import date`, e trocar `from rag.avaliacao import Consulta` por `from rag.avaliacao import ARQUIVO_CONSULTAS, RAIZ_REPO, Consulta, ErroDeAvaliacao, avaliar, ler_conjunto`. O comando roda como `python -m rag.complementares`, pelo bloco `if __name__ == "__main__"` do próprio módulo. Ao fim do arquivo:

```python
ARQUIVO_PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "pertinencia-complementares.xlsx"
ARQUIVO_CSV = RAIZ_REPO / "eval" / "recuperacao" / "pertinencia.csv"
PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"


@dataclass
class Ambiente:
    consultas: list[Consulta]
    ancoras: dict[str, TrechoIndexado]
    trechos: list[TrechoIndexado]
    ranqueadores: dict[str, Ranqueador]


def carregar_ambiente() -> Ambiente:
    """Os trechos do índice e as três buscas sobre eles. Os vetores vêm do cache da
    medição de 11/10; sem ele, falha — recalcular em silêncio mudaria o que se mede."""
    from core.analise.contexto import carregar_gabaritos
    from rag.busca import K_FUSAO, IndiceBm25, fundir_rrf, ranquear
    from rag.embeddings import PASTA_EMBEDDINGS, EmbedderBge, ler_cache
    from rag.indice import BaseRag

    base = BaseRag.carregar()
    trechos = base.trechos
    textos = [t.texto_indexado for t in trechos]
    embedder = EmbedderBge()
    vetores = ler_cache(PASTA_EMBEDDINGS, base.configuracao.variante, embedder.nome, textos)
    if vetores is None:
        raise ErroDeComplementares(
            f"sem cache de embeddings para {base.configuracao.variante} - rode `python -m rag.medicao`"
        )
    bm25 = IndiceBm25(textos)

    def por_bm25(consulta: str, k: int) -> list[int]:
        return ranquear(bm25.pontuacoes(consulta), None, k)

    def densa(consulta: str, k: int) -> list[int]:
        return ranquear(vetores @ embedder.vetor_consulta(consulta), None, k)

    def hibrida(consulta: str, k: int) -> list[int]:
        return fundir_rrf([densa(consulta, K_FUSAO), por_bm25(consulta, K_FUSAO)], k)

    ancoras = {
        id_regra: base.trecho_ancora(g.id_pagina, g.ancora, g.frase_marca)
        for id_regra, g in carregar_gabaritos().items()
    }
    return Ambiente(
        consultas=ler_conjunto(ARQUIVO_CONSULTAS).consultas,
        ancoras=ancoras,
        trechos=trechos,
        ranqueadores={"bm25": por_bm25, "densa": densa, "hibrida": hibrida},
    )


class ResultadoComplementares(BaseModel):
    por_busca: dict[str, MedidaBusca]
    decisao: DecisaoBusca
    regua_antiga: dict[str, dict[str, float]]
    """Acerto@5 e MRR@10 da âncora, por busca, nas 70 consultas: registro, não decide."""
    ambiente: dict


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.2f}"


def formatar(r: ResultadoComplementares) -> str:
    regras = sorted(next(iter(r.por_busca.values())).por_regra)
    linhas = ["regra      " + "".join(f"{t:>10}" for t in TIPOS)]
    for regra in regras:
        linhas.append(f"{regra:<10} " + "".join(f"{_pct(r.por_busca[t].por_regra[regra].principal):>10}" for t in TIPOS))
    linhas.append("macro      " + "".join(f"{_pct(r.por_busca[t].macro.principal):>10}" for t in TIPOS))
    linhas.append("micro      " + "".join(f"{_pct(r.por_busca[t].micro.principal):>10}" for t in TIPOS))
    linhas.append("piso-teto  " + "".join(
        f"{_pct(r.por_busca[t].macro.piso) + '-' + _pct(r.por_busca[t].macro.teto):>10}" for t in TIPOS
    ))
    linhas.append("regua antiga (acerto@5 / MRR@10): " + ", ".join(
        f"{t} {r.regua_antiga[t]['acerto5']:.3f}/{r.regua_antiga[t]['mrr']:.3f}" for t in TIPOS
    ))
    linhas.append(f"Decisao: {r.decisao.vencedora} - {r.decisao.justificativa}")
    return _ascii("\n".join(linhas))


def _pool(amb: Ambiente) -> list[ItemPool]:
    return formar_pool(amb.consultas, amb.ancoras, amb.trechos, amb.ranqueadores)


def _gerar() -> int:
    from rag.pertinencia import gerar_planilha

    amb = carregar_ambiente()
    pool = _pool(amb)
    gerar_planilha(pool, amb.ancoras, ARQUIVO_PLANILHA)
    print(_ascii(f"Planilha gerada em {ARQUIVO_PLANILHA} ({len(pool)} secoes)"))
    return 0


def _importar(parcial: bool) -> int:
    from rag.pertinencia import gravar_csv, ler_planilha, progresso, validar

    lidas = ler_planilha(ARQUIVO_PLANILHA)
    problemas = validar(lidas, _pool(carregar_ambiente()), parcial=parcial)
    if problemas:
        for p in problemas:
            onde = f"linha {p.linha}" if p.linha is not None else "fora da planilha"
            print(_ascii(f"erro: {p.aba} {onde} | {p.id} | {p.motivo}"), file=sys.stderr)
        print(f"erro: {len(problemas)} problema(s); nada foi gravado", file=sys.stderr)
        return 1
    if parcial:
        for regra, (julgadas, total) in sorted(progresso(lidas).items()):
            print(f"{regra}: {julgadas}/{total}")
        return 0
    gravar_csv([l for _, _, l in lidas], ARQUIVO_CSV)
    print(_ascii(f"Pertinencia gravada em {ARQUIVO_CSV} ({len(lidas)} linhas)"))
    return 0


def _medir() -> int:
    from rag.pertinencia import ler_csv

    if not ARQUIVO_CSV.is_file():
        print(f"erro: {ARQUIVO_CSV.name} ausente - rode `python -m rag.complementares importar`", file=sys.stderr)
        return 1
    julgamentos = ler_csv(ARQUIVO_CSV)
    amb = carregar_ambiente()
    medidas = complementares_por_busca(amb.consultas, amb.ancoras, amb.trechos, amb.ranqueadores)
    por_busca = {t: medir_busca(medidas[t], julgamentos) for t in TIPOS}
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    regua_antiga = {}
    for t in TIPOS:
        relatorio = avaliar(lambda q, k, r=amb.ranqueadores[t]: [amb.trechos[i].para_regua() for i in r(q, k)], conjunto)
        regua_antiga[t] = {"acerto5": relatorio.macro.acerto[5], "mrr": relatorio.macro.mrr}
    resultado = ResultadoComplementares(
        por_busca=por_busca,
        decisao=decidir_busca({t: por_busca[t].macro.principal for t in TIPOS}),
        regua_antiga=regua_antiga,
        ambiente={
            "data": date.today().isoformat(),
            "sha256_consultas": hashlib.sha256(ARQUIVO_CONSULTAS.read_bytes()).hexdigest(),
            "sha256_pertinencia": hashlib.sha256(ARQUIVO_CSV.read_bytes()).hexdigest(),
            "margem": MARGEM,
        },
    )
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"complementares-{date.today().isoformat()}.json"
    destino.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(formatar(resultado))
    print(_ascii(f"Resultado em {destino}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rag.complementares", description="Pertinencia dos complementares.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="gera a planilha cega de pertinencia")
    importar = sub.add_parser("importar", help="valida a planilha e grava eval/recuperacao/pertinencia.csv")
    importar.add_argument("--parcial", action="store_true", help="so mostra o progresso")
    sub.add_parser("medir", help="precisao dos complementares por busca e decisao")
    args = parser.parse_args(argv)
    try:
        if args.comando == "gerar":
            return _gerar()
        if args.comando == "importar":
            return _importar(args.parcial)
        return _medir()
    except (ErroDeComplementares, ErroDeAvaliacao, OSError) as erro:
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Os imports de `rag.pertinencia`, `rag.indice`, `rag.embeddings` e `rag.busca` ficam dentro das funções porque `rag.pertinencia` importa `rag.complementares` (ciclo) e porque carregar o modelo só deve acontecer quando o comando roda.

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_complementares_comando.py tests/test_rag_complementares.py tests/test_rag_pertinencia.py -q`
Expected: todos passam (4 novos).

- [ ] **Step 5: Teste sobre a base real e commit**

Acrescentar a `tests/test_rag_complementares_comando.py`:

```python
from rag.indice import ARQUIVO_CONFIG  # noqa: E402

SEM_BASE = not ARQUIVO_CONFIG.is_file()


@pytest.mark.skipif(SEM_BASE, reason="índice da base RAG não construído")
def test_pool_real_cobre_as_9_regras():
    amb = comando.carregar_ambiente()
    pool = comando.formar_pool(amb.consultas, amb.ancoras, amb.trechos, amb.ranqueadores)
    assert len({p.id_regra for p in pool}) == 9
```

Run: `$env:HF_HUB_OFFLINE="1"; $env:HF_HOME="D:\dev\hf-cache"; .\.venv\Scripts\python.exe -m pytest -q`
Expected: tudo passa.

```bash
git add rag/complementares.py tests/test_rag_complementares_comando.py
git commit -m "feat(rag): comando python -m rag.complementares gerar, importar e medir"
```

---

### Task 6: `python -m rag.indice construir --busca`

**Files:**
- Modify: `rag/indice.py` (`resultado_mais_recente`, `configuracao_do_indice`, `construir`, `main`)
- Test: `tests/test_rag_indice.py` (acrescentar)

**Interfaces:**
- Consumes: `ler_resultado`, `Configuracao` (`rag.medicao`); o JSON da Tarefa 5 (`decisao.vencedora`).
- Produces: `resultado_mais_recente(pasta: Path, padrao: str = "recuperacao-*.json") -> Path`; `configuracao_do_indice(pasta_resultados: Path, busca: str | None) -> tuple[Configuracao, str | None]` (configuração e nome do arquivo de complementares que decidiu a troca); `ARQUIVO_ORIGEM = PASTA_INDICE / "origem-da-busca.json"`; `construir(..., busca: str | None = None)`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_rag_indice.py` (o import de `configuracao_do_indice` entra junto dos outros de `rag.indice`, no topo):

```python
import json as _json

from rag.indice import configuracao_do_indice


def _complementares(pasta, vencedora, data="2026-10-13"):
    (pasta / f"complementares-{data}.json").write_text(
        _json.dumps({"decisao": {"vencedora": vencedora, "justificativa": "x"}}), encoding="utf-8"
    )


def test_sem_busca_a_configuracao_e_a_vencedora_de_11_10(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    configuracao, origem = configuracao_do_indice(tmp_path, None)
    assert configuracao.busca == "bm25" and origem is None


def test_busca_que_casa_com_a_decisao_troca_so_a_busca(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    _complementares(tmp_path, "hibrida")
    configuracao, origem = configuracao_do_indice(tmp_path, "hibrida")
    assert (configuracao.busca, configuracao.chunking, configuracao.cabecalho, configuracao.corpus) == (
        "hibrida", "secao", False, "completo",
    )
    assert origem == "complementares-2026-10-13.json"


def test_busca_que_nao_casa_com_a_decisao_e_recusada(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    _complementares(tmp_path, "bm25")
    with pytest.raises(ErroDeIndice, match="decisão mais recente"):
        configuracao_do_indice(tmp_path, "densa")


def test_busca_sem_resultado_de_complementares_e_recusada(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    with pytest.raises(ErroDeIndice, match="rag.complementares medir"):
        configuracao_do_indice(tmp_path, "hibrida")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: erro de coleta — `cannot import name 'configuracao_do_indice'`.

- [ ] **Step 3: Implementar**

Em `rag/indice.py`: acrescentar `import json` aos imports e `ARQUIVO_ORIGEM = PASTA_INDICE / "origem-da-busca.json"` junto das outras constantes. Trocar `resultado_mais_recente` por:

```python
def resultado_mais_recente(pasta: Path, padrao: str = "recuperacao-*.json") -> Path:
    arquivos = sorted(pasta.glob(padrao)) if pasta.is_dir() else []
```

(o resto da função fica igual). Acrescentar, antes de `construir`:

```python
def configuracao_do_indice(pasta_resultados: Path, busca: str | None) -> tuple[Configuracao, str | None]:
    """A vencedora da medição de 11/10; com `busca`, só o tipo de busca muda, e só se casar
    com a decisão mais recente da medição dos complementares."""
    _, decisao = ler_resultado(resultado_mais_recente(pasta_resultados))
    configuracao = decisao.vencedora
    if busca is None:
        return configuracao, None
    arquivos = sorted(pasta_resultados.glob("complementares-*.json")) if pasta_resultados.is_dir() else []
    if not arquivos:
        raise ErroDeIndice("sem resultado de complementares — rode `python -m rag.complementares medir`")
    vencedora = json.loads(arquivos[-1].read_text(encoding="utf-8"))["decisao"]["vencedora"]
    if vencedora != busca:
        raise ErroDeIndice(f"--busca {busca} não casa com a decisão mais recente ({arquivos[-1].name}: {vencedora})")
    return configuracao.model_copy(update={"busca": busca}), arquivos[-1].name
```

Em `construir`, acrescentar o parâmetro `busca: str | None = None` e trocar as duas primeiras linhas do corpo por:

```python
    configuracao, origem = configuracao_do_indice(pasta_resultados, busca)
```

e, logo depois de gravar o `config.json`, acrescentar:

```python
    arquivo_origem = pasta_indice / ARQUIVO_ORIGEM.name
    if origem is None:
        arquivo_origem.unlink(missing_ok=True)
    else:
        arquivo_origem.write_text(
            json.dumps({"busca": busca, "decidida_por": origem}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
```

Em `main`, trocar `sub.add_parser("construir", ...)` e a chamada por:

```python
    construir_ = sub.add_parser("construir", help="constrói o índice da configuração vencedora da medição")
    construir_.add_argument(
        "--busca", choices=("bm25", "densa", "hibrida"),
        help="troca só o tipo de busca; precisa casar com a decisão de `python -m rag.complementares medir`",
    )
    args = parser.parse_args(argv)
    try:
        configuracao = construir(busca=args.busca)
```

Ajustar `test_resumo_do_comando_imprime_no_console_padrao_do_windows`: o `monkeypatch.setattr(modulo_indice, "construir", lambda: ...)` passa a `lambda busca=None: ...`.

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: todos passam (4 novos).

- [ ] **Step 5: Suíte e commit**

Run: `$env:HF_HUB_OFFLINE="1"; $env:HF_HOME="D:\dev\hf-cache"; .\.venv\Scripts\python.exe -m pytest -q`
Expected: tudo passa.

```bash
git add rag/indice.py tests/test_rag_indice.py
git commit -m "feat(rag): construir --busca, so quando casa com a decisao dos complementares"
```

---

### Task 7: Gerar a planilha real e registrar

**Files:**
- Modify: `docs/project/progress-log.md`, `docs/project/status.md`

- [ ] **Step 1: Gerar**

Run: `$env:HF_HUB_OFFLINE="1"; $env:HF_HOME="D:\dev\hf-cache"; .\.venv\Scripts\python.exe -m rag.complementares gerar`
Expected: `Planilha gerada em ...\eval\gabarito\pertinencia-complementares.xlsx (89 secoes)` — o levantamento de 12/10 deu 89; um número diferente só se o índice mudou, e então anotar a diferença.

- [ ] **Step 2: Conferir**

Run: `...python.exe -m rag.complementares importar --parcial` (com as mesmas variáveis)
Expected: uma linha por regra, todas `0/<n>`, somando o total do Step 1.

- [ ] **Step 3: Registrar, commit e push**

Entrada nova no fim de `docs/project/progress-log.md`, `## <data> — Pertinência dos complementares: ferramentas prontas, planilha gerada`, com: a régua nova e por que a antiga não serve; o pool por regra; a regra de decisão (margem 0,10); e `**Próximo passo:**` "o Fred julga `eval/gabarito/pertinencia-complementares.xlsx`; depois `importar` e `medir`". Em `docs/project/status.md`, na linha 1 dos próximos passos, acrescentar "— planilha de pertinência gerada, aguardando julgamento".

```bash
git add docs/project/progress-log.md docs/project/status.md
git commit -m "docs: pertinencia dos complementares - planilha gerada"
git push
```

---

### Task 8: Depois do julgamento — medir, decidir e aplicar

Esta tarefa só começa quando o Fred terminar a planilha.

**Files:**
- Create: `eval/recuperacao/pertinencia.csv`, `eval/results/complementares-<data>.json`
- Modify: `docs/adr/ADR-002-stack-tecnologica.md`, `docs/project/progress-log.md`, `docs/project/status.md`

- [ ] **Step 1: Importar e medir**

Run (com `HF_HUB_OFFLINE=1` e `HF_HOME`): `python -m rag.complementares importar` e `python -m rag.complementares medir`
Expected: CSV gravado; tabela por regra e busca; decisão impressa.

- [ ] **Step 2: Se a vencedora não for o BM25**

Run: `python -m rag.indice construir --busca <vencedora>` e depois `python -m core.auditoria "data/pbip/P8_contoso-vendas"` (exige o Ollama no ar).
Expected: índice reconstruído com `origem-da-busca.json`; auditoria do P8 com 15 achados. Conferir à mão os complementares da PERF-001 e da PERF-003 e o tempo por achado.

- [ ] **Step 3: Registrar, commit e push**

- `docs/adr/ADR-002-stack-tecnologica.md`: "Emenda de <data> — busca escolhida pela pertinência dos complementares", com a tabela de macros por busca, a decisão, a régua antiga como registro e as limitações declaradas da spec (§4).
- `docs/project/progress-log.md`: entrada com as precisões, a decisão e, se houve troca, o P8 de novo.
- `docs/project/status.md`: linha da Fase 3 e próximos passos.

```bash
git add eval/recuperacao/pertinencia.csv eval/results docs
git commit -m "eval: pertinencia dos complementares medida e busca decidida"
git push
```
