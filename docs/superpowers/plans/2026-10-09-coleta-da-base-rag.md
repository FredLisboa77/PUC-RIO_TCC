# Coleta e extração da base RAG — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Baixar as 1.420 páginas do catálogo com `indexar: true` para `rag/store/` e extrair de cada uma o texto estruturado por seção (âncora, nível, caminho, blocos tipados), pronto para o chunking.

**Architecture:** Dois comandos. `python -m rag.coleta` (único com rede) grava o HTML bruto e um registro `coleta.jsonl` retomável; `python -m rag.extracao` (offline) lê o HTML e grava um JSON por página. Núcleo puro com buscador, pausa e relógio injetados; tudo em `rag/store/`, fora do Git.

**Tech Stack:** Python 3.11.9, Pydantic 2.13.5, PyYAML 6.0.3, **beautifulsoup4 4.13.4 + soupsieve 2.7** (novas), pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-10-09-coleta-da-base-rag-design.md`

## Global Constraints

- Código, nomes, mensagens, testes e commits em **português**.
- Rodar pelo `.venv`: `.\.venv\Scripts\python.exe -m pytest -q`. Instalação de pacote: o `.venv/pip.ini` já aponta o certificado do Norton.
- Dependências novas, fixadas: `beautifulsoup4==4.13.4` e `soupsieve==2.7`. Parser sempre `"html.parser"` (biblioteca padrão; nunca lxml).
- Rede **só** via `rag.tocs.buscar_padrao` (mesmo `User-Agent`, timeout 30 s, recusa redirecionamento). **Nenhum teste usa rede.**
- Pausa padrão **1,0 s** entre requisições. **429 ou 503** interrompem na hora; **5 falhas seguidas** interrompem.
- Só entradas com `indexar: true`. O SQLBI nunca é pedido.
- Tudo o que é coletado ou extraído fica em `rag/store/` (já no `.gitignore`). **Nenhum HTML do Learn entra no Git**, nem como fixture de teste: fixtures são HTML sintético escrito à mão.
- Gravação de arquivo sempre atômica (`.tmp` + `replace`); a linha do registro só é escrita depois do arquivo.
- Pedido do Fred: **salvar cada etapa importante** — commit e push a cada tarefa; números medidos no `progress-log.md` assim que existirem.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Branch: `fase2-regras-de-dax` (o PR #1 recebe os commits).

## Review Focus

1. **Última linha do `coleta.jsonl` truncada** por desligamento no meio da escrita — a retomada não pode quebrar; a linha cortada é ignorada (só se for a última). Teste na Task 2.
2. **HTML que não decodifica como UTF-8** ou página sem `<meta>` de versão — a coleta não pode cair; metadados ausentes viram `null`. Teste na Task 2.
3. **Seção excluída com subseções** (`h2#related-content` seguido de `h3`) — as subseções também saem; uma `h2` seguinte volta a entrar. Teste na Task 4.
4. **Texto com aspas tipográficas** (`’` no Learn, `'` na transcrição das specs) — a frase-marca dos dados reais precisa casar mesmo assim. Normalização na Task 6.
5. **Registro `ok` cujo HTML foi apagado depois** — a extração nomeia o erro e indica rodar a coleta; a coleta baixa de novo. Testes nas Tasks 2 e 5.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | + `beautifulsoup4==4.13.4`, `soupsieve==2.7` |
| `rag/tocs.py` | `ErroDeRetrato` ganha `status: int \| None` |
| `rag/coleta.py` | Modelos do registro, caminhos, metadados, leitura do registro, `coletar`, resumo e comando |
| `rag/extracao.py` | Modelos da página extraída, `extrair` (pura), `extrair_tudo`, resumo e comando |
| `tests/test_rag_coleta.py`, `tests/test_rag_extracao.py`, `tests/test_rag_store_real.py` | Testes |

---

### Task 1: Dependências e o código HTTP no erro do buscador

**Files:**
- Modify: `requirements.txt`
- Modify: `rag/tocs.py` (classe `ErroDeRetrato` e `buscar_padrao`)
- Test: `tests/test_rag_tocs.py` (acrescentar)

**Interfaces:**
- Produces: `ErroDeRetrato(mensagem: str, status: int | None = None)`, com atributo `.status`. `buscar_padrao` preenche `status` com o código HTTP quando houver.

- [ ] **Step 1: Dependências**

Acrescentar ao fim de `requirements.txt`:

```
beautifulsoup4==4.13.4
soupsieve==2.7
```

Run: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q`
Then: `.\.venv\Scripts\python.exe -c "import bs4, soupsieve; print(bs4.__version__, soupsieve.__version__)"`
Expected: `4.13.4 2.7`

- [ ] **Step 2: Teste que falha**

Acrescentar a `tests/test_rag_tocs.py`:

```python
def test_erro_http_carrega_o_status(monkeypatch):
    def urlopen_falso(pedido, timeout):
        raise urllib.error.HTTPError(pedido.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato) as erro:
        buscar_padrao("https://learn.microsoft.com/en-us/dax/abs-function-dax")
    assert erro.value.status == 429


def test_erro_de_rede_tem_status_vazio(monkeypatch):
    def urlopen_falso(pedido, timeout):
        raise urllib.error.URLError("sem rota")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato) as erro:
        buscar_padrao("https://learn.microsoft.com/en-us/dax/abs-function-dax")
    assert erro.value.status is None


def test_erro_de_retrato_sem_status_continua_valendo():
    assert ErroDeRetrato("x").status is None
    assert str(ErroDeRetrato("mensagem", status=404)) == "mensagem"
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_tocs.py -q`
Expected: 3 falhas (`AttributeError: 'ErroDeRetrato' object has no attribute 'status'` / `TypeError` no construtor).

- [ ] **Step 3: Implementar**

Em `rag/tocs.py`, trocar a classe:

```python
class ErroDeRetrato(Exception):
    """Falha ao obter ou interpretar um `toc.json` ou uma página.

    `status` é o código HTTP quando houve resposta. É o que deixa a coleta
    distinguir página inexistente (404: registra e segue) de servidor pedindo
    para parar (429/503: interrompe).
    """

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status
```

Em `buscar_padrao`, as duas linhas que levantam com código passam a levar o status:

```python
            if resposta.status != 200:
                raise ErroDeRetrato(f"{url}: HTTP {resposta.status}", status=resposta.status)
```

```python
    except urllib.error.HTTPError as erro:
        raise ErroDeRetrato(f"{url}: HTTP {erro.code}", status=erro.code) from erro
```

- [ ] **Step 4: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam (299 + 3).

- [ ] **Step 5: Commit e push**

```bash
git add requirements.txt rag/tocs.py tests/test_rag_tocs.py
git commit -m "feat(rag): erro do buscador carrega o codigo HTTP; beautifulsoup4 como dependencia

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 2: Coleta — modelos, caminhos, metadados e registro

**Files:**
- Create: `rag/coleta.py`
- Test: `tests/test_rag_coleta.py`

**Interfaces:**
- Consumes: `rag.catalogo.RAIZ`, `rag.catalogo.ARQUIVO_FONTES`.
- Produces (`rag/coleta.py`):
  - `PASTA_STORE`, `PASTA_PAGINAS`, `ARQUIVO_REGISTRO` (`Path`); `PAUSA_PADRAO_S = 1.0`; `FALHAS_SEGUIDAS_MAX = 5`; `STATUS_PARAR = frozenset({429, 503})`
  - `class ErroDeColeta(Exception)`
  - `class PaginaAColetar(BaseModel)`: `id: str`, `url: str`
  - `class RegistroColeta(BaseModel)`: `id`, `url`, `situacao: Literal["ok", "erro"]`, `acessado_em: datetime`, `motivo: str | None`, `tamanho: int | None`, `sha256: str | None`, `updated_at`, `ms_date`, `git_commit_id`, `document_id` (todos `str | None`)
  - `caminho_da_pagina(pasta: Path, id_fonte: str) -> Path`
  - `metadados_da_pagina(html: str) -> dict[str, str | None]`
  - `paginas_do_catalogo(caminho: Path) -> list[PaginaAColetar]`
  - `ler_registro(caminho: Path) -> dict[str, RegistroColeta]` (última linha por id)
  - `ja_coletada(registro: RegistroColeta | None, pasta_paginas: Path) -> bool`
  - `anexar_registro(caminho: Path, registro: RegistroColeta) -> None`

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_coleta.py`:

```python
"""Coleta das páginas do catálogo.

HTML sintético escrito à mão: nenhum HTML do Learn entra no repositório (termos
de uso, spec do catálogo 5.2).
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rag.coleta import (
    ErroDeColeta,
    PaginaAColetar,
    RegistroColeta,
    anexar_registro,
    caminho_da_pagina,
    ja_coletada,
    ler_registro,
    metadados_da_pagina,
    paginas_do_catalogo,
)

AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

HTML_COM_META = """<html><head>
<meta name="updated_at" content="2026-08-04T22:03:00Z">
<meta name="ms.date" content="2026-06-29T00:00:00Z">
<meta name="git_commit_id" content="b39c707">
<meta name="document_id" content="8ad6539c">
</head><body><main id="main"><h1 id="x">X</h1></main></body></html>"""


def test_caminho_da_pagina_aninha_pelo_id():
    assert caminho_da_pagina(Path("p"), "learn:dax/calculate-function-dax") == Path(
        "p/learn/dax/calculate-function-dax.html"
    )


@pytest.mark.parametrize("id_ruim", ["sem-prefixo", "learn:", "learn:../fora", ":dax/x"])
def test_caminho_da_pagina_recusa_id_invalido(id_ruim):
    with pytest.raises(ErroDeColeta, match="id inválido"):
        caminho_da_pagina(Path("p"), id_ruim)


def test_metadados_da_pagina():
    assert metadados_da_pagina(HTML_COM_META) == {
        "updated_at": "2026-08-04T22:03:00Z",
        "ms_date": "2026-06-29T00:00:00Z",
        "git_commit_id": "b39c707",
        "document_id": "8ad6539c",
    }


def test_metadados_ausentes_viram_none():
    assert metadados_da_pagina("<html><body>sem meta</body></html>") == {
        "updated_at": None,
        "ms_date": None,
        "git_commit_id": None,
        "document_id": None,
    }


def test_paginas_do_catalogo_so_indexaveis_em_ordem(tmp_path):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(
        "- id: learn:dax/b\n  url: https://learn.microsoft.com/en-us/dax/b\n  indexar: true\n"
        "- id: sqlbi:x\n  url: https://www.sqlbi.com/articles/x/\n  indexar: false\n"
        "- id: learn:dax/a\n  url: https://learn.microsoft.com/en-us/dax/a\n  indexar: true\n",
        encoding="utf-8",
    )
    assert paginas_do_catalogo(fontes) == [
        PaginaAColetar(id="learn:dax/a", url="https://learn.microsoft.com/en-us/dax/a"),
        PaginaAColetar(id="learn:dax/b", url="https://learn.microsoft.com/en-us/dax/b"),
    ]


def test_catalogo_ausente_ou_sem_indexavel_falha(tmp_path):
    with pytest.raises(ErroDeColeta, match="rag.catalogo"):
        paginas_do_catalogo(tmp_path / "nao-existe.yaml")
    vazio = tmp_path / "sources.yaml"
    vazio.write_text("- id: sqlbi:x\n  url: u\n  indexar: false\n", encoding="utf-8")
    with pytest.raises(ErroDeColeta, match="indexar: true"):
        paginas_do_catalogo(vazio)


def _ok(id_fonte, sha="abc"):
    return RegistroColeta(
        id=id_fonte, url="u", situacao="ok", acessado_em=AGORA, tamanho=3, sha256=sha
    )


def test_registro_guarda_a_ultima_linha_de_cada_id(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    anexar_registro(caminho, RegistroColeta(id="a", url="u", situacao="erro", acessado_em=AGORA, motivo="HTTP 500"))
    anexar_registro(caminho, _ok("a"))
    anexar_registro(caminho, _ok("b"))
    registro = ler_registro(caminho)
    assert registro["a"].situacao == "ok"
    assert set(registro) == {"a", "b"}
    assert b"\r\n" not in caminho.read_bytes()


def test_registro_ausente_e_vazio(tmp_path):
    assert ler_registro(tmp_path / "nao-existe.jsonl") == {}


def test_ultima_linha_truncada_e_ignorada(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    anexar_registro(caminho, _ok("a"))
    with open(caminho, "a", encoding="utf-8") as arquivo:
        arquivo.write('{"id": "b", "url": "u", "situ')
    assert set(ler_registro(caminho)) == {"a"}


def test_linha_invalida_no_meio_falha_nomeando_a_linha(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    caminho.write_text('{"quebrada": 1}\n' + _ok("a").model_dump_json() + "\n", encoding="utf-8")
    with pytest.raises(ErroDeColeta, match="coleta.jsonl:1"):
        ler_registro(caminho)


def test_ja_coletada_exige_ok_arquivo_e_mesmo_sha256(tmp_path):
    arquivo = caminho_da_pagina(tmp_path, "learn:dax/a")
    arquivo.parent.mkdir(parents=True)
    arquivo.write_bytes(b"abc")
    sha = hashlib.sha256(b"abc").hexdigest()
    assert ja_coletada(_ok("learn:dax/a", sha), tmp_path)
    assert not ja_coletada(_ok("learn:dax/a", "outro"), tmp_path)
    assert not ja_coletada(None, tmp_path)
    erro = RegistroColeta(id="learn:dax/a", url="u", situacao="erro", acessado_em=AGORA, motivo="x")
    assert not ja_coletada(erro, tmp_path)
    arquivo.unlink()
    assert not ja_coletada(_ok("learn:dax/a", sha), tmp_path)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_coleta.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.coleta'`.

- [ ] **Step 2: Implementar**

Criar `rag/coleta.py`:

```python
"""Coleta das páginas do catálogo (Fase 3).

`python -m rag.coleta` baixa o HTML de cada página com `indexar: true` para
`rag/store/raw/paginas/` e acrescenta uma linha por tentativa em
`rag/store/coleta.jsonl`. É retomável: pula o que já está `ok` com o mesmo
`sha256`. Tudo fica fora do Git — termos de uso do Learn. Desenho:
`docs/superpowers/specs/2026-10-09-coleta-da-base-rag-design.md`.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

from rag.catalogo import RAIZ

PASTA_STORE = RAIZ / "store"
PASTA_PAGINAS = PASTA_STORE / "raw" / "paginas"
ARQUIVO_REGISTRO = PASTA_STORE / "coleta.jsonl"

PAUSA_PADRAO_S = 1.0
FALHAS_SEGUIDAS_MAX = 5
STATUS_PARAR = frozenset({429, 503})
"""O servidor pedindo para parar: a coleta interrompe na hora."""

_METAS = {
    "updated_at": "updated_at",
    "ms.date": "ms_date",
    "git_commit_id": "git_commit_id",
    "document_id": "document_id",
}


class ErroDeColeta(Exception):
    """A coleta não pode seguir sem perder algo em silêncio."""


class PaginaAColetar(BaseModel):
    id: str
    url: str


class RegistroColeta(BaseModel):
    """Uma linha de `coleta.jsonl`: uma tentativa de baixar uma página."""

    id: str
    url: str
    situacao: Literal["ok", "erro"]
    acessado_em: datetime
    motivo: str | None = None
    tamanho: int | None = None
    sha256: str | None = None
    updated_at: str | None = None
    ms_date: str | None = None
    git_commit_id: str | None = None
    document_id: str | None = None


def caminho_da_pagina(pasta: Path, id_fonte: str) -> Path:
    """`learn:dax/calculate-function-dax` → `<pasta>/learn/dax/calculate-function-dax.html`."""
    organizacao, _, caminho = id_fonte.partition(":")
    partes = caminho.split("/")
    if not organizacao or not caminho or ".." in partes or "" in partes:
        raise ErroDeColeta(f"id inválido: {id_fonte!r}")
    return pasta / organizacao / f"{caminho}.html"


def metadados_da_pagina(html: str) -> dict[str, str | None]:
    """Os metadados de versão que o Learn publica em `<meta>`; ausente vira `None`."""
    sopa = BeautifulSoup(html, "html.parser")
    saida: dict[str, str | None] = {}
    for nome, campo in _METAS.items():
        tag = sopa.find("meta", attrs={"name": nome})
        saida[campo] = tag.get("content") if tag is not None else None
    return saida


def paginas_do_catalogo(caminho: Path) -> list[PaginaAColetar]:
    if not caminho.is_file():
        raise ErroDeColeta(f"{caminho} não existe — rode `python -m rag.catalogo`")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    paginas = sorted(
        (PaginaAColetar(id=f["id"], url=f["url"]) for f in dados if f.get("indexar")),
        key=lambda p: p.id,
    )
    if not paginas:
        raise ErroDeColeta(f"{caminho}: nenhuma entrada com indexar: true")
    return paginas


def ler_registro(caminho: Path) -> dict[str, RegistroColeta]:
    """A última linha de cada id. Uma última linha cortada por desligamento no
    meio da escrita é ignorada; linha inválida em qualquer outro lugar é erro."""
    if not caminho.is_file():
        return {}
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    ultimos: dict[str, RegistroColeta] = {}
    for numero, linha in enumerate(linhas, 1):
        if not linha.strip():
            continue
        try:
            registro = RegistroColeta.model_validate_json(linha)
        except ValidationError as erro:
            if numero == len(linhas):
                break
            raise ErroDeColeta(f"{caminho.name}:{numero}: linha inválida — {erro}") from erro
        ultimos[registro.id] = registro
    return ultimos


def ja_coletada(registro: RegistroColeta | None, pasta_paginas: Path) -> bool:
    if registro is None or registro.situacao != "ok":
        return False
    arquivo = caminho_da_pagina(pasta_paginas, registro.id)
    if not arquivo.is_file():
        return False
    return hashlib.sha256(arquivo.read_bytes()).hexdigest() == registro.sha256


def anexar_registro(caminho: Path, registro: RegistroColeta) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(registro.model_dump_json() + "\n")
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_coleta.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/coleta.py tests/test_rag_coleta.py
git commit -m "feat(rag): coleta — registro retomavel, caminhos e metadados de versao

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 3: Coleta — o laço `coletar`, o resumo e o comando

**Files:**
- Modify: `rag/coleta.py` (acrescentar)
- Test: `tests/test_rag_coleta.py` (acrescentar)

**Interfaces:**
- Consumes: Task 2; `rag.tocs.ErroDeRetrato` com `.status` (Task 1); `rag.tocs.buscar_padrao`; `rag.catalogo.ARQUIVO_FONTES`.
- Produces:
  - `@dataclass class ResumoColeta`: `coletadas: list[str]`, `ja_existentes: int`, `erros: list[RegistroColeta]`, `interrompida: str | None`, `total_ok: int`, `total: int`
  - `coletar(paginas: list[PaginaAColetar], *, buscar: Callable[[str], bytes], dormir: Callable[[float], None], agora: Callable[[], datetime], pasta_paginas: Path, arquivo_registro: Path, pausa: float = PAUSA_PADRAO_S, limite: int | None = None) -> ResumoColeta`
  - `resumo_coleta(resumo: ResumoColeta) -> str`
  - `main(argv: list[str] | None = None) -> int` — sai com 1 se interrompida.

- [ ] **Step 1: Testes que falham**

Acrescentar ao import de `rag.coleta` em `tests/test_rag_coleta.py`: `coletar`, `main`, `resumo_coleta`. Acrescentar `from rag.tocs import ErroDeRetrato` e `from rag import coleta as modulo_coleta`. Acrescentar no fim:

```python
def _paginas(n):
    return [
        PaginaAColetar(id=f"learn:dax/p{i}", url=f"https://learn.microsoft.com/en-us/dax/p{i}")
        for i in range(n)
    ]


class Simulador:
    """Buscador, pausa e relógio falsos, com o que foi pedido registrado."""

    def __init__(self, falhas=None):
        self.falhas = falhas or {}
        self.pedidos = []
        self.pausas = []

    def buscar(self, url):
        self.pedidos.append(url)
        if url in self.falhas:
            raise self.falhas[url]
        return HTML_COM_META.replace("<h1 id=\"x\">X</h1>", f"<h1>{url}</h1>").encode()

    def dormir(self, segundos):
        self.pausas.append(segundos)

    def agora(self):
        return AGORA


def _coletar(sim, paginas, tmp_path, **extra):
    return coletar(
        paginas,
        buscar=sim.buscar,
        dormir=sim.dormir,
        agora=sim.agora,
        pasta_paginas=tmp_path / "paginas",
        arquivo_registro=tmp_path / "coleta.jsonl",
        **extra,
    )


def test_coleta_grava_html_e_registro_com_metadados(tmp_path):
    sim = Simulador()
    resumo = _coletar(sim, _paginas(2), tmp_path)
    assert resumo.coletadas == ["learn:dax/p0", "learn:dax/p1"]
    assert resumo.total_ok == resumo.total == 2
    registro = ler_registro(tmp_path / "coleta.jsonl")["learn:dax/p0"]
    arquivo = caminho_da_pagina(tmp_path / "paginas", "learn:dax/p0")
    assert registro.situacao == "ok"
    assert registro.sha256 == hashlib.sha256(arquivo.read_bytes()).hexdigest()
    assert registro.tamanho == len(arquivo.read_bytes())
    assert registro.updated_at == "2026-08-04T22:03:00Z"
    assert registro.acessado_em == AGORA


def test_pausa_entre_requisicoes_e_nao_antes_da_primeira(tmp_path):
    sim = Simulador()
    _coletar(sim, _paginas(3), tmp_path, pausa=1.0)
    assert sim.pausas == [1.0, 1.0]


def test_retomada_pula_o_que_ja_esta_ok(tmp_path):
    _coletar(Simulador(), _paginas(2), tmp_path)
    sim = Simulador()
    resumo = _coletar(sim, _paginas(3), tmp_path)
    assert sim.pedidos == ["https://learn.microsoft.com/en-us/dax/p2"]
    assert resumo.ja_existentes == 2
    assert resumo.total_ok == 3


def test_arquivo_apagado_ou_alterado_e_baixado_de_novo(tmp_path):
    _coletar(Simulador(), _paginas(2), tmp_path)
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/p0").unlink()
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/p1").write_bytes(b"mexido")
    sim = Simulador()
    _coletar(sim, _paginas(2), tmp_path)
    assert len(sim.pedidos) == 2


def test_erro_comum_registra_e_segue(tmp_path):
    url = "https://learn.microsoft.com/en-us/dax/p0"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP 404", status=404)})
    resumo = _coletar(sim, _paginas(3), tmp_path)
    assert resumo.coletadas == ["learn:dax/p1", "learn:dax/p2"]
    assert [e.id for e in resumo.erros] == ["learn:dax/p0"]
    assert resumo.interrompida is None
    assert ler_registro(tmp_path / "coleta.jsonl")["learn:dax/p0"].motivo.endswith("HTTP 404")


@pytest.mark.parametrize("status", [429, 503])
def test_servidor_pedindo_para_parar_interrompe_na_hora(tmp_path, status):
    url = "https://learn.microsoft.com/en-us/dax/p1"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP {status}", status=status)})
    resumo = _coletar(sim, _paginas(4), tmp_path)
    assert len(sim.pedidos) == 2
    assert resumo.interrompida and str(status) in resumo.interrompida


def test_cinco_falhas_seguidas_interrompem(tmp_path):
    paginas = _paginas(8)
    sim = Simulador({p.url: ErroDeRetrato(f"{p.url}: sem rota") for p in paginas})
    resumo = _coletar(sim, paginas, tmp_path)
    assert len(sim.pedidos) == 5
    assert "5 falhas seguidas" in resumo.interrompida


def test_sucesso_zera_a_contagem_de_falhas_seguidas(tmp_path):
    paginas = _paginas(10)
    falhas = {p.url: ErroDeRetrato(f"{p.url}: sem rota") for i, p in enumerate(paginas) if i != 4}
    resumo = _coletar(Simulador(falhas), paginas, tmp_path)
    assert resumo.interrompida is not None
    assert resumo.coletadas == ["learn:dax/p4"]
    assert len(resumo.erros) == 9


def test_limite_coleta_so_as_primeiras_pendentes(tmp_path):
    sim = Simulador()
    resumo = _coletar(sim, _paginas(5), tmp_path, limite=2)
    assert len(sim.pedidos) == 2
    assert resumo.total_ok == 2 and resumo.total == 5


def test_resumo_lista_erros_e_interrupcao(tmp_path):
    url = "https://learn.microsoft.com/en-us/dax/p0"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP 404", status=404)})
    texto = resumo_coleta(_coletar(sim, _paginas(2), tmp_path))
    assert "Coletadas nesta execução: 1" in texto
    assert "Total ok: 1 de 2" in texto
    assert "learn:dax/p0" in texto


def test_main_sem_catalogo_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_coleta, "ARQUIVO_FONTES", tmp_path / "nao-existe.yaml")
    assert main([]) == 1
    assert "rag.catalogo" in capsys.readouterr().err
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_coleta.py -q`
Expected: `ImportError: cannot import name 'coletar'`.

- [ ] **Step 2: Implementar**

Em `rag/coleta.py`, completar os imports:

```python
import argparse
import hashlib
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

from rag import tocs
from rag.catalogo import ARQUIVO_FONTES, RAIZ
```

E acrescentar no fim:

```python
@dataclass
class ResumoColeta:
    coletadas: list[str] = field(default_factory=list)
    ja_existentes: int = 0
    erros: list[RegistroColeta] = field(default_factory=list)
    interrompida: str | None = None
    total_ok: int = 0
    total: int = 0


def _gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(caminho)


def coletar(
    paginas: list[PaginaAColetar],
    *,
    buscar: Callable[[str], bytes],
    dormir: Callable[[float], None],
    agora: Callable[[], datetime],
    pasta_paginas: Path,
    arquivo_registro: Path,
    pausa: float = PAUSA_PADRAO_S,
    limite: int | None = None,
) -> ResumoColeta:
    """Baixa as páginas pendentes, uma por vez, com pausa entre requisições.

    O arquivo é gravado antes da linha do registro: uma interrupção em qualquer
    ponto deixa, no pior caso, um arquivo sem linha `ok`, que a próxima execução
    baixa de novo.
    """
    anteriores = ler_registro(arquivo_registro)
    pendentes = [p for p in paginas if not ja_coletada(anteriores.get(p.id), pasta_paginas)]
    resumo = ResumoColeta(ja_existentes=len(paginas) - len(pendentes), total=len(paginas))
    if limite is not None:
        pendentes = pendentes[:limite]

    falhas_seguidas = 0
    for indice, pagina in enumerate(pendentes):
        if indice > 0:
            dormir(pausa)
        try:
            conteudo = buscar(pagina.url)
        except tocs.ErroDeRetrato as erro:
            registro = RegistroColeta(
                id=pagina.id, url=pagina.url, situacao="erro", acessado_em=agora(), motivo=str(erro)
            )
            anexar_registro(arquivo_registro, registro)
            resumo.erros.append(registro)
            falhas_seguidas += 1
            if erro.status in STATUS_PARAR:
                resumo.interrompida = (
                    f"o servidor pediu para parar (HTTP {erro.status}) em {pagina.url}"
                )
                break
            if falhas_seguidas >= FALHAS_SEGUIDAS_MAX:
                resumo.interrompida = f"{FALHAS_SEGUIDAS_MAX} falhas seguidas; a última: {erro}"
                break
            continue

        falhas_seguidas = 0
        _gravar_atomico(caminho_da_pagina(pasta_paginas, pagina.id), conteudo)
        registro = RegistroColeta(
            id=pagina.id,
            url=pagina.url,
            situacao="ok",
            acessado_em=agora(),
            tamanho=len(conteudo),
            sha256=hashlib.sha256(conteudo).hexdigest(),
            **metadados_da_pagina(conteudo.decode("utf-8", errors="replace")),
        )
        anexar_registro(arquivo_registro, registro)
        resumo.coletadas.append(pagina.id)

    finais = ler_registro(arquivo_registro)
    resumo.total_ok = sum(1 for p in paginas if ja_coletada(finais.get(p.id), pasta_paginas))
    return resumo


def resumo_coleta(resumo: ResumoColeta) -> str:
    linhas = [
        f"Coletadas nesta execução: {len(resumo.coletadas)}",
        f"Já existentes: {resumo.ja_existentes}",
        f"Erros nesta execução: {len(resumo.erros)}",
        *(f"  {r.id}: {r.motivo}" for r in resumo.erros),
        f"Total ok: {resumo.total_ok} de {resumo.total}",
    ]
    if resumo.interrompida:
        linhas.append(f"INTERROMPIDA: {resumo.interrompida} — rode de novo para retomar")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.coleta",
        description="Baixa as páginas do catálogo (indexar: true) para rag/store/.",
    )
    parser.add_argument("--limite", type=int, default=None, help="coleta só as N primeiras pendentes")
    parser.add_argument("--pausa", type=float, default=PAUSA_PADRAO_S, help="segundos entre requisições")
    args = parser.parse_args(argv)
    try:
        resumo = coletar(
            paginas_do_catalogo(ARQUIVO_FONTES),
            buscar=tocs.buscar_padrao,
            dormir=time.sleep,
            agora=lambda: datetime.now(UTC),
            pasta_paginas=PASTA_PAGINAS,
            arquivo_registro=ARQUIVO_REGISTRO,
            pausa=args.pausa,
            limite=args.limite,
        )
    except ErroDeColeta as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(resumo_coleta(resumo))
    return 1 if resumo.interrompida else 0


if __name__ == "__main__":
    sys.exit(main())
```

`main` lê `ARQUIVO_FONTES`, `PASTA_PAGINAS` e `ARQUIVO_REGISTRO` como globais do módulo no momento da chamada — é o que permite ao teste trocá-los com `monkeypatch`.

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_coleta.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/coleta.py tests/test_rag_coleta.py
git commit -m "feat(rag): comando python -m rag.coleta, retomavel e com parada no 429/503

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 4: Extração — `extrair` sobre HTML sintético

**Files:**
- Create: `rag/extracao.py`
- Test: `tests/test_rag_extracao.py`

**Interfaces:**
- Produces (`rag/extracao.py`):
  - `VERSAO_EXTRATOR: int = 1`
  - `SECOES_EXCLUIDAS: frozenset[str] = frozenset({"related-content", "next-steps", "see-also"})`
  - `class ErroDeExtracao(Exception)`
  - `class Bloco(BaseModel)`: `tipo: Literal["paragrafo", "lista", "tabela", "codigo", "nota"]`, `texto: str`, `linguagem: str | None = None`, `rotulo: str | None = None`
  - `class Secao(BaseModel)`: `ancora: str`, `titulo: str`, `nivel: int`, `caminho: str`, `blocos: list[Bloco]`
  - `class PaginaExtraida(BaseModel)`: `versao_extrator: int`, `id: str`, `url: str`, `titulo: str`, `secoes: list[Secao]`, `secoes_excluidas: list[str]`, `metadados: dict[str, str | None] = {}`
  - `extrair(html: str, id_fonte: str, url: str) -> PaginaExtraida`

A estrutura sintética abaixo reproduz a medida em 09/10/2026 (spec, seção 3): H1 sozinho num `div.content`; o corpo no `div.content` irmão seguinte, com filhos planos; "In this article", "Feedback" e "Additional resources" fora do corpo.

- [ ] **Step 1: Testes que falham**

Criar `tests/test_rag_extracao.py`:

```python
"""Extração do texto estruturado. HTML sintético, escrito à mão imitando a
estrutura medida no Learn; nenhuma página real entra no repositório."""

import pytest

from rag.extracao import (
    VERSAO_EXTRATOR,
    Bloco,
    ErroDeExtracao,
    extrair,
)

URL = "https://learn.microsoft.com/en-us/dax/calculate-function-dax"


def pagina(corpo: str, h1: str = '<h1 id="calculate">CALCULATE</h1>') -> str:
    return f"""<html><body><main id="main" class="layout-body-main">
<nav id="center-doc-outline"><h2 id="ms--in-this-article">In this article</h2></nav>
<div><div class="content">{h1}</div>
<div id="article-metadata">metadados</div>
<div class="content">{corpo}</div></div>
<h2 id="ms--feedback">Feedback</h2>
<h2 id="ms--additional-resources-mobile-heading">Additional resources</h2>
</main></body></html>"""


CORPO = """
<p>Evaluates an expression in a modified <a href="x">filter context</a>.</p>
<div class="NOTE"><p>Note</p><p>There's also the CALCULATETABLE function.</p></div>
<h2 id="syntax">Syntax</h2>
<pre><code class="lang-dax">CALCULATE(&lt;expression&gt;[, &lt;filter1&gt;])
  -- indentação preservada</code></pre>
<h3 id="parameters">Parameters</h3>
<table><tr><th>Term</th><th>Definition</th></tr><tr><td>expression</td><td>The expression to be evaluated.</td></tr></table>
<ul><li>Boolean filter expressions</li><li>Table filter expression</li></ul>
<p><img src="x.png" alt="diagrama"></p>
<h2 id="related-content">Related content</h2>
<ul><li><a href="y">CALCULATETABLE</a></li></ul>
<h3 id="mais-links">Mais links</h3>
<p>também fora</p>
<h2 id="remarks">Remarks</h2>
<p>Remarks text.</p>
"""


def test_identificacao_e_titulo_real():
    resultado = extrair(pagina(CORPO), "learn:dax/calculate-function-dax", URL)
    assert resultado.versao_extrator == VERSAO_EXTRATOR
    assert (resultado.id, resultado.url, resultado.titulo) == (
        "learn:dax/calculate-function-dax",
        URL,
        "CALCULATE",
    )


def test_secoes_com_ancora_nivel_e_caminho():
    secoes = extrair(pagina(CORPO), "x:y", URL).secoes
    assert [(s.ancora, s.nivel, s.caminho) for s in secoes] == [
        ("calculate", 1, "CALCULATE"),
        ("syntax", 2, "Syntax"),
        ("parameters", 3, "Syntax › Parameters"),
        ("remarks", 2, "Remarks"),
    ]


def test_cada_tipo_de_bloco():
    secoes = {s.ancora: s for s in extrair(pagina(CORPO), "x:y", URL).secoes}
    assert secoes["calculate"].blocos == [
        Bloco(tipo="paragrafo", texto="Evaluates an expression in a modified filter context ."),
        Bloco(tipo="nota", texto="There's also the CALCULATETABLE function.", rotulo="Note"),
    ]
    assert secoes["parameters"].blocos == [
        Bloco(tipo="tabela", texto="Term | Definition\nexpression | The expression to be evaluated."),
        Bloco(tipo="lista", texto="- Boolean filter expressions\n- Table filter expression"),
    ]


def test_codigo_e_preservado_verbatim_com_linguagem():
    (bloco,) = {s.ancora: s for s in extrair(pagina(CORPO), "x:y", URL).secoes}["syntax"].blocos
    assert bloco.tipo == "codigo"
    assert bloco.linguagem == "dax"
    assert bloco.texto == "CALCULATE(<expression>[, <filter1>])\n  -- indentação preservada"


def test_secao_de_navegacao_sai_com_as_subsecoes_e_a_seguinte_volta():
    resultado = extrair(pagina(CORPO), "x:y", URL)
    ancoras = [s.ancora for s in resultado.secoes]
    assert "related-content" not in ancoras and "mais-links" not in ancoras
    assert "remarks" in ancoras
    assert resultado.secoes_excluidas == ["related-content"]
    texto = " ".join(b.texto for s in resultado.secoes for b in s.blocos)
    assert "também fora" not in texto
    assert "In this article" not in texto and "Feedback" not in texto


def test_imagem_some_e_texto_de_link_fica():
    texto = " ".join(b.texto for s in extrair(pagina(CORPO), "x:y", URL).secoes for b in s.blocos)
    assert "diagrama" not in texto
    assert "filter context" in texto


def test_secao_sem_bloco_nao_entra():
    corpo = '<h2 id="vazia">Vazia</h2><h3 id="filha">Filha</h3><p>texto</p>'
    secoes = extrair(pagina(corpo), "x:y", URL).secoes
    assert [(s.ancora, s.caminho) for s in secoes] == [("filha", "Vazia › Filha")]


def test_pagina_sem_h1_e_erro_nomeado():
    with pytest.raises(ErroDeExtracao, match="learn:dax/x.*H1"):
        extrair("<html><body><main id='main'><p>x</p></main></body></html>", "learn:dax/x", URL)


def test_pagina_sem_texto_e_erro_nomeado():
    with pytest.raises(ErroDeExtracao, match="sem texto"):
        extrair(pagina('<h2 id="a">A</h2>', h1='<h1 id="t">T</h1>'), "learn:dax/x", URL)


def test_mesma_entrada_mesma_saida():
    assert extrair(pagina(CORPO), "x:y", URL) == extrair(pagina(CORPO), "x:y", URL)
```

O texto do primeiro parágrafo tem um espaço antes do ponto (`filter context .`) porque `get_text(" ")` separa o texto do link do texto seguinte. É o comportamento esperado do extrator — o espaço extra não atrapalha a busca — e o teste o fixa para que uma mudança no extrator apareça.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_extracao.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.extracao'`.

- [ ] **Step 2: Implementar**

Criar `rag/extracao.py`:

```python
"""Extração do texto estruturado das páginas coletadas (Fase 3).

`python -m rag.extracao` lê o HTML bruto de `rag/store/raw/paginas/` e grava em
`rag/store/textos/` um JSON por página: título real, seções com âncora, nível
e caminho, e blocos tipados. Offline: mudou o extrator, reprocessa-se em
segundos (R-13). Desenho: `docs/superpowers/specs/
2026-10-09-coleta-da-base-rag-design.md`, seção 3.
"""

from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

VERSAO_EXTRATOR = 1

SECOES_EXCLUIDAS = frozenset({"related-content", "next-steps", "see-also"})
"""Seções do corpo que são só listas de links. "In this article", "Feedback" e
"Additional resources" já ficam fora do corpo do artigo."""

_ROTULOS_DE_NOTA = {
    "NOTE": "Note",
    "TIP": "Tip",
    "IMPORTANT": "Important",
    "WARNING": "Warning",
    "CAUTION": "Caution",
}
_NIVEIS = {"h2": 2, "h3": 3, "h4": 4}
_IGNORADOS = frozenset({"img", "script", "style", "nav", "svg"})


class ErroDeExtracao(Exception):
    """Uma página não pôde ser extraída; as demais seguem."""


class Bloco(BaseModel):
    tipo: Literal["paragrafo", "lista", "tabela", "codigo", "nota"]
    texto: str
    linguagem: str | None = None
    rotulo: str | None = None


class Secao(BaseModel):
    ancora: str
    titulo: str
    nivel: int
    caminho: str
    blocos: list[Bloco]


class PaginaExtraida(BaseModel):
    versao_extrator: int
    id: str
    url: str
    titulo: str
    secoes: list[Secao]
    secoes_excluidas: list[str]
    metadados: dict[str, str | None] = {}


def _texto(no: Tag) -> str:
    return " ".join(no.get_text(" ", strip=True).split())


def _blocos(no: Tag) -> list[Bloco]:
    nome = no.name
    if nome in _IGNORADOS:
        return []
    if nome == "p":
        texto = _texto(no)
        return [Bloco(tipo="paragrafo", texto=texto)] if texto else []
    if nome in ("ul", "ol"):
        itens = [t for li in no.find_all("li", recursive=False) if (t := _texto(li))]
        return [Bloco(tipo="lista", texto="\n".join(f"- {i}" for i in itens))] if itens else []
    if nome == "table":
        linhas = []
        for tr in no.find_all("tr"):
            celulas = [_texto(c) for c in tr.find_all(["th", "td"])]
            if any(celulas):
                linhas.append(" | ".join(celulas))
        return [Bloco(tipo="tabela", texto="\n".join(linhas))] if linhas else []
    if nome == "pre":
        codigo = no.find("code") or no
        classes = codigo.get("class") or []
        linguagem = next((c.removeprefix("lang-") for c in classes if c.startswith("lang-")), None)
        texto = codigo.get_text().strip("\n")
        return [Bloco(tipo="codigo", texto=texto, linguagem=linguagem)] if texto.strip() else []
    if nome == "div":
        classes = no.get("class") or []
        rotulo = next((_ROTULOS_DE_NOTA[c] for c in classes if c in _ROTULOS_DE_NOTA), None)
        if rotulo is not None:
            texto = _texto(no)
            if texto.startswith(rotulo):
                texto = texto[len(rotulo):].strip()
            return [Bloco(tipo="nota", texto=texto, rotulo=rotulo)] if texto else []
        blocos = [b for filho in no.find_all(recursive=False) for b in _blocos(filho)]
        if blocos:
            return blocos
    texto = _texto(no)
    return [Bloco(tipo="paragrafo", texto=texto)] if texto else []


def extrair(html: str, id_fonte: str, url: str) -> PaginaExtraida:
    """A página como seções e blocos. Função pura."""
    sopa = BeautifulSoup(html, "html.parser")
    principal = sopa.find("main", id="main") or sopa
    h1 = principal.find("h1")
    if h1 is None:
        raise ErroDeExtracao(f"{id_fonte}: página sem H1")
    caixa = h1.find_parent("div", class_="content")
    corpo = caixa.find_next_sibling("div", class_="content") if caixa is not None else None
    if corpo is None:
        raise ErroDeExtracao(f"{id_fonte}: corpo do artigo não encontrado")

    titulo = _texto(h1)
    secoes = [Secao(ancora=h1.get("id") or "", titulo=titulo, nivel=1, caminho=titulo, blocos=[])]
    pilha: list[tuple[int, str]] = []
    excluidas: list[str] = []
    excluindo_ate: int | None = None

    for no in corpo.find_all(recursive=False):
        nivel = _NIVEIS.get(no.name)
        if nivel is not None:
            if excluindo_ate is not None and nivel <= excluindo_ate:
                excluindo_ate = None
            if excluindo_ate is not None:
                continue
            ancora = no.get("id") or ""
            if ancora in SECOES_EXCLUIDAS:
                excluidas.append(ancora)
                excluindo_ate = nivel
                continue
            titulo_secao = _texto(no)
            while pilha and pilha[-1][0] >= nivel:
                pilha.pop()
            pilha.append((nivel, titulo_secao))
            secoes.append(
                Secao(
                    ancora=ancora,
                    titulo=titulo_secao,
                    nivel=nivel,
                    caminho=" › ".join(t for _, t in pilha),
                    blocos=[],
                )
            )
            continue
        if excluindo_ate is not None:
            continue
        secoes[-1].blocos.extend(_blocos(no))

    com_texto = [s for s in secoes if s.blocos]
    if not com_texto:
        raise ErroDeExtracao(f"{id_fonte}: página sem texto")
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_fonte,
        url=url,
        titulo=titulo,
        secoes=com_texto,
        secoes_excluidas=excluidas,
    )
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_extracao.py -q`
Expected: todos passam. Se `test_cada_tipo_de_bloco` falhar só pelo espaçamento do primeiro parágrafo, conferir a saída real de `_texto` e ajustar **o teste** ao comportamento descrito acima (espaço entre o texto do link e o ponto) — não o extrator.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/extracao.py tests/test_rag_extracao.py
git commit -m "feat(rag): extracao de secoes com ancora, caminho e blocos tipados

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 5: Extração — `extrair_tudo`, resumo e comando

**Files:**
- Modify: `rag/extracao.py` (acrescentar)
- Test: `tests/test_rag_extracao.py` (acrescentar)

**Interfaces:**
- Consumes: Task 4; `rag.coleta.ler_registro`, `caminho_da_pagina`, `PASTA_STORE`, `PASTA_PAGINAS`, `ARQUIVO_REGISTRO`; `rag.catalogo.ARQUIVO_FONTES`.
- Produces:
  - `PASTA_TEXTOS: Path` (= `PASTA_STORE / "textos"`)
  - `caminho_do_texto(pasta: Path, id_fonte: str) -> Path` — o caminho de `caminho_da_pagina` com sufixo `.json`
  - `@dataclass class ResumoExtracao`: `extraidas: int`, `erros: list[str]`, `excluidas: Counter`, `titulos_diferentes: int`
  - `extrair_tudo(*, arquivo_registro: Path, pasta_paginas: Path, pasta_textos: Path, titulos_do_catalogo: dict[str, str]) -> ResumoExtracao`
  - `resumo_extracao(resumo: ResumoExtracao) -> str`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Testes que falham**

Acrescentar ao import de `rag.extracao`: `PaginaExtraida`, `caminho_do_texto`, `extrair_tudo`, `resumo_extracao`, `main`. Acrescentar `import hashlib`, `from datetime import UTC, datetime`, `from rag import extracao as modulo_extracao` e `from rag.coleta import RegistroColeta, anexar_registro, caminho_da_pagina`. No fim:

```python
AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _coletada(tmp_path, id_fonte, html, **meta):
    arquivo = caminho_da_pagina(tmp_path / "paginas", id_fonte)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(html, encoding="utf-8")
    anexar_registro(
        tmp_path / "coleta.jsonl",
        RegistroColeta(
            id=id_fonte,
            url=URL,
            situacao="ok",
            acessado_em=AGORA,
            tamanho=len(html),
            sha256=hashlib.sha256(html.encode()).hexdigest(),
            **meta,
        ),
    )


def _extrair_tudo(tmp_path, titulos=None):
    return extrair_tudo(
        arquivo_registro=tmp_path / "coleta.jsonl",
        pasta_paginas=tmp_path / "paginas",
        pasta_textos=tmp_path / "textos",
        titulos_do_catalogo=titulos or {},
    )


def test_extrai_toda_pagina_ok_com_metadados(tmp_path):
    _coletada(tmp_path, "learn:dax/calculate-function-dax", pagina(CORPO), updated_at="2026-08-04T22:03:00Z")
    resumo = _extrair_tudo(tmp_path, {"learn:dax/calculate-function-dax": "CALCULATE"})
    assert resumo.extraidas == 1 and resumo.erros == [] and resumo.titulos_diferentes == 0
    destino = caminho_do_texto(tmp_path / "textos", "learn:dax/calculate-function-dax")
    assert destino.suffix == ".json"
    salvo = PaginaExtraida.model_validate_json(destino.read_text(encoding="utf-8"))
    assert salvo.metadados["updated_at"] == "2026-08-04T22:03:00Z"
    assert salvo.metadados["acessado_em"] == AGORA.isoformat()
    assert resumo.excluidas["related-content"] == 1


def test_erro_de_uma_pagina_nao_para_as_outras(tmp_path):
    _coletada(tmp_path, "learn:dax/sem-h1", "<html><body><main id='main'><p>x</p></main></body></html>")
    _coletada(tmp_path, "learn:dax/boa", pagina(CORPO))
    resumo = _extrair_tudo(tmp_path)
    assert resumo.extraidas == 1
    assert len(resumo.erros) == 1 and "learn:dax/sem-h1" in resumo.erros[0]


def test_html_apagado_depois_da_coleta_vira_erro_nomeado(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/a").unlink()
    resumo = _extrair_tudo(tmp_path)
    assert resumo.extraidas == 0
    assert "rag.coleta" in resumo.erros[0]


def test_titulo_diferente_do_catalogo_e_contado_nao_e_erro(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    resumo = _extrair_tudo(tmp_path, {"learn:dax/a": "Introduction"})
    assert resumo.extraidas == 1 and resumo.titulos_diferentes == 1


def test_sem_nada_coletado_falha_indicando_a_coleta(tmp_path):
    with pytest.raises(ErroDeExtracao, match="rag.coleta"):
        _extrair_tudo(tmp_path)


def test_resumo_da_extracao(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    texto = resumo_extracao(_extrair_tudo(tmp_path))
    assert "Extraídas: 1" in texto
    assert "related-content: 1" in texto


def test_main_sem_coleta_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_extracao, "ARQUIVO_REGISTRO", tmp_path / "nao-existe.jsonl")
    monkeypatch.setattr(modulo_extracao, "ARQUIVO_FONTES", tmp_path / "nao-existe.yaml")
    assert main([]) == 1
    assert "rag.coleta" in capsys.readouterr().err
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_extracao.py -q`
Expected: `ImportError: cannot import name 'caminho_do_texto'`.

- [ ] **Step 2: Implementar**

Em `rag/extracao.py`, completar os imports:

```python
import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

from rag.catalogo import ARQUIVO_FONTES
from rag.coleta import (
    ARQUIVO_REGISTRO,
    PASTA_PAGINAS,
    PASTA_STORE,
    caminho_da_pagina,
    ler_registro,
)
```

E acrescentar no fim:

```python
PASTA_TEXTOS = PASTA_STORE / "textos"


def caminho_do_texto(pasta: Path, id_fonte: str) -> Path:
    return caminho_da_pagina(pasta, id_fonte).with_suffix(".json")


@dataclass
class ResumoExtracao:
    extraidas: int = 0
    erros: list[str] = field(default_factory=list)
    excluidas: Counter = field(default_factory=Counter)
    titulos_diferentes: int = 0


def _gravar_texto(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(texto, encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def extrair_tudo(
    *,
    arquivo_registro: Path,
    pasta_paginas: Path,
    pasta_textos: Path,
    titulos_do_catalogo: dict[str, str],
) -> ResumoExtracao:
    """Extrai toda página cuja última linha no registro é `ok`. Erro de uma
    página entra no resumo e não interrompe as outras."""
    coletadas = sorted(
        (r for r in ler_registro(arquivo_registro).values() if r.situacao == "ok"),
        key=lambda r: r.id,
    )
    if not coletadas:
        raise ErroDeExtracao("nenhuma página coletada — rode `python -m rag.coleta` antes")

    resumo = ResumoExtracao()
    for registro in coletadas:
        html = caminho_da_pagina(pasta_paginas, registro.id)
        if not html.is_file():
            resumo.erros.append(
                f"{registro.id}: HTML ausente — rode `python -m rag.coleta` para baixar de novo"
            )
            continue
        try:
            pagina = extrair(html.read_text(encoding="utf-8", errors="replace"), registro.id, registro.url)
        except ErroDeExtracao as erro:
            resumo.erros.append(str(erro))
            continue
        pagina = pagina.model_copy(
            update={
                "metadados": {
                    "acessado_em": registro.acessado_em.isoformat(),
                    "updated_at": registro.updated_at,
                    "ms_date": registro.ms_date,
                    "git_commit_id": registro.git_commit_id,
                    "document_id": registro.document_id,
                }
            }
        )
        _gravar_texto(caminho_do_texto(pasta_textos, registro.id), pagina.model_dump_json(indent=2) + "\n")
        resumo.extraidas += 1
        resumo.excluidas.update(pagina.secoes_excluidas)
        titulo_catalogo = titulos_do_catalogo.get(registro.id)
        if titulo_catalogo is not None and titulo_catalogo != pagina.titulo:
            resumo.titulos_diferentes += 1
    return resumo


def resumo_extracao(resumo: ResumoExtracao) -> str:
    return "\n".join(
        [
            f"Extraídas: {resumo.extraidas}",
            f"Erros: {len(resumo.erros)}",
            *(f"  {e}" for e in resumo.erros),
            "Seções excluídas por âncora:",
            *(f"  {ancora}: {n}" for ancora, n in sorted(resumo.excluidas.items())),
            f"Título real diferente do título de navegação do catálogo: {resumo.titulos_diferentes}",
        ]
    )


def _titulos_do_catalogo(caminho: Path) -> dict[str, str]:
    if not caminho.is_file():
        return {}
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    return {f["id"]: f["titulo"] for f in dados}


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        prog="python -m rag.extracao",
        description="Extrai o texto estruturado das páginas coletadas em rag/store/.",
    ).parse_args(argv)
    try:
        resumo = extrair_tudo(
            arquivo_registro=ARQUIVO_REGISTRO,
            pasta_paginas=PASTA_PAGINAS,
            pasta_textos=PASTA_TEXTOS,
            titulos_do_catalogo=_titulos_do_catalogo(ARQUIVO_FONTES),
        )
    except ErroDeExtracao as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(resumo_extracao(resumo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Verificar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_extracao.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 4: Commit e push**

```bash
git add rag/extracao.py tests/test_rag_extracao.py
git commit -m "feat(rag): comando python -m rag.extracao sobre o registro da coleta

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 6: Execução real — ensaio, coleta completa e extração

**Files:**
- Create: `tests/test_rag_store_real.py`
- Modify: `docs/project/progress-log.md` (uma entrada por passo medido)

**Interfaces:**
- Consumes: os dois comandos; `rag.catalogo.ancoras_do_registro`; `rag.urls.normalizar_url`, `caminho_sem_idioma`.

Cada passo com rede só começa depois que o anterior foi conferido. Cada número medido vai para o `progress-log.md` com commit e push **no mesmo passo**.

- [ ] **Step 1: Ensaio com 20 páginas**

Run: `.\.venv\Scripts\python.exe -m rag.coleta --limite 20`
Expected: `Coletadas nesta execução: 20`, `Erros nesta execução: 0`, `Total ok: 20 de 1420`, sem `INTERROMPIDA`. Tempo ≈ 20 × (0,6 + 1,0) s ≈ 32 s.
Then: `.\.venv\Scripts\python.exe -m rag.extracao`
Expected: `Extraídas: 20`, `Erros: 0`.
Conferir à mão **um** JSON de `rag/store/textos/learn/dax/` e **um** de `.../power-bi/guidance/` se houver: seções com âncora, código DAX intacto, sem "Feedback".
Conferir que nada de `rag/store/` aparece em `git status --short`.

Se houver erro ou o JSON vier errado: **parar**, usar superpowers:systematic-debugging, corrigir com teste que falha primeiro, e só então seguir.

Acrescentar ao `progress-log.md` uma linha curta sob uma nova entrada "09/10/2026 — Fase 3 — coleta e extração" com o resultado do ensaio. Commit e push: `docs: ensaio da coleta (20 paginas) conferido`.

- [ ] **Step 2: Coleta completa, em segundo plano**

Run (em segundo plano, saída em arquivo): `.\.venv\Scripts\python.exe -m rag.coleta > rag/store/coleta-execucao.log 2>&1`
Expected: ~40 min; ao final `Total ok: 1420 de 1420` (ou o número de páginas do catálogo vigente), sem `INTERROMPIDA`.
Acompanhar pelo tamanho de `rag/store/coleta.jsonl` (uma linha por página). Se interromper (429/503 ou 5 falhas seguidas): ler a causa no log, esperar e rodar de novo — a retomada pula o que já está `ok`. Páginas com erro 404 ou redirecionadas: listar no progress-log; são o catálogo envelhecendo, não falha da coleta.

Registrar no `progress-log.md`: total ok, erros (com os ids), tempo total, tamanho em disco de `rag/store/raw/paginas/`. Commit e push: `docs: coleta completa — <N> paginas`.

- [ ] **Step 3: Extração completa**

Run: `.\.venv\Scripts\python.exe -m rag.extracao`
Expected: `Extraídas` igual ao total ok da coleta, `Erros: 0`.
Registrar no `progress-log.md`: extraídas, erros, seções excluídas por âncora, títulos diferentes do catálogo, tamanho de `rag/store/textos/`. Commit e push: `docs: extracao completa — <N> paginas`.

- [ ] **Step 4: Teste sobre os dados reais**

Criar `tests/test_rag_store_real.py`:

```python
"""A base coletada, conferida contra o catálogo e as âncoras das regras.

Pulados quando `rag/store/` não existe — o conteúdo do Learn não é versionado
(termos de uso). É aqui que se prova que a RAG terá o trecho que cada regra cita.
"""

import pytest
import yaml

from rag.catalogo import ARQUIVO_FONTES, ancoras_do_registro
from rag.coleta import ARQUIVO_REGISTRO, ler_registro
from rag.extracao import PASTA_TEXTOS, VERSAO_EXTRATOR, PaginaExtraida, caminho_do_texto
from rag.urls import caminho_sem_idioma, normalizar_url

pytestmark = pytest.mark.skipif(
    not ARQUIVO_REGISTRO.is_file(), reason="rag/store/ não existe (conteúdo do Learn não é versionado)"
)

FRASES_MARCA = {
    "DAX-001": "use the DIVIDE function whenever the denominator is an expression",
    "MOD-001": "disable the global Auto date/time option",
    "MOD-002": "minimize the use of bi-directional relationships",
    "MOD-003": "the right number of tables with the right relationships",
    "MOD-005": "mark your date table as a date table",
    "MOD-006": "the benefits of a single model table outweigh the benefits",
    "MOD-007": "avoid creating one-to-one model relationships",
    "PERF-001": "preference creating custom columns in Power Query",
    "PERF-003": "calculations that sum the values of a column of Decimal number",
}
"""Uma frase curta (até ~10 palavras) de cada passagem transcrita nas specs de
regras — citação acadêmica com fonte, não republicação da página."""


def _normalizar(texto: str) -> str:
    for de, para in {"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}.items():
        texto = texto.replace(de, para)
    return " ".join(texto.lower().split())


def _pagina(id_fonte: str) -> PaginaExtraida:
    return PaginaExtraida.model_validate_json(
        caminho_do_texto(PASTA_TEXTOS, id_fonte).read_text(encoding="utf-8")
    )


def test_toda_pagina_do_catalogo_foi_coletada_e_extraida():
    indexaveis = {
        f["id"] for f in yaml.safe_load(ARQUIVO_FONTES.read_text(encoding="utf-8")) if f["indexar"]
    }
    registro = ler_registro(ARQUIVO_REGISTRO)
    ok = {i for i, r in registro.items() if r.situacao == "ok"}
    assert indexaveis <= ok, sorted(indexaveis - ok)[:10]
    for id_fonte in sorted(indexaveis):
        assert _pagina(id_fonte).versao_extrator == VERSAO_EXTRATOR, id_fonte


def test_toda_regra_tem_frase_marca():
    assert set(FRASES_MARCA) == set(ancoras_do_registro())


@pytest.mark.parametrize("id_regra", sorted(FRASES_MARCA))
def test_a_passagem_citada_pela_regra_esta_no_texto_extraido(id_regra):
    url = ancoras_do_registro()[id_regra]
    pagina = _pagina("learn:" + caminho_sem_idioma(normalizar_url(url)))
    texto = _normalizar(" ".join(b.texto for s in pagina.secoes for b in s.blocos))
    assert _normalizar(FRASES_MARCA[id_regra]) in texto
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_store_real.py -q`
Expected: 11 passam.

Se uma frase-marca falhar: abrir o JSON da página âncora e procurar a passagem transcrita. Três casos, cada um registrado no `progress-log.md`:
- a passagem está lá com outra redação curta (hífen, maiúscula) → ajustar a frase-marca ao texto real;
- a passagem está em outra página citada pela mesma regra (a spec da MOD-001 cita `auto-date-time` **e** `import-modeling-data-reduction`) → ajustar o teste para procurar na página certa e registrar;
- a passagem **sumiu** da página → é deriva da âncora: **parar** e trazer ao Fred antes de qualquer mudança, porque afeta a regra.

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Step 5: Commit e push**

```bash
git add tests/test_rag_store_real.py docs/project/progress-log.md
git commit -m "test(rag): a base coletada contem a passagem que cada regra cita

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```

---

### Task 7: Registros do projeto

**Files:**
- Modify: `README.md`, `docs/project/status.md`, `docs/project/backlog.md`, `docs/project/progress-log.md`
- Republicar: a página de acompanhamento do orientador (artifact `https://claude.ai/code/artifact/476dde6e-9da2-4871-8cfc-afc67784f0c0`, arquivo-fonte no scratchpad desta sessão: `andamento-auditor-pbip.html`)

- [ ] **Step 1: README**

Na seção "Catálogo de fontes da RAG", acrescentar:

````markdown
```powershell
python -m rag.coleta --limite 20  # ensaio: baixa as 20 primeiras páginas pendentes
python -m rag.coleta              # baixa as páginas do catálogo para rag/store/ (retomável)
python -m rag.extracao            # extrai o texto por seção para rag/store/textos/ (offline)
```

`rag/store/` não é versionado: é cópia local do Microsoft Learn, para uso pessoal e não comercial.
````

- [ ] **Step 2: status.md**

- Linha "Posição": trocar "Fase 3 iniciada com o catálogo de fontes pronto" por "Fase 3: catálogo de fontes e base coletada".
- Seção 3, tabela "O que já funciona": acrescentar a linha `| Coleta e extração da base RAG (`python -m rag.coleta`, `python -m rag.extracao`) | <N> páginas coletadas e extraídas por seção, com âncora; a passagem citada por cada uma das 9 regras conferida no texto extraído |` com o N medido.
- Seção 8, passo 1: trocar pela próxima etapa: `| 1 | **Conjunto de avaliação da recuperação e chunking** | ADR-002, emenda de 09/10: o gabarito (seção âncora de cada regra) é montado antes de escolher chunking e embeddings |`.
- Número de testes nas seções 1, 3 e 9: o da última execução.

- [ ] **Step 3: backlog.md**

Na tabela "Pendências abertas do gate da Fase 1", não há linha para a coleta; acrescentar ao fim do "Log de alertas de escopo" só se algo da execução real mudou o escopo (por exemplo, páginas do catálogo que já não existem). Se nada mudou, não mexer.

- [ ] **Step 4: Página do orientador**

No arquivo-fonte da página, atualizar: meta-row (testes), seção 5 (acrescentar um parágrafo curto com a coleta e a extração medidas), seção 9 (próximos passos: conjunto de avaliação e chunking; integrar o PR #1) e a data. Republicar no mesmo endereço.

- [ ] **Step 5: Verificar, commit e push**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

```bash
git add README.md docs/project
git commit -m "docs: coleta e extracao da base RAG concluidas

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q
```
