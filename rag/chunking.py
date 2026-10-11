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
