"""Conjunto de avaliação da recuperação: gabarito, consultas e métricas.

Dados sintéticos; os testes sobre a base e os PBIP reais estão em
`test_rag_avaliacao_real.py`.
"""

import pytest

from core.rules.todas import REGISTRO
from core.rules.base import Achado, Evidencia
from rag.avaliacao import (
    ARQUIVO_GABARITO,
    ConjuntoAvaliacao,
    Consulta,
    ErroDeAvaliacao,
    FraseMarca,
    Gabarito,
    como_yaml,
    deduzir_secao,
    gerar,
    id_da_pagina,
    ler_conjunto,
    ler_frases_marca,
)
from rag.consulta import montar_consulta
from rag.extracao import VERSAO_EXTRATOR, Bloco, PaginaExtraida, Secao


def test_ler_frases_marca_ordena_por_regra(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-006\n  frase_marca: b\n- id_regra: MOD-003\n  frase_marca: a\n",
        encoding="utf-8",
    )
    assert ler_frases_marca(arquivo) == [
        FraseMarca(id_regra="MOD-003", frase_marca="a"),
        FraseMarca(id_regra="MOD-006", frase_marca="b"),
    ]


def test_gabarito_ausente_falha(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="não existe"):
        ler_frases_marca(tmp_path / "nao-existe.yaml")


def test_regra_repetida_no_gabarito_falha(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-003\n  frase_marca: a\n- id_regra: MOD-003\n  frase_marca: b\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*mais de uma vez"):
        ler_frases_marca(arquivo)


def test_gabarito_versionado_cobre_exatamente_as_regras_do_registro():
    frases = ler_frases_marca(ARQUIVO_GABARITO)
    assert [f.id_regra for f in frases] == REGISTRO.ids()
    assert all(0 < len(f.frase_marca.split()) <= 12 for f in frases)


METAS = {m.id: m for m in REGISTRO.metas()}
STAR = "learn:power-bi/guidance/star-schema"
FRASES = [
    FraseMarca(id_regra="MOD-003", frase_marca="right number of tables"),
    FraseMarca(id_regra="MOD-006", frase_marca="a single model table"),
]


def _pagina(id_pagina, secoes):
    """`secoes`: lista de (ancora, [textos dos blocos])."""
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_pagina,
        url="https://learn.microsoft.com/en-us/x",
        titulo="T",
        secoes=[
            Secao(
                ancora=ancora,
                titulo=ancora,
                nivel=2,
                caminho=ancora,
                blocos=[Bloco(tipo="paragrafo", texto=t) for t in textos],
            )
            for ancora, textos in secoes
        ],
        secoes_excluidas=[],
    )


PAGINA_STAR = _pagina(
    STAR,
    [
        ("relevance", ["Use the Right Number of Tables here."]),
        ("snowflake-dimensions", ["Usually A single model table is better."]),
        ("outra", ["nada a ver"]),
    ],
)


def _achado(id_regra, objeto, tipo="tabela"):
    return Achado(id_regra=id_regra, evidencia=Evidencia(tipo_objeto=tipo, objeto=objeto), mensagem="m")


def _gerar(achados=None, frases=FRASES, paginas=None):
    paginas = paginas or {STAR: PAGINA_STAR}
    return gerar(
        metas=[METAS["MOD-003"], METAS["MOD-006"]],
        frases=frases,
        ler_pagina=lambda id_pagina: paginas[id_pagina],
        achados_por_projeto=achados or {},
    )


def test_id_da_pagina_vem_da_url_canonica():
    assert id_da_pagina(METAS["MOD-003"].url_canonica) == STAR


def test_deduz_a_secao_de_cada_regra():
    assert _gerar().gabaritos == [
        Gabarito(id_regra="MOD-003", frase_marca="right number of tables", id_pagina=STAR, ancora="relevance"),
        Gabarito(
            id_regra="MOD-006",
            frase_marca="a single model table",
            id_pagina=STAR,
            ancora="snowflake-dimensions",
        ),
    ]


def test_frase_partida_entre_dois_blocos_da_mesma_secao_e_encontrada():
    pagina = _pagina(STAR, [("s", ["the right number", "of tables matters"])])
    assert deduzir_secao(pagina, "right number of tables", "MOD-003") == "s"


def test_frase_em_nenhuma_secao_falha_nomeando_a_regra():
    pagina = _pagina(STAR, [("s", ["nada"])])
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*nenhuma seção.*star-schema"):
        deduzir_secao(pagina, "right number of tables", "MOD-003")


def test_frase_em_mais_de_uma_secao_falha_nomeando_as_secoes():
    pagina = _pagina(STAR, [("a", ["right number of tables"]), ("b", ["Right number of tables"])])
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*mais de uma seção.*a, b"):
        deduzir_secao(pagina, "right number of tables", "MOD-003")


def test_regra_sem_gabarito_e_gabarito_sem_regra_falham():
    with pytest.raises(ErroDeAvaliacao, match="sem gabarito: MOD-006"):
        _gerar(frases=FRASES[:1])
    with pytest.raises(ErroDeAvaliacao, match="regra inexistente: XXX-999"):
        _gerar(frases=[*FRASES, FraseMarca(id_regra="XXX-999", frase_marca="x")])


def test_consultas_por_regra_e_por_achado_com_ids_estaveis():
    achados = {
        "P2": [_achado("MOD-003", "Toggle A"), _achado("MOD-003", "Toggle B")],
        "P1": [_achado("MOD-006", "Product")],
    }
    conjunto = _gerar(achados)
    assert [(c.id, c.tipo, c.projeto, c.objeto) for c in conjunto.consultas] == [
        ("REGRA/MOD-003", "regra", None, None),
        ("REGRA/MOD-006", "regra", None, None),
        ("P1/MOD-006/1", "achado", "P1", "Product"),
        ("P2/MOD-003/1", "achado", "P2", "Toggle A"),
        ("P2/MOD-003/2", "achado", "P2", "Toggle B"),
    ]
    assert conjunto.consultas[0].texto == montar_consulta(METAS["MOD-003"])
    assert conjunto.consultas[2].texto == montar_consulta(METAS["MOD-006"], achados["P1"][0])


def test_achado_de_regra_fora_do_registro_falha():
    with pytest.raises(ErroDeAvaliacao, match="P1.*XXX-999"):
        _gerar({"P1": [_achado("XXX-999", "T")]})


def test_yaml_faz_ida_e_volta_com_nomes_especiais(tmp_path):
    achados = {"P5": [_achado("MOD-003", "Sales[Avg $/Unit LY] → % 'x'", tipo="medida")]}
    conjunto = _gerar(achados)
    texto = como_yaml(conjunto)
    assert texto.startswith("# Gerado por `python -m rag.avaliacao gerar`")
    arquivo = tmp_path / "consultas.yaml"
    arquivo.write_text(texto, encoding="utf-8", newline="\n")
    assert ler_conjunto(arquivo) == conjunto
    assert b"\r\n" not in arquivo.read_bytes()


def test_ler_conjunto_ausente_falha_indicando_o_gerador(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="rag.avaliacao gerar"):
        ler_conjunto(tmp_path / "nao-existe.yaml")
