"""A medição sobre a base real: oráculo e limite de tokens.

Pulados sem `rag/store/`. Os que usam o modelo rodam offline e são pulados se o
`bge-small` não estiver no cache do Hugging Face.
"""

import os

import pytest

from rag.avaliacao import ARQUIVO_CONSULTAS, ler_conjunto
from rag.coleta import ARQUIVO_REGISTRO
from rag.medicao import carregar_paginas, trechos_das_variantes, verificar_oraculo

pytestmark = pytest.mark.skipif(
    not ARQUIVO_REGISTRO.is_file(), reason="rag/store/ não existe (conteúdo do Learn não é versionado)"
)


@pytest.fixture(scope="module")
def variantes():
    return trechos_das_variantes(carregar_paginas())


@pytest.mark.parametrize("variante", ["secao-sem", "secao-com", "janela-sem", "janela-com"])
def test_oraculo_nenhum_chunking_parte_uma_frase_marca(variantes, variante):
    assert verificar_oraculo(variantes[variante], ler_conjunto(ARQUIVO_CONSULTAS)) == []


@pytest.fixture(scope="module")
def embedder():
    os.environ["HF_HUB_OFFLINE"] = "1"
    from rag.embeddings import EmbedderBge, ErroDeEmbeddings

    modelo = EmbedderBge()
    try:
        modelo.contar_tokens("teste")
    except ErroDeEmbeddings:
        pytest.skip("bge-small não está no cache do Hugging Face")
    return modelo


def test_nenhum_trecho_secao_passa_de_512_tokens(variantes, embedder):
    maior = max(embedder.contar_tokens(t.texto_indexado) for t in variantes["secao-com"])
    assert maior <= 512, f"maior trecho com {maior} tokens: reduzir LIMITE_SECAO"
