"""Embeddings da base RAG (Fase 3): `bge-small-en-v1.5` em CPU, com cache em disco.

A GPU fica para o LLM. O cache leva no nome um hash do modelo e de todos os
textos, em ordem: mudou o chunking, o extrator ou o modelo, o cache não casa e é
recalculado — nunca se devolve vetor desalinhado dos trechos.
"""

import hashlib
import os
import sys
from pathlib import Path
from typing import Protocol

import numpy as np

from rag.coleta import PASTA_STORE

MODELO = "BAAI/bge-small-en-v1.5"
PREFIXO_CONSULTA = "Represent this sentence for searching relevant passages: "
PASTA_EMBEDDINGS = PASTA_STORE / "embeddings"
TAMANHO_LOTE = 64


class ErroDeEmbeddings(Exception):
    """O modelo não pôde ser carregado."""


class Embedder(Protocol):
    nome: str

    def vetores(self, textos: list[str]) -> np.ndarray: ...

    def vetor_consulta(self, texto: str) -> np.ndarray: ...


class EmbedderBge:
    """O modelo é carregado na primeira chamada: importar o módulo não custa nada."""

    def __init__(self, nome: str = MODELO) -> None:
        self.nome = nome
        self._modelo = None

    def _carregado(self):
        if self._modelo is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._modelo = SentenceTransformer(self.nome, device="cpu")
            except Exception as erro:  # rede, cache ou versão: a mensagem diz onde olhar
                raise ErroDeEmbeddings(
                    f"não foi possível carregar {self.nome} (HF_HOME={os.environ.get('HF_HOME', '<padrão>')}): {erro}"
                ) from erro
        return self._modelo

    def vetores(self, textos: list[str]) -> np.ndarray:
        return self._carregado().encode(
            textos,
            batch_size=TAMANHO_LOTE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=len(textos) > 1000,
        ).astype(np.float32)

    def vetor_consulta(self, texto: str) -> np.ndarray:
        return self.vetores([PREFIXO_CONSULTA + texto])[0]

    def contar_tokens(self, texto: str) -> int:
        return len(self._carregado().tokenizer(texto)["input_ids"])


def chave_do_cache(nome_modelo: str, textos: list[str]) -> str:
    resumo = hashlib.sha256(nome_modelo.encode("utf-8"))
    for texto in textos:
        resumo.update(b"\x00")
        resumo.update(texto.encode("utf-8"))
    return resumo.hexdigest()[:16]


def arquivo_do_cache(pasta: Path, nome: str, nome_modelo: str, textos: list[str]) -> Path:
    return pasta / f"{nome}-{chave_do_cache(nome_modelo, textos)}.npy"


def ler_cache(pasta: Path, nome: str, nome_modelo: str, textos: list[str]) -> np.ndarray | None:
    arquivo = arquivo_do_cache(pasta, nome, nome_modelo, textos)
    if not arquivo.is_file():
        return None
    try:
        vetores = np.load(arquivo)
    except (OSError, ValueError) as erro:
        print(f"aviso: cache ilegível {arquivo.name} ({erro}); recalculando", file=sys.stderr)
        return None
    if vetores.ndim != 2 or vetores.shape[0] != len(textos):
        print(f"aviso: cache {arquivo.name} com forma {vetores.shape}; recalculando", file=sys.stderr)
        return None
    return vetores


def vetores_com_cache(embedder: Embedder, textos: list[str], *, pasta: Path, nome: str) -> np.ndarray:
    vetores = ler_cache(pasta, nome, embedder.nome, textos)
    if vetores is not None:
        return vetores
    vetores = np.asarray(embedder.vetores(textos), dtype=np.float32)
    arquivo = arquivo_do_cache(pasta, nome, embedder.nome, textos)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_name(arquivo.name + ".tmp")
    with open(temporario, "wb") as saida:
        np.save(saida, vetores)
    temporario.replace(arquivo)
    return vetores
