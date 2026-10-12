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


@pytest.fixture(scope="module")
def variantes_do_modelo(embedder):
    """As variantes como a medição as monta: com o contador de tokens do modelo."""
    return trechos_das_variantes(carregar_paginas(), contar_tokens=embedder.contar_tokens)


@pytest.mark.parametrize("variante", ["secao-sem", "secao-com", "janela-sem", "janela-com"])
def test_nenhum_trecho_passa_de_512_tokens(variantes_do_modelo, embedder, variante):
    maior = max(embedder.contar_tokens(t.texto_indexado) for t in variantes_do_modelo[variante])
    assert maior <= 512, f"{variante}: maior trecho com {maior} tokens"


@pytest.mark.parametrize("variante", ["secao-sem", "secao-com", "janela-sem", "janela-com"])
def test_oraculo_com_o_contador_do_modelo(variantes_do_modelo, variante):
    assert verificar_oraculo(variantes_do_modelo[variante], ler_conjunto(ARQUIVO_CONSULTAS)) == []


def test_o_indice_chroma_reproduz_a_metrica_da_medicao(embedder):
    from rag.avaliacao import avaliar
    from rag.indice import ARQUIVO_CONFIG, carregar_buscador, resultado_mais_recente
    from rag.medicao import PASTA_RESULTADOS, Configuracao, ler_resultado

    if not ARQUIVO_CONFIG.is_file():
        pytest.skip("índice não construído — rode `python -m rag.indice construir`")
    # A configuração gravada no índice, não a vencedora de 11/10: depois de
    # `construir --busca`, o índice pode usar outra busca da mesma medição.
    configuracao = Configuracao.model_validate_json(ARQUIVO_CONFIG.read_text(encoding="utf-8"))
    resultados, _ = ler_resultado(resultado_mais_recente(PASTA_RESULTADOS))
    medido = next(r for r in resultados if r.configuracao == configuracao)
    relatorio = avaliar(carregar_buscador(embedder), ler_conjunto(ARQUIVO_CONSULTAS))
    assert relatorio.macro.acerto[5] == pytest.approx(medido.macro.acerto[5])
