"""Índice da base RAG (Fase 3): a configuração vencedora da medição, em ChromaDB.

`python -m rag.indice construir` grava os trechos e a coleção Chroma a partir do
resultado mais recente em `eval/results/`, reaproveitando os vetores do cache.
`carregar_buscador()` é a busca que o pipeline usa. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 6.
"""

import argparse
import json
import sys
from pathlib import Path

from rag.avaliacao import Buscador, Trecho
from rag.busca import K_FUSAO, IndiceBm25, fundir_rrf, ranquear
from rag.chunking import TrechoIndexado, montar_trechos
from rag.coleta import PASTA_STORE
from rag.embeddings import PASTA_EMBEDDINGS, Embedder, EmbedderBge, ler_cache
from rag.medicao import PASTA_RESULTADOS, Configuracao, carregar_paginas, ler_resultado

PASTA_INDICE = PASTA_STORE / "indice"
ARQUIVO_TRECHOS = PASTA_INDICE / "trechos.jsonl"
ARQUIVO_CONFIG = PASTA_INDICE / "config.json"
PASTA_CHROMA = PASTA_STORE / "chroma"
COLECAO = "base_rag"
LOTE_CHROMA = 1000


class ErroDeIndice(Exception):
    """O índice não pode ser construído ou carregado."""


def _cliente(pasta_chroma: Path):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(pasta_chroma), settings=Settings(anonymized_telemetry=False))


def _exigir_corpus_completo(configuracao: Configuracao) -> None:
    """O índice cobre sempre o corpus completo. Outro corpus só entra por decisão
    explícita (regra de decisão, item 1) e exige filtrar aqui — não pode passar em
    silêncio."""
    if configuracao.corpus != "completo":
        raise ErroDeIndice(
            f"configuração {configuracao.nome} usa o corpus {configuracao.corpus}; "
            "o índice só cobre o corpus completo"
        )


def resultado_mais_recente(pasta: Path) -> Path:
    arquivos = sorted(pasta.glob("recuperacao-*.json")) if pasta.is_dir() else []
    if not arquivos:
        raise ErroDeIndice(f"nenhum resultado em {pasta} — rode `python -m rag.medicao`")
    return arquivos[-1]


def construir(
    *,
    pasta_resultados: Path = PASTA_RESULTADOS,
    pasta_indice: Path = PASTA_INDICE,
    pasta_chroma: Path = PASTA_CHROMA,
    pasta_embeddings: Path = PASTA_EMBEDDINGS,
) -> Configuracao:
    _, decisao = ler_resultado(resultado_mais_recente(pasta_resultados))
    configuracao = decisao.vencedora
    _exigir_corpus_completo(configuracao)
    embedder = EmbedderBge()
    # Os trechos são montados como na medição — com o contador de tokens do modelo —
    # senão o cache de vetores não casa.
    trechos = montar_trechos(
        carregar_paginas(), configuracao.chunking, configuracao.cabecalho, contar_tokens=embedder.contar_tokens
    )
    textos = [t.texto_indexado for t in trechos]
    vetores = ler_cache(pasta_embeddings, configuracao.variante, embedder.nome, textos)
    if vetores is None:
        raise ErroDeIndice(f"sem cache de embeddings para {configuracao.variante} — rode `python -m rag.medicao`")

    pasta_indice.mkdir(parents=True, exist_ok=True)
    temporario = pasta_indice / (ARQUIVO_TRECHOS.name + ".tmp")
    temporario.write_text(
        "".join(t.model_dump_json() + "\n" for t in trechos), encoding="utf-8", newline="\n"
    )
    temporario.replace(pasta_indice / ARQUIVO_TRECHOS.name)

    cliente = _cliente(pasta_chroma)
    try:
        cliente.delete_collection(COLECAO)
    except Exception:  # coleção ainda não existe: o tipo da exceção muda entre versões do Chroma
        pass
    colecao = cliente.create_collection(COLECAO)
    for inicio in range(0, len(trechos), LOTE_CHROMA):
        lote = trechos[inicio : inicio + LOTE_CHROMA]
        colecao.add(
            ids=[t.id for t in lote],
            embeddings=vetores[inicio : inicio + LOTE_CHROMA].tolist(),
            documents=[t.texto for t in lote],
            metadatas=[
                {"id_pagina": t.id_pagina, "ancora": t.ancora, "caminho": t.caminho, "url": t.url} for t in lote
            ],
        )
    (pasta_indice / ARQUIVO_CONFIG.name).write_text(
        configuracao.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return configuracao


def carregar_buscador(
    embedder: Embedder | None = None,
    *,
    pasta_indice: Path = PASTA_INDICE,
    pasta_chroma: Path = PASTA_CHROMA,
) -> Buscador:
    config = pasta_indice / ARQUIVO_CONFIG.name
    if not config.is_file():
        raise ErroDeIndice(f"índice ausente em {pasta_indice} — rode `python -m rag.indice construir`")
    configuracao = Configuracao.model_validate_json(config.read_text(encoding="utf-8"))
    _exigir_corpus_completo(configuracao)
    linhas = (pasta_indice / ARQUIVO_TRECHOS.name).read_text(encoding="utf-8").splitlines()
    trechos = [TrechoIndexado.model_validate_json(linha) for linha in linhas if linha.strip()]
    posicao = {t.id: i for i, t in enumerate(trechos)}
    embedder = embedder or EmbedderBge()
    colecao = _cliente(pasta_chroma).get_collection(COLECAO)
    bm25 = IndiceBm25([t.texto_indexado for t in trechos]) if configuracao.busca != "densa" else None

    def densa(consulta: str, k: int) -> list[int]:
        resposta = colecao.query(
            query_embeddings=[embedder.vetor_consulta(consulta).tolist()], n_results=k, include=["distances"]
        )
        return [posicao[i] for i in resposta["ids"][0]]

    def por_bm25(consulta: str, k: int) -> list[int]:
        return ranquear(bm25.pontuacoes(consulta), None, k)

    def buscar(consulta: str, k: int) -> list[Trecho]:
        if configuracao.busca == "densa":
            indices = densa(consulta, k)
        elif configuracao.busca == "bm25":
            indices = por_bm25(consulta, k)
        else:
            indices = fundir_rrf([densa(consulta, K_FUSAO), por_bm25(consulta, K_FUSAO)], k)
        return [trechos[i].para_regua() for i in indices]

    return buscar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rag.indice", description="Índice da base RAG.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("construir", help="constrói o índice da configuração vencedora da medição")
    parser.parse_args(argv)
    try:
        configuracao = construir()
    except ErroDeIndice as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(f"Índice construído: {configuracao.nome} -> {PASTA_CHROMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
