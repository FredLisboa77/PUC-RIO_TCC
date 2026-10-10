"""Regras de URL do catálogo de fontes.

O `toc.json` do Learn mistura quatro formas de link, e uma delas — relativa à
raiz — não traz o idioma. Medido em 09/10/2026: resolvida sem prefixar o
idioma, ela tiraria do guidance as 9 páginas de boas práticas de DAX.
"""

import pytest

from rag.urls import (
    FORA_DO_LEARN,
    NAO_DOCUMENTAL,
    caminho_sem_idioma,
    em_outro_idioma,
    motivo_de_exclusao,
    normalizar_url,
    resolver_href,
    secao_propria,
)

L = "https://learn.microsoft.com/en-us/"


def test_href_relativo_resolve_na_pasta_da_secao():
    assert resolver_href("star-schema", "power-bi/guidance") == (
        L + "power-bi/guidance/star-schema"
    )


def test_href_com_subida_de_pasta():
    assert resolver_href("../transform-model/dataflows/x", "power-bi/guidance") == (
        L + "power-bi/transform-model/dataflows/x"
    )


def test_href_relativo_a_raiz_recebe_o_idioma():
    assert resolver_href("/dax/best-practices/dax-variables", "power-bi/guidance") == (
        L + "dax/best-practices/dax-variables"
    )
    assert resolver_href("/dax/x", "dax", "pt-br") == (
        "https://learn.microsoft.com/pt-br/dax/x"
    )


def test_href_relativo_a_raiz_que_ja_traz_idioma_nao_duplica():
    assert resolver_href("/en-us/dax/x", "dax") == L + "dax/x"
    assert resolver_href("/pt-br/dax/x", "dax") == L + "dax/x"


def test_href_absoluto_externo_fica_como_esta():
    assert resolver_href("https://ideas.fabric.microsoft.com/", "power-bi/guidance") == (
        "https://ideas.fabric.microsoft.com/"
    )


def test_href_absoluto_do_learn_sem_idioma_ou_em_outro_idioma():
    assert resolver_href(
        "https://learn.microsoft.com/power-bi/guidance/star-schema", "dax"
    ) == L + "power-bi/guidance/star-schema"
    assert resolver_href("https://learn.microsoft.com/pt-br/dax/x", "dax") == L + "dax/x"


def test_pagina_de_entrada_da_secao_resolve_com_barra_final():
    assert resolver_href("./", "dax") == L + "dax/"


@pytest.mark.parametrize(
    "url",
    [
        "https://ideas.fabric.microsoft.com/",
        "https://aka.ms/learndax",
        "https://community.fabric.microsoft.com/",
    ],
)
def test_host_fora_do_learn_e_excluido(url):
    assert motivo_de_exclusao(url) == FORA_DO_LEARN


@pytest.mark.parametrize(
    "url",
    [
        L + "power-bi/guidance/",
        L + "contribute/",
        L + "answers/",
        L + "training/fabric/",
        L + "training/modules/algum-modulo",
    ],
)
def test_entrada_de_secao_e_area_nao_documental_sao_excluidas(url):
    assert motivo_de_exclusao(url) == NAO_DOCUMENTAL


def test_artigo_do_learn_nao_e_excluido_mesmo_fora_das_secoes():
    assert motivo_de_exclusao(L + "fabric/cicd/best-practices-cicd") is None


def test_normalizar_tira_query_fragmento_barra_e_padroniza_caixa_no_learn():
    assert normalizar_url(
        "HTTPS://Learn.Microsoft.com/en-us/DAX/best-practices/dax-variables/?view=x#a"
    ) == L + "dax/best-practices/dax-variables"


def test_normalizar_preserva_a_caixa_do_caminho_fora_do_learn():
    assert normalizar_url("https://www.sqlbi.com/articles/Mark-As-Date-Table/") == (
        "https://www.sqlbi.com/articles/Mark-As-Date-Table"
    )


def test_caminho_sem_idioma():
    assert caminho_sem_idioma(L + "dax/best-practices/x") == "dax/best-practices/x"


def test_em_outro_idioma():
    assert em_outro_idioma(L + "dax/x", "pt-br") == "https://learn.microsoft.com/pt-br/dax/x"


def test_secao_propria():
    secoes = ["power-bi/guidance", "dax", "powerquery-m"]
    assert secao_propria(L + "dax/best-practices/x", secoes) == "dax"
    assert secao_propria(L + "power-bi/guidance/star-schema", secoes) == "power-bi/guidance"
    assert secao_propria(L + "fabric/cicd/x", secoes) is None


def test_secao_propria_e_prefixo_de_pasta_nao_de_texto():
    assert secao_propria(L + "daxguide/x", ["dax"]) is None


def test_secao_propria_prefere_a_mais_longa():
    assert secao_propria(L + "power-bi/guidance/x", ["power-bi", "power-bi/guidance"]) == (
        "power-bi/guidance"
    )


def test_raiz_do_idioma_sem_barra_e_excluida_e_nao_duplica_o_idioma():
    url = resolver_href("https://learn.microsoft.com/en-us", "dax")
    assert url == "https://learn.microsoft.com/en-us"
    assert motivo_de_exclusao(url) == NAO_DOCUMENTAL
    assert motivo_de_exclusao(resolver_href("https://learn.microsoft.com", "dax")) == (
        NAO_DOCUMENTAL
    )


def test_idioma_com_tres_partes_e_trocado():
    assert resolver_href("/sr-latn-rs/dax/x", "dax") == L + "dax/x"
    assert caminho_sem_idioma("https://learn.microsoft.com/sr-latn-rs/dax/x") == "dax/x"
