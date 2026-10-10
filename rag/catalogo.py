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
