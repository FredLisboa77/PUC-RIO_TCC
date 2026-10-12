# Geração com o LLM e citação obrigatória — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** transformar cada achado das regras num achado enriquecido — explicação e recomendação do LLM com citação validada por código — e rodar a auditoria inteira sobre um PBIP com `python -m core.auditoria`.

**Architecture:** pacote `core/analise/` com uma unidade por responsabilidade (contratos, contexto, prompt, cliente do LLM, validação, fidelidade, enriquecimento) e `core/auditoria.py` com `run_audit()` e o comando. A busca vem de uma nova classe `BaseRag` em `rag/indice.py`; a âncora de cada regra vem do gabarito da avaliação. LLM e base são injetados, então a suíte roda sem Ollama e sem índice real.

**Tech Stack:** Python 3.11, Pydantic 2, `urllib` (stdlib) contra a API do Ollama, pytest. Nenhuma dependência nova.

**Spec:** `docs/superpowers/specs/2026-10-11-geracao-com-citacao-design.md`

## Global Constraints

- Tudo em português do Brasil: código, nomes de função e de teste, docstrings, mensagens, commits.
- Nenhuma dependência nova; o cliente do Ollama usa `urllib` como `eval/spike_llm.py`.
- Ollama: `POST /api/chat`, `stream: false`, `num_ctx=4096`, `temperature=0`, `seed=42`, timeout de 120 s, modelo padrão `qwen2.5:7b-instruct-q4_K_M`.
- Contexto: trecho âncora sempre em [1]; até 4 complementares de `buscar(consulta, k=10)`; orçamento de 1.800 palavras; trecho de DAX/M no prompt cortado em 1.500 caracteres.
- Citações: 1 a 3 inteiros distintos em `1..len(contexto)`. Motivos de descarte exatamente: `json_invalido`, `campo_vazio`, `citacoes_fora_do_limite`, `citacao_inexistente`, `erro_llm`.
- Fidelidade registra e **não** descarta.
- Saída do comando no console em ASCII (o console do Windows já quebrou o resumo do índice).
- Rodar testes com `.\.venv\Scripts\python.exe -m pytest -q` (PowerShell) a partir da raiz do repositório.
- Cada commit termina com a linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push autorizado na branch `fase3-geracao-citacao`.
- Densidade de comentário do repositório: docstrings que dizem **por quê**, não o quê.

## Review Focus

- **PBIP sem nenhum achado** — a auditoria não aquece nem chama o LLM, grava JSON com lista vazia e o resumo não divide por zero (teste na Tarefa 9).
- **Citação que não é inteiro** (`[true]`, `["1"]`, `[1.0]`) — `json_invalido`; `True` não pode passar por 1, embora `bool` seja subclasse de `int` em Python (teste na Tarefa 4).
- **Modelo não baixado no Ollama** (HTTP 404) — a mensagem de erro nomeia o modelo, e o comando aborta no aquecimento com código 1 (testes nas Tarefas 7 e 9).
- **`detalhe` com valor não serializável em JSON** (`Path`, `set`) — prompt e fidelidade não quebram (testes nas Tarefas 5 e 6).
- **Nome de projeto com espaço** (`P1_AdventureWorks Sales`) **ou entrada `.zip`** — o nome do arquivo de saída sai do nome da pasta, ou do zip sem extensão (teste na Tarefa 9).

---

### Task 1: Contratos da geração

**Files:**
- Create: `core/analise/__init__.py`
- Create: `core/analise/base.py`
- Create: `tests/fabricas_analise.py`
- Test: `tests/test_analise_base.py`

**Interfaces:**
- Consumes: `core.rules.base.Achado`, `Evidencia`, `RegraMeta`.
- Produces: `TrechoDeContexto`, `Geracao`, `Fidelidade`, `AchadoEnriquecido` (com `recomendacao_final(meta) -> str`), os literais `Origem`, `Situacao`, `MotivoDescarte`; em `tests/fabricas_analise.py`: `meta()`, `achado()`, `trecho_de_contexto()`, `contexto()`.

- [ ] **Step 1: Criar as fábricas dos testes**

`tests/fabricas_analise.py`:

```python
"""Fábricas dos testes da geração (`core/analise`, `core/auditoria`).

Ficam fora do `conftest.py` porque não são fixtures: são construtores que cada
teste chama com os parâmetros que quer variar.
"""

from core.analise.base import TrechoDeContexto
from core.rules.base import Achado, Evidencia, RegraMeta

RECOMENDACAO_PADRAO = (
    "Desative a opção global de data/hora automática e use uma tabela de datas própria."
)


def meta(id_regra: str = "MOD-001", termos: tuple[str, ...] = ("auto date time",)) -> RegraMeta:
    return RegraMeta(
        id=id_regra,
        titulo="Tabela de data automática",
        categoria="modelagem",
        severidade="media",
        url_canonica="https://learn.microsoft.com/x",
        termos_consulta=termos,
        recomendacao_padrao=RECOMENDACAO_PADRAO,
    )


def achado(
    id_regra: str = "MOD-001",
    *,
    objeto: str = "LocalDateTable_1",
    mensagem: str = "O modelo tem 4 tabelas de data automáticas.",
    trecho: str | None = None,
    detalhe: dict | None = None,
    tipo_objeto: str = "tabela",
) -> Achado:
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(
            tipo_objeto=tipo_objeto, objeto=objeto, tabela=objeto, trecho=trecho, detalhe=detalhe or {}
        ),
        mensagem=mensagem,
    )


def trecho_de_contexto(
    numero: int, texto: str = "Disable the auto date/time option.", origem: str | None = None
) -> TrechoDeContexto:
    return TrechoDeContexto(
        numero=numero,
        id_pagina=f"learn:p{numero}",
        url=f"https://learn.microsoft.com/p{numero}",
        titulo=f"Página {numero}",
        ancora="s",
        caminho="Seção",
        texto=texto,
        origem=origem or ("ancora" if numero == 1 else "busca"),
    )


def contexto(n: int = 3) -> list[TrechoDeContexto]:
    return [trecho_de_contexto(i) for i in range(1, n + 1)]
```

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_analise_base.py`:

```python
"""Contrato do achado enriquecido: coerência entre situação e campos."""

import pytest
from pydantic import ValidationError

from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from fabricas_analise import achado, contexto, meta


def _gerado(**extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(),
        contexto=contexto(2),
        geracao=Geracao(explicacao="e", recomendacao="Use DIVIDE.", citacoes=[1]),
        situacao="gerado",
        cita_ancora=True,
        fidelidade=Fidelidade(),
        modelo="m",
        segundos=1.0,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _descartado(**extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(), contexto=contexto(1), situacao="sem_fundamentacao",
        motivo_descarte="json_invalido", modelo="m",
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def test_gerado_coerente_e_aceito():
    assert _gerado().situacao == "gerado"


def test_gerado_sem_geracao_e_recusado():
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(geracao=None)


def test_gerado_com_motivo_de_descarte_e_recusado():
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(motivo_descarte="erro_llm")


def test_sem_fundamentacao_precisa_de_motivo():
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(motivo_descarte=None)


def test_sem_fundamentacao_nao_pode_ter_fidelidade_nem_cita_ancora():
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(fidelidade=Fidelidade())
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(cita_ancora=False)


def test_recomendacao_final_usa_a_do_llm_quando_gerado():
    assert _gerado().recomendacao_final(meta()) == "Use DIVIDE."


def test_recomendacao_final_cai_na_padrao_quando_descartado():
    assert _descartado().recomendacao_final(meta()) == meta().recomendacao_padrao


def test_recomendacao_final_recusa_meta_de_outra_regra():
    with pytest.raises(ValueError, match="MOD-002"):
        _gerado().recomendacao_final(meta("MOD-002"))
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise'`

- [ ] **Step 4: Implementar**

`core/analise/__init__.py`:

```python
"""Geração com o LLM e citação obrigatória (Fase 3, semana 7).

Desenho: `docs/superpowers/specs/2026-10-11-geracao-com-citacao-design.md`.
"""
```

`core/analise/base.py`:

```python
"""Contrato entre a geração e o resto do pipeline.

O achado enriquecido guarda o contexto inteiro, não só as citações: a Fase 5 e
a banca precisam ver o que o modelo tinha à disposição para julgar a citação.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.rules.base import Achado, RegraMeta

Origem = Literal["ancora", "busca"]
Situacao = Literal["gerado", "sem_fundamentacao"]
MotivoDescarte = Literal[
    "json_invalido", "campo_vazio", "citacoes_fora_do_limite", "citacao_inexistente", "erro_llm"
]


class TrechoDeContexto(BaseModel):
    """Um trecho entregue ao LLM, com o número pelo qual ele é citado."""

    numero: int
    id_pagina: str
    url: str
    titulo: str
    ancora: str
    caminho: str
    texto: str
    origem: Origem
    """`ancora` é sempre o número 1 (emenda de 09/10 da ADR-002)."""


class Geracao(BaseModel):
    explicacao: str
    recomendacao: str
    citacoes: list[int]


class Fidelidade(BaseModel):
    divergencias: list[str] = Field(default_factory=list)
    """Números e nomes da resposta que não aparecem no achado nem nos trechos.
    Vazia = sem divergência. Registra, não descarta: a heurística ainda não está
    calibrada para ser portão."""


class AchadoEnriquecido(BaseModel):
    achado: Achado
    contexto: list[TrechoDeContexto]
    geracao: Geracao | None = None
    situacao: Situacao
    motivo_descarte: MotivoDescarte | None = None
    cita_ancora: bool | None = None
    """Pertinência automática: o trecho âncora está entre as citações."""
    fidelidade: Fidelidade | None = None
    modelo: str
    segundos: float | None = None
    """Tempo da chamada, sem a carga do modelo. `None` quando o LLM não respondeu."""

    @model_validator(mode="after")
    def _situacao_coerente(self) -> "AchadoEnriquecido":
        gerado = self.situacao == "gerado"
        coerentes = (
            (self.geracao is not None) == gerado
            and (self.motivo_descarte is None) == gerado
            and (self.cita_ancora is not None) == gerado
            and (self.fidelidade is not None) == gerado
        )
        if not coerentes:
            raise ValueError(
                f"achado enriquecido incoerente: situação {self.situacao} com geração, motivo, "
                "cita_ancora e fidelidade que não batem"
            )
        return self

    def recomendacao_final(self, meta: RegraMeta) -> str:
        """A recomendação que o relatório mostra. Método e não propriedade porque o
        achado guarda só o `id_regra`: a recomendação padrão vem do catálogo."""
        if meta.id != self.achado.id_regra:
            raise ValueError(f"meta da regra {meta.id} para um achado da regra {self.achado.id_regra}")
        if self.geracao is not None:
            return self.geracao.recomendacao
        return meta.recomendacao_padrao
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py -q`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add core/analise tests/fabricas_analise.py tests/test_analise_base.py
git commit -m "feat(analise): contrato do achado enriquecido"
```

---

### Task 2: `BaseRag` no índice

**Files:**
- Modify: `rag/indice.py` (substituir `carregar_buscador`, linhas ~108–145)
- Test: `tests/test_rag_indice.py` (acrescentar ao fim)

**Interfaces:**
- Consumes: `TrechoIndexado` (`rag.chunking`), `Configuracao` (`rag.medicao`), `IndiceBm25`, `ranquear`, `fundir_rrf`, `K_FUSAO` (`rag.busca`), `normalizar` (`rag.texto`).
- Produces: `BaseRag(configuracao, trechos, *, embedder=None, colecao=None)`; `BaseRag.carregar(embedder=None, *, pasta_indice=PASTA_INDICE, pasta_chroma=PASTA_CHROMA) -> BaseRag`; `BaseRag.buscar(consulta: str, k: int) -> list[TrechoIndexado]`; `BaseRag.trecho_ancora(id_pagina: str, ancora: str, frase_marca: str) -> TrechoIndexado` (levanta `ErroDeIndice`). `carregar_buscador` mantém a assinatura.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `tests/test_rag_indice.py`:

```python
from rag.indice import BaseRag


def _t(id_pagina, texto, *, parte=1, ancora="s"):
    return TrechoIndexado(
        id=f"{id_pagina}#{ancora}/{parte}", id_pagina=id_pagina, url="u", titulo_pagina="T",
        ancora=ancora, caminho="S", texto=texto, texto_indexado=texto,
    )


def _config(busca):
    return Configuracao(chunking="secao", cabecalho=False, busca=busca, corpus="completo")


def test_base_bm25_nao_carrega_embedder_nem_chroma(tmp_path, monkeypatch):
    pasta = tmp_path / "i"
    pasta.mkdir()
    trechos = [_t("learn:p", "auto date time"), _t("learn:q", "divide by zero")]
    (pasta / "trechos.jsonl").write_text("".join(t.model_dump_json() + "\n" for t in trechos), encoding="utf-8")
    (pasta / "config.json").write_text(_config("bm25").model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(modulo_indice, "EmbedderBge", lambda: pytest.fail("BM25 não usa embedder"))
    monkeypatch.setattr(modulo_indice, "_cliente", lambda pasta: pytest.fail("BM25 não usa o Chroma"))

    base = BaseRag.carregar(pasta_indice=pasta, pasta_chroma=tmp_path / "c")

    achados = base.buscar("divide", 1)
    assert [t.id for t in achados] == ["learn:q#s/1"]
    assert (achados[0].url, achados[0].titulo_pagina) == ("u", "T")


def test_trecho_ancora_pega_a_parte_da_secao_com_a_frase_marca():
    base = BaseRag(_config("bm25"), [
        _t("learn:p", "intro text"),
        _t("learn:p", "You should disable the Auto  date/time option.", parte=2),
        _t("learn:q", "disable the auto date/time option"),
    ])
    assert base.trecho_ancora("learn:p", "s", "disable the auto date/time option").id == "learn:p#s/2"


def test_trecho_ancora_de_secao_ausente_falha():
    base = BaseRag(_config("bm25"), [_t("learn:p", "texto")])
    with pytest.raises(ErroDeIndice, match="ausente"):
        base.trecho_ancora("learn:sumiu", "s", "texto")


def test_trecho_ancora_sem_a_frase_marca_falha():
    base = BaseRag(_config("bm25"), [_t("learn:p", "outro texto")])
    with pytest.raises(ErroDeIndice, match="frase-marca"):
        base.trecho_ancora("learn:p", "s", "disable the option")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: FAIL — `ImportError: cannot import name 'BaseRag'`

- [ ] **Step 3: Implementar**

Em `rag/indice.py`, acrescentar `from rag.texto import normalizar` aos imports e substituir a função `carregar_buscador` inteira por:

```python
class BaseRag:
    """Os trechos do índice e a busca da configuração vencedora.

    A geração precisa de mais do que a régua: URL e título para o contexto, e o
    trecho âncora de cada regra. Com a vencedora BM25, a consulta não passa pelo
    Chroma nem pelo `bge-small` — então nenhum dos dois é carregado.
    """

    def __init__(
        self,
        configuracao: Configuracao,
        trechos: list[TrechoIndexado],
        *,
        embedder: Embedder | None = None,
        colecao=None,
    ) -> None:
        self.configuracao = configuracao
        self.trechos = trechos
        self._posicao = {t.id: i for i, t in enumerate(trechos)}
        self._embedder = embedder
        self._colecao = colecao
        self._bm25 = IndiceBm25([t.texto_indexado for t in trechos]) if configuracao.busca != "densa" else None

    @classmethod
    def carregar(
        cls,
        embedder: Embedder | None = None,
        *,
        pasta_indice: Path = PASTA_INDICE,
        pasta_chroma: Path = PASTA_CHROMA,
    ) -> "BaseRag":
        config = pasta_indice / ARQUIVO_CONFIG.name
        if not config.is_file():
            raise ErroDeIndice(f"índice ausente em {pasta_indice} — rode `python -m rag.indice construir`")
        configuracao = Configuracao.model_validate_json(config.read_text(encoding="utf-8"))
        _exigir_corpus_completo(configuracao)
        linhas = (pasta_indice / ARQUIVO_TRECHOS.name).read_text(encoding="utf-8").splitlines()
        trechos = [TrechoIndexado.model_validate_json(linha) for linha in linhas if linha.strip()]
        if configuracao.busca == "bm25":
            return cls(configuracao, trechos)
        return cls(
            configuracao,
            trechos,
            embedder=embedder or EmbedderBge(),
            colecao=_cliente(pasta_chroma).get_collection(COLECAO),
        )

    def _densa(self, consulta: str, k: int) -> list[int]:
        resposta = self._colecao.query(
            query_embeddings=[self._embedder.vetor_consulta(consulta).tolist()], n_results=k, include=["distances"]
        )
        return [self._posicao[i] for i in resposta["ids"][0]]

    def _por_bm25(self, consulta: str, k: int) -> list[int]:
        return ranquear(self._bm25.pontuacoes(consulta), None, k)

    def buscar(self, consulta: str, k: int) -> list[TrechoIndexado]:
        busca = self.configuracao.busca
        if busca == "densa":
            indices = self._densa(consulta, k)
        elif busca == "bm25":
            indices = self._por_bm25(consulta, k)
        else:
            indices = fundir_rrf([self._densa(consulta, K_FUSAO), self._por_bm25(consulta, K_FUSAO)], k)
        return [self.trechos[i] for i in indices]

    def trecho_ancora(self, id_pagina: str, ancora: str, frase_marca: str) -> TrechoIndexado:
        """A parte da seção âncora que contém a frase-marca — o mesmo critério de
        acerto da régua, para que o contexto use o trecho que a medição validou."""
        da_secao = [t for t in self.trechos if t.id_pagina == id_pagina and t.ancora == ancora]
        if not da_secao:
            raise ErroDeIndice(f"seção {id_pagina}#{ancora} ausente do índice")
        alvo = normalizar(frase_marca)
        for trecho in da_secao:
            if alvo in normalizar(trecho.texto):
                return trecho
        raise ErroDeIndice(f"nenhuma parte de {id_pagina}#{ancora} contém a frase-marca")


def carregar_buscador(
    embedder: Embedder | None = None,
    *,
    pasta_indice: Path = PASTA_INDICE,
    pasta_chroma: Path = PASTA_CHROMA,
) -> Buscador:
    """A busca no formato da régua — o que a medição e seus testes consomem."""
    base = BaseRag.carregar(embedder, pasta_indice=pasta_indice, pasta_chroma=pasta_chroma)

    def buscar(consulta: str, k: int) -> list[Trecho]:
        return [t.para_regua() for t in base.buscar(consulta, k)]

    return buscar
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: todos passam, incluindo os três `test_carregar_buscador_reproduz_a_busca_em_memoria` já existentes.

- [ ] **Step 5: Suíte inteira e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: 483 + 8 + 4 = 495 passed.

```bash
git add rag/indice.py tests/test_rag_indice.py
git commit -m "feat(rag): BaseRag com trecho ancora e busca BM25 sem embedder"
```

---

### Task 3: Montagem do contexto

**Files:**
- Create: `core/analise/contexto.py`
- Modify: `tests/fabricas_analise.py` (acrescentar fábricas de índice)
- Test: `tests/test_analise_contexto.py`

**Interfaces:**
- Consumes: `BaseRag`, `ErroDeIndice` (Task 2); `TrechoDeContexto` (Task 1); `montar_consulta` (`rag.consulta`); `Gabarito`, `ler_conjunto`, `ARQUIVO_CONSULTAS` (`rag.avaliacao`).
- Produces: `ErroDeContexto`; `carregar_gabaritos(caminho=ARQUIVO_CONSULTAS) -> dict[str, Gabarito]`; `verificar_ancoras(ids_regra: Iterable[str], gabaritos: dict[str, Gabarito], base: BaseRag) -> None`; `montar_contexto(meta, achado, base, gabarito) -> list[TrechoDeContexto]`; constantes `K_BUSCA = 10`, `MAX_COMPLEMENTARES = 4`, `ORCAMENTO_PALAVRAS = 1800`. Em fábricas: `trecho_indexado()`, `base_bm25()`, `gabarito()`, `TRECHO_ANCORA`, `base_padrao()`.

- [ ] **Step 1: Acrescentar as fábricas**

Ao fim de `tests/fabricas_analise.py` (e os imports no topo):

```python
from rag.avaliacao import Gabarito
from rag.chunking import TrechoIndexado
from rag.indice import BaseRag
from rag.medicao import Configuracao


def trecho_indexado(id_pagina: str, texto: str, *, ancora: str = "s", parte: int = 1) -> TrechoIndexado:
    return TrechoIndexado(
        id=f"{id_pagina}#{ancora}/{parte}",
        id_pagina=id_pagina,
        url=f"https://learn.microsoft.com/{id_pagina.split(':', 1)[1]}",
        titulo_pagina="T",
        ancora=ancora,
        caminho="Seção",
        texto=texto,
        texto_indexado=texto,
    )


def base_bm25(trechos: list[TrechoIndexado]) -> BaseRag:
    return BaseRag(Configuracao(chunking="secao", cabecalho=False, busca="bm25", corpus="completo"), trechos)


def gabarito(
    id_regra: str = "MOD-001",
    *,
    id_pagina: str = "learn:auto",
    ancora: str = "s",
    frase_marca: str = "disable the auto date time option",
) -> Gabarito:
    return Gabarito(id_regra=id_regra, frase_marca=frase_marca, id_pagina=id_pagina, ancora=ancora)


TRECHO_ANCORA = trecho_indexado("learn:auto", "You should disable the auto date time option in every model.")


def base_padrao() -> BaseRag:
    return base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time tables are hidden")])
```

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_analise_contexto.py`:

```python
"""Contexto da geração: âncora sempre em [1], complementares do BM25 com orçamento."""

import pytest

from core.analise.contexto import ErroDeContexto, carregar_gabaritos, montar_contexto, verificar_ancoras
from core.rules.todas import REGISTRO
from fabricas_analise import TRECHO_ANCORA, achado, base_bm25, gabarito, meta, trecho_indexado


def test_ancora_e_sempre_o_trecho_1_e_os_numeros_sao_sequenciais():
    base = base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time tables are hidden")])
    ctx = montar_contexto(meta(), achado(), base, gabarito())
    assert (ctx[0].numero, ctx[0].origem, ctx[0].id_pagina) == (1, "ancora", "learn:auto")
    assert [t.numero for t in ctx] == list(range(1, len(ctx) + 1))
    assert all(t.origem == "busca" for t in ctx[1:])
    assert ctx[0].url == "https://learn.microsoft.com/auto"


def test_ancora_nao_se_repete_entre_os_complementares():
    base = base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time")])
    ids = [t.id_pagina for t in montar_contexto(meta(), achado(), base, gabarito())]
    assert ids.count("learn:auto") == 1


def test_no_maximo_quatro_complementares():
    outros = [trecho_indexado(f"learn:p{i}", "auto date time") for i in range(8)]
    ctx = montar_contexto(meta(), achado(), base_bm25([TRECHO_ANCORA, *outros]), gabarito())
    assert len(ctx) == 5


def test_complementar_que_estoura_o_orcamento_e_pulado_e_o_proximo_entra(monkeypatch):
    longo = trecho_indexado("learn:longo", "auto date time " + "palavra " * 1790)
    curto = trecho_indexado("learn:curto", "auto date time")
    base = base_bm25([TRECHO_ANCORA, longo, curto])
    monkeypatch.setattr(base, "buscar", lambda consulta, k: [longo, curto])
    ctx = montar_contexto(meta(), achado(), base, gabarito())
    assert [t.id_pagina for t in ctx] == ["learn:auto", "learn:curto"]


def test_ancora_entra_mesmo_acima_do_orcamento():
    enorme = trecho_indexado("learn:auto", "disable the auto date time option " + "x " * 2000)
    ctx = montar_contexto(meta(), achado(), base_bm25([enorme]), gabarito())
    assert [t.origem for t in ctx] == ["ancora"]


def test_regra_sem_gabarito_falha_na_verificacao():
    with pytest.raises(ErroDeContexto, match="MOD-002"):
        verificar_ancoras(["MOD-001", "MOD-002"], {"MOD-001": gabarito()}, base_bm25([TRECHO_ANCORA]))


def test_ancora_ausente_do_indice_falha_na_verificacao():
    with pytest.raises(ErroDeContexto, match="MOD-001"):
        verificar_ancoras(["MOD-001"], {"MOD-001": gabarito(id_pagina="learn:sumiu")}, base_bm25([TRECHO_ANCORA]))


def test_gabaritos_reais_cobrem_todas_as_regras_registradas():
    assert set(REGISTRO.ids()) <= set(carregar_gabaritos())
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_contexto.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise.contexto'`

- [ ] **Step 4: Implementar**

`core/analise/contexto.py`:

```python
"""O contexto entregue ao LLM: a âncora da regra e os complementares da busca.

A âncora entra sempre como [1] (emenda de 09/10 da ADR-002): a fonte que sustenta
o achado está garantida, qualquer que seja a qualidade da busca. Ela vem do
gabarito da avaliação, que já é verificado contra a base por teste — o
`RegraMeta` não ganha um campo que duplicaria essa informação.
"""

from collections.abc import Iterable
from pathlib import Path

from core.analise.base import Origem, TrechoDeContexto
from core.rules.base import Achado, RegraMeta
from rag.avaliacao import ARQUIVO_CONSULTAS, Gabarito, ler_conjunto
from rag.chunking import TrechoIndexado
from rag.consulta import montar_consulta
from rag.indice import BaseRag, ErroDeIndice

K_BUSCA = 10
MAX_COMPLEMENTARES = 4
ORCAMENTO_PALAVRAS = 1800
"""~2.500 tokens de trechos; sobram ~1.600 dos 4096 do `num_ctx` para a
instrução, a evidência e a resposta."""


class ErroDeContexto(Exception):
    """Uma regra não tem âncora utilizável. Nunca se gera sem âncora em silêncio."""


def carregar_gabaritos(caminho: Path = ARQUIVO_CONSULTAS) -> dict[str, Gabarito]:
    return {g.id_regra: g for g in ler_conjunto(caminho).gabaritos}


def _trecho_ancora(base: BaseRag, gabarito: Gabarito) -> TrechoIndexado:
    try:
        return base.trecho_ancora(gabarito.id_pagina, gabarito.ancora, gabarito.frase_marca)
    except ErroDeIndice as erro:
        raise ErroDeContexto(f"{gabarito.id_regra}: {erro}") from erro


def verificar_ancoras(ids_regra: Iterable[str], gabaritos: dict[str, Gabarito], base: BaseRag) -> None:
    """Checagem de partida: aborta antes da primeira chamada ao LLM, e não no
    meio da auditoria, com metade dos achados já gerados."""
    ids = list(ids_regra)
    sem_gabarito = [i for i in ids if i not in gabaritos]
    if sem_gabarito:
        raise ErroDeContexto(f"regras sem gabarito de âncora: {', '.join(sem_gabarito)}")
    for id_regra in ids:
        _trecho_ancora(base, gabaritos[id_regra])


def _palavras(trecho: TrechoIndexado) -> int:
    return len(trecho.texto.split())


def _para_contexto(trecho: TrechoIndexado, numero: int, origem: Origem) -> TrechoDeContexto:
    return TrechoDeContexto(
        numero=numero,
        id_pagina=trecho.id_pagina,
        url=trecho.url,
        titulo=trecho.titulo_pagina,
        ancora=trecho.ancora,
        caminho=trecho.caminho,
        texto=trecho.texto,
        origem=origem,
    )


def montar_contexto(meta: RegraMeta, achado: Achado, base: BaseRag, gabarito: Gabarito) -> list[TrechoDeContexto]:
    ancora = _trecho_ancora(base, gabarito)
    escolhidos = [ancora]
    total = _palavras(ancora)
    for trecho in base.buscar(montar_consulta(meta, achado), K_BUSCA):
        if len(escolhidos) > MAX_COMPLEMENTARES:
            break
        if trecho.id == ancora.id or total + _palavras(trecho) > ORCAMENTO_PALAVRAS:
            continue
        escolhidos.append(trecho)
        total += _palavras(trecho)
    return [
        _para_contexto(t, numero, "ancora" if numero == 1 else "busca")
        for numero, t in enumerate(escolhidos, start=1)
    ]
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_contexto.py -q`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add core/analise/contexto.py tests/fabricas_analise.py tests/test_analise_contexto.py
git commit -m "feat(analise): contexto com ancora em [1] e complementares por orcamento"
```

---

### Task 4: Validação da resposta

**Files:**
- Create: `core/analise/validacao.py`
- Test: `tests/test_analise_validacao.py`

**Interfaces:**
- Consumes: `Geracao`, `MotivoDescarte` (Task 1).
- Produces: `validar(texto: str, tamanho_contexto: int) -> tuple[Geracao | None, MotivoDescarte | None]`; `MAX_CITACOES = 3`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_analise_validacao.py`:

```python
"""Validação da resposta do LLM: a primeira falha decide o motivo do descarte."""

import json

import pytest

from core.analise.validacao import validar


def _json(**campos) -> str:
    resposta = {"explicacao": "Tabelas automáticas aumentam o modelo.", "recomendacao": "Desative a opção.", "citacoes": [1]}
    resposta.update(campos)
    return json.dumps(resposta, ensure_ascii=False)


def test_resposta_valida_e_aceita():
    geracao, motivo = validar(_json(citacoes=[1, 3]), 3)
    assert motivo is None
    assert geracao.citacoes == [1, 3]


def test_campos_sao_aparados():
    geracao, _ = validar(_json(explicacao="  x  ", recomendacao=" y "), 1)
    assert (geracao.explicacao, geracao.recomendacao) == ("x", "y")


@pytest.mark.parametrize(
    "texto",
    [
        "não é json",
        "[1, 2]",
        json.dumps({"explicacao": "x", "recomendacao": "y"}),
        _json(citacoes="1"),
        _json(explicacao=3),
    ],
)
def test_json_invalido(texto):
    assert validar(texto, 3) == (None, "json_invalido")


@pytest.mark.parametrize("citacoes", [[True], ["1"], [1.0]])
def test_citacao_que_nao_e_inteiro_e_json_invalido(citacoes):
    # `True` é `int` em Python; sem checar o tipo exato, passaria por citação 1.
    assert validar(_json(citacoes=citacoes), 3) == (None, "json_invalido")


@pytest.mark.parametrize("campo", ["explicacao", "recomendacao"])
def test_campo_vazio(campo):
    assert validar(_json(**{campo: "   "}), 3) == (None, "campo_vazio")


@pytest.mark.parametrize("citacoes", [[], [1, 2, 3, 4], [2, 2]])
def test_citacoes_fora_do_limite(citacoes):
    assert validar(_json(citacoes=citacoes), 5) == (None, "citacoes_fora_do_limite")


@pytest.mark.parametrize("citacoes", [[0], [4], [1, -1]])
def test_citacao_inexistente(citacoes):
    assert validar(_json(citacoes=citacoes), 3) == (None, "citacao_inexistente")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_validacao.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise.validacao'`

- [ ] **Step 3: Implementar**

`core/analise/validacao.py`:

```python
"""Validação da resposta do LLM (ADR-003): sem citação válida, não há geração.

Não confia no esquema imposto pelo Ollama: os limites de itens do JSON Schema
podem não ser respeitados pela decodificação restrita, então tudo é conferido
de novo aqui.
"""

import json

from core.analise.base import Geracao, MotivoDescarte

MAX_CITACOES = 3


def validar(texto: str, tamanho_contexto: int) -> tuple[Geracao | None, MotivoDescarte | None]:
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError:
        return None, "json_invalido"
    if not isinstance(bruto, dict):
        return None, "json_invalido"
    explicacao = bruto.get("explicacao")
    recomendacao = bruto.get("recomendacao")
    citacoes = bruto.get("citacoes")
    # `type(c) is int`, não `isinstance`: `True` é `int` em Python.
    if (
        not isinstance(explicacao, str)
        or not isinstance(recomendacao, str)
        or not isinstance(citacoes, list)
        or not all(type(c) is int for c in citacoes)
    ):
        return None, "json_invalido"
    if not explicacao.strip() or not recomendacao.strip():
        return None, "campo_vazio"
    if not 1 <= len(citacoes) <= MAX_CITACOES or len(set(citacoes)) != len(citacoes):
        return None, "citacoes_fora_do_limite"
    if any(not 1 <= c <= tamanho_contexto for c in citacoes):
        return None, "citacao_inexistente"
    return Geracao(explicacao=explicacao.strip(), recomendacao=recomendacao.strip(), citacoes=citacoes), None
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_validacao.py -q`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add core/analise/validacao.py tests/test_analise_validacao.py
git commit -m "feat(analise): validacao da resposta com motivo de descarte"
```

---

### Task 5: Verificação de fidelidade

**Files:**
- Create: `core/analise/fidelidade.py`
- Test: `tests/test_analise_fidelidade.py`

**Interfaces:**
- Consumes: `Geracao`, `Fidelidade`, `TrechoDeContexto` (Task 1); `Achado`; `normalizar` (`rag.texto`).
- Produces: `verificar_fidelidade(geracao: Geracao, achado: Achado, contexto: list[TrechoDeContexto]) -> Fidelidade`. Mensagens: `"número {valor:g} ausente do achado e dos trechos"` e `"nome {nome} ausente do achado e dos trechos"`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_analise_fidelidade.py`:

```python
"""Fidelidade à evidência: números e nomes da resposta precisam ter origem."""

from pathlib import Path

from core.analise.base import Geracao
from core.analise.fidelidade import verificar_fidelidade
from fabricas_analise import achado, contexto, trecho_de_contexto


def _divergencias(explicacao, recomendacao="Desative a opção.", *, a=None, ctx=None):
    geracao = Geracao(explicacao=explicacao, recomendacao=recomendacao, citacoes=[1])
    return verificar_fidelidade(geracao, a or achado(), ctx or contexto(1)).divergencias


def test_numero_por_extenso_errado_e_divergencia():
    # O caso do spike de 29/09: a evidência dizia 4 tabelas, o 3B escreveu "duas".
    assert _divergencias("O modelo tem duas tabelas de data automáticas.") == [
        "número 2 ausente do achado e dos trechos"
    ]


def test_numero_certo_nao_diverge():
    assert _divergencias("O modelo tem quatro tabelas automáticas.") == []
    assert _divergencias("O modelo tem 4 tabelas automáticas.") == []


def test_numero_presente_so_no_trecho_e_aceito():
    ctx = [trecho_de_contexto(1, "Each hidden table adds 7 columns.")]
    assert _divergencias("Cada tabela oculta tem 7 colunas.", ctx=ctx) == []


def test_numero_por_extenso_em_ingles_no_trecho_e_aceito():
    ctx = [trecho_de_contexto(1, "It creates three hidden tables.")]
    assert _divergencias("Cria três tabelas ocultas.", ctx=ctx) == []


def test_decimal_com_virgula_casa_com_ponto():
    a = achado(mensagem="A coluna ocupa 12.5 MB.")
    assert _divergencias("A coluna ocupa 12,5 MB.", a=a) == []


def test_um_e_uma_nao_sao_numeros():
    assert _divergencias("Uma tabela de datas resolve um problema.") == []


def test_numero_dentro_de_nome_nao_e_extraido():
    a = achado(objeto="LocalDateTable_1", mensagem="A tabela 'LocalDateTable_1' é automática.")
    assert _divergencias("A tabela LocalDateTable_1 é automática.", a=a) == []


def test_nome_com_maiusculas_trocadas_e_aceito():
    a = achado(objeto="Vendas[Total]", tipo_objeto="medida", mensagem="A medida Vendas[Total] divide com /.")
    assert _divergencias("A medida vendas[TOTAL] usa o operador /.", a=a) == []


def test_nome_inventado_e_divergencia():
    assert _divergencias("Corrija a medida [Margem].") == ["nome [Margem] ausente do achado e dos trechos"]


def test_nome_entre_aspas_presente_no_achado_e_aceito():
    a = achado(objeto="DateTableTemplate_0eab", mensagem="A tabela oculta 'DateTableTemplate_0eab' foi gerada.")
    assert _divergencias("A tabela ‘DateTableTemplate_0eab’ é automática.", a=a) == []


def test_detalhe_nao_serializavel_nao_quebra():
    a = achado(detalhe={"caminho": Path("x/y"), "conjunto": {3}})
    assert _divergencias("Há 3 itens.", a=a) == []


def test_divergencias_nao_se_repetem():
    assert _divergencias("Duas tabelas e duas colunas.") == ["número 2 ausente do achado e dos trechos"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_fidelidade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise.fidelidade'`

- [ ] **Step 3: Implementar**

`core/analise/fidelidade.py`:

```python
"""Fidelidade à evidência: números e nomes da resposta precisam aparecer no
achado ou nos trechos do contexto.

Critério nascido no spike de 29/09 (ADR-002): o 3B escreveu "duas tabelas"
quando a evidência dizia quatro, e passou nos critérios de tempo e de citação.
É uma heurística de superfície — não pega erro de sentido com números certos e
pode acusar um número derivado corretamente (8 − 4 = 4) —, por isso registra e
não descarta.
"""

import json
import re

from core.analise.base import Fidelidade, Geracao, TrechoDeContexto
from core.rules.base import Achado
from rag.texto import normalizar

_NUMERO = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?!\w)")
_PALAVRA = re.compile(r"[a-zà-ü]+")
EXTENSO_PT = {
    "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}
"""De dois a dez. `um`/`uma` ficam de fora: são artigos na maior parte das vezes."""
EXTENSO_EN = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
"""Só do lado da fonte: os trechos são em inglês, a resposta é em português."""
_NOMES = (
    re.compile(r"(?:'[^'\n]+'|[\w.-]+)?\[[^\]\n]+\]"),  # Tabela[Coluna], 'Tabela X'[Coluna], [Medida]
    re.compile(r"'([^'\n]{2,80})'"),
    re.compile(r'"([^"\n]{2,80})"'),
    re.compile(r"`([^`\n]{2,80})`"),
)
_ASPAS_RETAS = {"’": "'", "‘": "'", "“": '"', "”": '"'}


def _retas(texto: str) -> str:
    for de, para in _ASPAS_RETAS.items():
        texto = texto.replace(de, para)
    return texto


def _numeros(texto: str, extenso: dict[str, int]) -> list[float]:
    valores = [float(n.replace(",", ".")) for n in _NUMERO.findall(texto)]
    valores += [float(extenso[p]) for p in _PALAVRA.findall(normalizar(texto)) if p in extenso]
    return valores


def _nomes(texto: str) -> list[str]:
    nomes: list[str] = []
    for padrao in _NOMES:
        for casado in padrao.finditer(texto):
            nomes.append(casado.group(1) if padrao.groups else casado.group(0))
    return nomes


def _comparavel(texto: str) -> str:
    """Sem maiúsculas e sem aspas simples: `'Dim Data'[Data]` e `Dim Data[Data]`
    são o mesmo objeto."""
    return normalizar(texto).replace("'", "")


def _fonte(achado: Achado, contexto: list[TrechoDeContexto]) -> str:
    evidencia = achado.evidencia
    partes = [
        achado.mensagem,
        evidencia.objeto,
        evidencia.tabela or "",
        evidencia.trecho or "",
        json.dumps(evidencia.detalhe, ensure_ascii=False, default=str),
        *(t.texto for t in contexto),
    ]
    return _retas("\n".join(partes))


def verificar_fidelidade(geracao: Geracao, achado: Achado, contexto: list[TrechoDeContexto]) -> Fidelidade:
    resposta = _retas(f"{geracao.explicacao}\n{geracao.recomendacao}")
    fonte = _fonte(achado, contexto)
    numeros_da_fonte = set(_numeros(fonte, {**EXTENSO_EN, **EXTENSO_PT}))
    fonte_comparavel = _comparavel(fonte)

    divergencias: list[str] = []
    for valor in _numeros(resposta, EXTENSO_PT):
        if valor not in numeros_da_fonte:
            divergencias.append(f"número {valor:g} ausente do achado e dos trechos")
    for nome in _nomes(resposta):
        if _comparavel(nome) not in fonte_comparavel:
            divergencias.append(f"nome {nome} ausente do achado e dos trechos")
    return Fidelidade(divergencias=list(dict.fromkeys(divergencias)))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_fidelidade.py -q`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add core/analise/fidelidade.py tests/test_analise_fidelidade.py
git commit -m "feat(analise): verificacao de fidelidade a evidencia"
```

---

### Task 6: Prompt e esquema

**Files:**
- Create: `core/analise/prompt.py`
- Test: `tests/test_analise_prompt.py`

**Interfaces:**
- Consumes: `TrechoDeContexto` (Task 1); `RegraMeta`, `Achado`; `cabecalho_de` (`rag.chunking`).
- Produces: `ESQUEMA: dict`; `SISTEMA: str`; `LIMITE_TRECHO_CODIGO = 1500`; `montar_mensagens(meta, achado, contexto) -> list[dict[str, str]]` (papéis `system` e `user`).

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_analise_prompt.py`:

```python
"""Prompt da geração: o LLM explica um achado já decidido e cita pelo número."""

from pathlib import Path

from core.analise.prompt import ESQUEMA, LIMITE_TRECHO_CODIGO, montar_mensagens
from fabricas_analise import achado, contexto, meta


def test_duas_mensagens_sistema_e_usuario():
    assert [m["role"] for m in montar_mensagens(meta(), achado(), contexto(1))] == ["system", "user"]


def test_sistema_fixa_o_papel_do_llm():
    sistema = montar_mensagens(meta(), achado(), contexto(1))[0]["content"]
    assert "NÃO decide" in sistema
    assert "1 a 3" in sistema
    assert "português do Brasil" in sistema


def test_usuario_traz_o_achado_e_os_trechos_numerados():
    usuario = montar_mensagens(meta(), achado(), contexto(2))[1]["content"]
    assert "MOD-001" in usuario
    assert "O modelo tem 4 tabelas de data automáticas." in usuario
    assert "[1] Página 1 › Seção" in usuario
    assert "[2] Página 2 › Seção" in usuario


def test_trecho_de_codigo_longo_e_cortado():
    usuario = montar_mensagens(meta(), achado(trecho="X" * 3000), contexto(1))[1]["content"]
    assert "X" * LIMITE_TRECHO_CODIGO + " […]" in usuario
    assert "X" * (LIMITE_TRECHO_CODIGO + 1) not in usuario


def test_achado_sem_trecho_nem_detalhe_omite_as_secoes():
    usuario = montar_mensagens(meta(), achado(), contexto(1))[1]["content"]
    assert "TRECHO DO MODELO" not in usuario
    assert "DETALHE" not in usuario


def test_detalhe_nao_serializavel_nao_quebra():
    usuario = montar_mensagens(meta(), achado(detalhe={"p": Path("a/b"), "s": {1}}), contexto(1))[1]["content"]
    assert "DETALHE" in usuario


def test_esquema_exige_os_tres_campos_e_limita_citacoes():
    assert set(ESQUEMA["required"]) == {"explicacao", "recomendacao", "citacoes"}
    citacoes = ESQUEMA["properties"]["citacoes"]
    assert (citacoes["minItems"], citacoes["maxItems"], citacoes["items"]["type"]) == (1, 3, "integer")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_prompt.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise.prompt'`

- [ ] **Step 3: Implementar**

`core/analise/prompt.py`:

```python
"""Prompt da geração (ADR-003): a regra já decidiu, o LLM só explica e cita.

Os trechos ficam em inglês, como o corpus (ADR-002, C-6); a resposta é pedida em
português. A citação é pelo número do trecho: o código traduz para página e
seção, e um 7B não precisa copiar URLs.
"""

import json

from core.analise.base import TrechoDeContexto
from core.rules.base import Achado, RegraMeta
from rag.chunking import cabecalho_de

LIMITE_TRECHO_CODIGO = 1500

ESQUEMA = {
    "type": "object",
    "properties": {
        "explicacao": {"type": "string"},
        "recomendacao": {"type": "string"},
        "citacoes": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 3},
    },
    "required": ["explicacao", "recomendacao", "citacoes"],
}

SISTEMA = """Você é um auditor de modelos semânticos do Power BI.
Uma regra determinística JÁ detectou o problema descrito pelo usuário. Você NÃO decide se o problema existe: sua tarefa é explicá-lo e recomendar a correção.
Use somente as informações do achado e dos trechos de documentação numerados. Não invente números, nomes de objetos nem fatos.
Responda em português do Brasil, em JSON, com:
- "explicacao": por que isso é um problema neste modelo;
- "recomendacao": o que fazer, de forma acionável;
- "citacoes": de 1 a 3 números dos trechos que sustentam a explicação.
Explicação e recomendação juntas devem ter no máximo 120 palavras."""


def _cortar(codigo: str) -> str:
    if len(codigo) <= LIMITE_TRECHO_CODIGO:
        return codigo
    return codigo[:LIMITE_TRECHO_CODIGO] + " […]"


def _usuario(meta: RegraMeta, achado: Achado, contexto: list[TrechoDeContexto]) -> str:
    evidencia = achado.evidencia
    partes = [
        f"REGRA: {meta.id} — {meta.titulo} (categoria {meta.categoria})",
        f"OBJETO: {evidencia.tipo_objeto} {evidencia.objeto}",
        f"ACHADO: {achado.mensagem}",
    ]
    if evidencia.trecho:
        partes.append(f"TRECHO DO MODELO:\n{_cortar(evidencia.trecho)}")
    if evidencia.detalhe:
        detalhe = json.dumps(evidencia.detalhe, ensure_ascii=False, default=str, sort_keys=True)
        partes.append(f"DETALHE: {detalhe}")
    trechos = "\n\n".join(
        f"[{t.numero}] {cabecalho_de(t.titulo, t.caminho)}\n{t.texto}" for t in contexto
    )
    partes.append(f"TRECHOS DE DOCUMENTAÇÃO\n{trechos}")
    return "\n\n".join(partes)


def montar_mensagens(meta: RegraMeta, achado: Achado, contexto: list[TrechoDeContexto]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": _usuario(meta, achado, contexto)},
    ]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_prompt.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add core/analise/prompt.py tests/test_analise_prompt.py
git commit -m "feat(analise): prompt e esquema JSON da geracao"
```

---

### Task 7: Cliente do Ollama

**Files:**
- Create: `core/analise/llm.py`
- Test: `tests/test_analise_llm.py`

**Interfaces:**
- Produces: `ErroDeLLM`; `RespostaLLM(texto: str, segundos: float)`; protocolo `LLMClient` com `nome: str`, `aquecer() -> None`, `gerar(mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM`; `ClienteOllama(modelo=MODELO_PADRAO, url=URL_OLLAMA, timeout=TIMEOUT_S)`; constantes `URL_OLLAMA`, `MODELO_PADRAO`, `NUM_CTX`, `SEED`, `TIMEOUT_S`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_analise_llm.py`:

```python
"""Cliente do Ollama, com `urlopen` substituído: corpo enviado e falhas."""

import io
import json
import urllib.error

import pytest

from core.analise import llm
from core.analise.llm import ClienteOllama, ErroDeLLM


class UrlopenFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta
        self.erro = erro
        self.pedidos = []

    def __call__(self, pedido, timeout):
        self.pedidos.append((pedido, timeout))
        if self.erro is not None:
            raise self.erro
        return io.BytesIO(json.dumps(self.resposta).encode("utf-8"))


def _instalar(monkeypatch, **kw) -> UrlopenFalso:
    falso = UrlopenFalso(**kw)
    monkeypatch.setattr(llm.urllib.request, "urlopen", falso)
    return falso


def test_gerar_envia_esquema_contexto_temperatura_e_semente(monkeypatch):
    falso = _instalar(monkeypatch, resposta={"message": {"content": '{"a": 1}'}})
    resposta = ClienteOllama("qwen-teste").gerar([{"role": "user", "content": "oi"}], {"type": "object"})
    pedido, timeout = falso.pedidos[0]
    corpo = json.loads(pedido.data)
    assert pedido.full_url == "http://127.0.0.1:11434/api/chat"
    assert (corpo["model"], corpo["stream"], corpo["format"]) == ("qwen-teste", False, {"type": "object"})
    assert corpo["messages"] == [{"role": "user", "content": "oi"}]
    assert corpo["options"] == {"num_ctx": 4096, "temperature": 0, "seed": 42}
    assert timeout == 120
    assert resposta.texto == '{"a": 1}'
    assert resposta.segundos >= 0


def test_aquecer_nao_envia_esquema(monkeypatch):
    falso = _instalar(monkeypatch, resposta={"message": {"content": "ok"}})
    ClienteOllama().aquecer()
    assert "format" not in json.loads(falso.pedidos[0][0].data)


def test_timeout_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, erro=TimeoutError("timed out"))
    with pytest.raises(ErroDeLLM, match="não respondeu"):
        ClienteOllama().gerar([], {})


def test_conexao_recusada_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, erro=urllib.error.URLError("connection refused"))
    with pytest.raises(ErroDeLLM, match="não respondeu"):
        ClienteOllama().aquecer()


def test_modelo_ausente_nomeia_o_modelo(monkeypatch):
    corpo = io.BytesIO(b'{"error":"model \'qwen-x\' not found"}')
    _instalar(monkeypatch, erro=urllib.error.HTTPError("http://x", 404, "Not Found", {}, corpo))
    with pytest.raises(ErroDeLLM, match="404.*qwen-x"):
        ClienteOllama("qwen-x").aquecer()


def test_resposta_sem_conteudo_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, resposta={"done": True})
    with pytest.raises(ErroDeLLM, match="message"):
        ClienteOllama().gerar([], {})
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_llm.py -q`
Expected: FAIL — `ImportError: cannot import name 'llm' from 'core.analise'`

- [ ] **Step 3: Implementar**

`core/analise/llm.py`:

```python
"""Cliente do LLM (ADR-002): Ollama local, atrás de um protocolo.

O protocolo deixa os testes rodarem com um LLM falso e mantém aberta a troca por
uma API paga sem mexer no resto do pipeline. Temperatura 0 e semente fixa: a
mesma auditoria repetida dá a mesma resposta, o que a avaliação acadêmica pede
(o spike usou 0,2).
"""

import json
import time
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel

URL_OLLAMA = "http://127.0.0.1:11434"
MODELO_PADRAO = "qwen2.5:7b-instruct-q4_K_M"
NUM_CTX = 4096
"""O 7B em Q4_K_M ocupa ~5,3 GB dos 6 GB de VRAM com este contexto (spike de
29/09); aumentá-lo empurraria camadas para a CPU."""
SEED = 42
TIMEOUT_S = 120


class ErroDeLLM(Exception):
    """O LLM não respondeu, ou respondeu algo que não é uma resposta do chat."""


class RespostaLLM(BaseModel):
    texto: str
    segundos: float


class LLMClient(Protocol):
    nome: str

    def aquecer(self) -> None: ...

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM: ...


class ClienteOllama:
    def __init__(self, modelo: str = MODELO_PADRAO, url: str = URL_OLLAMA, timeout: float = TIMEOUT_S) -> None:
        self.nome = modelo
        self.url = url
        self.timeout = timeout

    def _corpo(self, mensagens: list[dict[str, str]], esquema: dict | None = None) -> dict:
        corpo = {
            "model": self.nome,
            "messages": mensagens,
            "stream": False,
            "options": {"num_ctx": NUM_CTX, "temperature": 0, "seed": SEED},
        }
        if esquema is not None:
            corpo["format"] = esquema
        return corpo

    def _chamar(self, corpo: dict) -> dict:
        pedido = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                return json.loads(resposta.read())
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", "replace")[:200]
            raise ErroDeLLM(f"o Ollama respondeu HTTP {erro.code} para o modelo {self.nome}: {detalhe}") from erro
        except OSError as erro:  # URLError, recusa de conexão e timeout são OSError
            raise ErroDeLLM(f"o Ollama não respondeu em {self.url}: {erro}") from erro
        except json.JSONDecodeError as erro:
            raise ErroDeLLM(f"o Ollama devolveu algo que não é JSON: {erro}") from erro

    def aquecer(self) -> None:
        """Carrega o modelo na VRAM fora da medição: a carga custa dezenas de
        segundos uma vez por sessão, não por achado (ressalva de método do spike)."""
        self._chamar(self._corpo([{"role": "user", "content": "Responda apenas: ok"}]))

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM:
        inicio = time.perf_counter()
        dados = self._chamar(self._corpo(mensagens, esquema))
        segundos = time.perf_counter() - inicio
        try:
            texto = dados["message"]["content"]
        except (KeyError, TypeError) as erro:
            raise ErroDeLLM("resposta do Ollama sem message.content") from erro
        return RespostaLLM(texto=texto, segundos=round(segundos, 2))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_llm.py -q`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add core/analise/llm.py tests/test_analise_llm.py
git commit -m "feat(analise): cliente do Ollama com esquema, temperatura 0 e semente"
```

---

### Task 8: Enriquecimento de um achado

**Files:**
- Create: `core/analise/enriquecimento.py`
- Modify: `tests/fabricas_analise.py` (acrescentar `LLMFalso`, `resposta`, `RESPOSTA_BOA`)
- Test: `tests/test_analise_enriquecimento.py`

**Interfaces:**
- Consumes: `montar_contexto` (Task 3), `validar` (Task 4), `verificar_fidelidade` (Task 5), `ESQUEMA`, `montar_mensagens` (Task 6), `LLMClient`, `ErroDeLLM`, `RespostaLLM` (Task 7), `AchadoEnriquecido` (Task 1).
- Produces: `enriquecer(achado: Achado, meta: RegraMeta, *, base: BaseRag, gabarito: Gabarito, llm: LLMClient) -> AchadoEnriquecido`. Em fábricas: `LLMFalso(*respostas, falha_no_aquecimento=False)` com `nome="llm-falso"`, `chamadas`, `aquecimentos`; `resposta(...) -> str`; `RESPOSTA_BOA`.

- [ ] **Step 1: Acrescentar as fábricas**

Ao fim de `tests/fabricas_analise.py` (imports no topo: `import json` e `from core.analise.llm import ErroDeLLM, RespostaLLM`):

```python
def resposta(
    explicacao: str = "As tabelas automáticas aumentam o tamanho do modelo sem necessidade.",
    recomendacao: str = "Desative a opção global de data/hora automática.",
    citacoes: tuple[int, ...] = (1,),
) -> str:
    return json.dumps(
        {"explicacao": explicacao, "recomendacao": recomendacao, "citacoes": list(citacoes)}, ensure_ascii=False
    )


RESPOSTA_BOA = resposta()


class LLMFalso:
    """Devolve as respostas roteirizadas, em ordem; depois delas, `RESPOSTA_BOA`.
    Uma exceção na lista é levantada no lugar da resposta."""

    nome = "llm-falso"

    def __init__(self, *respostas, falha_no_aquecimento: bool = False) -> None:
        self.respostas = list(respostas)
        self.falha_no_aquecimento = falha_no_aquecimento
        self.chamadas: list[list[dict[str, str]]] = []
        self.aquecimentos = 0

    def aquecer(self) -> None:
        self.aquecimentos += 1
        if self.falha_no_aquecimento:
            raise ErroDeLLM("o Ollama não respondeu em http://127.0.0.1:11434")

    def gerar(self, mensagens, esquema) -> RespostaLLM:
        self.chamadas.append(mensagens)
        proxima = self.respostas.pop(0) if self.respostas else RESPOSTA_BOA
        if isinstance(proxima, Exception):
            raise proxima
        return RespostaLLM(texto=proxima, segundos=0.5)
```

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_analise_enriquecimento.py`:

```python
"""Enriquecimento de um achado: contexto → LLM → validação → fidelidade."""

from core.analise.enriquecimento import enriquecer
from core.analise.llm import ErroDeLLM
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta, resposta


def _enriquecer(llm):
    return enriquecer(achado(), meta(), base=base_padrao(), gabarito=gabarito(), llm=llm)


def test_resposta_valida_vira_achado_gerado():
    r = _enriquecer(LLMFalso(resposta(citacoes=(1, 2))))
    assert r.situacao == "gerado"
    assert r.cita_ancora is True
    assert r.fidelidade.divergencias == []
    assert (r.modelo, r.segundos) == ("llm-falso", 0.5)
    assert r.contexto[0].origem == "ancora"


def test_citar_so_complementar_nao_cita_a_ancora():
    r = _enriquecer(LLMFalso(resposta(citacoes=(2,))))
    assert (r.situacao, r.cita_ancora) == ("gerado", False)


def test_resposta_invalida_cai_na_recomendacao_padrao():
    r = _enriquecer(LLMFalso(resposta(citacoes=(9,))))
    assert (r.situacao, r.motivo_descarte) == ("sem_fundamentacao", "citacao_inexistente")
    assert r.recomendacao_final(meta()) == meta().recomendacao_padrao
    assert r.segundos == 0.5


def test_erro_do_llm_vira_erro_llm_e_preserva_o_contexto():
    r = _enriquecer(LLMFalso(ErroDeLLM("timeout")))
    assert (r.situacao, r.motivo_descarte, r.segundos) == ("sem_fundamentacao", "erro_llm", None)
    assert r.contexto[0].origem == "ancora"


def test_divergencia_de_fidelidade_nao_descarta():
    r = _enriquecer(LLMFalso(resposta(explicacao="O modelo tem duas tabelas automáticas.")))
    assert r.situacao == "gerado"
    assert r.fidelidade.divergencias == ["número 2 ausente do achado e dos trechos"]


def test_prompt_enviado_traz_a_ancora_como_trecho_1():
    llm = LLMFalso()
    _enriquecer(llm)
    assert "[1] T › Seção\nYou should disable the auto date time option" in llm.chamadas[0][1]["content"]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_enriquecimento.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analise.enriquecimento'`

- [ ] **Step 4: Implementar**

`core/analise/enriquecimento.py`:

```python
"""Enriquecimento de um achado (ADR-003): o LLM explica e cita; se a resposta não
passa na validação, o achado sai com a recomendação padrão da regra."""

import logging

from core.analise.base import AchadoEnriquecido
from core.analise.contexto import montar_contexto
from core.analise.fidelidade import verificar_fidelidade
from core.analise.llm import ErroDeLLM, LLMClient
from core.analise.prompt import ESQUEMA, montar_mensagens
from core.analise.validacao import validar
from core.rules.base import Achado, RegraMeta
from rag.avaliacao import Gabarito
from rag.indice import BaseRag

logger = logging.getLogger(__name__)


def enriquecer(
    achado: Achado, meta: RegraMeta, *, base: BaseRag, gabarito: Gabarito, llm: LLMClient
) -> AchadoEnriquecido:
    contexto = montar_contexto(meta, achado, base, gabarito)
    comum = dict(achado=achado, contexto=contexto, modelo=llm.nome)
    try:
        resposta = llm.gerar(montar_mensagens(meta, achado, contexto), ESQUEMA)
    except ErroDeLLM as erro:
        logger.warning("LLM falhou no achado %s/%s: %s", achado.id_regra, achado.evidencia.objeto, erro)
        return AchadoEnriquecido(**comum, situacao="sem_fundamentacao", motivo_descarte="erro_llm")

    geracao, motivo = validar(resposta.texto, len(contexto))
    if geracao is None:
        return AchadoEnriquecido(
            **comum, situacao="sem_fundamentacao", motivo_descarte=motivo, segundos=resposta.segundos
        )
    return AchadoEnriquecido(
        **comum,
        geracao=geracao,
        situacao="gerado",
        cita_ancora=1 in geracao.citacoes,
        fidelidade=verificar_fidelidade(geracao, achado, contexto),
        segundos=resposta.segundos,
    )
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_enriquecimento.py -q`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add core/analise/enriquecimento.py tests/fabricas_analise.py tests/test_analise_enriquecimento.py
git commit -m "feat(analise): enriquecimento de um achado com descarte e fidelidade"
```

---

### Task 9: `run_audit()` e o comando

**Files:**
- Create: `core/auditoria.py`
- Test: `tests/test_auditoria.py`

**Interfaces:**
- Consumes: `enriquecer` (Task 8); `ErroDeContexto`, `carregar_gabaritos`, `verificar_ancoras` (Task 3); `ClienteOllama`, `ErroDeLLM`, `LLMClient`, `MODELO_PADRAO` (Task 7); `BaseRag`, `ErroDeIndice` (Task 2); `abrir_pbip`, `ErroEstruturaPbip`; `ler_modelo`; `avaliar`, `ResultadoRegras`; `REGISTRO` (`core.rules.todas`); `RAIZ_REPO` (`rag.avaliacao`).
- Produces: `ErroDeAuditoria`; `ResultadoAuditoria`; `run_audit(pasta_pbip, *, llm, base, registro=None, gabaritos=None) -> ResultadoAuditoria`; `nome_do_projeto(caminho) -> str`; `resumir(resultado) -> str`; `gravar(resultado, pasta=None) -> Path`; `main(argv=None) -> int`; `PASTA_SAIDA`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_auditoria.py`:

```python
"""Auditoria de ponta a ponta com LLM falso e base sintética."""

import pytest

from conftest import escrever_pbip, modelo_tmsl, tabela
from core import auditoria
from core.analise.contexto import ErroDeContexto
from core.analise.llm import ErroDeLLM
from core.auditoria import ErroDeAuditoria, ResultadoAuditoria, gravar, resumir, run_audit
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta, resposta


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(
        meta(),
        lambda modelo: [
            achado(objeto=t.nome, mensagem=f"A tabela '{t.nome}' foi gerada automaticamente.")
            for t in modelo.tabelas
        ],
    )
    return registro


def _pbip(tmp_path, tabelas=("LocalDateTable_1", "LocalDateTable_2")):
    return escrever_pbip(tmp_path, model_bim=modelo_tmsl([tabela(n) for n in tabelas]))


def _auditar(tmp_path, tabelas=("LocalDateTable_1", "LocalDateTable_2"), llm=None):
    llm = llm or LLMFalso()
    resultado = run_audit(
        _pbip(tmp_path, tabelas), llm=llm, base=base_padrao(), registro=_registro(),
        gabaritos={"MOD-001": gabarito()},
    )
    return resultado, llm


def test_auditoria_enriquece_cada_achado(tmp_path):
    resultado, llm = _auditar(tmp_path)
    assert (resultado.projeto, resultado.modelo_llm) == ("Minimal", "llm-falso")
    assert [a.achado.evidencia.objeto for a in resultado.achados] == ["LocalDateTable_1", "LocalDateTable_2"]
    assert all(a.situacao == "gerado" for a in resultado.achados)
    assert (llm.aquecimentos, len(llm.chamadas)) == (1, 2)
    assert resultado.regras.regras_executadas == 1
    assert resultado.regras.achados == []


def test_pbip_sem_achados_nao_chama_o_llm(tmp_path):
    resultado, llm = _auditar(tmp_path, tabelas=())
    assert resultado.achados == []
    assert (llm.aquecimentos, llm.chamadas) == (0, [])
    assert "Achados: 0" in resumir(resultado)


def test_llm_fora_do_ar_aborta_no_aquecimento(tmp_path):
    with pytest.raises(ErroDeAuditoria, match="aquecimento"):
        _auditar(tmp_path, llm=LLMFalso(falha_no_aquecimento=True))


def test_regra_sem_ancora_aborta_na_partida_sem_chamar_o_llm(tmp_path):
    llm = LLMFalso()
    with pytest.raises(ErroDeContexto, match="MOD-001"):
        run_audit(_pbip(tmp_path), llm=llm, base=base_padrao(), registro=_registro(), gabaritos={})
    assert llm.aquecimentos == 0


def test_erro_do_llm_num_achado_nao_para_os_outros(tmp_path):
    resultado, _ = _auditar(tmp_path, llm=LLMFalso(ErroDeLLM("timeout")))
    assert [a.situacao for a in resultado.achados] == ["sem_fundamentacao", "gerado"]


def test_nome_do_projeto_de_pasta_com_espaco_e_de_zip(tmp_path):
    assert auditoria.nome_do_projeto(tmp_path / "P1_AdventureWorks Sales") == "P1_AdventureWorks Sales"
    assert auditoria.nome_do_projeto(tmp_path / "projeto.zip") == "projeto"


def test_gravar_usa_projeto_e_data_e_relê_igual(tmp_path):
    resultado, _ = _auditar(tmp_path)
    caminho = gravar(resultado, tmp_path / "saida")
    assert caminho.name == f"Minimal-{resultado.gerado_em[:10]}.json"
    assert ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8")) == resultado


def test_resumo_conta_motivos_e_e_ascii(tmp_path):
    resultado, _ = _auditar(tmp_path, llm=LLMFalso(resposta(citacoes=(9,))))
    texto = resumir(resultado)
    assert "citacao_inexistente=1" in texto
    assert "gerados: 1" in texto
    texto.encode("ascii")


def _comando_falso(monkeypatch, tmp_path, llm=None):
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(auditoria.BaseRag, "carregar", staticmethod(lambda: base_padrao()))
    monkeypatch.setattr(auditoria, "ClienteOllama", lambda modelo: llm or LLMFalso())
    monkeypatch.setattr(auditoria, "REGISTRO", _registro())
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {"MOD-001": gabarito()})


def test_comando_grava_o_json_e_imprime_em_ascii(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    assert auditoria.main([str(_pbip(tmp_path))]) == 0
    assert len(list((tmp_path / "saida").glob("Minimal-*.json"))) == 1
    capsys.readouterr().out.encode("ascii")


def test_comando_com_pbip_invalido_sai_com_erro(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    assert auditoria.main([str(tmp_path / "nao-existe")]) == 1
    assert "erro:" in capsys.readouterr().err


def test_comando_com_ollama_fora_do_ar_sai_com_erro(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path, llm=LLMFalso(falha_no_aquecimento=True))
    assert auditoria.main([str(_pbip(tmp_path))]) == 1
    assert "aquecimento" in capsys.readouterr().err
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: FAIL — `ImportError: cannot import name 'auditoria' from 'core'`

- [ ] **Step 3: Implementar**

`core/auditoria.py`:

```python
"""Auditoria de ponta a ponta (ADR-003): ingestão → parsing → regras →
recuperação → geração → validação da citação.

`python -m core.auditoria <pasta-pbip>` grava os achados enriquecidos em
`outputs/` e imprime um resumo. Desenho:
`docs/superpowers/specs/2026-10-11-geracao-com-citacao-design.md`, seção 9.
"""

import argparse
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from core.analise.base import AchadoEnriquecido
from core.analise.contexto import ErroDeContexto, carregar_gabaritos, verificar_ancoras
from core.analise.enriquecimento import enriquecer
from core.analise.llm import MODELO_PADRAO, ClienteOllama, ErroDeLLM, LLMClient
from core.ingest import ErroEstruturaPbip, abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.registry import Registro
from core.rules.runner import ResultadoRegras, avaliar
from core.rules.todas import REGISTRO
from rag.avaliacao import RAIZ_REPO, Gabarito
from rag.indice import BaseRag, ErroDeIndice

PASTA_SAIDA = RAIZ_REPO / "outputs"


class ErroDeAuditoria(Exception):
    """A auditoria não pode seguir sem produzir um resultado enganoso."""


class ResultadoAuditoria(BaseModel):
    projeto: str
    modelo_llm: str
    gerado_em: str
    regras: ResultadoRegras
    """Sem os achados, que estão enriquecidos em `achados`: falhas de regra,
    lacunas de DAX e cobertura continuam visíveis."""
    achados: list[AchadoEnriquecido]
    segundos_total: float


def nome_do_projeto(caminho: str | Path) -> str:
    caminho = Path(caminho)
    return caminho.stem if caminho.suffix.lower() == ".zip" else caminho.name


def run_audit(
    pasta_pbip: str | Path,
    *,
    llm: LLMClient,
    base: BaseRag,
    registro: Registro | None = None,
    gabaritos: dict[str, Gabarito] | None = None,
) -> ResultadoAuditoria:
    inicio = time.perf_counter()
    registro = REGISTRO if registro is None else registro
    gabaritos = carregar_gabaritos() if gabaritos is None else gabaritos
    # Partida: nenhuma chamada ao LLM se alguma regra não tiver âncora.
    verificar_ancoras(registro.ids(), gabaritos, base)

    projeto = abrir_pbip(pasta_pbip)
    resultado = avaliar(ler_modelo(projeto.model_bim), registro)
    if resultado.achados:
        try:
            llm.aquecer()
        except ErroDeLLM as erro:
            # Abortar aqui, e não marcar cada achado com `erro_llm`: um relatório
            # com tudo "sem fundamentação" pareceria resultado, e é falha de ambiente.
            raise ErroDeAuditoria(f"o LLM não respondeu no aquecimento: {erro}") from erro

    enriquecidos = [
        enriquecer(a, registro.meta(a.id_regra), base=base, gabarito=gabaritos[a.id_regra], llm=llm)
        for a in resultado.achados
    ]
    return ResultadoAuditoria(
        projeto=nome_do_projeto(pasta_pbip),
        modelo_llm=llm.nome,
        gerado_em=datetime.now().isoformat(timespec="seconds"),
        regras=resultado.model_copy(update={"achados": []}),
        achados=enriquecidos,
        segundos_total=round(time.perf_counter() - inicio, 1),
    )


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def resumir(resultado: ResultadoAuditoria) -> str:
    achados = resultado.achados
    gerados = [a for a in achados if a.situacao == "gerado"]
    motivos = Counter(a.motivo_descarte for a in achados if a.motivo_descarte)
    tempos = [a.segundos for a in achados if a.segundos is not None]
    linhas = [
        f"Projeto {resultado.projeto} - modelo {resultado.modelo_llm}",
        f"Achados: {len(achados)} | gerados: {len(gerados)} | sem fundamentacao: {len(achados) - len(gerados)}",
    ]
    if motivos:
        linhas.append("Motivos de descarte: " + ", ".join(f"{m}={n}" for m, n in sorted(motivos.items())))
    if gerados:
        citam = sum(1 for a in gerados if a.cita_ancora)
        divergem = sum(1 for a in gerados if a.fidelidade.divergencias)
        linhas.append(f"Citam a ancora: {citam}/{len(gerados)} | com divergencia de fidelidade: {divergem}")
    if tempos:
        linhas.append(f"Tempo por achado: medio {sum(tempos) / len(tempos):.1f}s, pior {max(tempos):.1f}s")
    linhas.append(f"Tempo total: {resultado.segundos_total:.1f}s")
    return _ascii("\n".join(linhas))


def gravar(resultado: ResultadoAuditoria, pasta: Path | None = None) -> Path:
    pasta = PASTA_SAIDA if pasta is None else pasta
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{resultado.projeto}-{resultado.gerado_em[:10]}.json"
    caminho.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return caminho


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.auditoria", description="Audita um projeto PBIP.")
    parser.add_argument("pasta_pbip", help="pasta do projeto PBIP ou arquivo .zip")
    parser.add_argument("--modelo", default=MODELO_PADRAO, help="modelo do Ollama")
    args = parser.parse_args(argv)
    try:
        resultado = run_audit(args.pasta_pbip, llm=ClienteOllama(args.modelo), base=BaseRag.carregar())
    except (ErroDeAuditoria, ErroDeContexto, ErroDeIndice, ErroEstruturaPbip) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    caminho = gravar(resultado)
    print(resumir(resultado))
    print(_ascii(f"Gravado em {caminho}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: 11 passed

- [ ] **Step 5: Suíte inteira e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: tudo passa.

```bash
git add core/auditoria.py tests/test_auditoria.py
git commit -m "feat: run_audit e comando python -m core.auditoria"
```

---

### Task 10: Teste real contra o Ollama, rodada no P8 e registro

**Files:**
- Modify: `pytest.ini` (registrar o marcador `ollama`)
- Create: `tests/test_analise_ollama_real.py`
- Modify: `docs/project/progress-log.md` (nova entrada ao fim)
- Modify: `docs/project/status.md` (semana 7)

**Interfaces:**
- Consumes: `ClienteOllama`, `MODELO_PADRAO` (Task 7); `ESQUEMA`, `montar_mensagens` (Task 6); `validar` (Task 4); fábricas `meta`, `achado`, `contexto`.

- [ ] **Step 1: Registrar o marcador**

`pytest.ini` passa a ser:

```ini
[pytest]
pythonpath = .
testpaths = tests
markers =
    ollama: chama o Ollama local; pulado quando ele não responde ou o modelo não está baixado
```

- [ ] **Step 2: Escrever o teste real**

`tests/test_analise_ollama_real.py`:

```python
"""Uma geração de verdade contra o Ollama local, com o modelo principal.

Pulado quando o Ollama não responde ou o modelo não está baixado: a suíte padrão
não depende de GPU. Quando roda, confirma que o esquema imposto e o prompt
produzem uma resposta que passa na validação.
"""

import json
import urllib.request

import pytest

from core.analise.llm import MODELO_PADRAO, URL_OLLAMA, ClienteOllama
from core.analise.prompt import ESQUEMA, montar_mensagens
from core.analise.validacao import validar
from fabricas_analise import achado, contexto, meta


def _modelo_disponivel() -> bool:
    try:
        with urllib.request.urlopen(f"{URL_OLLAMA}/api/tags", timeout=2) as resposta:
            modelos = json.loads(resposta.read()).get("models", [])
    except OSError:
        return False
    return any(m.get("name") == MODELO_PADRAO for m in modelos)


pytestmark = [
    pytest.mark.ollama,
    pytest.mark.skipif(not _modelo_disponivel(), reason=f"Ollama ou {MODELO_PADRAO} indisponível"),
]


def test_geracao_real_passa_na_validacao():
    ctx = contexto(2)
    cliente = ClienteOllama()
    cliente.aquecer()
    resposta = cliente.gerar(montar_mensagens(meta(), achado(), ctx), ESQUEMA)
    geracao, motivo = validar(resposta.texto, len(ctx))
    assert motivo is None, resposta.texto
    assert geracao.citacoes
```

- [ ] **Step 3: Rodar o teste real**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_ollama_real.py -v`
Expected: PASSED com o Ollama no ar (o `qwen2.5:7b-instruct-q4_K_M` está instalado); SKIPPED sem ele. Se falhar com `motivo` preenchido, ler `resposta.texto` antes de mexer em qualquer coisa — é dado da Fase 5, não bug a esconder.

- [ ] **Step 4: Suíte inteira e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: tudo passa.

```bash
git add pytest.ini tests/test_analise_ollama_real.py
git commit -m "test: geracao real contra o Ollama, pulada sem ele"
```

- [ ] **Step 5: Rodar a auditoria no P8**

Run: `.\.venv\Scripts\python.exe -m core.auditoria data/pbip/P8_contoso-vendas`
Expected: 15 achados (contagem de 11/10/2026: MOD-001 ×4, MOD-002 ×3, MOD-003 ×2, MOD-006 ×2, MOD-005, MOD-007, PERF-001, PERF-003), resumo no console e `outputs/P8_contoso-vendas-<data>.json`.

- [ ] **Step 6: Ler à mão as respostas**

Abrir o JSON gerado e ler as 15 explicações e recomendações. Anotar: citações pertinentes ou não, divergências de fidelidade verdadeiras ou falsos positivos, e qualquer erro factual que os critérios automáticos não pegaram (lição do spike).

- [ ] **Step 7: Registrar no progress-log e no status**

Acrescentar ao fim de `docs/project/progress-log.md` uma entrada `## <data> — Geração com citação (semana 7)` com: o que foi construído (pacote `core/analise/`, `BaseRag`, `run_audit`); os números medidos no P8 (achados, gerados, motivos de descarte, citam a âncora, divergências de fidelidade, tempo médio e pior, tempo total); as observações da leitura à mão; a suíte (`N testes passando`); e `**Próximo passo:**` com a revisão final da branch e o PR. Atualizar a linha da semana 7 em `docs/project/status.md`.

- [ ] **Step 8: Commit e push**

```bash
git add docs/project/progress-log.md docs/project/status.md
git commit -m "docs: geracao com citacao rodada no P8"
git push
```
