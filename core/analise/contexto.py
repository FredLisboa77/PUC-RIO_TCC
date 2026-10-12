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
