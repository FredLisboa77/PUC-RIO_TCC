"""Contexto da geração: âncora sempre em [1], complementares do BM25 com orçamento."""

import pytest

from core.analise.contexto import ErroDeContexto, carregar_gabaritos, montar_contexto, verificar_ancoras
from core.rules.todas import REGISTRO
from fabricas_analise import TRECHO_ANCORA, achado, base_bm25, gabarito, meta, trecho_indexado


def test_ancora_e_sempre_o_trecho_1_e_os_numeros_sao_sequenciais():
    base = base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time tables are hidden")])
    ctx = montar_contexto(meta(), achado(), base, gabarito())
    assert (ctx[0].numero, ctx[0].origem, ctx[0].id_pagina) == (1, "ancora", "learn:auto")
    assert [t.numero for t in ctx] == list(range(1, len(ctx) + 1))
    assert all(t.origem == "busca" for t in ctx[1:])
    assert ctx[0].url == "https://learn.microsoft.com/auto"


def test_ancora_nao_se_repete_entre_os_complementares():
    base = base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time")])
    ids = [t.id_pagina for t in montar_contexto(meta(), achado(), base, gabarito())]
    assert ids.count("learn:auto") == 1


def test_no_maximo_quatro_complementares():
    outros = [trecho_indexado(f"learn:p{i}", "auto date time") for i in range(8)]
    ctx = montar_contexto(meta(), achado(), base_bm25([TRECHO_ANCORA, *outros]), gabarito())
    assert len(ctx) == 5


def test_complementar_que_estoura_o_orcamento_e_pulado_e_o_proximo_entra(monkeypatch):
    longo = trecho_indexado("learn:longo", "auto date time " + "palavra " * 1790)
    curto = trecho_indexado("learn:curto", "auto date time")
    base = base_bm25([TRECHO_ANCORA, longo, curto])
    monkeypatch.setattr(base, "buscar", lambda consulta, k: [longo, curto])
    ctx = montar_contexto(meta(), achado(), base, gabarito())
    assert [t.id_pagina for t in ctx] == ["learn:auto", "learn:curto"]


def test_ancora_entra_mesmo_acima_do_orcamento():
    enorme = trecho_indexado("learn:auto", "disable the auto date time option " + "x " * 2000)
    ctx = montar_contexto(meta(), achado(), base_bm25([enorme]), gabarito())
    assert [t.origem for t in ctx] == ["ancora"]


def test_regra_sem_gabarito_falha_na_verificacao():
    with pytest.raises(ErroDeContexto, match="MOD-002"):
        verificar_ancoras(["MOD-001", "MOD-002"], {"MOD-001": gabarito()}, base_bm25([TRECHO_ANCORA]))


def test_ancora_ausente_do_indice_falha_na_verificacao():
    with pytest.raises(ErroDeContexto, match="MOD-001"):
        verificar_ancoras(["MOD-001"], {"MOD-001": gabarito(id_pagina="learn:sumiu")}, base_bm25([TRECHO_ANCORA]))


def test_gabaritos_reais_cobrem_todas_as_regras_registradas():
    assert set(REGISTRO.ids()) <= set(carregar_gabaritos())
