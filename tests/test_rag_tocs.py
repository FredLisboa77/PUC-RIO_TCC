"""Retratos dos `toc.json` do Learn.

O retrato versionado é uma listagem normalizada (caminho e título), não o
arquivo bruto: os termos de uso do Learn não permitem publicar cópia literal
num repositório público (spec, seção 5.2).
"""

from datetime import date
from pathlib import Path

import pytest

from rag.tocs import (
    IDIOMAS,
    SECOES,
    ErroDeRetrato,
    ItemToc,
    Retrato,
    achatar_toc,
    caminho_do_retrato,
    serializar_retrato,
    url_do_toc,
)

HOJE = date(2026, 10, 9)

TOC = {
    "items": [
        {"href": "./", "toc_title": "Guidance"},
        {
            "toc_title": "Grupo sem href",
            "children": [
                {"href": "star-schema", "toc_title": "Star schema"},
                {"href": "auto-date-time"},
            ],
        },
    ]
}


def test_secoes_e_idiomas_da_spec():
    assert [(s.caminho, s.papel) for s in SECOES] == [
        ("power-bi/guidance", "origem"),
        ("dax", "origem"),
        ("powerquery-m", "origem"),
        ("power-bi/connect-data", "ancora"),
        ("power-bi/transform-model", "ancora"),
    ]
    assert IDIOMAS == ("en-us", "pt-br")


def test_achatar_toc_em_ordem_e_so_com_href():
    assert achatar_toc(TOC, "x") == [
        ItemToc(href="./", titulo="Guidance"),
        ItemToc(href="star-schema", titulo="Star schema"),
        ItemToc(href="auto-date-time", titulo=None),
    ]


@pytest.mark.parametrize("bruto", [{}, {"items": None}, [], "texto"])
def test_achatar_toc_recusa_estrutura_inesperada(bruto):
    with pytest.raises(ErroDeRetrato, match="items"):
        achatar_toc(bruto, "origem.json")


def test_url_do_toc():
    assert url_do_toc("power-bi/guidance", "pt-br") == (
        "https://learn.microsoft.com/pt-br/power-bi/guidance/toc.json"
    )


def test_caminho_do_retrato_aninha_a_secao():
    assert caminho_do_retrato(Path("r"), "en-us", "power-bi/guidance") == Path(
        "r/en-us/power-bi/guidance.json"
    )


def test_serializacao_tem_ordem_e_indentacao_fixas_e_volta_igual():
    retrato = Retrato(
        secao="dax",
        idioma="en-us",
        url="u",
        baixado_em=HOJE,
        itens=[ItemToc(href="a", titulo="Á")],
    )
    texto = serializar_retrato(retrato)
    assert texto == (
        '{\n  "secao": "dax",\n  "idioma": "en-us",\n  "url": "u",\n'
        '  "baixado_em": "2026-10-09",\n  "itens": [\n    {\n'
        '      "href": "a",\n      "titulo": "Á"\n    }\n  ]\n}\n'
    )
    assert Retrato.model_validate_json(texto) == retrato
