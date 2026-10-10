"""Montagem do catálogo de fontes.

Os retratos dos testes são feitos à mão e pequenos; os reais, com 1.420
páginas, são exercitados em `test_rag_dados_reais.py`.
"""

from datetime import date

import pytest

from rag.catalogo import (
    LICENCA_LEARN,
    ErroDeCatalogo,
    Fonte,
    montar_catalogo,
)
from rag.tocs import SECOES, ItemToc, Retrato
from rag.urls import FORA_DO_LEARN, NAO_DOCUMENTAL

HOJE = date(2026, 10, 9)
L = "https://learn.microsoft.com/en-us/"
P = "https://learn.microsoft.com/pt-br/"


def retratos(en=None, pt=None, baixado_em=HOJE):
    """Os dez retratos. Seção não citada fica vazia; `pt=None` replica o `en`."""
    en = en or {}
    pt = en if pt is None else pt
    saida = {}
    for secao in SECOES:
        for idioma, itens in (("en-us", en), ("pt-br", pt)):
            saida[(idioma, secao.caminho)] = Retrato(
                secao=secao.caminho,
                idioma=idioma,
                url=f"https://learn.microsoft.com/{idioma}/{secao.caminho}/toc.json",
                baixado_em=baixado_em,
                itens=[ItemToc(href=h, titulo=t) for h, t in itens.get(secao.caminho, [])],
            )
    return saida


def montar(en=None, pt=None, ancoras=None, observacoes=None, leituras=None, baixado_em=HOJE):
    return montar_catalogo(
        retratos(en, pt, baixado_em), ancoras or {}, observacoes or {}, leituras or []
    )


def por_id(resultado):
    return {f.id: f for f in resultado.fontes}


def test_pagina_de_origem_vira_entrada_completa():
    resultado = montar(en={"power-bi/guidance": [("star-schema", "Star schema")]})
    assert resultado.fontes == [
        Fonte(
            id="learn:power-bi/guidance/star-schema",
            url=L + "power-bi/guidance/star-schema",
            url_pt_br=P + "power-bi/guidance/star-schema",
            titulo="Star schema",
            organizacao="Microsoft",
            data_acesso="2026-10-09",
            licenca=LICENCA_LEARN,
            origem=["toc:power-bi/guidance"],
            indexar=True,
            regras=[],
            observacao=None,
        )
    ]


def test_data_acesso_e_a_do_retrato():
    resultado = montar(en={"dax": [("a", "A")]}, baixado_em=date(2026, 1, 2))
    assert resultado.fontes[0].data_acesso == "2026-01-02"


def test_exclusoes_sao_contadas_por_motivo_e_nao_entram():
    resultado = montar(
        en={
            "power-bi/guidance": [
                ("./", "Guidance"),
                ("/contribute/", "Contribute"),
                ("https://ideas.fabric.microsoft.com/", "Ideas"),
                ("star-schema", "Star"),
            ],
            "dax": [("https://aka.ms/learndax", "Learn DAX")],
        }
    )
    assert [f.id for f in resultado.fontes] == ["learn:power-bi/guidance/star-schema"]
    assert dict(resultado.exclusoes) == {FORA_DO_LEARN: 2, NAO_DOCUMENTAL: 2}


def test_secao_de_ancora_nao_e_origem_nem_conta_exclusao():
    resultado = montar(en={"power-bi/connect-data": [("pagina", "P"), ("./", "Entrada")]})
    assert resultado.fontes == []
    assert dict(resultado.exclusoes) == {}


def test_pagina_em_duas_origens_vira_uma_entrada_com_titulo_da_propria_secao():
    resultado = montar(
        en={
            "power-bi/guidance": [("/dax/best-practices/dax-variables", "Pelo guidance")],
            "dax": [("best-practices/dax-variables", "Use variables")],
        }
    )
    (fonte,) = resultado.fontes
    assert fonte.id == "learn:dax/best-practices/dax-variables"
    assert fonte.origem == ["toc:dax", "toc:power-bi/guidance"]
    assert fonte.titulo == "Use variables"


def test_sem_secao_propria_o_titulo_segue_a_ordem_das_secoes():
    resultado = montar(
        en={
            "power-bi/guidance": [("/fabric/cicd/x", "Do guidance")],
            "powerquery-m": [("/fabric/cicd/x", "Do M")],
        }
    )
    assert resultado.fontes[0].titulo == "Do guidance"


def test_item_sem_titulo_usa_o_ultimo_segmento():
    resultado = montar(en={"power-bi/guidance": [("star-schema", None)]})
    assert resultado.fontes[0].titulo == "star-schema"


def test_url_pt_br_so_quando_o_caminho_esta_no_retrato_pt_br():
    resultado = montar(en={"dax": [("a", "A"), ("b", "B")]}, pt={"dax": [("a", "A pt")]})
    fontes = por_id(resultado)
    assert fontes["learn:dax/a"].url_pt_br == P + "dax/a"
    assert fontes["learn:dax/b"].url_pt_br is None


def test_ancora_dentro_de_origem_acrescenta_origem_e_regra():
    url = L + "power-bi/guidance/star-schema"
    resultado = montar(
        en={"power-bi/guidance": [("star-schema", "Star")]},
        ancoras={"MOD-006": url, "MOD-003": url},
    )
    (fonte,) = resultado.fontes
    assert fonte.origem == ["regra:MOD-003", "regra:MOD-006", "toc:power-bi/guidance"]
    assert fonte.regras == ["MOD-003", "MOD-006"]


def test_ancora_em_secao_que_nao_e_origem_entra_sozinha():
    resultado = montar(
        en={"power-bi/connect-data": [("desktop-data-types", "Data types"), ("outra", "Outra")]},
        ancoras={"PERF-003": L + "power-bi/connect-data/desktop-data-types"},
    )
    (fonte,) = resultado.fontes
    assert fonte.id == "learn:power-bi/connect-data/desktop-data-types"
    assert fonte.origem == ["regra:PERF-003"]
    assert fonte.titulo == "Data types"
    assert fonte.url_pt_br == P + "power-bi/connect-data/desktop-data-types"


def test_ancora_escrita_com_outra_caixa_ou_barra_final_ainda_casa():
    resultado = montar(
        en={"dax": [("best-practices/dax-divide-function-operator", "DIVIDE")]},
        ancoras={"DAX-001": L + "DAX/best-practices/dax-divide-function-operator/"},
    )
    assert resultado.fontes[0].regras == ["DAX-001"]


def test_ancora_ausente_falha_listando_regra_e_url():
    with pytest.raises(ErroDeCatalogo, match="DAX-999: https://learn.microsoft.com/en-us/dax/nao-existe"):
        montar(ancoras={"DAX-999": L + "dax/nao-existe"})


def test_observacao_e_incorporada():
    resultado = montar(en={"dax": [("a", "A")]}, observacoes={"learn:dax/a": "Nota."})
    assert resultado.fontes[0].observacao == "Nota."


def test_observacao_orfa_falha():
    with pytest.raises(ErroDeCatalogo, match="learn:dax/sumiu"):
        montar(en={"dax": [("a", "A")]}, observacoes={"learn:dax/sumiu": "Nota."})


def test_falta_retrato_falha_indicando_atualizar():
    incompletos = retratos()
    del incompletos[("pt-br", "dax")]
    with pytest.raises(ErroDeCatalogo, match="atualizar"):
        montar_catalogo(incompletos, {}, {}, [])


def test_ordem_de_entrada_nao_muda_a_saida():
    itens = [("b", "B"), ("a", "A"), ("c", "C")]
    url = L + "dax/a"
    um = montar(en={"dax": itens}, ancoras={"X-1": url, "X-2": url})
    outro = montar(en={"dax": list(reversed(itens))}, ancoras={"X-2": url, "X-1": url})
    assert um.fontes == outro.fontes
    assert [f.id for f in um.fontes] == ["learn:dax/a", "learn:dax/b", "learn:dax/c"]
