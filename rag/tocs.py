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
