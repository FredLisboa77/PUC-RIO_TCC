# Catálogo de fontes da RAG — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar `rag/sources.yaml` — o catálogo versionado das 1.420 páginas do Microsoft Learn que a RAG vai indexar, mais as leituras complementares do SQLBI só como referência — a partir de retratos datados dos `toc.json` do Learn.

**Architecture:** Três módulos com uma função cada: `rag/urls.py` (regras puras de URL), `rag/tocs.py` (retratos dos `toc.json`: único ponto com rede, buscador injetado) e `rag/catalogo.py` (montagem pura, leitura/escrita de arquivos e o comando `python -m rag.catalogo`). Os retratos normalizados vão para `rag/tocs/` (versionado); o bruto para `rag/store/raw/tocs/` (fora do Git). A geração é offline e determinística, e um teste compara o `sources.yaml` versionado com o que o gerador produz.

**Tech Stack:** Python 3.11.9, Pydantic 2.13.5, PyYAML 6.0.3 (nova), `urllib` da biblioteca padrão, pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-10-09-catalogo-de-fontes-rag-design.md`

## Global Constraints

- Todo o código, nomes de função, de teste, mensagens, docstrings e commits em **português** (convenção do projeto).
- Python 3.11.9; rodar sempre pelo `.venv`: `.\.venv\Scripts\python.exe -m pytest -q`.
- Dependência nova: **`pyyaml==6.0.3`** no `requirements.txt`, usada só via `yaml.safe_load` / `yaml.safe_dump`. Instalação nesta máquina exige o certificado do Norton: `.\.venv\Scripts\python.exe -m pip install pyyaml==6.0.3 --cert C:\ProgramData\Norton\Antivirus\wscert.pem` (ou o `.venv/pip.ini` já configurado).
- Rede só em `rag/tocs.py`, com `User-Agent` exato `powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)` e `timeout` de **30 s**; sem e-mail no cabeçalho; sem repetição automática.
- **Nenhum teste usa rede.**
- Seções retratadas, nesta ordem: `power-bi/guidance`, `dax`, `powerquery-m` (origem); `power-bi/connect-data`, `power-bi/transform-model` (âncora). Idiomas: `en-us`, `pt-br`.
- `licenca` do Learn, verbatim: `Termos de uso do Microsoft Learn — uso pessoal e não comercial; cópia local não redistribuída (https://learn.microsoft.com/en-us/legal/termsofuse)`
- `licenca` do SQLBI, verbatim: `© SQLBI, todos os direitos reservados — somente referência bibliográfica; conteúdo não coletado`
- O `toc.json` **bruto nunca** vai para o Git (termos de uso do Learn, spec 5.2); só a listagem normalizada em `rag/tocs/`.
- O SQLBI **nunca** é baixado nem indexado: `indexar: false`; só o código de status é conferido em `atualizar`.
- `rag/sources.yaml` nunca é editado à mão.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Branch atual: `fase2-regras-de-dax` (não fazer push).

## Review Focus

1. **Link absoluto do Learn sem idioma, ou em outro idioma, dentro do `toc.json`** (`https://learn.microsoft.com/power-bi/...`, `https://learn.microsoft.com/pt-br/dax/...`) — deve resolver para `/en-us/`, não ser descartado nem duplicado. Teste na Tarefa 1.
2. **Âncora de regra escrita com outra caixa ou barra final** — a busca de 09/10 devolveu `learn.microsoft.com/en-us/DAX/best-practices/...`; uma `url_canonica` assim tem de casar com o `toc.json` (que é minúsculo). Teste na Tarefa 4.
3. **Item do `toc.json` com `href` e sem `toc_title`** — não pode quebrar a geração nem gerar título vazio; usa o último segmento do caminho. Teste na Tarefa 4.
4. **Checkout no Windows com `core.autocrlf`** (o repositório converte LF→CRLF, como mostram os avisos do Git) — o teste de arquivo gerado compara **texto**, não bytes, senão falha em todo clone. Teste na Tarefa 6 e uso na Tarefa 7.
5. **`observacoes.yaml` / `leituras_sqlbi.yaml` ausentes, vazios ou só com comentários** — tratados como vazios, sem erro. Testes na Tarefa 6.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | + `pyyaml==6.0.3` |
| `rag/__init__.py` | Marca o pacote; docstring curta |
| `rag/urls.py` | Puras: resolver `href`, motivo de exclusão, normalizar URL, trocar idioma, seção própria |
| `rag/tocs.py` | `SECOES`, `IDIOMAS`, modelos `ItemToc`/`Retrato`, achatar `toc.json`, serializar, buscador padrão (`urllib`), `baixar_retratos` |
| `rag/catalogo.py` | Modelos `Fonte`/`LeituraSqlbi`, `montar_catalogo` (pura), leitura de retratos/observações/leituras, `como_yaml`/`escrever_yaml`, `gerar`/`atualizar`/`resumo`/`main` |
| `rag/tocs/<idioma>/<seção>.json` | Retratos normalizados (gerados, versionados) |
| `rag/observacoes.yaml` | Notas humanas por `id` (à mão) |
| `rag/leituras_sqlbi.yaml` | Curadoria do SQLBI (à mão) |
| `rag/sources.yaml` | Catálogo (gerado, versionado) |
| `tests/test_rag_urls.py`, `tests/test_rag_tocs.py`, `tests/test_rag_catalogo.py`, `tests/test_rag_dados_reais.py` | Testes |

**Três precisões em relação à spec, nenhuma muda o comportamento pedido:**
- As funções de URL ficam num módulo próprio, `rag/urls.py`, em vez de dentro de `rag/catalogo.py`, para manter cada arquivo com uma função.
- `montar_catalogo` devolve `ResultadoCatalogo(fontes, exclusoes)` em vez de `list[Fonte]`: o resumo do comando precisa das exclusões por motivo (spec 3.3), e elas só são conhecidas durante a montagem.
- A normalização de URL do Learn põe **também o caminho** em minúsculas (a spec diz esquema e host), porque o Learn não diferencia caixa no caminho e uma âncora com `/DAX/` precisa casar (Review Focus 2). Fora do Learn, o caminho mantém a caixa.

---

### Tarefa 1: Pacote `rag`, dependência e regras de URL

**Files:**
- Modify: `requirements.txt`
- Create: `rag/__init__.py`
- Create: `rag/urls.py`
- Test: `tests/test_rag_urls.py`

**Interfaces:**
- Consumes: nada.
- Produces (`rag/urls.py`):
  - `HOST_LEARN: str = "learn.microsoft.com"`
  - `FORA_DO_LEARN: str = "fora do learn"`
  - `NAO_DOCUMENTAL: str = "entrada de seção ou área não documental"`
  - `resolver_href(href: str, secao: str, idioma: str = "en-us") -> str`
  - `motivo_de_exclusao(url: str) -> str | None`
  - `normalizar_url(url: str) -> str`
  - `caminho_sem_idioma(url: str) -> str`
  - `em_outro_idioma(url: str, idioma: str) -> str`
  - `secao_propria(url: str, secoes: Iterable[str]) -> str | None`

- [ ] **Passo 1: Acrescentar a dependência e instalar**

Em `requirements.txt`, depois da linha `pytest==9.1.1`, acrescentar:

```
# Fase 3 - catalogo de fontes da RAG
pyyaml==6.0.3
```

Run: `.\.venv\Scripts\python.exe -m pip install pyyaml==6.0.3 --cert C:\ProgramData\Norton\Antivirus\wscert.pem`
Then: `.\.venv\Scripts\python.exe -c "import yaml; print(yaml.__version__)"`
Expected: `6.0.3`

- [ ] **Passo 2: Escrever os testes que falham**

Criar `tests/test_rag_urls.py`:

```python
"""Regras de URL do catálogo de fontes.

O `toc.json` do Learn mistura quatro formas de link, e uma delas — relativa à
raiz — não traz o idioma. Medido em 09/10/2026: resolvida sem prefixar o
idioma, ela tiraria do guidance as 9 páginas de boas práticas de DAX.
"""

import pytest

from rag.urls import (
    FORA_DO_LEARN,
    NAO_DOCUMENTAL,
    caminho_sem_idioma,
    em_outro_idioma,
    motivo_de_exclusao,
    normalizar_url,
    resolver_href,
    secao_propria,
)

L = "https://learn.microsoft.com/en-us/"


def test_href_relativo_resolve_na_pasta_da_secao():
    assert resolver_href("star-schema", "power-bi/guidance") == (
        L + "power-bi/guidance/star-schema"
    )


def test_href_com_subida_de_pasta():
    assert resolver_href("../transform-model/dataflows/x", "power-bi/guidance") == (
        L + "power-bi/transform-model/dataflows/x"
    )


def test_href_relativo_a_raiz_recebe_o_idioma():
    assert resolver_href("/dax/best-practices/dax-variables", "power-bi/guidance") == (
        L + "dax/best-practices/dax-variables"
    )
    assert resolver_href("/dax/x", "dax", "pt-br") == (
        "https://learn.microsoft.com/pt-br/dax/x"
    )


def test_href_relativo_a_raiz_que_ja_traz_idioma_nao_duplica():
    assert resolver_href("/en-us/dax/x", "dax") == L + "dax/x"
    assert resolver_href("/pt-br/dax/x", "dax") == L + "dax/x"


def test_href_absoluto_externo_fica_como_esta():
    assert resolver_href("https://ideas.fabric.microsoft.com/", "power-bi/guidance") == (
        "https://ideas.fabric.microsoft.com/"
    )


def test_href_absoluto_do_learn_sem_idioma_ou_em_outro_idioma():
    assert resolver_href(
        "https://learn.microsoft.com/power-bi/guidance/star-schema", "dax"
    ) == L + "power-bi/guidance/star-schema"
    assert resolver_href("https://learn.microsoft.com/pt-br/dax/x", "dax") == L + "dax/x"


def test_pagina_de_entrada_da_secao_resolve_com_barra_final():
    assert resolver_href("./", "dax") == L + "dax/"


@pytest.mark.parametrize(
    "url",
    [
        "https://ideas.fabric.microsoft.com/",
        "https://aka.ms/learndax",
        "https://community.fabric.microsoft.com/",
    ],
)
def test_host_fora_do_learn_e_excluido(url):
    assert motivo_de_exclusao(url) == FORA_DO_LEARN


@pytest.mark.parametrize(
    "url",
    [
        L + "power-bi/guidance/",
        L + "contribute/",
        L + "answers/",
        L + "training/fabric/",
        L + "training/modules/algum-modulo",
    ],
)
def test_entrada_de_secao_e_area_nao_documental_sao_excluidas(url):
    assert motivo_de_exclusao(url) == NAO_DOCUMENTAL


def test_artigo_do_learn_nao_e_excluido_mesmo_fora_das_secoes():
    assert motivo_de_exclusao(L + "fabric/cicd/best-practices-cicd") is None


def test_normalizar_tira_query_fragmento_barra_e_padroniza_caixa_no_learn():
    assert normalizar_url(
        "HTTPS://Learn.Microsoft.com/en-us/DAX/best-practices/dax-variables/?view=x#a"
    ) == L + "dax/best-practices/dax-variables"


def test_normalizar_preserva_a_caixa_do_caminho_fora_do_learn():
    assert normalizar_url("https://www.sqlbi.com/articles/Mark-As-Date-Table/") == (
        "https://www.sqlbi.com/articles/Mark-As-Date-Table"
    )


def test_caminho_sem_idioma():
    assert caminho_sem_idioma(L + "dax/best-practices/x") == "dax/best-practices/x"


def test_em_outro_idioma():
    assert em_outro_idioma(L + "dax/x", "pt-br") == "https://learn.microsoft.com/pt-br/dax/x"


def test_secao_propria():
    secoes = ["power-bi/guidance", "dax", "powerquery-m"]
    assert secao_propria(L + "dax/best-practices/x", secoes) == "dax"
    assert secao_propria(L + "power-bi/guidance/star-schema", secoes) == "power-bi/guidance"
    assert secao_propria(L + "fabric/cicd/x", secoes) is None


def test_secao_propria_e_prefixo_de_pasta_nao_de_texto():
    assert secao_propria(L + "daxguide/x", ["dax"]) is None


def test_secao_propria_prefere_a_mais_longa():
    assert secao_propria(L + "power-bi/guidance/x", ["power-bi", "power-bi/guidance"]) == (
        "power-bi/guidance"
    )
```

- [ ] **Passo 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_urls.py -q`
Expected: erro de coleta `ModuleNotFoundError: No module named 'rag'`.

- [ ] **Passo 4: Implementar**

Criar `rag/__init__.py`:

```python
"""Base de conhecimento da auditoria (Fase 3): catálogo, coleta e recuperação."""
```

Criar `rag/urls.py`:

```python
"""Regras de URL do catálogo de fontes.

Funções puras: nenhuma faz rede. O `toc.json` do Learn usa quatro formas de
link — relativo, relativo com `../`, relativo à raiz e absoluto —, e a relativa
à raiz não traz o idioma (`/dax/best-practices/...`). Resolvida sem prefixá-lo,
ela apontaria para fora do Learn em inglês e seria descartada.
"""

import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

HOST_LEARN = "learn.microsoft.com"

FORA_DO_LEARN = "fora do learn"
NAO_DOCUMENTAL = "entrada de seção ou área não documental"

PREFIXOS_NAO_DOCUMENTAIS = ("contribute/", "answers/", "training/")
"""Áreas do Learn que aparecem na navegação mas não são documentação. Segunda
barreira: as páginas de entrada delas já terminam em `/`."""

_IDIOMA = re.compile(r"^/[a-z]{2}-[a-z]{2}/", re.IGNORECASE)


def _com_idioma(caminho: str, idioma: str) -> str:
    if _IDIOMA.match(caminho):
        return _IDIOMA.sub(f"/{idioma}/", caminho, count=1)
    return f"/{idioma}{caminho}"


def resolver_href(href: str, secao: str, idioma: str = "en-us") -> str:
    """URL absoluta de um `href` do `toc.json` da `secao`, no `idioma` dado."""
    if href.startswith(("http://", "https://")):
        partes = urlsplit(href)
        if partes.netloc.lower() != HOST_LEARN:
            return href
        return f"https://{HOST_LEARN}{_com_idioma(partes.path, idioma)}"
    if href.startswith("/"):
        return f"https://{HOST_LEARN}{_com_idioma(href, idioma)}"
    return urljoin(f"https://{HOST_LEARN}/{idioma}/{secao}/", href)


def motivo_de_exclusao(url: str) -> str | None:
    """Por que a URL resolvida não entra no catálogo; `None` se entra."""
    partes = urlsplit(url)
    if partes.netloc.lower() != HOST_LEARN:
        return FORA_DO_LEARN
    caminho = _IDIOMA.sub("", partes.path, count=1).lower()
    if partes.path.endswith("/") or caminho.startswith(PREFIXOS_NAO_DOCUMENTAIS):
        return NAO_DOCUMENTAL
    return None


def normalizar_url(url: str) -> str:
    """Forma canônica para comparar e para gravar.

    Sem `?query`, sem `#fragmento`, sem barra final; esquema e host em
    minúsculas. No Learn o caminho também vai para minúsculas, porque o site
    não diferencia caixa e uma âncora escrita com `/DAX/` precisa casar com o
    `toc.json`, que é todo minúsculo.
    """
    partes = urlsplit(url.strip())
    host = partes.netloc.lower()
    caminho = partes.path.rstrip("/")
    if host == HOST_LEARN:
        caminho = caminho.lower()
    return urlunsplit((partes.scheme.lower(), host, caminho, "", ""))


def caminho_sem_idioma(url: str) -> str:
    """`https://learn.microsoft.com/en-us/dax/x` → `dax/x`."""
    return _IDIOMA.sub("", urlsplit(url).path, count=1)


def em_outro_idioma(url: str, idioma: str) -> str:
    """A mesma página do Learn em outro idioma."""
    partes = urlsplit(url)
    return urlunsplit(
        (partes.scheme, partes.netloc, _com_idioma(partes.path, idioma), "", "")
    )


def secao_propria(url: str, secoes: Iterable[str]) -> str | None:
    """A seção à qual a página pertence pelo caminho — a mais longa que casar."""
    caminho = caminho_sem_idioma(url) + "/"
    candidatas = [s for s in secoes if caminho.startswith(s + "/")]
    return max(candidatas, key=len) if candidatas else None
```

- [ ] **Passo 5: Rodar e ver passar; rodar a suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_urls.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 196 + os novos, todos passando.

- [ ] **Passo 6: Commit**

```bash
git add requirements.txt rag/__init__.py rag/urls.py tests/test_rag_urls.py
git commit -m "feat(rag): regras de URL do catalogo de fontes

Resolve as quatro formas de href do toc.json do Learn, prefixando o
idioma no link relativo a raiz; exclui host externo e area nao
documental; normaliza para comparar com as ancoras das regras.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 2: Retratos — modelos, achatamento e serialização

**Files:**
- Create: `rag/tocs.py`
- Test: `tests/test_rag_tocs.py`

**Interfaces:**
- Consumes: nada.
- Produces (`rag/tocs.py`):
  - `class Secao(NamedTuple): caminho: str; papel: Literal["origem", "ancora"]`
  - `SECOES: tuple[Secao, ...]` (ordem da Global Constraints)
  - `IDIOMAS: tuple[str, ...] = ("en-us", "pt-br")`
  - `class ErroDeRetrato(Exception)`
  - `class ItemToc(BaseModel): href: str; titulo: str | None = None`
  - `class Retrato(BaseModel): secao: str; idioma: str; url: str; baixado_em: date; itens: list[ItemToc]`
  - `url_do_toc(secao: str, idioma: str) -> str`
  - `caminho_do_retrato(pasta: Path, idioma: str, secao: str) -> Path`
  - `achatar_toc(bruto: object, origem: str) -> list[ItemToc]`
  - `serializar_retrato(retrato: Retrato) -> str`

- [ ] **Passo 1: Escrever os testes que falham**

Criar `tests/test_rag_tocs.py`:

```python
"""Retratos dos `toc.json` do Learn.

O retrato versionado é uma listagem normalizada (caminho e título), não o
arquivo bruto: os termos de uso do Learn não permitem publicar cópia literal
num repositório público (spec, seção 5.2).
"""

from datetime import date
from pathlib import Path

import pytest

from rag.tocs import (
    IDIOMAS,
    SECOES,
    ErroDeRetrato,
    ItemToc,
    Retrato,
    achatar_toc,
    caminho_do_retrato,
    serializar_retrato,
    url_do_toc,
)

HOJE = date(2026, 10, 9)

TOC = {
    "items": [
        {"href": "./", "toc_title": "Guidance"},
        {
            "toc_title": "Grupo sem href",
            "children": [
                {"href": "star-schema", "toc_title": "Star schema"},
                {"href": "auto-date-time"},
            ],
        },
    ]
}


def test_secoes_e_idiomas_da_spec():
    assert [(s.caminho, s.papel) for s in SECOES] == [
        ("power-bi/guidance", "origem"),
        ("dax", "origem"),
        ("powerquery-m", "origem"),
        ("power-bi/connect-data", "ancora"),
        ("power-bi/transform-model", "ancora"),
    ]
    assert IDIOMAS == ("en-us", "pt-br")


def test_achatar_toc_em_ordem_e_so_com_href():
    assert achatar_toc(TOC, "x") == [
        ItemToc(href="./", titulo="Guidance"),
        ItemToc(href="star-schema", titulo="Star schema"),
        ItemToc(href="auto-date-time", titulo=None),
    ]


@pytest.mark.parametrize("bruto", [{}, {"items": None}, [], "texto"])
def test_achatar_toc_recusa_estrutura_inesperada(bruto):
    with pytest.raises(ErroDeRetrato, match="items"):
        achatar_toc(bruto, "origem.json")


def test_url_do_toc():
    assert url_do_toc("power-bi/guidance", "pt-br") == (
        "https://learn.microsoft.com/pt-br/power-bi/guidance/toc.json"
    )


def test_caminho_do_retrato_aninha_a_secao():
    assert caminho_do_retrato(Path("r"), "en-us", "power-bi/guidance") == Path(
        "r/en-us/power-bi/guidance.json"
    )


def test_serializacao_tem_ordem_e_indentacao_fixas_e_volta_igual():
    retrato = Retrato(
        secao="dax",
        idioma="en-us",
        url="u",
        baixado_em=HOJE,
        itens=[ItemToc(href="a", titulo="Á")],
    )
    texto = serializar_retrato(retrato)
    assert texto == (
        '{\n  "secao": "dax",\n  "idioma": "en-us",\n  "url": "u",\n'
        '  "baixado_em": "2026-10-09",\n  "itens": [\n    {\n'
        '      "href": "a",\n      "titulo": "Á"\n    }\n  ]\n}\n'
    )
    assert Retrato.model_validate_json(texto) == retrato
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_tocs.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.tocs'`.

- [ ] **Passo 3: Implementar**

Criar `rag/tocs.py`:

```python
"""Retratos dos `toc.json` do Microsoft Learn.

Único módulo do catálogo que faz rede. Um retrato é a listagem normalizada de
um `toc.json` — caminho e título de cada item, em ordem —, datada e gravada em
`rag/tocs/`, que é versionado. O arquivo bruto vai para `rag/store/raw/tocs/`,
fora do Git: os termos de uso do Learn permitem uso pessoal e não comercial,
não a republicação de cópia literal (spec, seção 5.2).
"""

import json
from datetime import date
from pathlib import Path
from typing import Literal, NamedTuple

from pydantic import BaseModel


class Secao(NamedTuple):
    caminho: str
    papel: Literal["origem", "ancora"]
    """`origem`: a seção inteira entra no catálogo. `ancora`: só serve para
    achar o título da âncora de uma regra que mora fora das origens."""


SECOES: tuple[Secao, ...] = (
    Secao("power-bi/guidance", "origem"),
    Secao("dax", "origem"),
    Secao("powerquery-m", "origem"),
    Secao("power-bi/connect-data", "ancora"),
    Secao("power-bi/transform-model", "ancora"),
)
"""Âncora de regra futura fora destas cinco faz `gerar` falhar nomeando a URL;
a correção é uma linha aqui e um `atualizar` (spec, seção 3.5)."""

IDIOMAS: tuple[str, ...] = ("en-us", "pt-br")


class ErroDeRetrato(Exception):
    """Falha ao obter ou interpretar um `toc.json`."""


class ItemToc(BaseModel):
    href: str
    titulo: str | None = None


class Retrato(BaseModel):
    secao: str
    idioma: str
    url: str
    baixado_em: date
    itens: list[ItemToc]


def url_do_toc(secao: str, idioma: str) -> str:
    return f"https://learn.microsoft.com/{idioma}/{secao}/toc.json"


def caminho_do_retrato(pasta: Path, idioma: str, secao: str) -> Path:
    return pasta / idioma / f"{secao}.json"


def achatar_toc(bruto: object, origem: str) -> list[ItemToc]:
    """Os itens com `href`, na ordem em que aparecem na árvore."""
    if not isinstance(bruto, dict) or not isinstance(bruto.get("items"), list):
        raise ErroDeRetrato(f"{origem}: estrutura inesperada — falta a lista 'items'")
    itens: list[ItemToc] = []

    def visitar(nos: list) -> None:
        for no in nos:
            if not isinstance(no, dict):
                continue
            if no.get("href"):
                itens.append(ItemToc(href=no["href"], titulo=no.get("toc_title")))
            visitar(no.get("children") or [])

    visitar(bruto["items"])
    return itens


def serializar_retrato(retrato: Retrato) -> str:
    """JSON com ordem de chaves e indentação fixas: o `git diff` entre dois
    retratos mostra exatamente o que a Microsoft mudou."""
    return json.dumps(retrato.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
```

- [ ] **Passo 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_tocs.py -q`
Expected: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add rag/tocs.py tests/test_rag_tocs.py
git commit -m "feat(rag): retratos normalizados dos toc.json do Learn

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 3: Retratos — download com buscador injetado e gravação só no fim

**Files:**
- Modify: `rag/tocs.py` (acrescentar no fim)
- Test: `tests/test_rag_tocs.py` (acrescentar no fim)

**Interfaces:**
- Consumes: tudo da Tarefa 2.
- Produces (`rag/tocs.py`):
  - `USER_AGENT: str`, `TIMEOUT_S: int = 30`
  - `Buscador = Callable[[str], bytes]`
  - `buscar_padrao(url: str) -> bytes` (levanta `ErroDeRetrato` em HTTP ≠ 200, erro de rede ou timeout)
  - `baixar_retratos(buscar: Buscador, hoje: date, pasta_versionada: Path, pasta_bruta: Path, links_a_verificar: Sequence[str] = ()) -> list[Retrato]`

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar a `tests/test_rag_tocs.py` (e incluir `import json` e `import urllib.error, urllib.request` no topo, junto dos outros imports; e `baixar_retratos`, `buscar_padrao` no import de `rag.tocs`):

```python
import json
import urllib.error
import urllib.request
```

```python
from rag import tocs
from rag.tocs import baixar_retratos, buscar_padrao
```

```python
TOC_MINIMO = {"items": [{"href": "pagina", "toc_title": "Página"}]}


def _buscador(falhar_em=None, respostas=None):
    chamadas = []

    def buscar(url):
        chamadas.append(url)
        if url == falhar_em:
            raise ErroDeRetrato(f"{url}: HTTP 500")
        if respostas and url in respostas:
            return respostas[url]
        return json.dumps(TOC_MINIMO).encode("utf-8")

    return buscar, chamadas


def test_baixa_os_dez_retratos_e_grava_listagem_e_bruto(tmp_path):
    buscar, _ = _buscador()
    retratos = baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert len(retratos) == len(SECOES) * len(IDIOMAS) == 10
    for secao in SECOES:
        for idioma in IDIOMAS:
            versionado = caminho_do_retrato(tmp_path / "tocs", idioma, secao.caminho)
            retrato = Retrato.model_validate_json(versionado.read_text(encoding="utf-8"))
            assert retrato.baixado_em == HOJE
            assert retrato.url == url_do_toc(secao.caminho, idioma)
            assert retrato.itens == [ItemToc(href="pagina", titulo="Página")]
            bruto = caminho_do_retrato(tmp_path / "bruto", idioma, secao.caminho)
            assert json.loads(bruto.read_bytes()) == TOC_MINIMO


def test_retrato_versionado_tem_fim_de_linha_lf(tmp_path):
    buscar, _ = _buscador()
    baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    arquivo = caminho_do_retrato(tmp_path / "tocs", "en-us", "dax")
    assert b"\r\n" not in arquivo.read_bytes()


def test_falha_no_meio_preserva_os_retratos_antigos(tmp_path):
    pasta = tmp_path / "tocs"
    antigo = caminho_do_retrato(pasta, "en-us", "dax")
    antigo.parent.mkdir(parents=True)
    antigo.write_text("ANTIGO", encoding="utf-8")
    buscar, _ = _buscador(falhar_em=url_do_toc("powerquery-m", "pt-br"))

    with pytest.raises(ErroDeRetrato, match="powerquery-m"):
        baixar_retratos(buscar, HOJE, pasta, tmp_path / "bruto")

    assert antigo.read_text(encoding="utf-8") == "ANTIGO"
    assert [p.name for p in pasta.rglob("*.json")] == ["dax.json"]
    assert not (tmp_path / "bruto").exists()


def test_json_invalido_aborta_nomeando_a_url(tmp_path):
    url = url_do_toc("dax", "en-us")
    buscar, _ = _buscador(respostas={url: b"<html>erro</html>"})
    with pytest.raises(ErroDeRetrato, match="JSON inválido") as erro:
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert url in str(erro.value)
    assert not (tmp_path / "tocs").exists()


def test_toc_sem_items_aborta(tmp_path):
    url = url_do_toc("dax", "pt-br")
    buscar, _ = _buscador(respostas={url: b'{"outra": 1}'})
    with pytest.raises(ErroDeRetrato, match="items"):
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert not (tmp_path / "tocs").exists()


def test_links_do_sqlbi_sao_verificados_sem_gravar_nada(tmp_path):
    link = "https://www.sqlbi.com/articles/mark-as-date-table/"
    buscar, chamadas = _buscador()
    baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto", [link])
    assert link in chamadas
    assert not any("sqlbi" in str(p) for p in tmp_path.rglob("*"))


def test_link_do_sqlbi_morto_aborta_antes_de_gravar(tmp_path):
    link = "https://www.sqlbi.com/articles/morto/"
    buscar, _ = _buscador(falhar_em=link)
    with pytest.raises(ErroDeRetrato, match="morto"):
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto", [link])
    assert not (tmp_path / "tocs").exists()


def test_buscar_padrao_identifica_o_projeto_e_converte_erro_http(monkeypatch):
    pedidos = []

    def urlopen_falso(pedido, timeout):
        pedidos.append((pedido, timeout))
        raise urllib.error.HTTPError(pedido.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato, match="HTTP 404"):
        buscar_padrao("https://learn.microsoft.com/en-us/dax/toc.json")

    pedido, timeout = pedidos[0]
    assert pedido.get_header("User-agent") == tocs.USER_AGENT
    assert tocs.USER_AGENT == "powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)"
    assert timeout == 30


def test_buscar_padrao_converte_erro_de_rede(monkeypatch):
    def urlopen_falso(pedido, timeout):
        raise urllib.error.URLError("sem rota")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato, match="sem rota"):
        buscar_padrao("https://learn.microsoft.com/en-us/dax/toc.json")
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_tocs.py -q`
Expected: `ImportError: cannot import name 'baixar_retratos'`.

- [ ] **Passo 3: Implementar**

Em `rag/tocs.py`, acrescentar aos imports:

```python
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
```

E acrescentar no fim do arquivo:

```python
USER_AGENT = "powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)"
"""Identifica o projeto e o repositório. Sem e-mail: o cabeçalho viaja para
cada servidor consultado."""

TIMEOUT_S = 30

Buscador = Callable[[str], bytes]


def buscar_padrao(url: str) -> bytes:
    """GET com `urllib`. Sem repetição automática: falha é falha, e o comando é
    rodado de novo."""
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
            if resposta.status != 200:
                raise ErroDeRetrato(f"{url}: HTTP {resposta.status}")
            return resposta.read()
    except urllib.error.HTTPError as erro:
        raise ErroDeRetrato(f"{url}: HTTP {erro.code}") from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroDeRetrato(f"{url}: {erro}") from erro


def _gravar_texto(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(texto, encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def baixar_retratos(
    buscar: Buscador,
    hoje: date,
    pasta_versionada: Path,
    pasta_bruta: Path,
    links_a_verificar: Sequence[str] = (),
) -> list[Retrato]:
    """Baixa os dez `toc.json` e confere os links de `links_a_verificar`.

    Nada é gravado antes de tudo dar certo: uma falha no meio deixa os retratos
    antigos intactos. Dos links a verificar só importa a resposta 200; o corpo
    é descartado — é assim que o SQLBI é conferido sem ser copiado.
    """
    baixados: list[tuple[Retrato, bytes]] = []
    for secao in SECOES:
        for idioma in IDIOMAS:
            url = url_do_toc(secao.caminho, idioma)
            conteudo = buscar(url)
            try:
                bruto = json.loads(conteudo)
            except (UnicodeDecodeError, json.JSONDecodeError) as erro:
                raise ErroDeRetrato(f"{url}: JSON inválido ({erro})") from erro
            retrato = Retrato(
                secao=secao.caminho,
                idioma=idioma,
                url=url,
                baixado_em=hoje,
                itens=achatar_toc(bruto, url),
            )
            baixados.append((retrato, conteudo))

    for link in links_a_verificar:
        buscar(link)

    for retrato, conteudo in baixados:
        _gravar_texto(
            caminho_do_retrato(pasta_versionada, retrato.idioma, retrato.secao),
            serializar_retrato(retrato),
        )
        destino_bruto = caminho_do_retrato(pasta_bruta, retrato.idioma, retrato.secao)
        destino_bruto.parent.mkdir(parents=True, exist_ok=True)
        destino_bruto.write_bytes(conteudo)
    return [retrato for retrato, _ in baixados]
```

- [ ] **Passo 4: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_tocs.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add rag/tocs.py tests/test_rag_tocs.py
git commit -m "feat(rag): download dos retratos com buscador injetado

Baixa os dez toc.json e confere os links do SQLBI antes de gravar
qualquer coisa; falha no meio preserva os retratos antigos. O bruto vai
para rag/store/raw/tocs, fora do Git.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 4: Montagem do catálogo do Learn

**Files:**
- Create: `rag/catalogo.py`
- Test: `tests/test_rag_catalogo.py`

**Interfaces:**
- Consumes: `rag.urls.*` (Tarefa 1); `rag.tocs.SECOES`, `IDIOMAS`, `Retrato`, `ItemToc` (Tarefa 2).
- Produces (`rag/catalogo.py`):
  - `LICENCA_LEARN: str`, `LICENCA_SQLBI: str` (verbatim da Global Constraints)
  - `Retratos = dict[tuple[str, str], Retrato]` — chave `(idioma, secao)`
  - `class ErroDeCatalogo(Exception)`
  - `class Fonte(BaseModel)`: campos nesta ordem — `id: str`, `url: str`, `url_pt_br: str | None`, `titulo: str`, `organizacao: str`, `data_acesso: str`, `licenca: str`, `origem: list[str]`, `indexar: bool`, `regras: list[str]`, `observacao: str | None = None`
  - `class LeituraSqlbi(BaseModel)`: `url: str`, `titulo: str`, `regras: list[str]`, `verificado_em: date`
  - `@dataclass class ResultadoCatalogo`: `fontes: list[Fonte]`, `exclusoes: Counter`
  - `montar_catalogo(retratos: Retratos, ancoras: dict[str, str], observacoes: dict[str, str], leituras_sqlbi: list[LeituraSqlbi]) -> ResultadoCatalogo`

Nesta tarefa `montar_catalogo` já recebe `leituras_sqlbi`, mas só a Tarefa 5 a usa; aqui ela é ignorada (lista vazia em todos os testes).

- [ ] **Passo 1: Escrever os testes que falham**

Criar `tests/test_rag_catalogo.py`:

```python
"""Montagem do catálogo de fontes.

Os retratos dos testes são feitos à mão e pequenos; os reais, com 1.420
páginas, são exercitados em `test_rag_dados_reais.py`.
"""

from datetime import date

import pytest

from rag.catalogo import (
    LICENCA_LEARN,
    ErroDeCatalogo,
    Fonte,
    montar_catalogo,
)
from rag.tocs import SECOES, ItemToc, Retrato
from rag.urls import FORA_DO_LEARN, NAO_DOCUMENTAL

HOJE = date(2026, 10, 9)
L = "https://learn.microsoft.com/en-us/"
P = "https://learn.microsoft.com/pt-br/"


def retratos(en=None, pt=None, baixado_em=HOJE):
    """Os dez retratos. Seção não citada fica vazia; `pt=None` replica o `en`."""
    en = en or {}
    pt = en if pt is None else pt
    saida = {}
    for secao in SECOES:
        for idioma, itens in (("en-us", en), ("pt-br", pt)):
            saida[(idioma, secao.caminho)] = Retrato(
                secao=secao.caminho,
                idioma=idioma,
                url=f"https://learn.microsoft.com/{idioma}/{secao.caminho}/toc.json",
                baixado_em=baixado_em,
                itens=[ItemToc(href=h, titulo=t) for h, t in itens.get(secao.caminho, [])],
            )
    return saida


def montar(en=None, pt=None, ancoras=None, observacoes=None, leituras=None, baixado_em=HOJE):
    return montar_catalogo(
        retratos(en, pt, baixado_em), ancoras or {}, observacoes or {}, leituras or []
    )


def por_id(resultado):
    return {f.id: f for f in resultado.fontes}


def test_pagina_de_origem_vira_entrada_completa():
    resultado = montar(en={"power-bi/guidance": [("star-schema", "Star schema")]})
    assert resultado.fontes == [
        Fonte(
            id="learn:power-bi/guidance/star-schema",
            url=L + "power-bi/guidance/star-schema",
            url_pt_br=P + "power-bi/guidance/star-schema",
            titulo="Star schema",
            organizacao="Microsoft",
            data_acesso="2026-10-09",
            licenca=LICENCA_LEARN,
            origem=["toc:power-bi/guidance"],
            indexar=True,
            regras=[],
            observacao=None,
        )
    ]


def test_data_acesso_e_a_do_retrato():
    resultado = montar(en={"dax": [("a", "A")]}, baixado_em=date(2026, 1, 2))
    assert resultado.fontes[0].data_acesso == "2026-01-02"


def test_exclusoes_sao_contadas_por_motivo_e_nao_entram():
    resultado = montar(
        en={
            "power-bi/guidance": [
                ("./", "Guidance"),
                ("/contribute/", "Contribute"),
                ("https://ideas.fabric.microsoft.com/", "Ideas"),
                ("star-schema", "Star"),
            ],
            "dax": [("https://aka.ms/learndax", "Learn DAX")],
        }
    )
    assert [f.id for f in resultado.fontes] == ["learn:power-bi/guidance/star-schema"]
    assert dict(resultado.exclusoes) == {FORA_DO_LEARN: 2, NAO_DOCUMENTAL: 2}


def test_secao_de_ancora_nao_e_origem_nem_conta_exclusao():
    resultado = montar(en={"power-bi/connect-data": [("pagina", "P"), ("./", "Entrada")]})
    assert resultado.fontes == []
    assert dict(resultado.exclusoes) == {}


def test_pagina_em_duas_origens_vira_uma_entrada_com_titulo_da_propria_secao():
    resultado = montar(
        en={
            "power-bi/guidance": [("/dax/best-practices/dax-variables", "Pelo guidance")],
            "dax": [("best-practices/dax-variables", "Use variables")],
        }
    )
    (fonte,) = resultado.fontes
    assert fonte.id == "learn:dax/best-practices/dax-variables"
    assert fonte.origem == ["toc:dax", "toc:power-bi/guidance"]
    assert fonte.titulo == "Use variables"


def test_sem_secao_propria_o_titulo_segue_a_ordem_das_secoes():
    resultado = montar(
        en={
            "power-bi/guidance": [("/fabric/cicd/x", "Do guidance")],
            "powerquery-m": [("/fabric/cicd/x", "Do M")],
        }
    )
    assert resultado.fontes[0].titulo == "Do guidance"


def test_item_sem_titulo_usa_o_ultimo_segmento():
    resultado = montar(en={"power-bi/guidance": [("star-schema", None)]})
    assert resultado.fontes[0].titulo == "star-schema"


def test_url_pt_br_so_quando_o_caminho_esta_no_retrato_pt_br():
    resultado = montar(en={"dax": [("a", "A"), ("b", "B")]}, pt={"dax": [("a", "A pt")]})
    fontes = por_id(resultado)
    assert fontes["learn:dax/a"].url_pt_br == P + "dax/a"
    assert fontes["learn:dax/b"].url_pt_br is None


def test_ancora_dentro_de_origem_acrescenta_origem_e_regra():
    url = L + "power-bi/guidance/star-schema"
    resultado = montar(
        en={"power-bi/guidance": [("star-schema", "Star")]},
        ancoras={"MOD-006": url, "MOD-003": url},
    )
    (fonte,) = resultado.fontes
    assert fonte.origem == ["regra:MOD-003", "regra:MOD-006", "toc:power-bi/guidance"]
    assert fonte.regras == ["MOD-003", "MOD-006"]


def test_ancora_em_secao_que_nao_e_origem_entra_sozinha():
    resultado = montar(
        en={"power-bi/connect-data": [("desktop-data-types", "Data types"), ("outra", "Outra")]},
        ancoras={"PERF-003": L + "power-bi/connect-data/desktop-data-types"},
    )
    (fonte,) = resultado.fontes
    assert fonte.id == "learn:power-bi/connect-data/desktop-data-types"
    assert fonte.origem == ["regra:PERF-003"]
    assert fonte.titulo == "Data types"
    assert fonte.url_pt_br == P + "power-bi/connect-data/desktop-data-types"


def test_ancora_escrita_com_outra_caixa_ou_barra_final_ainda_casa():
    resultado = montar(
        en={"dax": [("best-practices/dax-divide-function-operator", "DIVIDE")]},
        ancoras={"DAX-001": L + "DAX/best-practices/dax-divide-function-operator/"},
    )
    assert resultado.fontes[0].regras == ["DAX-001"]


def test_ancora_ausente_falha_listando_regra_e_url():
    with pytest.raises(ErroDeCatalogo, match="DAX-999: https://learn.microsoft.com/en-us/dax/nao-existe"):
        montar(ancoras={"DAX-999": L + "dax/nao-existe"})


def test_observacao_e_incorporada():
    resultado = montar(en={"dax": [("a", "A")]}, observacoes={"learn:dax/a": "Nota."})
    assert resultado.fontes[0].observacao == "Nota."


def test_observacao_orfa_falha():
    with pytest.raises(ErroDeCatalogo, match="learn:dax/sumiu"):
        montar(en={"dax": [("a", "A")]}, observacoes={"learn:dax/sumiu": "Nota."})


def test_falta_retrato_falha_indicando_atualizar():
    incompletos = retratos()
    del incompletos[("pt-br", "dax")]
    with pytest.raises(ErroDeCatalogo, match="atualizar"):
        montar_catalogo(incompletos, {}, {}, [])


def test_ordem_de_entrada_nao_muda_a_saida():
    itens = [("b", "B"), ("a", "A"), ("c", "C")]
    url = L + "dax/a"
    um = montar(en={"dax": itens}, ancoras={"X-1": url, "X-2": url})
    outro = montar(en={"dax": list(reversed(itens))}, ancoras={"X-2": url, "X-1": url})
    assert um.fontes == outro.fontes
    assert [f.id for f in um.fontes] == ["learn:dax/a", "learn:dax/b", "learn:dax/c"]
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: `ModuleNotFoundError: No module named 'rag.catalogo'`.

- [ ] **Passo 3: Implementar**

Criar `rag/catalogo.py`:

```python
"""Catálogo de fontes da RAG (`rag/sources.yaml`).

`python -m rag.catalogo gerar` monta o catálogo, offline, a partir dos retratos
em `rag/tocs/`, das âncoras das regras, das notas de `rag/observacoes.yaml` e da
curadoria de `rag/leituras_sqlbi.yaml`. `python -m rag.catalogo atualizar`
baixa os retratos antes. Desenho: `docs/superpowers/specs/
2026-10-09-catalogo-de-fontes-rag-design.md`.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from pydantic import BaseModel

from rag.tocs import SECOES, Retrato
from rag.urls import (
    caminho_sem_idioma,
    em_outro_idioma,
    motivo_de_exclusao,
    normalizar_url,
    resolver_href,
    secao_propria,
)

LICENCA_LEARN = (
    "Termos de uso do Microsoft Learn — uso pessoal e não comercial; cópia local "
    "não redistribuída (https://learn.microsoft.com/en-us/legal/termsofuse)"
)
LICENCA_SQLBI = (
    "© SQLBI, todos os direitos reservados — somente referência bibliográfica; "
    "conteúdo não coletado"
)

Retratos = dict[tuple[str, str], Retrato]
"""Chave `(idioma, secao)`."""


class ErroDeCatalogo(Exception):
    """O catálogo não pode ser gerado sem perder algo em silêncio."""


class Fonte(BaseModel):
    """Uma entrada do `sources.yaml`. A ordem dos campos é a ordem no arquivo."""

    id: str
    url: str
    url_pt_br: str | None
    titulo: str
    organizacao: str
    data_acesso: str
    licenca: str
    origem: list[str]
    indexar: bool
    regras: list[str]
    observacao: str | None = None


class LeituraSqlbi(BaseModel):
    """Uma entrada de `rag/leituras_sqlbi.yaml`, mantido à mão."""

    url: str
    titulo: str
    regras: list[str]
    verificado_em: date


@dataclass
class ResultadoCatalogo:
    fontes: list[Fonte]
    exclusoes: Counter = field(default_factory=Counter)


def _retrato(retratos: Retratos, idioma: str, secao: str) -> Retrato:
    try:
        return retratos[(idioma, secao)]
    except KeyError:
        raise ErroDeCatalogo(
            f"falta o retrato {idioma}/{secao} — rode `python -m rag.catalogo atualizar`"
        ) from None


def _ultimo_segmento(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _secao_do_titulo(url: str, por_secao: dict[str, object]) -> str:
    """A seção própria da página, se ela a retrata; senão, a primeira na ordem
    de `SECOES` que a retrata."""
    propria = secao_propria(url, por_secao)
    if propria is not None:
        return propria
    return next(s.caminho for s in SECOES if s.caminho in por_secao)


def _fontes_do_learn(
    retratos: Retratos, ancoras: dict[str, str]
) -> tuple[dict[str, Fonte], Counter]:
    exclusoes: Counter = Counter()
    titulos: dict[str, dict[str, tuple[str | None, Retrato]]] = {}
    origens: dict[str, set[str]] = {}

    for secao in SECOES:
        retrato = _retrato(retratos, "en-us", secao.caminho)
        for item in retrato.itens:
            url = resolver_href(item.href, secao.caminho, "en-us")
            motivo = motivo_de_exclusao(url)
            if motivo is not None:
                if secao.papel == "origem":
                    exclusoes[motivo] += 1
                continue
            chave = normalizar_url(url)
            titulos.setdefault(chave, {}).setdefault(secao.caminho, (item.titulo, retrato))
            if secao.papel == "origem":
                origens.setdefault(chave, set()).add(f"toc:{secao.caminho}")

    em_pt_br: dict[str, set[str]] = {}
    for secao in SECOES:
        retrato = _retrato(retratos, "pt-br", secao.caminho)
        conjunto: set[str] = set()
        for item in retrato.itens:
            url = resolver_href(item.href, secao.caminho, "pt-br")
            if motivo_de_exclusao(url) is None:
                conjunto.add(normalizar_url(em_outro_idioma(url, "en-us")))
        em_pt_br[secao.caminho] = conjunto

    regras_por_url: dict[str, set[str]] = {}
    faltantes: list[str] = []
    for id_regra, url in sorted(ancoras.items()):
        chave = normalizar_url(url)
        if chave not in titulos:
            faltantes.append(f"{id_regra}: {url}")
            continue
        origens.setdefault(chave, set()).add(f"regra:{id_regra}")
        regras_por_url.setdefault(chave, set()).add(id_regra)
    if faltantes:
        raise ErroDeCatalogo(
            "âncora fora de todos os retratos — acrescente a seção em "
            "`rag.tocs.SECOES` e rode `python -m rag.catalogo atualizar`:\n  "
            + "\n  ".join(faltantes)
        )

    fontes: dict[str, Fonte] = {}
    for chave, conjunto in origens.items():
        secao = _secao_do_titulo(chave, titulos[chave])
        titulo, retrato = titulos[chave][secao]
        identificador = "learn:" + caminho_sem_idioma(chave)
        fontes[identificador] = Fonte(
            id=identificador,
            url=chave,
            url_pt_br=em_outro_idioma(chave, "pt-br") if chave in em_pt_br[secao] else None,
            titulo=titulo or _ultimo_segmento(chave),
            organizacao="Microsoft",
            data_acesso=retrato.baixado_em.isoformat(),
            licenca=LICENCA_LEARN,
            origem=sorted(conjunto),
            indexar=True,
            regras=sorted(regras_por_url.get(chave, set())),
        )
    return fontes, exclusoes


def montar_catalogo(
    retratos: Retratos,
    ancoras: dict[str, str],
    observacoes: dict[str, str],
    leituras_sqlbi: list[LeituraSqlbi],
) -> ResultadoCatalogo:
    """O catálogo, ordenado por `id`. Função pura: sem rede e sem arquivo.

    Falha alto — `ErroDeCatalogo` — quando produzir o catálogo perderia algo em
    silêncio: retrato ausente, âncora de regra fora de todos os retratos, nota
    para uma página que saiu do catálogo.
    """
    fontes, exclusoes = _fontes_do_learn(retratos, ancoras)

    orfas = sorted(set(observacoes) - set(fontes))
    if orfas:
        raise ErroDeCatalogo(
            "nota em rag/observacoes.yaml para id fora do catálogo: " + ", ".join(orfas)
        )
    for identificador, texto in observacoes.items():
        fontes[identificador] = fontes[identificador].model_copy(update={"observacao": texto})

    return ResultadoCatalogo(
        fontes=[fontes[i] for i in sorted(fontes)], exclusoes=exclusoes
    )
```

- [ ] **Passo 4: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add rag/catalogo.py tests/test_rag_catalogo.py
git commit -m "feat(rag): montagem do catalogo do Learn

Origens dos toc.json, ancoras das regras, url_pt_br conferida no
retrato pt-BR e notas humanas. Falha com ancora fora dos retratos,
retrato ausente ou nota orfa.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 5: Curadoria do SQLBI no catálogo

**Files:**
- Modify: `rag/catalogo.py`
- Test: `tests/test_rag_catalogo.py` (acrescentar)

**Interfaces:**
- Consumes: `montar_catalogo`, `Fonte`, `LeituraSqlbi`, `LICENCA_SQLBI` (Tarefa 4); `normalizar_url` (Tarefa 1).
- Produces: `montar_catalogo` passa a incluir as leituras do SQLBI. Assinatura inalterada.

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar ao import de `rag.catalogo` em `tests/test_rag_catalogo.py`: `LICENCA_SQLBI`, `LeituraSqlbi`. Acrescentar `import re` no topo. Acrescentar no fim:

```python
LEITURA = LeituraSqlbi(
    url="https://www.sqlbi.com/articles/mark-as-date-table/",
    titulo="Mark as Date table",
    regras=["MOD-005"],
    verificado_em=HOJE,
)
ANCORAS = {"MOD-005": L + "power-bi/transform-model/desktop-date-tables"}
EN_ANCORA = {"power-bi/transform-model": [("desktop-date-tables", "Date tables")]}


def test_leitura_do_sqlbi_vira_referencia_nao_indexada():
    resultado = montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA])
    assert por_id(resultado)["sqlbi:mark-as-date-table"] == Fonte(
        id="sqlbi:mark-as-date-table",
        url="https://www.sqlbi.com/articles/mark-as-date-table/",
        url_pt_br=None,
        titulo="Mark as Date table",
        organizacao="SQLBI",
        data_acesso="2026-10-09",
        licenca=LICENCA_SQLBI,
        origem=["curadoria:sqlbi"],
        indexar=False,
        regras=["MOD-005"],
        observacao=None,
    )


def test_learn_e_sqlbi_ficam_ordenados_juntos_por_id():
    resultado = montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA])
    assert [f.id for f in resultado.fontes] == [
        "learn:power-bi/transform-model/desktop-date-tables",
        "sqlbi:mark-as-date-table",
    ]


@pytest.mark.parametrize(
    "mudanca, trecho",
    [
        ({"url": "https://sqlbi.com/articles/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "https://www.sqlbi.com/blog/marco/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "http://www.sqlbi.com/articles/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "https://www.sqlbi.com/articles/"}, "https://www.sqlbi.com/articles/"),
        ({"regras": []}, "sem regra"),
        ({"regras": ["XYZ-001"]}, "XYZ-001"),
    ],
)
def test_leitura_invalida_falha_nomeando_a_entrada(mudanca, trecho):
    leitura = LEITURA.model_copy(update=mudanca)
    with pytest.raises(ErroDeCatalogo, match=re.escape(trecho)):
        montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[leitura])


def test_leitura_repetida_falha():
    sem_barra = LEITURA.model_copy(
        update={"url": "https://www.sqlbi.com/articles/mark-as-date-table"}
    )
    with pytest.raises(ErroDeCatalogo, match="repetida"):
        montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA, sem_barra])


def test_nota_pode_ser_dada_a_uma_leitura_do_sqlbi():
    resultado = montar(
        en=EN_ANCORA,
        ancoras=ANCORAS,
        leituras=[LEITURA],
        observacoes={"sqlbi:mark-as-date-table": "Complementa a âncora."},
    )
    assert por_id(resultado)["sqlbi:mark-as-date-table"].observacao == "Complementa a âncora."
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: falham `test_leitura_do_sqlbi_vira_referencia_nao_indexada` (KeyError), `test_learn_e_sqlbi_...`, as parametrizadas (`DID NOT RAISE`), `test_leitura_repetida_falha` e `test_nota_pode_ser_dada_...` (nota órfã).

- [ ] **Passo 3: Implementar**

Em `rag/catalogo.py`, acrescentar `from urllib.parse import urlsplit` aos imports e, antes de `montar_catalogo`, a função:

```python
def _fontes_do_sqlbi(
    leituras: list[LeituraSqlbi], ids_de_regras: set[str]
) -> list[Fonte]:
    """Referências curadas: entram com `indexar: false` e nunca são baixadas.

    O conteúdo do SQLBI é de todos os direitos reservados, sem permissão de uso
    nos termos do site (spec, seção 5.3); link e título são referência
    bibliográfica.
    """
    fontes: list[Fonte] = []
    vistas: set[str] = set()
    for leitura in leituras:
        partes = urlsplit(leitura.url)
        if (
            partes.scheme != "https"
            or partes.netloc.lower() != "www.sqlbi.com"
            or not partes.path.startswith("/articles/")
            or partes.path.rstrip("/") == "/articles"
        ):
            raise ErroDeCatalogo(
                f"leitura do SQLBI fora de https://www.sqlbi.com/articles/: {leitura.url}"
            )
        if not leitura.regras:
            raise ErroDeCatalogo(f"leitura do SQLBI sem regra: {leitura.url}")
        desconhecidas = sorted(set(leitura.regras) - ids_de_regras)
        if desconhecidas:
            raise ErroDeCatalogo(
                f"leitura do SQLBI com regra inexistente {', '.join(desconhecidas)}: "
                f"{leitura.url}"
            )
        chave = normalizar_url(leitura.url)
        if chave in vistas:
            raise ErroDeCatalogo(f"leitura do SQLBI repetida: {leitura.url}")
        vistas.add(chave)
        fontes.append(
            Fonte(
                id="sqlbi:" + _ultimo_segmento(chave),
                url=leitura.url,
                url_pt_br=None,
                titulo=leitura.titulo,
                organizacao="SQLBI",
                data_acesso=leitura.verificado_em.isoformat(),
                licenca=LICENCA_SQLBI,
                origem=["curadoria:sqlbi"],
                indexar=False,
                regras=sorted(set(leitura.regras)),
            )
        )
    return fontes
```

Em `montar_catalogo`, logo depois de `fontes, exclusoes = _fontes_do_learn(retratos, ancoras)`, acrescentar:

```python
    for fonte in _fontes_do_sqlbi(leituras_sqlbi, set(ancoras)):
        fontes[fonte.id] = fonte
```

E acrescentar à docstring de `montar_catalogo`, depois da primeira frase: `As leituras do SQLBI entram como referência (`indexar: false`).`

- [ ] **Passo 4: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add rag/catalogo.py tests/test_rag_catalogo.py
git commit -m "feat(rag): leituras do SQLBI como referencia nao indexada

Validacao offline da curadoria: so www.sqlbi.com/articles, ao menos uma
regra, toda regra existente, sem repeticao.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 6: Arquivos e comando — leitura, YAML determinístico, `gerar`/`atualizar`

**Files:**
- Modify: `rag/catalogo.py`
- Test: `tests/test_rag_catalogo.py` (acrescentar)

**Interfaces:**
- Consumes: tudo das Tarefas 2–5; `rag.tocs.baixar_retratos`, `buscar_padrao`, `caminho_do_retrato`, `serializar_retrato`, `ErroDeRetrato`, `IDIOMAS`.
- Produces (`rag/catalogo.py`):
  - `RAIZ`, `PASTA_TOCS`, `PASTA_BRUTA`, `ARQUIVO_FONTES`, `ARQUIVO_OBSERVACOES`, `ARQUIVO_LEITURAS` (`Path`)
  - `CABECALHO_YAML: str`
  - `ler_retratos(pasta: Path) -> Retratos`
  - `ler_observacoes(caminho: Path) -> dict[str, str]`
  - `ler_leituras_sqlbi(caminho: Path) -> list[LeituraSqlbi]`
  - `como_yaml(fontes: list[Fonte]) -> str`
  - `escrever_yaml(fontes: list[Fonte], caminho: Path) -> None`
  - `ancoras_do_registro() -> dict[str, str]`
  - `gerar(*, pasta_tocs=None, destino=None, observacoes=None, leituras=None, ancoras=None) -> ResultadoCatalogo` (`None` = constante do módulo, resolvida na chamada)
  - `atualizar(*, buscar=None, hoje=None, pasta_tocs=None, pasta_bruta=None, destino=None, observacoes=None, leituras=None, ancoras=None) -> ResultadoCatalogo`
  - `resumo(resultado: ResultadoCatalogo, ancoras: dict[str, str]) -> str`
  - `main(argv: list[str] | None = None) -> int`

- [ ] **Passo 1: Escrever os testes que falham**

Acrescentar ao import de `rag.catalogo`: `CABECALHO_YAML`, `atualizar`, `como_yaml`, `escrever_yaml`, `gerar`, `ler_leituras_sqlbi`, `ler_observacoes`, `ler_retratos`, `main`, `resumo`; e `from rag import catalogo`. Acrescentar `import json`, `import yaml` e `from rag.tocs import IDIOMAS, caminho_do_retrato, serializar_retrato` no topo. Acrescentar no fim:

```python
def gravar_retratos(pasta, en=None, pt=None):
    for (idioma, secao), retrato in retratos(en, pt).items():
        caminho = caminho_do_retrato(pasta, idioma, secao)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(serializar_retrato(retrato), encoding="utf-8")


def test_ler_retratos_volta_o_que_foi_gravado(tmp_path):
    gravar_retratos(tmp_path, en={"dax": [("a", "A")]})
    assert ler_retratos(tmp_path) == retratos(en={"dax": [("a", "A")]})


def test_ler_retratos_sem_um_arquivo_falha_nomeando_e_indicando_atualizar(tmp_path):
    gravar_retratos(tmp_path)
    faltando = caminho_do_retrato(tmp_path, "pt-br", "powerquery-m")
    faltando.unlink()
    with pytest.raises(ErroDeCatalogo, match="atualizar") as erro:
        ler_retratos(tmp_path)
    assert "powerquery-m" in str(erro.value)


def test_ler_retratos_com_estrutura_inesperada_falha(tmp_path):
    gravar_retratos(tmp_path)
    caminho_do_retrato(tmp_path, "en-us", "dax").write_text('{"x": 1}', encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="estrutura inesperada"):
        ler_retratos(tmp_path)


@pytest.mark.parametrize("conteudo", [None, "", "# só comentário\n", "# cabeçalho\n{}\n"])
def test_observacoes_ausentes_ou_vazias_sao_vazias(tmp_path, conteudo):
    caminho = tmp_path / "observacoes.yaml"
    if conteudo is not None:
        caminho.write_text(conteudo, encoding="utf-8")
    assert ler_observacoes(caminho) == {}


def test_observacoes_lidas(tmp_path):
    caminho = tmp_path / "observacoes.yaml"
    caminho.write_text("learn:dax/a: Nota sobre a página.\n", encoding="utf-8")
    assert ler_observacoes(caminho) == {"learn:dax/a": "Nota sobre a página."}


def test_observacoes_em_formato_errado_falham(tmp_path):
    caminho = tmp_path / "observacoes.yaml"
    caminho.write_text("- uma lista\n", encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="id -> texto"):
        ler_observacoes(caminho)


@pytest.mark.parametrize("conteudo", [None, "", "# só comentário\n", "[]\n"])
def test_leituras_ausentes_ou_vazias_sao_vazias(tmp_path, conteudo):
    caminho = tmp_path / "leituras.yaml"
    if conteudo is not None:
        caminho.write_text(conteudo, encoding="utf-8")
    assert ler_leituras_sqlbi(caminho) == []


def test_leituras_lidas(tmp_path):
    caminho = tmp_path / "leituras.yaml"
    caminho.write_text(
        "- url: https://www.sqlbi.com/articles/mark-as-date-table/\n"
        "  titulo: Mark as Date table\n"
        "  regras: [MOD-005]\n"
        "  verificado_em: '2026-10-09'\n",
        encoding="utf-8",
    )
    assert ler_leituras_sqlbi(caminho) == [LEITURA]


def test_leitura_sem_campo_obrigatorio_falha(tmp_path):
    caminho = tmp_path / "leituras.yaml"
    caminho.write_text("- url: https://www.sqlbi.com/articles/x/\n", encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="entrada inválida"):
        ler_leituras_sqlbi(caminho)


def test_yaml_e_deterministico_com_lf_e_unicode(tmp_path):
    resultado = montar(en={"dax": [("a", "Ação")]})
    um, outro = tmp_path / "um.yaml", tmp_path / "outro.yaml"
    escrever_yaml(resultado.fontes, um)
    escrever_yaml(resultado.fontes, outro)
    assert um.read_bytes() == outro.read_bytes()
    assert b"\r\n" not in um.read_bytes()
    assert "Ação" in um.read_text(encoding="utf-8")


def test_yaml_comeca_avisando_que_e_gerado_e_volta_igual():
    resultado = montar(en={"dax": [("a", "A")]}, leituras=[])
    texto = como_yaml(resultado.fontes)
    assert texto.startswith(CABECALHO_YAML)
    dados = yaml.safe_load(texto)
    assert [Fonte.model_validate(d) for d in dados] == resultado.fontes
    assert list(dados[0]) == list(Fonte.model_fields)


def test_gerar_escreve_o_catalogo(tmp_path):
    gravar_retratos(tmp_path / "tocs", en={"dax": [("a", "A")]})
    destino = tmp_path / "sources.yaml"
    resultado = gerar(
        pasta_tocs=tmp_path / "tocs",
        destino=destino,
        observacoes=tmp_path / "nao-existe.yaml",
        leituras=tmp_path / "nao-existe.yaml",
        ancoras={},
    )
    assert destino.read_text(encoding="utf-8") == como_yaml(resultado.fontes)
    assert [f.id for f in resultado.fontes] == ["learn:dax/a"]


def test_atualizar_baixa_confere_o_sqlbi_e_gera(tmp_path):
    chamadas = []

    def buscar(url):
        chamadas.append(url)
        return json.dumps({"items": [{"href": "pagina", "toc_title": "Página"}]}).encode()

    leituras = tmp_path / "leituras.yaml"
    leituras.write_text(
        "- url: https://www.sqlbi.com/articles/x/\n  titulo: X\n  regras: [R-1]\n"
        "  verificado_em: '2026-10-09'\n",
        encoding="utf-8",
    )
    resultado = atualizar(
        buscar=buscar,
        hoje=HOJE,
        pasta_tocs=tmp_path / "tocs",
        pasta_bruta=tmp_path / "bruto",
        destino=tmp_path / "sources.yaml",
        observacoes=tmp_path / "nao-existe.yaml",
        leituras=leituras,
        ancoras={"R-1": L + "dax/pagina"},
    )
    assert "https://www.sqlbi.com/articles/x/" in chamadas
    assert {f.id for f in resultado.fontes} >= {"learn:dax/pagina", "sqlbi:x"}
    assert (tmp_path / "sources.yaml").is_file()


def test_resumo_traz_contagens_exclusoes_e_ancoras():
    ancoras = {
        "DAX-001": L + "dax/a",
        "MOD-005": L + "power-bi/transform-model/desktop-date-tables",
    }
    resultado = montar(
        en={
            "dax": [("a", "A"), ("https://aka.ms/x", "Fora")],
            "power-bi/transform-model": [("desktop-date-tables", "Date tables")],
        },
        ancoras=ancoras,
        leituras=[LEITURA],
    )
    texto = resumo(resultado, ancoras)
    # 2 do Learn (dax/a e a âncora de MOD-005), 1 do SQLBI, 1 link fora do Learn;
    # `pt` replica `en`, então as duas do Learn têm url_pt_br.
    assert "2 indexadas" in texto
    assert "1 só referência" in texto
    assert "toc:dax: 1" in texto
    assert "regra: 2" in texto
    assert "curadoria:sqlbi: 1" in texto
    assert f"{FORA_DO_LEARN}: 1" in texto
    assert "com url_pt_br: 2 de 2" in texto
    assert "DAX-001 -> learn:dax/a" in texto
    assert "MOD-005 -> learn:power-bi/transform-model/desktop-date-tables" in texto


def test_main_sem_retratos_sai_com_erro_indicando_atualizar(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catalogo, "PASTA_TOCS", tmp_path / "vazia")
    monkeypatch.setattr(catalogo, "ARQUIVO_FONTES", tmp_path / "sources.yaml")
    assert main(["gerar"]) == 1
    assert "atualizar" in capsys.readouterr().err
    assert not (tmp_path / "sources.yaml").exists()
```

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: `ImportError: cannot import name 'CABECALHO_YAML'`.

- [ ] **Passo 3: Implementar**

Em `rag/catalogo.py`, acrescentar aos imports:

```python
import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from rag import tocs
from rag.tocs import IDIOMAS
```

(e manter os existentes; `from rag.tocs import SECOES, Retrato` passa a `from rag.tocs import IDIOMAS, SECOES, Retrato`.)

Depois das constantes de licença, acrescentar:

```python
RAIZ = Path(__file__).resolve().parent
PASTA_TOCS = RAIZ / "tocs"
PASTA_BRUTA = RAIZ / "store" / "raw" / "tocs"
ARQUIVO_FONTES = RAIZ / "sources.yaml"
ARQUIVO_OBSERVACOES = RAIZ / "observacoes.yaml"
ARQUIVO_LEITURAS = RAIZ / "leituras_sqlbi.yaml"

CABECALHO_YAML = (
    "# Gerado por `python -m rag.catalogo gerar` — não editar à mão.\n"
    "# Notas: rag/observacoes.yaml. Leituras do SQLBI: rag/leituras_sqlbi.yaml.\n"
)
```

No fim do arquivo, acrescentar:

```python
def ler_retratos(pasta: Path) -> Retratos:
    retratos: Retratos = {}
    for secao in SECOES:
        for idioma in IDIOMAS:
            caminho = tocs.caminho_do_retrato(pasta, idioma, secao.caminho)
            if not caminho.is_file():
                raise ErroDeCatalogo(
                    f"falta o retrato {caminho} — rode `python -m rag.catalogo atualizar`"
                )
            try:
                retratos[(idioma, secao.caminho)] = Retrato.model_validate_json(
                    caminho.read_text(encoding="utf-8")
                )
            except ValidationError as erro:
                raise ErroDeCatalogo(
                    f"retrato com estrutura inesperada: {caminho}\n{erro}"
                ) from erro
    return retratos


def _ler_yaml(caminho: Path) -> object:
    if not caminho.is_file():
        return None
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def ler_observacoes(caminho: Path) -> dict[str, str]:
    dados = _ler_yaml(caminho) or {}
    if not isinstance(dados, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in dados.items()
    ):
        raise ErroDeCatalogo(f"{caminho}: esperado um mapeamento id -> texto")
    return dados


def ler_leituras_sqlbi(caminho: Path) -> list[LeituraSqlbi]:
    dados = _ler_yaml(caminho) or []
    if not isinstance(dados, list):
        raise ErroDeCatalogo(f"{caminho}: esperada uma lista de leituras")
    try:
        return [LeituraSqlbi.model_validate(item) for item in dados]
    except ValidationError as erro:
        raise ErroDeCatalogo(f"{caminho}: entrada inválida\n{erro}") from erro


def como_yaml(fontes: list[Fonte]) -> str:
    corpo = yaml.safe_dump(
        [f.model_dump() for f in fontes],
        sort_keys=False,
        allow_unicode=True,
        width=10_000,
        default_flow_style=False,
    )
    return CABECALHO_YAML + corpo


def escrever_yaml(fontes: list[Fonte], caminho: Path) -> None:
    """LF sempre: com `core.autocrlf` o Git converte no checkout, e o teste de
    arquivo gerado compara texto, não bytes."""
    caminho.write_text(como_yaml(fontes), encoding="utf-8", newline="\n")


def ancoras_do_registro() -> dict[str, str]:
    """`{id_regra: url_canonica}`. Importa o registro aqui, na camada de
    comando, para que a montagem não dependa de `core/`."""
    from core.rules.todas import REGISTRO

    return {meta.id: meta.url_canonica for meta in REGISTRO.metas()}


def gerar(
    *,
    pasta_tocs: Path | None = None,
    destino: Path | None = None,
    observacoes: Path | None = None,
    leituras: Path | None = None,
    ancoras: dict[str, str] | None = None,
) -> ResultadoCatalogo:
    resultado = montar_catalogo(
        ler_retratos(pasta_tocs or PASTA_TOCS),
        ancoras_do_registro() if ancoras is None else ancoras,
        ler_observacoes(observacoes or ARQUIVO_OBSERVACOES),
        ler_leituras_sqlbi(leituras or ARQUIVO_LEITURAS),
    )
    escrever_yaml(resultado.fontes, destino or ARQUIVO_FONTES)
    return resultado


def atualizar(
    *,
    buscar: tocs.Buscador | None = None,
    hoje: date | None = None,
    pasta_tocs: Path | None = None,
    pasta_bruta: Path | None = None,
    destino: Path | None = None,
    observacoes: Path | None = None,
    leituras: Path | None = None,
    ancoras: dict[str, str] | None = None,
) -> ResultadoCatalogo:
    arquivo_leituras = leituras or ARQUIVO_LEITURAS
    tocs.baixar_retratos(
        buscar or tocs.buscar_padrao,
        hoje or date.today(),
        pasta_tocs or PASTA_TOCS,
        pasta_bruta or PASTA_BRUTA,
        [leitura.url for leitura in ler_leituras_sqlbi(arquivo_leituras)],
    )
    return gerar(
        pasta_tocs=pasta_tocs,
        destino=destino,
        observacoes=observacoes,
        leituras=arquivo_leituras,
        ancoras=ancoras,
    )


def resumo(resultado: ResultadoCatalogo, ancoras: dict[str, str]) -> str:
    fontes = resultado.fontes
    indexadas = [f for f in fontes if f.indexar]
    # Conta entradas, não origens: uma página âncora de duas regras conta 1 em "regra".
    por_origem: Counter = Counter()
    for f in fontes:
        por_origem.update({"regra" if o.startswith("regra:") else o for o in f.origem})
    linhas = [
        f"Catálogo: {len(fontes)} entradas — {len(indexadas)} indexadas, "
        f"{len(fontes) - len(indexadas)} só referência",
        "Por origem:",
        *(f"  {origem}: {n}" for origem, n in sorted(por_origem.items())),
        "Excluídos:",
        *(f"  {motivo}: {n}" for motivo, n in sorted(resultado.exclusoes.items())),
        f"Learn com url_pt_br: {sum(1 for f in indexadas if f.url_pt_br)} de {len(indexadas)}",
        "Âncoras:",
    ]
    for id_regra in sorted(ancoras):
        entrada = next(f.id for f in indexadas if id_regra in f.regras)
        linhas.append(f"  {id_regra} -> {entrada}")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.catalogo",
        description="Gera rag/sources.yaml a partir dos retratos dos toc.json do Learn.",
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["gerar", "atualizar"],
        default="gerar",
        help="gerar (padrão, offline) ou atualizar (baixa os retratos e gera)",
    )
    args = parser.parse_args(argv)
    try:
        ancoras = ancoras_do_registro()
        if args.comando == "atualizar":
            resultado = atualizar(ancoras=ancoras)
        else:
            resultado = gerar(ancoras=ancoras)
    except (ErroDeCatalogo, tocs.ErroDeRetrato) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(resumo(resultado, ancoras))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Passo 4: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: todos passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add rag/catalogo.py tests/test_rag_catalogo.py
git commit -m "feat(rag): comando python -m rag.catalogo (gerar e atualizar)

YAML deterministico com LF e aviso de arquivo gerado; leitura dos
retratos, das notas e da curadoria do SQLBI, com ausente ou vazio
tratado como vazio; resumo com contagens, exclusoes e ancoras.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tarefa 7: Dados reais — retratos de hoje, curadoria aprovada e catálogo versionado

**Files:**
- Create: `rag/observacoes.yaml`
- Create: `rag/leituras_sqlbi.yaml`
- Create (gerados): `rag/tocs/en-us/**.json`, `rag/tocs/pt-br/**.json`, `rag/sources.yaml`
- Test: `tests/test_rag_dados_reais.py`

**Interfaces:**
- Consumes: `rag.catalogo` inteiro (Tarefa 6).
- Produces: os arquivos versionados que a coleta (etapa seguinte) vai ler.

- [ ] **Passo 1: Criar `rag/observacoes.yaml`**

```yaml
# Notas humanas por id do catálogo, incorporadas por `python -m rag.catalogo gerar`.
# Formato: <id>: <texto>. Nota para id que saiu do catálogo faz a geração falhar,
# para que a nota não se perca em silêncio quando a Microsoft remove uma página.
{}
```

- [ ] **Passo 2: Criar `rag/leituras_sqlbi.yaml` com a curadoria aprovada pelo Fred**

A lista abaixo foi proposta em 09/10/2026 junto com este plano; cada link respondeu 200 e o título é o da página. **Aprovada pelo Fred na revisão do plano** (spec 3.4). MOD-003, MOD-006 e MOD-007 ficam sem leitura complementar: a busca não encontrou artigo do SQLBI que as aprofunde, e a spec manda não forçar correspondência.

```yaml
# Leituras complementares do SQLBI — só referência: nada é baixado nem indexado
# (spec 2026-10-09, seção 5.3). Cada entrada foi aberta e lida pelo curador, que
# confirmou que ela aprofunda a regra; `verificado_em` registra essa leitura.
- url: https://www.sqlbi.com/articles/divide-performance/
  titulo: DIVIDE Performance
  regras: [DAX-001]
  verificado_em: '2026-10-09'
- url: https://www.sqlbi.com/articles/automatic-time-intelligence-in-power-bi/
  titulo: Automatic time intelligence in Power BI
  regras: [MOD-001]
  verificado_em: '2026-10-09'
- url: https://www.sqlbi.com/articles/bidirectional-relationships-and-ambiguity-in-dax/
  titulo: Bidirectional relationships and ambiguity in DAX
  regras: [MOD-002]
  verificado_em: '2026-10-09'
- url: https://www.sqlbi.com/articles/mark-as-date-table/
  titulo: Mark as Date table
  regras: [MOD-005]
  verificado_em: '2026-10-09'
- url: https://www.sqlbi.com/articles/comparing-dax-calculated-columns-with-power-query-computed-columns/
  titulo: Comparing DAX calculated columns with Power Query computed columns
  regras: [PERF-001]
  verificado_em: '2026-10-09'
- url: https://www.sqlbi.com/articles/choosing-numeric-data-types-in-dax/
  titulo: Choosing Numeric Data Types in DAX
  regras: [PERF-003]
  verificado_em: '2026-10-09'
```

- [ ] **Passo 3: Rodar o `atualizar` (único passo com rede do plano)**

Run: `.\.venv\Scripts\python.exe -m rag.catalogo atualizar`
Expected (números de 09/10/2026; podem variar alguns se a Microsoft publicar páginas, e a variação vai registrada no progress-log):

```
Catálogo: 1426 entradas — 1420 indexadas, 6 só referência
Por origem:
  curadoria:sqlbi: 6
  regra: 8
  toc:dax: 508
  toc:power-bi/guidance: 151
  toc:powerquery-m: 768
Excluídos:
  entrada de seção ou área não documental: 6
  fora do learn: 6
Learn com url_pt_br: 1420 de 1420
Âncoras:
  DAX-001 -> learn:dax/best-practices/dax-divide-function-operator
  MOD-001 -> learn:power-bi/guidance/auto-date-time
  MOD-002 -> learn:power-bi/guidance/relationships-bidirectional-filtering
  MOD-003 -> learn:power-bi/guidance/star-schema
  MOD-005 -> learn:power-bi/transform-model/desktop-date-tables
  MOD-006 -> learn:power-bi/guidance/star-schema
  MOD-007 -> learn:power-bi/guidance/relationships-one-to-one
  PERF-001 -> learn:power-bi/guidance/import-modeling-data-reduction
  PERF-003 -> learn:power-bi/connect-data/desktop-data-types
```

Se sair `erro:`, **parar** e investigar (superpowers:systematic-debugging) — não contornar.

Conferir que o bruto ficou fora do Git e a listagem dentro:
Run: `git status --short rag/`
Expected: `rag/tocs/`, `rag/sources.yaml`, `rag/observacoes.yaml`, `rag/leituras_sqlbi.yaml` como novos; **nada** de `rag/store/`.

- [ ] **Passo 4: Escrever os testes sobre os dados reais**

Criar `tests/test_rag_dados_reais.py`:

```python
"""O catálogo versionado, conferido contra os retratos versionados.

Ao contrário dos testes do PBIP real, estes sempre rodam: `rag/tocs/` está no
Git. O primeiro teste pega edição à mão do `sources.yaml` e catálogo
desatualizado em relação aos retratos.
"""

import pytest

from rag.catalogo import (
    ARQUIVO_FONTES,
    ARQUIVO_LEITURAS,
    ARQUIVO_OBSERVACOES,
    PASTA_TOCS,
    ancoras_do_registro,
    como_yaml,
    ler_leituras_sqlbi,
    ler_observacoes,
    ler_retratos,
    montar_catalogo,
)


@pytest.fixture(scope="module")
def resultado():
    return montar_catalogo(
        ler_retratos(PASTA_TOCS),
        ancoras_do_registro(),
        ler_observacoes(ARQUIVO_OBSERVACOES),
        ler_leituras_sqlbi(ARQUIVO_LEITURAS),
    )


def test_sources_yaml_versionado_e_o_que_o_gerador_produz(resultado):
    # Texto, não bytes: com core.autocrlf o checkout no Windows traz CRLF.
    assert ARQUIVO_FONTES.read_text(encoding="utf-8") == como_yaml(resultado.fontes), (
        "rag/sources.yaml desatualizado ou editado à mão — rode `python -m rag.catalogo gerar`"
    )


def test_a_ancora_de_cada_regra_esta_no_catalogo_indexado(resultado):
    ancoras = ancoras_do_registro()
    assert len(ancoras) == 9
    cobertas = {r for f in resultado.fontes if f.indexar for r in f.regras}
    assert cobertas == set(ancoras)


def test_tamanho_do_corpus_indexado(resultado):
    indexadas = [f for f in resultado.fontes if f.indexar]
    assert 1300 <= len(indexadas) <= 1600


def test_todo_o_indexado_e_learn_em_ingles(resultado):
    for fonte in resultado.fontes:
        if fonte.indexar:
            assert fonte.organizacao == "Microsoft", fonte.id
            assert fonte.url.startswith("https://learn.microsoft.com/en-us/"), fonte.id


def test_o_sqlbi_e_so_referencia(resultado):
    sqlbi = [f for f in resultado.fontes if f.organizacao == "SQLBI"]
    assert sqlbi
    assert all(not f.indexar and f.id.startswith("sqlbi:") and f.regras for f in sqlbi)
```

- [ ] **Passo 5: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_dados_reais.py -q`
Expected: 5 passam.
Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.

Prova de que o teste de arquivo gerado morde: acrescentar uma linha `# x` ao fim de `rag/sources.yaml`, rodar `tests/test_rag_dados_reais.py` e ver `test_sources_yaml_versionado_e_o_que_o_gerador_produz` falhar com a mensagem que indica `gerar`; depois `.\.venv\Scripts\python.exe -m rag.catalogo gerar` e ver passar de novo.

- [ ] **Passo 6: Commit**

```bash
git add rag/observacoes.yaml rag/leituras_sqlbi.yaml rag/tocs rag/sources.yaml tests/test_rag_dados_reais.py
git commit -m "feat(rag): catalogo de fontes gerado com os retratos de 09/10/2026

1.420 paginas do Learn indexaveis (guidance, referencias completas de
DAX e M, ancoras das 9 regras) e 6 leituras do SQLBI so como
referencia. Teste de arquivo gerado atualizado.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Se as contagens do Passo 3 forem diferentes das de 09/10, ajustar a mensagem do commit para os números medidos.)

---

### Tarefa 8: Registros do projeto

**Files:**
- Modify: `docs/project/backlog.md`
- Modify: `docs/project/riscos.md`
- Modify: `docs/project/status.md`
- Modify: `docs/project/progress-log.md`
- Modify: `README.md`

**Interfaces:** nenhuma de código.

- [ ] **Passo 1: `backlog.md`**

Na tabela "Pendências abertas do gate da Fase 1", trocar a linha do G-8 por:

```
| G-8 | ~~Gerar `rag/sources.yaml` a partir dos `toc.json`~~ | Semana 5 | **Concluído em 09/10/2026** — 1.420 páginas do Learn indexáveis e 6 leituras do SQLBI só como referência (spec `2026-10-09-catalogo-de-fontes-rag-design.md`) |
```

No "Log de alertas de escopo", depois da última linha de 09/10/2026, acrescentar:

```
| 09/10/2026 | Ampliar o corpus da RAG de ~60–120 documentos para as referências completas de DAX e de M | **Aceito** pelo Fred. O catálogo passa a 1.420 páginas do Learn (guidance inteiro, 508 de DAX, 768 de M, mais as âncoras das regras). O texto indexado segue em inglês (ADR-002 inalterado); cada entrada leva `url_pt_br`, conferida no retrato pt-BR, para o leitor do relatório |
| 09/10/2026 | Indexar todos os artigos públicos do SQLBI | **Recusado** em favor de leitura complementar só com link. O site é de todos os direitos reservados, os termos não concedem uso dos artigos, e a Lei 9.610/98 (art. 46) cobre citação de passagens e cópia de pequenos trechos, não o armazenamento de artigos inteiros. Seis artigos curados entram com `indexar: false` (spec, seção 5.3) |
```

- [ ] **Passo 2: `riscos.md`**

Atualizar a linha de "Última atualização" para:

```
Última atualização: **09/10/2026** (P1–P7 medidos: gatilho do R-12 não disparou; catálogo de fontes gerado: R-05 mitigado por desenho para o SQLBI).
```

Na linha do R-05, trocar a coluna de status `Aberto` por `**Mitigado** (SQLBI, por desenho); aberto para o DAX Guide` e acrescentar ao fim da coluna de mitigação: ` Em 09/10/2026 o SQLBI passou a entrar só como referência (link e título, `indexar: false`): os termos do site não concedem uso dos artigos, e sem armazenamento local não há restrição a violar.`

Na seção "Mudanças nesta revisão (09/10/2026 — P1–P7 medidos)", acrescentar o item:

```
- **R-05** passa a **Mitigado** para o SQLBI, por desenho: o catálogo o registra só como leitura complementar, sem baixar nem indexar conteúdo. Verificado em 09/10/2026: rodapé "© SQLBI. All rights are reserved.", termos e condições sem permissão de uso dos artigos, `robots.txt` bloqueando ferramentas de cópia de site. O DAX Guide segue fora do catálogo e o R-05 segue aberto para ele.
```

- [ ] **Passo 3: `status.md`**

Na tabela da seção 8 ("Próximos passos"), substituir as linhas 1 e 3 (hoje duplicadas, ambas sobre o início da Fase 3) por uma linha só e renumerar:

```
| 1 | **Coleta das páginas do catálogo** (`rag/store/`, fora do Git) | O catálogo do G-8 está pronto: 1.420 páginas do Learn com `indexar: true`. A coleta precisa de pausa entre requisições e de ser retomável (spec do catálogo, seção 5.1), e deve registrar o H1 e a data de acesso de cada página |
| 2 | Verificar empiricamente se o Power BI Desktop grava `roles[].tablePermissions[].filterExpression` no `model.bim` | (texto atual da linha 2, inalterado) |
```

- [ ] **Passo 4: `progress-log.md`**

Acrescentar no fim:

```
---

## 09/10/2026 — Fase 3, semana 6 — G-8: catálogo de fontes da RAG

`python -m rag.catalogo` gera `rag/sources.yaml` a partir de retratos datados dos
`toc.json` do Learn (spec `docs/superpowers/specs/2026-10-09-catalogo-de-fontes-rag-design.md`,
plano `docs/superpowers/plans/2026-10-09-catalogo-de-fontes-rag.md`).

**Medido:** <colar aqui o resumo impresso pelo `atualizar` da Tarefa 7, Passo 3>.

**Três correções que a verificação impôs ao desenho conversado:**
- O `toc.json` bruto **não** vai para o Git — os termos de uso do Learn permitem uso
  pessoal e não comercial, não republicar cópia literal. Versiona-se só a listagem
  normalizada (caminho e título); o bruto fica em `rag/store/raw/tocs/`.
- `licenca` descreve os termos de uso verificados, não CC BY 4.0, que não foi
  comprovada para essas páginas.
- O link relativo à raiz no `toc.json` (`/dax/...`) não traz o idioma; resolvido
  sem prefixá-lo, tiraria do guidance as 9 páginas de boas práticas de DAX.

**Decisões do Fred nesta etapa:** referências completas de DAX e M no corpus (de
~60–120 para ~1.420 páginas); texto indexado em inglês com `url_pt_br` para o
leitor; SQLBI só como leitura complementar, com 6 artigos curados (MOD-003,
MOD-006 e MOD-007 sem artigo adequado).

**Validação:** <número> testes passando; o teste de arquivo gerado foi visto falhar
com uma edição à mão e voltar a passar com `gerar`.

**Próximo passo:** coleta das 1.420 páginas para `rag/store/`, com pausa entre
requisições, retomável, registrando H1 e data de acesso.
```

Substituir os dois `<...>` pelos valores reais: o resumo do Passo 3 da Tarefa 7 e o número de testes da última execução de `pytest -q`. Não deixar o marcador no arquivo.

- [ ] **Passo 5: `README.md`**

Depois da seção que explica o certificado do PyPI, acrescentar:

````markdown
### Catálogo de fontes da RAG

```powershell
python -m rag.catalogo            # gera rag/sources.yaml a partir de rag/tocs/ (offline)
python -m rag.catalogo atualizar  # baixa os toc.json do Learn de novo e gera
```

`rag/sources.yaml` é gerado — não editar à mão. Notas vão em `rag/observacoes.yaml`;
leituras complementares do SQLBI (só link, nunca indexadas) em `rag/leituras_sqlbi.yaml`.
````

- [ ] **Passo 6: Conferir e commitar**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos passam.
Run: `git diff --stat`
Expected: só os cinco arquivos desta tarefa.

```bash
git add docs/project/backlog.md docs/project/riscos.md docs/project/status.md docs/project/progress-log.md README.md
git commit -m "docs: G-8 concluido; corpus ampliado e SQLBI so como referencia

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
