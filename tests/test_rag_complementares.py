"""Complementares: as três buscas, o pool, a precisão e a decisão."""

from fabricas_analise import trecho_indexado

from rag.avaliacao import Consulta
from rag.complementares import complementares_por_busca, formar_pool, id_da_secao

ANCORA = trecho_indexado("learn:ancora", "auto date time")
TRECHOS = [
    ANCORA,
    trecho_indexado("learn:a", "a", ancora="s1", parte=1),
    trecho_indexado("learn:a", "a2", ancora="s1", parte=2),
    trecho_indexado("learn:b", "b"),
    trecho_indexado("learn:c", "c"),
]
CONSULTAS = [
    Consulta(id="REGRA/MOD-001", tipo="regra", id_regra="MOD-001", texto="q1"),
    Consulta(id="P1/MOD-001/1", tipo="achado", projeto="P1", id_regra="MOD-001", objeto="X", texto="q2"),
]


def _fixo(ordem):
    return lambda consulta, k: ordem[:k]


RANQUEADORES = {"bm25": _fixo([0, 1, 2]), "densa": _fixo([3, 0]), "hibrida": _fixo([4, 1])}


def test_id_da_secao_junta_regra_pagina_e_ancora():
    assert id_da_secao("MOD-001", TRECHOS[1]) == "MOD-001|learn:a#s1"


def test_complementares_por_busca_usa_a_selecao_da_geracao():
    medidas = complementares_por_busca(CONSULTAS, {"MOD-001": ANCORA}, TRECHOS, RANQUEADORES)
    assert [m.secoes for m in medidas["bm25"]] == [["MOD-001|learn:a#s1", "MOD-001|learn:a#s1"]] * 2
    assert [m.secoes for m in medidas["densa"]] == [["MOD-001|learn:b#s"]] * 2


def test_pool_tem_uma_linha_por_secao_mesmo_com_varias_partes():
    pool = formar_pool(CONSULTAS, {"MOD-001": ANCORA}, TRECHOS, RANQUEADORES)
    assert [p.id for p in pool] == ["MOD-001|learn:a#s1", "MOD-001|learn:b#s", "MOD-001|learn:c#s"]
    assert pool[0].trecho.id == "learn:a#s1/1"
