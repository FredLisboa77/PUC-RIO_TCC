"""Buscas densa, BM25 e híbrida, com vetores feitos à mão."""

import numpy as np
import pytest

from rag.busca import (
    K_RRF,
    IndiceBm25,
    criar_buscador,
    fundir_rrf,
    ranquear,
    tokenizar,
)
from rag.chunking import TrechoIndexado


def _trecho(i, texto, pagina="learn:p"):
    return TrechoIndexado(
        id=f"{pagina}#s/{i}",
        id_pagina=pagina,
        url="u",
        titulo_pagina="T",
        ancora="s",
        caminho="S",
        texto=texto,
        texto_indexado=texto,
    )


TRECHOS = [
    _trecho(1, "divide by zero with the DIVIDE function"),
    _trecho(2, "star schema dimension tables", pagina="learn:q"),
    _trecho(3, "auto date time hidden tables"),
]
VETORES = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]], dtype=np.float32)


class EmbedderFixo:
    nome = "fixo"

    def __init__(self, consulta):
        self.consulta = np.asarray(consulta, dtype=np.float32)

    def vetores(self, textos):
        raise AssertionError("a busca não recalcula os vetores dos trechos")

    def vetor_consulta(self, texto):
        return self.consulta


def test_tokenizar_em_minusculas_letras_e_digitos():
    assert tokenizar("Auto date/time, DIVIDE(x, 0)") == ["auto", "date", "time", "divide", "x", "0"]


def test_ranquear_por_pontuacao_com_desempate_pela_ordem():
    assert ranquear(np.array([0.5, 0.9, 0.5, 0.1]), None, 3) == [1, 0, 2]


def test_ranquear_respeita_mascara_e_k():
    mascara = np.array([True, False, True, True])
    assert ranquear(np.array([0.5, 0.9, 0.5, 0.1]), mascara, 2) == [0, 2]


def test_densa_ordena_pelo_produto_escalar():
    buscar = criar_buscador("densa", TRECHOS, vetores=VETORES, embedder=EmbedderFixo([0.0, 1.0]))
    assert [t.id_pagina for t in buscar("q", 2)] == ["learn:q", "learn:p"]
    assert buscar("q", 2)[1].texto == TRECHOS[2].texto


def test_bm25_favorece_o_termo_exato():
    buscar = criar_buscador("bm25", TRECHOS, indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]))
    assert buscar("DIVIDE function", 1)[0].texto == TRECHOS[0].texto


def test_bm25_sem_termo_conhecido_devolve_em_ordem_estavel():
    buscar = criar_buscador("bm25", TRECHOS, indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]))
    assert [t.texto for t in buscar("xyzzy", 3)] == [t.texto for t in TRECHOS]


def test_conta_do_rrf():
    # d0: posições 1 e 2; d1: posição 2 e ausente; d2: ausente e posição 1
    assert fundir_rrf([[0, 1], [2, 0]], 3) == [0, 2, 1]
    assert 1 / (K_RRF + 1) + 1 / (K_RRF + 2) > 1 / (K_RRF + 1)


def test_hibrida_funde_as_duas_listas():
    buscar = criar_buscador(
        "hibrida",
        TRECHOS,
        vetores=VETORES,
        embedder=EmbedderFixo([0.0, 1.0]),
        indice_bm25=IndiceBm25([t.texto_indexado for t in TRECHOS]),
    )
    # densa: [1, 2, 0]; bm25 para "auto date": [2, ...] → 2 vence na fusão
    assert buscar("auto date", 1)[0].texto == TRECHOS[2].texto


def test_filtro_de_paginas_vale_nas_tres_buscas():
    paginas = frozenset({"learn:p"})
    indice = IndiceBm25([t.texto_indexado for t in TRECHOS])
    for tipo in ("densa", "bm25", "hibrida"):
        buscar = criar_buscador(
            tipo, TRECHOS, vetores=VETORES, embedder=EmbedderFixo([0.0, 1.0]), indice_bm25=indice, paginas=paginas
        )
        assert {t.id_pagina for t in buscar("star schema", 3)} == {"learn:p"}, tipo


def test_nunca_mais_que_k():
    buscar = criar_buscador("densa", TRECHOS, vetores=VETORES, embedder=EmbedderFixo([1.0, 0.0]))
    assert len(buscar("q", 2)) == 2


def test_empate_exato_e_deterministico():
    gemeos = [_trecho(1, "igual"), _trecho(2, "igual")]
    vetores = np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    buscar = criar_buscador("densa", gemeos, vetores=vetores, embedder=EmbedderFixo([1.0, 0.0]))
    assert [buscar("q", 2)[0].ancora, len(buscar("q", 2))] == ["s", 2]
    assert criar_buscador("densa", gemeos, vetores=vetores, embedder=EmbedderFixo([1.0, 0.0]))("q", 2) == buscar("q", 2)


def test_busca_sem_o_que_precisa_falha_ao_criar():
    with pytest.raises(ValueError, match="densa"):
        criar_buscador("densa", TRECHOS)
    with pytest.raises(ValueError, match="bm25"):
        criar_buscador("bm25", TRECHOS)
