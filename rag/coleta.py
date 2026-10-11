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
