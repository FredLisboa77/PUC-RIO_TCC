# Medição da recuperação — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir 24 combinações de chunking, cabeçalho, busca e corpus com a régua congelada, escolher a vencedora pela regra fixada e construir o índice ChromaDB dela para o pipeline.

**Architecture:** Peças do pipeline em `rag/`: `chunking.py` (puro), `embeddings.py` (bge-small com cache em disco), `busca.py` (densa, BM25, RRF, todas entregando o `Buscador` da régua), `medicao.py` (grade, oráculo, decisão, resultado em `eval/results/`) e `indice.py` (Chroma do vencedor e `carregar_buscador`). A medição roda em memória; o Chroma é construído só para o vencedor.

**Tech Stack:** Python 3.11.9, Pydantic 2.13.5, numpy 2.4.6, torch 2.14.0+cpu, sentence-transformers 6.1.0, transformers 5.17.0, rank-bm25 0.2.2, chromadb 1.5.9, pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`

## Global Constraints

- Código, nomes, mensagens, testes e commits em **português**.
- Rodar pelo `.venv`: `.\.venv\Scripts\python.exe -m pytest -q`. O `.venv/pip.ini` já aponta o certificado do Norton.
- Versões fixadas: `torch==2.14.0+cpu` (índice `https://download.pytorch.org/whl/cpu`), `sentence-transformers==6.1.0`, `transformers==5.17.0`, `numpy==2.4.6`, `rank-bm25==0.2.2`, `chromadb==1.5.9`.
- Modelo: `BAAI/bge-small-en-v1.5`, **sempre em CPU** (`device="cpu"`). `HF_HOME` = `D:\dev\hf-cache` (já definido no ambiente). Prefixo de consulta: `Represent this sentence for searching relevant passages: `.
- **Nenhum teste usa rede.** Testes que precisam do modelo rodam com `HF_HUB_OFFLINE=1` e são pulados se o modelo não estiver no cache; testes de dados reais são pulados sem `rag/store/`.
- Limites: seção 350 palavras; janela 200 palavras com passo 150. RRF com k = 60 sobre os 100 primeiros de cada lista. Margem de decisão 1/9.
- Embeddings, trechos e Chroma ficam em `rag/store/` (fora do Git). O JSON de resultado vai para `eval/results/` (versionado).
- Gravação de arquivo sempre atômica (`.tmp` + `replace`); arquivos de texto com `newline="\n"`.
- Pedido do Fred: **salvar cada etapa importante** — commit e push a cada tarefa; números medidos no `progress-log.md` assim que existirem.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Branch: `fase3-medicao-recuperacao`.

## Review Focus

1. **Empate exato de pontuação** (dois trechos idênticos, ou BM25 com zero para todos) — o ranking é determinístico pela ordem dos trechos, e a medição dá o mesmo número em duas execuções. Teste na Task 3.
2. **Diferença de exatamente 1/9** entre a melhor e outra candidata — não é empate (a regra diz "a menos de 1/9"), apesar do erro de ponto flutuante das médias. Teste na Task 4.
3. **Consulta sem nenhum termo que o BM25 conheça** — devolve trechos com pontuação zero em ordem estável, sem erro e sem lista vazia. Teste na Task 3.
4. **Cache de embeddings com o número de linhas errado** (arquivo de outra versão do chunking com o mesmo nome) — recalcula, nunca devolve vetores desalinhados dos trechos. Teste na Task 2.
5. **Seção com um bloco gigante entre dois blocos pequenos** — os pequenos não se fundem por cima do gigante, e a ordem do texto é preservada. Teste na Task 1.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | Dependências novas, fixadas |
| `rag/chunking.py` | `TrechoIndexado`, estratégias `secao` e `janela`, cabeçalho, corpus `guidance` |
| `rag/embeddings.py` | `Embedder`, `EmbedderBge`, cache em disco |
| `rag/busca.py` | `tokenizar`, `IndiceBm25`, `ranquear`, `fundir_rrf`, `criar_buscador` |
| `rag/medicao.py` | `Configuracao`, `GRADE`, `verificar_oraculo`, `medir`, `decidir`, tabela, JSON, comando |
| `rag/indice.py` | `construir`, `carregar_buscador`, comando |
| `tests/test_rag_chunking.py`, `tests/test_rag_embeddings.py`, `tests/test_rag_busca.py`, `tests/test_rag_medicao.py`, `tests/test_rag_medicao_real.py` | Testes |

---

### Task 1: Chunking

**Files:**
- Create: `rag/chunking.py`
- Test: `tests/test_rag_chunking.py`

**Interfaces:**
- Consumes: `rag.extracao.PaginaExtraida`, `Secao`, `Bloco`; `rag.avaliacao.Trecho`.
- Produces (`rag/chunking.py`):
  - `LIMITE_SECAO = 350`, `JANELA = 200`, `PASSO = 150`, `Estrategia = Literal["secao", "janela"]`
  - `class TrechoIndexado(BaseModel)`: `id`, `id_pagina`, `url`, `titulo_pagina`, `ancora`, `caminho`, `texto`, `texto_indexado` (todos `str`); `para_regua() -> Trecho`
  - `cabecalho_de(titulo_pagina: str, caminho: str) -> str`
  - `trechos_por_secao(pagina, *, cabecalho: bool, limite: int = LIMITE_SECAO) -> list[TrechoIndexado]`
  - `trechos_por_janela(pagina, *, cabecalho: bool, janela: int = JANELA, passo: int = PASSO) -> list[TrechoIndexado]`
  - `montar_trechos(paginas: list[PaginaExtraida], estrategia: Estrategia, cabecalho: bool) -> list[TrechoIndexado]`
  - `ids_do_corpus_guidance(fontes: list[dict]) -> frozenset[str]`

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_chunking.py`:

```python
"""Chunking da base: estratégias `secao` e `janela`, sobre páginas sintéticas."""

from rag.avaliacao import Trecho
from rag.chunking import (
    JANELA,
    PASSO,
    cabecalho_de,
    ids_do_corpus_guidance,
    montar_trechos,
    trechos_por_janela,
    trechos_por_secao,
)
from rag.extracao import VERSAO_EXTRATOR, Bloco, PaginaExtraida, Secao


def _pagina(secoes, id_pagina="learn:x/p", titulo="Título"):
    """`secoes`: lista de (ancora, caminho, [textos dos blocos])."""
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_pagina,
        url="https://learn.microsoft.com/en-us/x/p",
        titulo=titulo,
        secoes=[
            Secao(
                ancora=ancora,
                titulo=caminho.split(" › ")[-1],
                nivel=1 if caminho == titulo else 2,
                caminho=caminho,
                blocos=[Bloco(tipo="paragrafo", texto=t) for t in textos],
            )
            for ancora, caminho, textos in secoes
        ],
        secoes_excluidas=[],
    )


def test_secao_curta_vira_um_trecho_inteiro():
    pagina = _pagina([("s", "Sec", ["um dois", "três"])])
    (trecho,) = trechos_por_secao(pagina, cabecalho=False)
    assert (trecho.id, trecho.ancora, trecho.caminho) == ("learn:x/p#s/1", "s", "Sec")
    assert trecho.texto == "um dois\ntrês"
    assert trecho.texto_indexado == trecho.texto


def test_secao_longa_e_partida_nas_fronteiras_de_bloco():
    pagina = _pagina([("s", "Sec", ["a b c", "d e f", "g h"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=5)]
    assert textos == ["a b c", "d e f\ng h"]


def test_bloco_maior_que_o_limite_e_partido_por_palavras():
    pagina = _pagina([("s", "Sec", ["1 2 3 4 5 6 7"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=3)]
    assert textos == ["1 2 3", "4 5 6", "7"]


def test_bloco_gigante_entre_pequenos_preserva_a_ordem():
    pagina = _pagina([("s", "Sec", ["a b", "1 2 3 4 5 6 7", "c d"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=3)]
    assert textos == ["a b", "1 2 3", "4 5 6", "7", "c d"]


def test_pedacos_de_secao_partida_mantem_ancora_e_ids_seguem_na_pagina():
    pagina = _pagina([("s1", "Sec 1", ["a b c", "d e f"]), ("s2", "Sec 2", ["g"])])
    trechos = trechos_por_secao(pagina, cabecalho=False, limite=3)
    assert [(t.id, t.ancora) for t in trechos] == [
        ("learn:x/p#s1/1", "s1"),
        ("learn:x/p#s1/2", "s1"),
        ("learn:x/p#s2/3", "s2"),
    ]


def test_cabecalho_entra_so_no_texto_indexado():
    pagina = _pagina([("s", "Título › Sec", ["corpo"])])
    (trecho,) = trechos_por_secao(pagina, cabecalho=True)
    assert trecho.texto == "corpo"
    assert trecho.texto_indexado == "Título › Título › Sec\ncorpo"


def test_cabecalho_da_secao_de_nivel_1_nao_repete_o_titulo():
    assert cabecalho_de("CALCULATE", "CALCULATE") == "CALCULATE"
    assert cabecalho_de("Star schema", "Snowflake dimensions") == "Star schema › Snowflake dimensions"


def test_janelas_com_sobreposicao_atravessam_secoes():
    s1 = " ".join(f"w{i}" for i in range(10))
    s2 = " ".join(f"w{i}" for i in range(10, 20))
    pagina = _pagina([("s1", "Sec 1", [s1]), ("s2", "Sec 2", [s2])])
    trechos = trechos_por_janela(pagina, cabecalho=False, janela=8, passo=6)
    assert [(t.texto.split()[0], t.texto.split()[-1], t.ancora) for t in trechos] == [
        ("w0", "w7", "s1"),
        ("w6", "w13", "s1"),
        ("w12", "w19", "s2"),
    ]
    assert [t.id for t in trechos] == ["learn:x/p#s1/1", "learn:x/p#s1/2", "learn:x/p#s2/3"]


def test_pagina_curta_vira_uma_janela_so():
    pagina = _pagina([("s", "Sec", ["a b c"])])
    assert [t.texto for t in trechos_por_janela(pagina, cabecalho=False)] == ["a b c"]


def test_toda_sequencia_curta_cabe_inteira_em_alguma_janela():
    palavras = [f"w{i}" for i in range(1000)]
    pagina = _pagina([("s", "Sec", [" ".join(palavras)])])
    janelas = [t.texto.split() for t in trechos_por_janela(pagina, cabecalho=False)]
    tamanho = JANELA - PASSO + 1
    for inicio in range(0, len(palavras) - tamanho + 1):
        alvo = palavras[inicio : inicio + tamanho]
        assert any(
            " ".join(alvo) in " ".join(janela) for janela in janelas
        ), f"sequência a partir de w{inicio} não coube em nenhuma janela"


def test_montar_trechos_percorre_as_paginas_em_ordem():
    paginas = [_pagina([("s", "Sec", ["x"])], id_pagina="learn:b"), _pagina([("s", "Sec", ["y"])], id_pagina="learn:a")]
    trechos = montar_trechos(paginas, "secao", cabecalho=False)
    assert [t.id_pagina for t in trechos] == ["learn:b", "learn:a"]
    assert montar_trechos(paginas, "janela", cabecalho=False)[0].texto == "x"


def test_corpus_guidance_inclui_guidance_e_ancoras_de_regra():
    fontes = [
        {"id": "a", "indexar": True, "origem": ["toc:power-bi/guidance"]},
        {"id": "b", "indexar": True, "origem": ["regra:MOD-005"]},
        {"id": "c", "indexar": True, "origem": ["toc:dax"]},
        {"id": "d", "indexar": False, "origem": ["toc:power-bi/guidance"]},
    ]
    assert ids_do_corpus_guidance(fontes) == frozenset({"a", "b"})


def test_para_regua_leva_texto_puro():
    (trecho,) = trechos_por_secao(_pagina([("s", "Sec", ["corpo"])]), cabecalho=True)
    assert trecho.para_regua() == Trecho(texto="corpo", id_pagina="learn:x/p", ancora="s")
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_chunking.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.chunking'`.

- [ ] **Step 2: Implementar**

Criar `rag/chunking.py`:

```python
"""Chunking da base RAG (Fase 3).

Duas estratégias, medidas pela régua: `secao` (uma seção por trecho, partindo
as longas nas fronteiras de bloco) e `janela` (janelas de palavras com
sobreposição sobre a página inteira). Limites em palavras, não em tokens, para
que o chunking seja uma função pura; um teste de dados reais confere o limite de
512 tokens do `bge-small`. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 2.
"""

from typing import Literal

from pydantic import BaseModel

from rag.avaliacao import Trecho
from rag.extracao import PaginaExtraida, Secao

LIMITE_SECAO = 350
JANELA = 200
PASSO = 150
Estrategia = Literal["secao", "janela"]


class TrechoIndexado(BaseModel):
    id: str
    id_pagina: str
    url: str
    titulo_pagina: str
    ancora: str
    caminho: str
    texto: str
    """Texto puro dos blocos: é sobre ele que a régua julga o acerto."""
    texto_indexado: str
    """O que vai para os embeddings e o BM25: o texto, com ou sem cabeçalho."""

    def para_regua(self) -> Trecho:
        return Trecho(texto=self.texto, id_pagina=self.id_pagina, ancora=self.ancora)


def cabecalho_de(titulo_pagina: str, caminho: str) -> str:
    return titulo_pagina if caminho == titulo_pagina else f"{titulo_pagina} › {caminho}"


def _trecho(pagina: PaginaExtraida, n: int, secao: Secao, texto: str, cabecalho: bool) -> TrechoIndexado:
    indexado = f"{cabecalho_de(pagina.titulo, secao.caminho)}\n{texto}" if cabecalho else texto
    return TrechoIndexado(
        id=f"{pagina.id}#{secao.ancora}/{n}",
        id_pagina=pagina.id,
        url=pagina.url,
        titulo_pagina=pagina.titulo,
        ancora=secao.ancora,
        caminho=secao.caminho,
        texto=texto,
        texto_indexado=indexado,
    )


def _por_palavras(texto: str, limite: int) -> list[str]:
    palavras = texto.split()
    return [" ".join(palavras[i : i + limite]) for i in range(0, len(palavras), limite)]


def _pedacos(secao: Secao, limite: int) -> list[str]:
    """Acumula blocos até o limite; bloco maior que o limite vira pedaços próprios,
    sem fundir os vizinhos por cima dele."""
    pedacos: list[str] = []
    atual: list[str] = []
    contagem = 0
    for bloco in secao.blocos:
        tamanho = len(bloco.texto.split())
        if tamanho > limite:
            if atual:
                pedacos.append("\n".join(atual))
                atual, contagem = [], 0
            pedacos.extend(_por_palavras(bloco.texto, limite))
            continue
        if atual and contagem + tamanho > limite:
            pedacos.append("\n".join(atual))
            atual, contagem = [], 0
        atual.append(bloco.texto)
        contagem += tamanho
    if atual:
        pedacos.append("\n".join(atual))
    return pedacos


def trechos_por_secao(
    pagina: PaginaExtraida, *, cabecalho: bool, limite: int = LIMITE_SECAO
) -> list[TrechoIndexado]:
    trechos: list[TrechoIndexado] = []
    for secao in pagina.secoes:
        for texto in _pedacos(secao, limite):
            trechos.append(_trecho(pagina, len(trechos) + 1, secao, texto, cabecalho))
    return trechos


def trechos_por_janela(
    pagina: PaginaExtraida, *, cabecalho: bool, janela: int = JANELA, passo: int = PASSO
) -> list[TrechoIndexado]:
    """Janelas sobre a página inteira. A âncora e o caminho são os da seção em que
    a janela começa."""
    palavras: list[tuple[str, Secao]] = [
        (palavra, secao)
        for secao in pagina.secoes
        for bloco in secao.blocos
        for palavra in bloco.texto.split()
    ]
    trechos: list[TrechoIndexado] = []
    inicio = 0
    while palavras:
        fim = min(inicio + janela, len(palavras))
        texto = " ".join(p for p, _ in palavras[inicio:fim])
        trechos.append(_trecho(pagina, len(trechos) + 1, palavras[inicio][1], texto, cabecalho))
        if fim >= len(palavras):
            break
        inicio += passo
    return trechos


def montar_trechos(
    paginas: list[PaginaExtraida], estrategia: Estrategia, cabecalho: bool
) -> list[TrechoIndexado]:
    cortar = trechos_por_secao if estrategia == "secao" else trechos_por_janela
    return [t for pagina in paginas for t in cortar(pagina, cabecalho=cabecalho)]


def ids_do_corpus_guidance(fontes: list[dict]) -> frozenset[str]:
    """As páginas do guidance do Power BI mais as âncoras das regras fora dele."""
    return frozenset(
        f["id"]
        for f in fontes
        if f.get("indexar")
        and any(o == "toc:power-bi/guidance" or o.startswith("regra:") for o in f.get("origem", []))
    )
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_chunking.py -q`
Expected: 13 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/chunking.py tests/test_rag_chunking.py
git commit -m "feat(rag): chunking por secao e por janela, com cabecalho de contexto opcional

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 2: Dependências e embeddings com cache

**Files:**
- Modify: `requirements.txt`
- Create: `rag/embeddings.py`
- Test: `tests/test_rag_embeddings.py`

**Interfaces:**
- Consumes: `rag.coleta.PASTA_STORE`.
- Produces (`rag/embeddings.py`):
  - `MODELO = "BAAI/bge-small-en-v1.5"`, `PREFIXO_CONSULTA`, `PASTA_EMBEDDINGS = PASTA_STORE / "embeddings"`
  - `class ErroDeEmbeddings(Exception)`
  - `class Embedder(Protocol)`: `nome: str`; `vetores(textos: list[str]) -> np.ndarray`; `vetor_consulta(texto: str) -> np.ndarray`
  - `class EmbedderBge`: implementa `Embedder`, carrega o modelo na primeira chamada; `contar_tokens(texto: str) -> int`
  - `chave_do_cache(nome_modelo: str, textos: list[str]) -> str`
  - `arquivo_do_cache(pasta: Path, nome: str, nome_modelo: str, textos: list[str]) -> Path`
  - `ler_cache(pasta, nome, nome_modelo, textos) -> np.ndarray | None`
  - `vetores_com_cache(embedder: Embedder, textos: list[str], *, pasta: Path, nome: str) -> np.ndarray`

- [ ] **Step 1: Dependências**

Acrescentar ao fim de `requirements.txt`:

```
# Fase 3 - recuperacao (torch so de CPU: a GPU fica para o LLM)
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.14.0+cpu
transformers==5.17.0
sentence-transformers==6.1.0
numpy==2.4.6
rank-bm25==0.2.2
chromadb==1.5.9
```

Run: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q`
Then: `.\.venv\Scripts\python.exe -c "import torch, sentence_transformers, rank_bm25, chromadb, numpy; print(torch.__version__, sentence_transformers.__version__, chromadb.__version__, numpy.__version__, torch.cuda.is_available())"`
Expected: `2.14.0+cpu 6.1.0 1.5.9 2.4.6 False`.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam (as dependências não quebram nada).

- [ ] **Step 2: Testes que falham**

Criar `tests/test_rag_embeddings.py`:

```python
"""Cache de embeddings. Um embedder falso e determinístico: sem modelo, sem rede."""

import numpy as np

from rag.embeddings import arquivo_do_cache, chave_do_cache, ler_cache, vetores_com_cache


class EmbedderFalso:
    def __init__(self, nome="falso"):
        self.nome = nome
        self.chamadas = 0

    def vetores(self, textos):
        self.chamadas += 1
        return np.array([[len(t), 1.0] for t in textos], dtype=np.float32)

    def vetor_consulta(self, texto):
        return np.array([len(texto), 1.0], dtype=np.float32)


def test_cache_e_gravado_e_reaproveitado(tmp_path):
    embedder = EmbedderFalso()
    primeiro = vetores_com_cache(embedder, ["a", "bb"], pasta=tmp_path, nome="secao-sem")
    segundo = vetores_com_cache(embedder, ["a", "bb"], pasta=tmp_path, nome="secao-sem")
    assert embedder.chamadas == 1
    assert np.array_equal(primeiro, segundo)
    assert arquivo_do_cache(tmp_path, "secao-sem", "falso", ["a", "bb"]).is_file()


def test_mudar_um_texto_ou_o_modelo_muda_a_chave():
    base = chave_do_cache("m", ["a", "b"])
    assert chave_do_cache("m", ["a", "c"]) != base
    assert chave_do_cache("outro", ["a", "b"]) != base
    assert chave_do_cache("m", ["ab"]) != chave_do_cache("m", ["a", "b"])


def test_texto_mudado_recalcula(tmp_path):
    embedder = EmbedderFalso()
    vetores_com_cache(embedder, ["a"], pasta=tmp_path, nome="n")
    vetores_com_cache(embedder, ["b"], pasta=tmp_path, nome="n")
    assert embedder.chamadas == 2


def test_cache_corrompido_e_recalculado_com_aviso(tmp_path, capsys):
    embedder = EmbedderFalso()
    arquivo = arquivo_do_cache(tmp_path, "n", "falso", ["a"])
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(b"lixo")
    vetores = vetores_com_cache(embedder, ["a"], pasta=tmp_path, nome="n")
    assert embedder.chamadas == 1 and vetores.shape == (1, 2)
    assert "recalculando" in capsys.readouterr().err


def test_cache_com_linhas_erradas_nunca_e_devolvido(tmp_path):
    embedder = EmbedderFalso()
    arquivo = arquivo_do_cache(tmp_path, "n", "falso", ["a", "b"])
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    np.save(arquivo, np.zeros((5, 2), dtype=np.float32))
    assert ler_cache(tmp_path, "n", "falso", ["a", "b"]) is None
    assert vetores_com_cache(embedder, ["a", "b"], pasta=tmp_path, nome="n").shape == (2, 2)


def test_ler_cache_ausente_e_none(tmp_path):
    assert ler_cache(tmp_path, "n", "falso", ["a"]) is None
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_embeddings.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.embeddings'`.

- [ ] **Step 3: Implementar**

Criar `rag/embeddings.py`:

```python
"""Embeddings da base RAG (Fase 3): `bge-small-en-v1.5` em CPU, com cache em disco.

A GPU fica para o LLM. O cache leva no nome um hash do modelo e de todos os
textos, em ordem: mudou o chunking, o extrator ou o modelo, o cache não casa e é
recalculado — nunca se devolve vetor desalinhado dos trechos.
"""

import hashlib
import os
import sys
from pathlib import Path
from typing import Protocol

import numpy as np

from rag.coleta import PASTA_STORE

MODELO = "BAAI/bge-small-en-v1.5"
PREFIXO_CONSULTA = "Represent this sentence for searching relevant passages: "
PASTA_EMBEDDINGS = PASTA_STORE / "embeddings"
TAMANHO_LOTE = 64


class ErroDeEmbeddings(Exception):
    """O modelo não pôde ser carregado."""


class Embedder(Protocol):
    nome: str

    def vetores(self, textos: list[str]) -> np.ndarray: ...

    def vetor_consulta(self, texto: str) -> np.ndarray: ...


class EmbedderBge:
    """O modelo é carregado na primeira chamada: importar o módulo não custa nada."""

    def __init__(self, nome: str = MODELO) -> None:
        self.nome = nome
        self._modelo = None

    def _carregado(self):
        if self._modelo is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._modelo = SentenceTransformer(self.nome, device="cpu")
            except Exception as erro:  # rede, cache ou versão: a mensagem diz onde olhar
                raise ErroDeEmbeddings(
                    f"não foi possível carregar {self.nome} (HF_HOME={os.environ.get('HF_HOME', '<padrão>')}): {erro}"
                ) from erro
        return self._modelo

    def vetores(self, textos: list[str]) -> np.ndarray:
        return self._carregado().encode(
            textos,
            batch_size=TAMANHO_LOTE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(textos) > 1000,
        ).astype(np.float32)

    def vetor_consulta(self, texto: str) -> np.ndarray:
        return self.vetores([PREFIXO_CONSULTA + texto])[0]

    def contar_tokens(self, texto: str) -> int:
        return len(self._carregado().tokenizer(texto)["input_ids"])


def chave_do_cache(nome_modelo: str, textos: list[str]) -> str:
    resumo = hashlib.sha256(nome_modelo.encode("utf-8"))
    for texto in textos:
        resumo.update(b"\x00")
        resumo.update(texto.encode("utf-8"))
    return resumo.hexdigest()[:16]


def arquivo_do_cache(pasta: Path, nome: str, nome_modelo: str, textos: list[str]) -> Path:
    return pasta / f"{nome}-{chave_do_cache(nome_modelo, textos)}.npy"


def ler_cache(pasta: Path, nome: str, nome_modelo: str, textos: list[str]) -> np.ndarray | None:
    arquivo = arquivo_do_cache(pasta, nome, nome_modelo, textos)
    if not arquivo.is_file():
        return None
    try:
        vetores = np.load(arquivo)
    except (OSError, ValueError) as erro:
        print(f"aviso: cache ilegível {arquivo.name} ({erro}); recalculando", file=sys.stderr)
        return None
    if vetores.ndim != 2 or vetores.shape[0] != len(textos):
        print(f"aviso: cache {arquivo.name} com forma {vetores.shape}; recalculando", file=sys.stderr)
        return None
    return vetores


def vetores_com_cache(embedder: Embedder, textos: list[str], *, pasta: Path, nome: str) -> np.ndarray:
    vetores = ler_cache(pasta, nome, embedder.nome, textos)
    if vetores is not None:
        return vetores
    vetores = np.asarray(embedder.vetores(textos), dtype=np.float32)
    arquivo = arquivo_do_cache(pasta, nome, embedder.nome, textos)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_name(arquivo.name + ".tmp")
    with open(temporario, "wb") as saida:
        np.save(saida, vetores)
    temporario.replace(arquivo)
    return vetores
```

- [ ] **Step 4: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_embeddings.py -q`
Expected: 6 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 5: Commit e push**

```bash
git add requirements.txt rag/embeddings.py tests/test_rag_embeddings.py
git commit -m "feat(rag): embeddings bge-small em CPU com cache em disco; dependencias da recuperacao

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 3: Busca densa, BM25 e híbrida

**Files:**
- Create: `rag/busca.py`
- Test: `tests/test_rag_busca.py`

**Interfaces:**
- Consumes: Task 1 (`TrechoIndexado`); Task 2 (`Embedder`); `rag.avaliacao.Buscador`, `Trecho`.
- Produces (`rag/busca.py`):
  - `K_FUSAO = 100`, `K_RRF = 60`, `TipoBusca = Literal["densa", "bm25", "hibrida"]`
  - `tokenizar(texto: str) -> list[str]`
  - `class IndiceBm25`: `__init__(textos: list[str])`; `pontuacoes(consulta: str) -> np.ndarray`
  - `ranquear(pontuacoes: np.ndarray, mascara: np.ndarray | None, k: int) -> list[int]`
  - `fundir_rrf(listas: list[list[int]], k: int) -> list[int]`
  - `mascara_de_paginas(trechos, paginas: frozenset[str] | None) -> np.ndarray | None`
  - `criar_buscador(tipo: TipoBusca, trechos: list[TrechoIndexado], *, vetores: np.ndarray | None = None, embedder: Embedder | None = None, indice_bm25: IndiceBm25 | None = None, paginas: frozenset[str] | None = None) -> Buscador`

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_busca.py`:

```python
"""Buscas densa, BM25 e híbrida, com vetores feitos à mão."""

import numpy as np
import pytest

from rag.busca import (
    K_RRF,
    IndiceBm25,
    criar_buscador,
    fundir_rrf,
    ranquear,
    tokenizar,
)
from rag.chunking import TrechoIndexado


def _trecho(i, texto, pagina="learn:p"):
    return TrechoIndexado(
        id=f"{pagina}#s/{i}",
        id_pagina=pagina,
        url="u",
        titulo_pagina="T",
        ancora="s",
        caminho="S",
        texto=texto,
        texto_indexado=texto,
    )


TRECHOS = [
    _trecho(1, "divide by zero with the DIVIDE function"),
    _trecho(2, "star schema dimension tables", pagina="learn:q"),
    _trecho(3, "auto date time hidden tables"),
]
VETORES = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]], dtype=np.float32)


class EmbedderFixo:
    nome = "fixo"

    def __init__(self, consulta):
        self.consulta = np.asarray(consulta, dtype=np.float32)

    def vetores(self, textos):
        raise AssertionError("a busca não recalcula os vetores dos trechos")

    def vetor_consulta(self, texto):
        return self.consulta


def test_tokenizar_em_minusculas_letras_e_digitos():
    assert tokenizar("Auto date/time, DIVIDE(x, 0)") == ["auto", "date", "time", "divide", "x", "0"]


def test_ranquear_por_pontuacao_com_desempate_pela_ordem():
    assert ranquear(np.array([0.5, 0.9, 0.5, 0.1]), None, 3) == [1, 0, 2]


def test_ranquear_respeita_mascara_e_k():
    mascara = np.array([True, False, True, True])
    assert ranquear(np.array([0.5, 0.9, 0.5, 0.1]), mascara, 2) == [0, 2]


def test_densa_ordena_pelo_produto_escalar():
    buscar = criar_buscador("densa", TRECHOS, vetores=VETORES, embedder=EmbedderFixo([0.0, 1.0]))
    assert [t.id_pagina for t in buscar("q", 2)] == ["learn:q", "learn:p"]
    assert buscar("q", 2)[1].texto == TRECHOS[2].texto


def test_bm25_favorece_o_termo_exato():
    buscar = criar_buscador("bm25", TRECHOS, indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]))
    assert buscar("DIVIDE function", 1)[0].texto == TRECHOS[0].texto


def test_bm25_sem_termo_conhecido_devolve_em_ordem_estavel():
    buscar = criar_buscador("bm25", TRECHOS, indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]))
    assert [t.texto for t in buscar("xyzzy", 3)] == [t.texto for t in TRECHOS]


def test_conta_do_rrf():
    # d0: posições 1 e 2; d1: posição 2 e ausente; d2: ausente e posição 1
    assert fundir_rrf([[0, 1], [2, 0]], 3) == [0, 2, 1]
    assert 1 / (K_RRF + 1) + 1 / (K_RRF + 2) > 1 / (K_RRF + 1)


def test_hibrida_funde_as_duas_listas():
    buscar = criar_buscador(
        "hibrida",
        TRECHOS,
        vetores=VETORES,
        embedder=EmbedderFixo([0.0, 1.0]),
        indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]),
    )
    # densa: [1, 2, 0]; bm25 para "auto date": [2, ...] → 2 vence na fusão
    assert buscar("auto date", 1)[0].texto == TRECHOS[2].texto


def test_filtro_de_paginas_vale_nas_tres_buscas():
    paginas = frozenset({"learn:p"})
    indice = IndiceBm25([t.texto_indexado for t in TRECHOS])
    for tipo in ("densa", "bm25", "hibrida"):
        buscar = criar_buscador(
            tipo, TRECHOS, vetores=VETORES, embedder=EmbedderFixo([0.0, 1.0]), indice_bm25=indice, paginas=paginas
        )
        assert {t.id_pagina for t in buscar("star schema", 3)} == {"learn:p"}, tipo


def test_nunca_mais_que_k():
    buscar = criar_buscador("densa", TRECHOS, vetores=VETORES, embedder=EmbedderFixo([1.0, 0.0]))
    assert len(buscar("q", 2)) == 2


def test_empate_exato_e_deterministico():
    gemeos = [_trecho(1, "igual"), _trecho(2, "igual")]
    vetores = np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    buscar = criar_buscador("densa", gemeos, vetores=vetores, embedder=EmbedderFixo([1.0, 0.0]))
    assert [buscar("q", 2)[0].ancora, len(buscar("q", 2))] == ["s", 2]
    assert criar_buscador("densa", gemeos, vetores=vetores, embedder=EmbedderFixo([1.0, 0.0]))("q", 2) == buscar("q", 2)


def test_busca_sem_o_que_precisa_falha_ao_criar():
    with pytest.raises(ValueError, match="densa"):
        criar_buscador("densa", TRECHOS)
    with pytest.raises(ValueError, match="bm25"):
        criar_buscador("bm25", TRECHOS)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_busca.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.busca'`.

- [ ] **Step 2: Implementar**

Criar `rag/busca.py`:

```python
"""Buscas da base RAG (Fase 3): densa, BM25 e híbrida (RRF).

Cada uma entrega um `rag.avaliacao.Buscador`, a interface que a régua mede e que
o pipeline vai usar. Empates são resolvidos pela ordem dos trechos: o ranking é
determinístico. Desenho: `docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`,
seção 4.
"""

import re
from typing import Literal

import numpy as np
from rank_bm25 import BM25Okapi

from rag.avaliacao import Buscador, Trecho
from rag.chunking import TrechoIndexado
from rag.embeddings import Embedder

K_FUSAO = 100
K_RRF = 60
"""Cormack, Clarke & Büttcher (2009)."""
TipoBusca = Literal["densa", "bm25", "hibrida"]

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenizar(texto: str) -> list[str]:
    return _TOKEN.findall(texto.lower())


class IndiceBm25:
    def __init__(self, textos: list[str]) -> None:
        self._bm25 = BM25Okapi([tokenizar(t) for t in textos])

    def pontuacoes(self, consulta: str) -> np.ndarray:
        return np.asarray(self._bm25.get_scores(tokenizar(consulta)), dtype=np.float64)


def ranquear(pontuacoes: np.ndarray, mascara: np.ndarray | None, k: int) -> list[int]:
    """Os k maiores; empate desfeito pela posição (a menor primeiro)."""
    indices = np.arange(len(pontuacoes)) if mascara is None else np.flatnonzero(mascara)
    ordem = np.lexsort((indices, -pontuacoes[indices]))
    return [int(i) for i in indices[ordem][:k]]


def fundir_rrf(listas: list[list[int]], k: int) -> list[int]:
    pontos: dict[int, float] = {}
    for lista in listas:
        for posicao, indice in enumerate(lista, 1):
            pontos[indice] = pontos.get(indice, 0.0) + 1 / (K_RRF + posicao)
    return sorted(pontos, key=lambda i: (-pontos[i], i))[:k]


def mascara_de_paginas(trechos: list[TrechoIndexado], paginas: frozenset[str] | None) -> np.ndarray | None:
    if paginas is None:
        return None
    return np.array([t.id_pagina in paginas for t in trechos], dtype=bool)


def criar_buscador(
    tipo: TipoBusca,
    trechos: list[TrechoIndexado],
    *,
    vetores: np.ndarray | None = None,
    embedder: Embedder | None = None,
    indice_bm25: IndiceBm25 | None = None,
    paginas: frozenset[str] | None = None,
) -> Buscador:
    if tipo in ("densa", "hibrida") and (vetores is None or embedder is None):
        raise ValueError(f"busca {tipo}: a densa precisa de vetores e embedder")
    if tipo in ("bm25", "hibrida") and indice_bm25 is None:
        raise ValueError(f"busca {tipo}: a bm25 precisa de indice_bm25")
    mascara = mascara_de_paginas(trechos, paginas)

    def densa(consulta: str, k: int) -> list[int]:
        return ranquear(vetores @ embedder.vetor_consulta(consulta), mascara, k)

    def bm25(consulta: str, k: int) -> list[int]:
        return ranquear(indice_bm25.pontuacoes(consulta), mascara, k)

    def hibrida(consulta: str, k: int) -> list[int]:
        return fundir_rrf([densa(consulta, K_FUSAO), bm25(consulta, K_FUSAO)], k)

    ranking = {"densa": densa, "bm25": bm25, "hibrida": hibrida}[tipo]

    def buscar(consulta: str, k: int) -> list[Trecho]:
        return [trechos[i].para_regua() for i in ranking(consulta, k)]

    return buscar
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_busca.py -q`
Expected: 13 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/busca.py tests/test_rag_busca.py
git commit -m "feat(rag): busca densa, BM25 e hibrida por RRF, com ranking deterministico

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 4: Grade, oráculo, medição e regra de decisão

**Files:**
- Create: `rag/medicao.py`
- Test: `tests/test_rag_medicao.py`

**Interfaces:**
- Consumes: Tasks 1–3; `rag.avaliacao.ConjuntoAvaliacao`, `Metricas`, `ResultadoConsulta`, `avaliar`; `rag.texto.normalizar`.
- Produces (`rag/medicao.py`):
  - `MARGEM = 1 / 9`; `TipoCorpus = Literal["completo", "guidance"]`
  - `class Configuracao(BaseModel, frozen)`: `chunking: Estrategia`, `cabecalho: bool`, `busca: TipoBusca`, `corpus: TipoCorpus`; propriedades `nome: str`, `complexidade: int`, `variante: str` (`"<chunking>-<com|sem>"`)
  - `GRADE: list[Configuracao]` (24)
  - `class ResultadoConfiguracao(BaseModel)`: `configuracao`, `macro: Metricas`, `micro: Metricas`, `por_tipo: dict[str, Metricas]`, `por_regra: dict[str, Metricas]`, `erros: list[ResultadoConsulta]`
  - `class Decisao(BaseModel)`: `vencedora: Configuracao`, `empatadas: list[str]`, `justificativa: str`, `aviso_corpus: str | None`
  - `class ErroDeMedicao(Exception)`
  - `verificar_oraculo(trechos: list[TrechoIndexado], conjunto: ConjuntoAvaliacao) -> list[str]` (regras cuja frase-marca não está inteira em nenhum trecho da página âncora)
  - `medir(conjunto, *, trechos: dict[str, list[TrechoIndexado]], vetores: dict[str, np.ndarray], embedder: Embedder, paginas_guidance: frozenset[str], grade: list[Configuracao] = GRADE) -> list[ResultadoConfiguracao]` (as chaves de `trechos` e `vetores` são `Configuracao.variante`)
  - `decidir(resultados: list[ResultadoConfiguracao]) -> Decisao`
  - `formatar_tabela(resultados, decisao) -> str`

O oráculo da spec ("um recuperador que devolve os trechos da seção âncora dá acerto@1 = 1,0") é equivalente a: existe, na página âncora, um trecho cujo texto contém a frase-marca. Na janela, o trecho que contém a frase pode começar na seção anterior; por isso o oráculo olha a página inteira, não só os trechos com a âncora da seção.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_medicao.py`:

```python
"""Grade, oráculo, medição e regra de decisão, sobre dados sintéticos."""

import numpy as np
import pytest

from rag.avaliacao import ConjuntoAvaliacao, Consulta, Gabarito, Metricas
from rag.chunking import TrechoIndexado
from rag.medicao import (
    GRADE,
    MARGEM,
    Configuracao,
    ResultadoConfiguracao,
    decidir,
    formatar_tabela,
    medir,
    verificar_oraculo,
)


def test_grade_tem_24_combinacoes_distintas():
    assert len(GRADE) == 24
    assert len({c.nome for c in GRADE}) == 24
    assert {c.variante for c in GRADE} == {"secao-sem", "secao-com", "janela-sem", "janela-com"}


def test_complexidade():
    assert Configuracao(chunking="secao", cabecalho=False, busca="densa", corpus="completo").complexidade == 0
    assert Configuracao(chunking="secao", cabecalho=False, busca="bm25", corpus="completo").complexidade == 0
    assert Configuracao(chunking="janela", cabecalho=True, busca="hibrida", corpus="completo").complexidade == 3


def _metricas(acerto5, mrr=0.5):
    return Metricas(
        consultas=9,
        acerto={1: acerto5 / 2, 3: acerto5, 5: acerto5, 10: acerto5},
        precisao={1: 0.1, 3: 0.1, 5: 0.1, 10: 0.1},
        mrr=mrr,
    )


def _resultado(chunking="secao", cabecalho=False, busca="densa", corpus="completo", acerto5=0.5, mrr=0.5):
    m = _metricas(acerto5, mrr)
    return ResultadoConfiguracao(
        configuracao=Configuracao(chunking=chunking, cabecalho=cabecalho, busca=busca, corpus=corpus),
        macro=m,
        micro=m,
        por_tipo={"regra": m},
        por_regra={"R1": m},
        erros=[],
    )


def test_vence_a_maior_macro_acerto5_quando_a_diferenca_e_grande():
    decisao = decidir([_resultado(acerto5=4 / 9), _resultado(busca="hibrida", acerto5=6 / 9)])
    assert decisao.vencedora.busca == "hibrida"


def test_dentro_da_margem_vence_a_mais_simples():
    decisao = decidir([_resultado(acerto5=5 / 9), _resultado(busca="hibrida", cabecalho=True, acerto5=5.9 / 9)])
    assert decisao.vencedora.busca == "densa"
    assert len(decisao.empatadas) == 2


def test_diferenca_de_exatamente_uma_regra_nao_e_empate():
    melhor = sum([1.0] * 6 + [0.0] * 3) / 9
    outra = sum([1.0] * 5 + [0.0] * 4) / 9
    assert melhor - outra == pytest.approx(MARGEM)
    decisao = decidir([_resultado(acerto5=outra), _resultado(busca="hibrida", acerto5=melhor)])
    assert decisao.vencedora.busca == "hibrida"


def test_desempate_por_mrr_e_depois_pela_ordem_fixa():
    por_mrr = decidir([_resultado(busca="densa", acerto5=0.5, mrr=0.4), _resultado(busca="bm25", acerto5=0.5, mrr=0.6)])
    assert por_mrr.vencedora.busca == "bm25"
    por_ordem = decidir([_resultado(busca="bm25", acerto5=0.5), _resultado(busca="densa", acerto5=0.5)])
    assert por_ordem.vencedora.busca == "densa"


def test_corpus_guidance_nunca_vence_sozinho_mas_avisa():
    decisao = decidir([_resultado(acerto5=3 / 9), _resultado(corpus="guidance", acerto5=7 / 9)])
    assert decisao.vencedora.corpus == "completo"
    assert decisao.aviso_corpus is not None and "guidance" in decisao.aviso_corpus


def test_sem_aviso_quando_guidance_nao_supera_pela_margem():
    assert decidir([_resultado(acerto5=5 / 9), _resultado(corpus="guidance", acerto5=5.5 / 9)]).aviso_corpus is None


def _trecho(texto, pagina="learn:p", ancora="s", n=1):
    return TrechoIndexado(
        id=f"{pagina}#{ancora}/{n}", id_pagina=pagina, url="u", titulo_pagina="T",
        ancora=ancora, caminho="S", texto=texto, texto_indexado=texto,
    )


CONJUNTO = ConjuntoAvaliacao(
    gabaritos=[Gabarito(id_regra="R1", frase_marca="alpha beta", id_pagina="learn:p", ancora="s")],
    consultas=[Consulta(id="REGRA/R1", tipo="regra", id_regra="R1", texto="q")],
)


def test_oraculo_passa_quando_a_frase_esta_inteira_num_trecho_da_pagina():
    assert verificar_oraculo([_trecho("x Alpha  beta y", ancora="outra")], CONJUNTO) == []


def test_oraculo_acusa_frase_partida_ou_em_outra_pagina():
    partida = [_trecho("x alpha", n=1), _trecho("beta y", n=2)]
    assert verificar_oraculo(partida, CONJUNTO) == ["R1"]
    assert verificar_oraculo([_trecho("alpha beta", pagina="learn:outra")], CONJUNTO) == ["R1"]


class EmbedderFixo:
    nome = "fixo"

    def vetores(self, textos):
        raise AssertionError

    def vetor_consulta(self, texto):
        return np.array([1.0, 0.0], dtype=np.float32)


def test_medir_roda_cada_configuracao_da_grade_pedida():
    trechos = [_trecho("alpha beta"), _trecho("other", pagina="learn:q", n=2)]
    vetores = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    variantes = {"secao-sem": trechos}
    grade = [
        Configuracao(chunking="secao", cabecalho=False, busca=b, corpus=c)
        for b in ("densa", "bm25", "hibrida")
        for c in ("completo", "guidance")
    ]
    resultados = medir(
        CONJUNTO,
        trechos=variantes,
        vetores={"secao-sem": vetores},
        embedder=EmbedderFixo(),
        paginas_guidance=frozenset({"learn:q"}),
        grade=grade,
    )
    por_nome = {r.configuracao.nome: r for r in resultados}
    assert len(resultados) == 6
    assert por_nome["secao-sem-densa-completo"].macro.acerto[1] == 1.0
    assert por_nome["secao-sem-densa-guidance"].macro.acerto[10] == 0.0
    assert por_nome["secao-sem-densa-guidance"].erros[0].id == "REGRA/R1"


def test_tabela_marca_a_vencedora():
    resultados = [_resultado(acerto5=5 / 9), _resultado(busca="bm25", acerto5=2 / 9)]
    texto = formatar_tabela(resultados, decidir(resultados))
    assert "secao-sem-densa-completo" in texto and "*" in texto
    assert "0.556" in texto
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.medicao'`.

- [ ] **Step 2: Implementar**

Criar `rag/medicao.py`:

```python
"""Medição da recuperação (Fase 3).

Mede as 24 combinações de chunking, cabeçalho, busca e corpus com a régua
congelada e escolhe a vencedora pela regra fixada antes de medir. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 5.
"""

from typing import Literal

import numpy as np
from pydantic import BaseModel

from rag.avaliacao import ConjuntoAvaliacao, Metricas, ResultadoConsulta, avaliar
from rag.busca import IndiceBm25, TipoBusca, criar_buscador
from rag.chunking import Estrategia, TrechoIndexado
from rag.embeddings import Embedder
from rag.texto import normalizar

MARGEM = 1 / 9
"""Uma regra em nove: diferença menor que isso é ruído nesta régua."""
_EPS = 1e-9
TipoCorpus = Literal["completo", "guidance"]
_ORDEM_BUSCA = {"densa": 0, "bm25": 1, "hibrida": 2}


class ErroDeMedicao(Exception):
    """A medição não pode seguir sem medir algo errado."""


class Configuracao(BaseModel):
    model_config = {"frozen": True}

    chunking: Estrategia
    cabecalho: bool
    busca: TipoBusca
    corpus: TipoCorpus

    @property
    def variante(self) -> str:
        return f"{self.chunking}-{'com' if self.cabecalho else 'sem'}"

    @property
    def nome(self) -> str:
        return f"{self.variante}-{self.busca}-{self.corpus}"

    @property
    def complexidade(self) -> int:
        return int(self.busca == "hibrida") + int(self.chunking == "janela") + int(self.cabecalho)


GRADE = [
    Configuracao(chunking=chunking, cabecalho=cabecalho, busca=busca, corpus=corpus)
    for chunking in ("secao", "janela")
    for cabecalho in (False, True)
    for busca in ("densa", "bm25", "hibrida")
    for corpus in ("completo", "guidance")
]


class ResultadoConfiguracao(BaseModel):
    configuracao: Configuracao
    macro: Metricas
    micro: Metricas
    por_tipo: dict[str, Metricas]
    por_regra: dict[str, Metricas]
    erros: list[ResultadoConsulta]


class Decisao(BaseModel):
    vencedora: Configuracao
    empatadas: list[str]
    justificativa: str
    aviso_corpus: str | None = None


def verificar_oraculo(trechos: list[TrechoIndexado], conjunto: ConjuntoAvaliacao) -> list[str]:
    """Regras cuja frase-marca não está inteira em nenhum trecho da página âncora.
    Lista vazia = o chunking não parte nenhuma frase-marca."""
    falhas = []
    for gabarito in conjunto.gabaritos:
        alvo = normalizar(gabarito.frase_marca)
        if not any(t.id_pagina == gabarito.id_pagina and alvo in normalizar(t.texto) for t in trechos):
            falhas.append(gabarito.id_regra)
    return falhas


def medir(
    conjunto: ConjuntoAvaliacao,
    *,
    trechos: dict[str, list[TrechoIndexado]],
    vetores: dict[str, np.ndarray],
    embedder: Embedder,
    paginas_guidance: frozenset[str],
    grade: list[Configuracao] = GRADE,
) -> list[ResultadoConfiguracao]:
    indices_bm25: dict[str, IndiceBm25] = {}
    resultados = []
    for configuracao in grade:
        variante = configuracao.variante
        if configuracao.busca != "densa" and variante not in indices_bm25:
            indices_bm25[variante] = IndiceBm25([t.texto_indexado for t in trechos[variante]])
        buscar = criar_buscador(
            configuracao.busca,
            trechos[variante],
            vetores=vetores.get(variante),
            embedder=embedder,
            indice_bm25=indices_bm25.get(variante),
            paginas=paginas_guidance if configuracao.corpus == "guidance" else None,
        )
        relatorio = avaliar(buscar, conjunto)
        resultados.append(
            ResultadoConfiguracao(
                configuracao=configuracao,
                macro=relatorio.macro,
                micro=relatorio.micro,
                por_tipo=relatorio.por_tipo,
                por_regra=relatorio.por_regra,
                erros=relatorio.erros,
            )
        )
    return resultados


def _chave_de_simplicidade(r: ResultadoConfiguracao) -> tuple:
    c = r.configuracao
    return (c.complexidade, -r.macro.mrr, _ORDEM_BUSCA[c.busca], c.chunking != "secao", c.cabecalho)


def decidir(resultados: list[ResultadoConfiguracao]) -> Decisao:
    candidatas = [r for r in resultados if r.configuracao.corpus == "completo"]
    if not candidatas:
        raise ErroDeMedicao("nenhuma combinação do corpus completo foi medida")
    melhor = max(r.macro.acerto[5] for r in candidatas)
    empatadas = [r for r in candidatas if melhor - r.macro.acerto[5] < MARGEM - _EPS]
    vencedora = min(empatadas, key=_chave_de_simplicidade)
    justificativa = (
        f"maior macro acerto@5 do corpus completo = {melhor:.3f}; {len(empatadas)} combinação(ões) a menos "
        f"de 1/9 dela; vence a de menor complexidade ({vencedora.configuracao.complexidade}), "
        f"desempate por macro MRR@10 e pela ordem fixa"
    )
    aviso = None
    guidance = [r for r in resultados if r.configuracao.corpus == "guidance"]
    if guidance:
        melhor_guidance = max(guidance, key=lambda r: r.macro.acerto[5])
        if melhor_guidance.macro.acerto[5] - melhor >= MARGEM - _EPS:
            aviso = (
                f"o corpus guidance ({melhor_guidance.configuracao.nome}, macro acerto@5 "
                f"{melhor_guidance.macro.acerto[5]:.3f}) supera o completo ({melhor:.3f}) por 1/9 ou mais: "
                f"a decisão sobre o corpus é do Fred"
            )
    return Decisao(
        vencedora=vencedora.configuracao,
        empatadas=[r.configuracao.nome for r in empatadas],
        justificativa=justificativa,
        aviso_corpus=aviso,
    )


def formatar_tabela(resultados: list[ResultadoConfiguracao], decisao: Decisao) -> str:
    cabecalho = (
        f"{'':2}{'combinação':34} {'@1':>6} {'@3':>6} {'@5':>6} {'@10':>6} {'MRR':>6} "
        f"{'micro@5':>8} {'regra@5':>8} {'achado@5':>9}"
    )
    linhas = [cabecalho]
    for r in resultados:
        marca = "* " if r.configuracao == decisao.vencedora else "  "
        m = r.macro
        linhas.append(
            f"{marca}{r.configuracao.nome:34} {m.acerto[1]:6.3f} {m.acerto[3]:6.3f} {m.acerto[5]:6.3f} "
            f"{m.acerto[10]:6.3f} {m.mrr:6.3f} {r.micro.acerto[5]:8.3f} "
            f"{r.por_tipo['regra'].acerto[5] if 'regra' in r.por_tipo else float('nan'):8.3f} "
            f"{r.por_tipo['achado'].acerto[5] if 'achado' in r.por_tipo else float('nan'):9.3f}"
        )
    linhas.append(f"Vencedora: {decisao.vencedora.nome} — {decisao.justificativa}")
    if decisao.aviso_corpus:
        linhas.append(f"AVISO: {decisao.aviso_corpus}")
    linhas.append("Precision@K não entra na decisão; na janela ela conta passagens repetidas pela sobreposição.")
    return "\n".join(linhas)
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao.py -q`
Expected: 13 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/medicao.py tests/test_rag_medicao.py
git commit -m "feat(rag): grade de 24 combinacoes, oraculo, medicao e regra de decisao fixada

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 5: Comando de medição e a medição real

**Files:**
- Modify: `rag/medicao.py` (acrescentar)
- Create: `tests/test_rag_medicao_real.py`, `eval/results/recuperacao-<AAAA-MM-DD>.json` (gerado)
- Modify: `tests/test_rag_medicao.py` (acrescentar), `docs/project/progress-log.md`

**Interfaces:**
- Consumes: Tasks 1–4; `rag.avaliacao.ARQUIVO_CONSULTAS`, `ler_conjunto`, `ler_pagina_extraida`, `RAIZ_REPO`; `rag.coleta.paginas_do_catalogo`; `rag.catalogo.ARQUIVO_FONTES`; `rag.extracao.VERSAO_EXTRATOR`; `rag.embeddings.EmbedderBge`, `vetores_com_cache`, `PASTA_EMBEDDINGS`, `MODELO`.
- Produces (`rag/medicao.py`):
  - `PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"`; `VARIANTES = ("secao-sem", "secao-com", "janela-sem", "janela-com")`
  - `carregar_paginas() -> list[PaginaExtraida]`
  - `trechos_das_variantes(paginas) -> dict[str, list[TrechoIndexado]]`
  - `ambiente(trechos: dict[str, list[TrechoIndexado]]) -> dict`
  - `gravar_resultado(caminho: Path, resultados, decisao, ambiente: dict) -> None`
  - `ler_resultado(caminho: Path) -> tuple[list[ResultadoConfiguracao], Decisao]`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Testes que falham**

Acrescentar ao import de `rag.medicao` em `tests/test_rag_medicao.py`: `gravar_resultado`, `ler_resultado`, `main`. Acrescentar `from rag import medicao as modulo_medicao`. No fim:

```python
def test_resultado_faz_ida_e_volta_em_json(tmp_path):
    resultados = [_resultado(acerto5=5 / 9), _resultado(busca="bm25", acerto5=2 / 9)]
    decisao = decidir(resultados)
    arquivo = tmp_path / "recuperacao.json"
    gravar_resultado(arquivo, resultados, decisao, {"modelo": "m"})
    lidos, decisao_lida = ler_resultado(arquivo)
    assert lidos == resultados and decisao_lida == decisao
    assert b"\r\n" not in arquivo.read_bytes()


def test_main_sem_conjunto_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_medicao, "ARQUIVO_CONSULTAS", tmp_path / "nao-existe.yaml")
    assert main([]) == 1
    assert "rag.avaliacao gerar" in capsys.readouterr().err
```

Criar `tests/test_rag_medicao_real.py`:

```python
"""A medição sobre a base real: oráculo e limite de tokens.

Pulados sem `rag/store/`. Os que usam o modelo rodam offline e são pulados se o
`bge-small` não estiver no cache do Hugging Face.
"""

import os

import pytest

from rag.avaliacao import ARQUIVO_CONSULTAS, ler_conjunto
from rag.coleta import ARQUIVO_REGISTRO
from rag.medicao import carregar_paginas, trechos_das_variantes, verificar_oraculo

pytestmark = pytest.mark.skipif(
    not ARQUIVO_REGISTRO.is_file(), reason="rag/store/ não existe (conteúdo do Learn não é versionado)"
)


@pytest.fixture(scope="module")
def variantes():
    return trechos_das_variantes(carregar_paginas())


@pytest.mark.parametrize("variante", ["secao-sem", "secao-com", "janela-sem", "janela-com"])
def test_oraculo_nenhum_chunking_parte_uma_frase_marca(variantes, variante):
    assert verificar_oraculo(variantes[variante], ler_conjunto(ARQUIVO_CONSULTAS)) == []


@pytest.fixture(scope="module")
def embedder():
    os.environ["HF_HUB_OFFLINE"] = "1"
    from rag.embeddings import EmbedderBge, ErroDeEmbeddings

    modelo = EmbedderBge()
    try:
        modelo.contar_tokens("teste")
    except ErroDeEmbeddings:
        pytest.skip("bge-small não está no cache do Hugging Face")
    return modelo


def test_nenhum_trecho_secao_passa_de_512_tokens(variantes, embedder):
    maior = max(embedder.contar_tokens(t.texto_indexado) for t in variantes["secao-com"])
    assert maior <= 512, f"maior trecho com {maior} tokens: reduzir LIMITE_SECAO"
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao.py tests/test_rag_medicao_real.py -q`
Expected: `ImportError: cannot import name 'gravar_resultado'` e `'carregar_paginas'`.

- [ ] **Step 2: Implementar**

Em `rag/medicao.py`, acrescentar aos imports:

```python
import argparse
import hashlib
import json
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from rag.avaliacao import (
    ARQUIVO_CONSULTAS,
    RAIZ_REPO,
    ErroDeAvaliacao,
    ler_conjunto,
    ler_pagina_extraida,
)
from rag.catalogo import ARQUIVO_FONTES
from rag.chunking import ids_do_corpus_guidance, montar_trechos
from rag.coleta import paginas_do_catalogo
from rag.embeddings import MODELO, PASTA_EMBEDDINGS, EmbedderBge, ErroDeEmbeddings, vetores_com_cache
from rag.extracao import VERSAO_EXTRATOR, PaginaExtraida
```

(`ConjuntoAvaliacao`, `Metricas`, `ResultadoConsulta`, `avaliar` continuam no import de `rag.avaliacao`; juntar os dois num só.) E no fim do arquivo:

```python
PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"
VARIANTES = ("secao-sem", "secao-com", "janela-sem", "janela-com")


def carregar_paginas() -> list[PaginaExtraida]:
    """As páginas indexáveis do catálogo, extraídas, em ordem de id."""
    return [ler_pagina_extraida(p.id) for p in paginas_do_catalogo(ARQUIVO_FONTES)]


def trechos_das_variantes(paginas: list[PaginaExtraida]) -> dict[str, list[TrechoIndexado]]:
    return {
        f"{estrategia}-{'com' if cabecalho else 'sem'}": montar_trechos(paginas, estrategia, cabecalho)
        for estrategia in ("secao", "janela")
        for cabecalho in (False, True)
    }


def ambiente(trechos: dict[str, list[TrechoIndexado]]) -> dict:
    return {
        "data": date.today().isoformat(),
        "modelo": MODELO,
        "versoes": {
            p: version(p) for p in ("torch", "sentence-transformers", "transformers", "rank-bm25", "chromadb", "numpy")
        },
        "trechos_por_variante": {v: len(t) for v, t in trechos.items()},
        "versao_extrator": VERSAO_EXTRATOR,
        "sha256_consultas": hashlib.sha256(ARQUIVO_CONSULTAS.read_bytes()).hexdigest(),
    }


def gravar_resultado(
    caminho: Path, resultados: list[ResultadoConfiguracao], decisao: Decisao, ambiente: dict
) -> None:
    dados = {
        "ambiente": ambiente,
        "decisao": decisao.model_dump(mode="json"),
        "resultados": [r.model_dump(mode="json") for r in resultados],
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def ler_resultado(caminho: Path) -> tuple[list[ResultadoConfiguracao], Decisao]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return (
        [ResultadoConfiguracao.model_validate(r) for r in dados["resultados"]],
        Decisao.model_validate(dados["decisao"]),
    )


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        prog="python -m rag.medicao",
        description="Mede as 24 combinações de recuperação com a régua congelada.",
    ).parse_args(argv)
    try:
        conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
        paginas = carregar_paginas()
        trechos = trechos_das_variantes(paginas)
        for variante, lista in trechos.items():
            falhas = verificar_oraculo(lista, conjunto)
            if falhas:
                raise ErroDeMedicao(f"oráculo: {variante} parte a frase-marca de {', '.join(falhas)}")
        embedder = EmbedderBge()
        vetores = {
            v: vetores_com_cache(embedder, [t.texto_indexado for t in lista], pasta=PASTA_EMBEDDINGS, nome=v)
            for v, lista in trechos.items()
        }
        fontes = __import__("yaml").safe_load(ARQUIVO_FONTES.read_text(encoding="utf-8"))
        resultados = medir(
            conjunto,
            trechos=trechos,
            vetores=vetores,
            embedder=embedder,
            paginas_guidance=ids_do_corpus_guidance(fontes),
        )
    except (ErroDeAvaliacao, ErroDeEmbeddings, ErroDeMedicao) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    decisao = decidir(resultados)
    destino = PASTA_RESULTADOS / f"recuperacao-{date.today().isoformat()}.json"
    gravar_resultado(destino, resultados, decisao, ambiente(trechos))
    print(formatar_tabela(resultados, decisao))
    print(f"Resultado gravado em {destino.relative_to(RAIZ_REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Trocar o `__import__("yaml")` por um `import yaml` no topo do arquivo, junto dos outros imports — está escrito assim aqui só para deixar explícito de onde vem.

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao.py tests/test_rag_medicao_real.py -q`
Expected: os sintéticos passam; o oráculo das 4 variantes passa; o de tokens é pulado (o modelo ainda não foi baixado).
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push do comando**

```bash
git add rag/medicao.py tests/test_rag_medicao.py tests/test_rag_medicao_real.py
git commit -m "feat(rag): python -m rag.medicao — oraculo, 24 combinacoes, decisao e resultado em eval/results

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

- [ ] **Step 5: Baixar o modelo e conferir o limite de tokens**

Run: `.\.venv\Scripts\python.exe -c "from rag.embeddings import EmbedderBge; print(EmbedderBge().contar_tokens('auto date/time'))"`
Expected: um número pequeno (≈ 7); o modelo baixa para `D:\dev\hf-cache` (~130 MB). Conferir que nada novo apareceu em `C:\Users\fredl\.cache\huggingface`.
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao_real.py -q`
Expected: todos passam, incluindo `test_nenhum_trecho_secao_passa_de_512_tokens`. Se falhar: reduzir `LIMITE_SECAO` em `rag/chunking.py` (300, depois 250) até passar, rodar a suíte, commitar `fix(rag): limite da secao reduzido para N palavras (maior trecho com X tokens)` e registrar no ledger como Ruling.

- [ ] **Step 6: Medição real**

Run: `.\.venv\Scripts\python.exe -m rag.medicao`
Expected: a tabela com 24 linhas, uma marcada com `*`, a linha "Vencedora: ..." e o JSON em `eval/results/recuperacao-<data>.json`. Primeira execução: alguns minutos (embeddings de 4 variantes em CPU). Rodar de novo deve sair em segundos (cache) e com **os mesmos números** — conferir.
Se aparecer `AVISO:` sobre o corpus: **parar** e trazer ao Fred antes de construir o índice.

Registrar no `progress-log.md`, numa nova entrada "11/10/2026 — Fase 3 — medição da recuperação": número de trechos por variante; tempo dos embeddings; a tabela (as 12 do corpus completo e as 12 do guidance); a vencedora com a justificativa; o efeito de ampliar o corpus (melhor do completo × melhor do guidance); e as consultas que erram na vencedora.

```bash
git add eval/results docs/project/progress-log.md
git commit -m "docs: medicao da recuperacao — 24 combinacoes, vencedora <nome>

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 6: Índice ChromaDB do vencedor

**Files:**
- Create: `rag/indice.py`
- Test: `tests/test_rag_indice.py`; acrescentar a `tests/test_rag_medicao_real.py`

**Interfaces:**
- Consumes: Tasks 1–5 (`Configuracao`, `ler_resultado`, `PASTA_RESULTADOS`, `carregar_paginas`, `trechos_das_variantes`); `rag.embeddings.ler_cache`, `EmbedderBge`, `Embedder`, `PASTA_EMBEDDINGS`; `rag.busca.IndiceBm25`, `fundir_rrf`, `K_FUSAO`; `rag.chunking.montar_trechos`, `TrechoIndexado`.
- Produces (`rag/indice.py`):
  - `PASTA_INDICE = PASTA_STORE / "indice"`, `ARQUIVO_TRECHOS`, `ARQUIVO_CONFIG`, `PASTA_CHROMA = PASTA_STORE / "chroma"`, `COLECAO = "base_rag"`
  - `class ErroDeIndice(Exception)`
  - `resultado_mais_recente(pasta: Path) -> Path`
  - `construir(*, pasta_resultados: Path = ..., pasta_indice: Path = ..., pasta_chroma: Path = ..., pasta_embeddings: Path = ...) -> Configuracao`
  - `carregar_buscador(embedder: Embedder | None = None, *, pasta_indice: Path = ..., pasta_chroma: Path = ...) -> Buscador`
  - `main(argv: list[str] | None = None) -> int`

O Chroma usa a distância padrão (L2). Com vetores normalizados, a ordem por L2 é a mesma do cosseno, então não é preciso configurar a métrica.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_indice.py`:

```python
"""Índice do vencedor: arquivos e falhas, sem modelo nem base real."""

import pytest

from rag.indice import ErroDeIndice, carregar_buscador, construir, resultado_mais_recente


def test_resultado_mais_recente_pega_o_ultimo_por_data(tmp_path):
    (tmp_path / "recuperacao-2026-10-11.json").write_text("{}", encoding="utf-8")
    (tmp_path / "recuperacao-2026-10-12.json").write_text("{}", encoding="utf-8")
    (tmp_path / "spike_llm.json").write_text("{}", encoding="utf-8")
    assert resultado_mais_recente(tmp_path).name == "recuperacao-2026-10-12.json"


def test_sem_resultado_de_medicao_falha_indicando_a_medicao(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.medicao"):
        resultado_mais_recente(tmp_path)


def test_construir_sem_resultado_falha(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.medicao"):
        construir(pasta_resultados=tmp_path, pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")


def test_carregar_sem_indice_falha_indicando_construir(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.indice construir"):
        carregar_buscador(pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")
```

Acrescentar ao fim de `tests/test_rag_medicao_real.py`:

```python
def test_o_indice_chroma_reproduz_a_metrica_da_medicao(embedder):
    from rag.avaliacao import avaliar
    from rag.indice import ARQUIVO_CONFIG, carregar_buscador, resultado_mais_recente
    from rag.medicao import PASTA_RESULTADOS, ler_resultado

    if not ARQUIVO_CONFIG.is_file():
        pytest.skip("índice não construído — rode `python -m rag.indice construir`")
    resultados, decisao = ler_resultado(resultado_mais_recente(PASTA_RESULTADOS))
    medido = next(r for r in resultados if r.configuracao == decisao.vencedora)
    relatorio = avaliar(carregar_buscador(embedder), ler_conjunto(ARQUIVO_CONSULTAS))
    assert relatorio.macro.acerto[5] == pytest.approx(medido.macro.acerto[5])
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.indice'`.

- [ ] **Step 2: Implementar**

Criar `rag/indice.py`:

```python
"""Índice da base RAG (Fase 3): a configuração vencedora da medição, em ChromaDB.

`python -m rag.indice construir` grava os trechos e a coleção Chroma a partir do
resultado mais recente em `eval/results/`, reaproveitando os vetores do cache.
`carregar_buscador()` é a busca que o pipeline usa. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 6.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from rag.avaliacao import Buscador, Trecho
from rag.busca import K_FUSAO, IndiceBm25, fundir_rrf
from rag.chunking import TrechoIndexado, montar_trechos
from rag.coleta import PASTA_STORE
from rag.embeddings import PASTA_EMBEDDINGS, Embedder, EmbedderBge, ler_cache
from rag.medicao import PASTA_RESULTADOS, Configuracao, carregar_paginas, ler_resultado

PASTA_INDICE = PASTA_STORE / "indice"
ARQUIVO_TRECHOS = PASTA_INDICE / "trechos.jsonl"
ARQUIVO_CONFIG = PASTA_INDICE / "config.json"
PASTA_CHROMA = PASTA_STORE / "chroma"
COLECAO = "base_rag"
LOTE_CHROMA = 1000


class ErroDeIndice(Exception):
    """O índice não pode ser construído ou carregado."""


def _cliente(pasta_chroma: Path):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(pasta_chroma), settings=Settings(anonymized_telemetry=False))


def resultado_mais_recente(pasta: Path) -> Path:
    arquivos = sorted(pasta.glob("recuperacao-*.json")) if pasta.is_dir() else []
    if not arquivos:
        raise ErroDeIndice(f"nenhum resultado em {pasta} — rode `python -m rag.medicao`")
    return arquivos[-1]


def construir(
    *,
    pasta_resultados: Path = PASTA_RESULTADOS,
    pasta_indice: Path = PASTA_INDICE,
    pasta_chroma: Path = PASTA_CHROMA,
    pasta_embeddings: Path = PASTA_EMBEDDINGS,
) -> Configuracao:
    _, decisao = ler_resultado(resultado_mais_recente(pasta_resultados))
    configuracao = decisao.vencedora
    trechos = montar_trechos(carregar_paginas(), configuracao.chunking, configuracao.cabecalho)
    textos = [t.texto_indexado for t in trechos]
    vetores = ler_cache(pasta_embeddings, configuracao.variante, EmbedderBge().nome, textos)
    if vetores is None:
        raise ErroDeIndice(f"sem cache de embeddings para {configuracao.variante} — rode `python -m rag.medicao`")

    pasta_indice.mkdir(parents=True, exist_ok=True)
    temporario = pasta_indice / (ARQUIVO_TRECHOS.name + ".tmp")
    temporario.write_text(
        "".join(t.model_dump_json() + "\n" for t in trechos), encoding="utf-8", newline="\n"
    )
    temporario.replace(pasta_indice / ARQUIVO_TRECHOS.name)

    cliente = _cliente(pasta_chroma)
    if COLECAO in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(COLECAO)
    colecao = cliente.create_collection(COLECAO)
    for inicio in range(0, len(trechos), LOTE_CHROMA):
        lote = trechos[inicio : inicio + LOTE_CHROMA]
        colecao.add(
            ids=[t.id for t in lote],
            embeddings=vetores[inicio : inicio + LOTE_CHROMA].tolist(),
            documents=[t.texto for t in lote],
            metadatas=[
                {"id_pagina": t.id_pagina, "ancora": t.ancora, "caminho": t.caminho, "url": t.url} for t in lote
            ],
        )
    (pasta_indice / ARQUIVO_CONFIG.name).write_text(
        configuracao.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return configuracao


def carregar_buscador(
    embedder: Embedder | None = None,
    *,
    pasta_indice: Path = PASTA_INDICE,
    pasta_chroma: Path = PASTA_CHROMA,
) -> Buscador:
    config = pasta_indice / ARQUIVO_CONFIG.name
    if not config.is_file():
        raise ErroDeIndice(f"índice ausente em {pasta_indice} — rode `python -m rag.indice construir`")
    configuracao = Configuracao.model_validate_json(config.read_text(encoding="utf-8"))
    linhas = (pasta_indice / ARQUIVO_TRECHOS.name).read_text(encoding="utf-8").splitlines()
    trechos = [TrechoIndexado.model_validate_json(linha) for linha in linhas if linha.strip()]
    posicao = {t.id: i for i, t in enumerate(trechos)}
    embedder = embedder or EmbedderBge()
    colecao = _cliente(pasta_chroma).get_collection(COLECAO)
    bm25 = IndiceBm25([t.texto_indexado for t in trechos]) if configuracao.busca != "densa" else None

    def densa(consulta: str, k: int) -> list[int]:
        resposta = colecao.query(
            query_embeddings=[embedder.vetor_consulta(consulta).tolist()], n_results=k, include=[]
        )
        return [posicao[i] for i in resposta["ids"][0]]

    def por_bm25(consulta: str, k: int) -> list[int]:
        pontos = bm25.pontuacoes(consulta)
        return [int(i) for i in np.lexsort((np.arange(len(pontos)), -pontos))[:k]]

    def buscar(consulta: str, k: int) -> list[Trecho]:
        if configuracao.busca == "densa":
            indices = densa(consulta, k)
        elif configuracao.busca == "bm25":
            indices = por_bm25(consulta, k)
        else:
            indices = fundir_rrf([densa(consulta, K_FUSAO), por_bm25(consulta, K_FUSAO)], k)
        return [trechos[i].para_regua() for i in indices]

    return buscar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rag.indice", description="Índice da base RAG.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("construir", help="constrói o índice da configuração vencedora da medição")
    parser.parse_args(argv)
    try:
        configuracao = construir()
    except ErroDeIndice as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"Índice construído: {configuracao.nome} → {PASTA_CHROMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

O BM25 de `carregar_buscador` repete o desempate de `rag.busca.ranquear` (pontuação, depois posição); usar `ranquear(pontos, None, k)` diretamente em vez de reescrever o `lexsort` — está escrito por extenso aqui só para mostrar a equivalência.

- [ ] **Step 3: Verificar os testes sem dados**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_indice.py -q`
Expected: 4 passam.

- [ ] **Step 4: Construir e conferir**

Run: `.\.venv\Scripts\python.exe -m rag.indice construir`
Expected: `Índice construído: <vencedora> → ...rag\store\chroma`.
Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_medicao_real.py -q`
Expected: todos passam, incluindo `test_o_indice_chroma_reproduz_a_metrica_da_medicao`. Se a métrica diferir: **parar** (superpowers:systematic-debugging) — é a diferença entre o HNSW e a busca exata, ou um desalinhamento entre trechos e vetores.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam. Conferir `git status --short`: nada de `rag/store/`.

- [ ] **Step 5: Commit e push**

```bash
git add rag/indice.py tests/test_rag_indice.py tests/test_rag_medicao_real.py
git commit -m "feat(rag): indice ChromaDB da configuracao vencedora e o buscador do pipeline

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 7: Registros

**Files:**
- Modify: `docs/adr/ADR-002-stack-tecnologica.md`, `README.md`, `docs/project/status.md`, `docs/project/progress-log.md`
- Republicar: a página do orientador (fonte em `orientador/andamento.html` no scratchpad da sessão; se tiver sumido, baixar com Artifact `read_file`, path `index.html`, tirar o esqueleto até `<title>` e republicar com `url` `https://claude.ai/code/artifact/476dde6e-9da2-4871-8cfc-afc67784f0c0`)

- [ ] **Step 1: Emenda na ADR-002**

Acrescentar ao fim de `docs/adr/ADR-002-stack-tecnologica.md` a seção "Emenda de <data> — recuperação escolhida por medição", com: o que foi medido (a grade, a régua e a regra de decisão, citando as duas specs); a tabela das 12 combinações do corpus completo (macro acerto@1/5, MRR@10); a vencedora e a justificativa; o efeito de ampliar o corpus; se a busca híbrida entrou ou não no MVP (item 3 da emenda de 09/10); e a consequência para a semana 7 (o pipeline chama `rag.indice.carregar_buscador()` e `rag.consulta.montar_consulta`).

- [ ] **Step 2: README, status e progress-log**

- `README.md`, seção "Catálogo de fontes da RAG", depois do bloco de `rag.avaliacao`:

````markdown
```powershell
python -m rag.medicao             # mede as 24 combinacoes de recuperacao e grava eval/results/
python -m rag.indice construir    # constroi o indice ChromaDB da combinacao vencedora em rag/store/
```
````

- `docs/project/status.md`: na tabela "O que já funciona", a linha da medição e do índice (vencedora e macro acerto@5); seção 8, passo 1 vira `| 1 | **Geração com o LLM e citação obrigatória (semana 7)** | A recuperação está escolhida e indexada: a seção âncora mais os trechos complementares do índice entram no prompt |`; número de testes nas seções 1, 3 e 9.
- `docs/project/progress-log.md`: completar a entrada da Task 5 com o índice construído, a equivalência conferida, o número de testes e **Próximo passo:** brainstorming da geração com citação obrigatória.

- [ ] **Step 3: Página do orientador**

Na seção 5, um parágrafo curto "A recuperação escolhida por medição" (a vencedora, o número que a decidiu, o efeito de ampliar o corpus e se a busca híbrida entrou); seção 9, passo 1 vira "Geração com o LLM e citação obrigatória"; contagem de testes no meta-row, no cartão de números e na seção 10. Republicar no mesmo endereço.

- [ ] **Step 4: Verificar, commit e push**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

```bash
git add docs README.md
git commit -m "docs: recuperacao escolhida por medicao — emenda na ADR-002

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```
