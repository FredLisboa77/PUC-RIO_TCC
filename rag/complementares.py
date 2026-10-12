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
