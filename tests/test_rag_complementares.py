"""Complementares: as três buscas, o pool, a precisão e a decisão."""

import pytest
from fabricas_analise import trecho_indexado

from rag.avaliacao import Consulta
from rag.complementares import (
    ConsultaMedida,
    ErroDeComplementares,
    complementares_por_busca,
    decidir_busca,
    formar_pool,
    id_da_secao,
    medir_busca,
)

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


JULGAMENTOS = {"A|p#1": "pertinente", "A|p#2": "não pertinente", "A|p#3": "indeterminado", "B|p#1": "pertinente"}


def _m(id_, regra, secoes):
    return ConsultaMedida(id=id_, id_regra=regra, secoes=secoes)


def test_precisao_por_consulta_regra_macro_e_micro():
    medidas = [
        _m("1", "A", ["A|p#1", "A|p#2"]),           # 1/2
        _m("2", "A", ["A|p#1", "A|p#1", "A|p#3"]),  # principal 2/2; piso 2/3; teto 3/3
        _m("3", "B", ["B|p#1"]),                    # 1/1
    ]
    r = medir_busca(medidas, JULGAMENTOS)
    assert r.por_regra["A"].principal == pytest.approx((0.5 + 1.0) / 2)
    assert r.por_regra["A"].piso == pytest.approx((0.5 + 2 / 3) / 2)
    assert r.por_regra["A"].teto == pytest.approx((0.5 + 1.0) / 2)
    assert r.macro.principal == pytest.approx((0.75 + 1.0) / 2)
    assert r.micro.principal == pytest.approx(4 / 5)


def test_consulta_sem_complementar_nao_entra_na_media_e_e_contada():
    r = medir_busca([_m("1", "A", []), _m("2", "A", ["A|p#1"])], JULGAMENTOS)
    assert r.sem_complementar == 1
    assert r.por_regra["A"].principal == 1.0


def test_regra_so_com_consultas_vazias_fica_none_e_macro_a_ignora():
    r = medir_busca([_m("1", "A", []), _m("2", "B", ["B|p#1"])], JULGAMENTOS)
    assert r.por_regra["A"].principal is None
    assert r.macro.principal == 1.0


def test_complementar_sem_julgamento_aborta():
    with pytest.raises(ErroDeComplementares, match="A\\|p#9"):
        medir_busca([_m("1", "A", ["A|p#9"])], JULGAMENTOS)


@pytest.mark.parametrize(
    ("macros", "vencedora"),
    [
        ({"bm25": 0.50, "densa": 0.59, "hibrida": 0.55}, "bm25"),
        ({"bm25": 0.50, "densa": 0.55, "hibrida": 0.62}, "hibrida"),
        ({"bm25": 0.50, "densa": 0.70, "hibrida": 0.65}, "densa"),
        ({"bm25": 0.50, "densa": 0.65, "hibrida": 0.65}, "densa"),
        ({"bm25": 0.50, "densa": 0.60, "hibrida": None}, "densa"),
    ],
)
def test_regra_de_decisao(macros, vencedora):
    assert decidir_busca(macros).vencedora == vencedora


def test_decisao_sem_macro_do_bm25_aborta():
    with pytest.raises(ErroDeComplementares, match="bm25"):
        decidir_busca({"bm25": None, "densa": 0.9, "hibrida": 0.9})
