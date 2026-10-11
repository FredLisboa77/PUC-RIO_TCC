"""Chunking da base RAG (Fase 3).

Duas estratégias, medidas pela régua: `secao` (uma seção por trecho, partindo
as longas nas fronteiras de bloco) e `janela` (janelas de palavras com
sobreposição sobre a página inteira). Os limites são em palavras; um contador de
tokens opcional, injetado, parte ao meio o trecho que ainda passe do limite do
`bge-small`. Na base de 11/10/2026 isso atinge ~0,8% dos trechos: JSON de
exemplo, tabelas de datas e código, com 3 a 4 tokens por palavra. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 2.
"""

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from rag.avaliacao import Trecho
from rag.extracao import PaginaExtraida, Secao

LIMITE_SECAO = 350
JANELA = 200
PASSO = 150
LIMITE_TOKENS = 512
"""O `bge-small-en-v1.5` ignora o que passa disso."""
ContadorDeTokens = Callable[[str], int]
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


def _indexado(pagina: PaginaExtraida, secao: Secao, texto: str, cabecalho: bool) -> str:
    return f"{cabecalho_de(pagina.titulo, secao.caminho)}\n{texto}" if cabecalho else texto


def _caber(texto: str, cabe: Callable[[str], bool]) -> list[str]:
    """Parte ao meio, por palavras, até cada parte caber. Uma palavra sozinha fica
    como está: não há como partir mais."""
    palavras = texto.split()
    if cabe(texto) or len(palavras) <= 1:
        return [texto]
    meio = len(palavras) // 2
    return _caber(" ".join(palavras[:meio]), cabe) + _caber(" ".join(palavras[meio:]), cabe)


def _emitir(
    trechos: list[TrechoIndexado],
    pagina: PaginaExtraida,
    secao: Secao,
    texto: str,
    cabecalho: bool,
    contar_tokens: ContadorDeTokens | None,
    limite_tokens: int,
) -> None:
    partes = (
        [texto]
        if contar_tokens is None
        else _caber(texto, lambda t: contar_tokens(_indexado(pagina, secao, t, cabecalho)) <= limite_tokens)
    )
    for parte in partes:
        trechos.append(
            TrechoIndexado(
                id=f"{pagina.id}#{secao.ancora}/{len(trechos) + 1}",
                id_pagina=pagina.id,
                url=pagina.url,
                titulo_pagina=pagina.titulo,
                ancora=secao.ancora,
                caminho=secao.caminho,
                texto=parte,
                texto_indexado=_indexado(pagina, secao, parte, cabecalho),
            )
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
    pagina: PaginaExtraida,
    *,
    cabecalho: bool,
    limite: int = LIMITE_SECAO,
    contar_tokens: ContadorDeTokens | None = None,
    limite_tokens: int = LIMITE_TOKENS,
) -> list[TrechoIndexado]:
    trechos: list[TrechoIndexado] = []
    for secao in pagina.secoes:
        for texto in _pedacos(secao, limite):
            _emitir(trechos, pagina, secao, texto, cabecalho, contar_tokens, limite_tokens)
    return trechos


def trechos_por_janela(
    pagina: PaginaExtraida,
    *,
    cabecalho: bool,
    janela: int = JANELA,
    passo: int = PASSO,
    contar_tokens: ContadorDeTokens | None = None,
    limite_tokens: int = LIMITE_TOKENS,
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
        _emitir(trechos, pagina, palavras[inicio][1], texto, cabecalho, contar_tokens, limite_tokens)
        if fim >= len(palavras):
            break
        inicio += passo
    return trechos


def montar_trechos(
    paginas: list[PaginaExtraida],
    estrategia: Estrategia,
    cabecalho: bool,
    *,
    contar_tokens: ContadorDeTokens | None = None,
    limite_tokens: int = LIMITE_TOKENS,
) -> list[TrechoIndexado]:
    cortar = trechos_por_secao if estrategia == "secao" else trechos_por_janela
    return [
        t
        for pagina in paginas
        for t in cortar(pagina, cabecalho=cabecalho, contar_tokens=contar_tokens, limite_tokens=limite_tokens)
    ]


def ids_do_corpus_guidance(fontes: list[dict]) -> frozenset[str]:
    """As páginas do guidance do Power BI mais as âncoras das regras fora dele."""
    return frozenset(
        f["id"]
        for f in fontes
        if f.get("indexar")
        and any(o == "toc:power-bi/guidance" or o.startswith("regra:") for o in f.get("origem", []))
    )
