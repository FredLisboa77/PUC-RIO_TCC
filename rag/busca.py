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
