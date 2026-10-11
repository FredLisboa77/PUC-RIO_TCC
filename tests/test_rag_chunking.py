"""Chunking da base: estratégias `secao` e `janela`, sobre páginas sintéticas."""

from rag.avaliacao import Trecho
from rag.chunking import (
    JANELA,
    PASSO,
    cabecalho_de,
    ids_do_corpus_guidance,
    montar_trechos,
    trechos_por_janela,
    trechos_por_secao,
)
from rag.extracao import VERSAO_EXTRATOR, Bloco, PaginaExtraida, Secao


def _pagina(secoes, id_pagina="learn:x/p", titulo="Título"):
    """`secoes`: lista de (ancora, caminho, [textos dos blocos])."""
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_pagina,
        url="https://learn.microsoft.com/en-us/x/p",
        titulo=titulo,
        secoes=[
            Secao(
                ancora=ancora,
                titulo=caminho.split(" › ")[-1],
                nivel=1 if caminho == titulo else 2,
                caminho=caminho,
                blocos=[Bloco(tipo="paragrafo", texto=t) for t in textos],
            )
            for ancora, caminho, textos in secoes
        ],
        secoes_excluidas=[],
    )


def test_secao_curta_vira_um_trecho_inteiro():
    pagina = _pagina([("s", "Sec", ["um dois", "três"])])
    (trecho,) = trechos_por_secao(pagina, cabecalho=False)
    assert (trecho.id, trecho.ancora, trecho.caminho) == ("learn:x/p#s/1", "s", "Sec")
    assert trecho.texto == "um dois\ntrês"
    assert trecho.texto_indexado == trecho.texto


def test_secao_longa_e_partida_nas_fronteiras_de_bloco():
    pagina = _pagina([("s", "Sec", ["a b c", "d e f", "g h"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=5)]
    assert textos == ["a b c", "d e f\ng h"]


def test_bloco_maior_que_o_limite_e_partido_por_palavras():
    pagina = _pagina([("s", "Sec", ["1 2 3 4 5 6 7"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=3)]
    assert textos == ["1 2 3", "4 5 6", "7"]


def test_bloco_gigante_entre_pequenos_preserva_a_ordem():
    pagina = _pagina([("s", "Sec", ["a b", "1 2 3 4 5 6 7", "c d"])])
    textos = [t.texto for t in trechos_por_secao(pagina, cabecalho=False, limite=3)]
    assert textos == ["a b", "1 2 3", "4 5 6", "7", "c d"]


def test_pedacos_de_secao_partida_mantem_ancora_e_ids_seguem_na_pagina():
    pagina = _pagina([("s1", "Sec 1", ["a b c", "d e f"]), ("s2", "Sec 2", ["g"])])
    trechos = trechos_por_secao(pagina, cabecalho=False, limite=3)
    assert [(t.id, t.ancora) for t in trechos] == [
        ("learn:x/p#s1/1", "s1"),
        ("learn:x/p#s1/2", "s1"),
        ("learn:x/p#s2/3", "s2"),
    ]


def test_cabecalho_entra_so_no_texto_indexado():
    pagina = _pagina([("s", "Sec", ["corpo"])])
    (trecho,) = trechos_por_secao(pagina, cabecalho=True)
    assert trecho.texto == "corpo"
    assert trecho.texto_indexado == "Título › Sec\ncorpo"


def test_cabecalho_da_secao_de_nivel_1_nao_repete_o_titulo():
    assert cabecalho_de("CALCULATE", "CALCULATE") == "CALCULATE"
    assert cabecalho_de("Star schema", "Snowflake dimensions") == "Star schema › Snowflake dimensions"


def test_janelas_com_sobreposicao_atravessam_secoes():
    s1 = " ".join(f"w{i}" for i in range(10))
    s2 = " ".join(f"w{i}" for i in range(10, 20))
    pagina = _pagina([("s1", "Sec 1", [s1]), ("s2", "Sec 2", [s2])])
    trechos = trechos_por_janela(pagina, cabecalho=False, janela=8, passo=6)
    assert [(t.texto.split()[0], t.texto.split()[-1], t.ancora) for t in trechos] == [
        ("w0", "w7", "s1"),
        ("w6", "w13", "s1"),
        ("w12", "w19", "s2"),
    ]
    assert [t.id for t in trechos] == ["learn:x/p#s1/1", "learn:x/p#s1/2", "learn:x/p#s2/3"]


def test_pagina_curta_vira_uma_janela_so():
    pagina = _pagina([("s", "Sec", ["a b c"])])
    assert [t.texto for t in trechos_por_janela(pagina, cabecalho=False)] == ["a b c"]


def test_toda_sequencia_curta_cabe_inteira_em_alguma_janela():
    palavras = [f"w{i}" for i in range(1000)]
    pagina = _pagina([("s", "Sec", [" ".join(palavras)])])
    janelas = [t.texto.split() for t in trechos_por_janela(pagina, cabecalho=False)]
    tamanho = JANELA - PASSO + 1
    for inicio in range(0, len(palavras) - tamanho + 1):
        alvo = palavras[inicio : inicio + tamanho]
        assert any(
            " ".join(alvo) in " ".join(janela) for janela in janelas
        ), f"sequência a partir de w{inicio} não coube em nenhuma janela"


def test_montar_trechos_percorre_as_paginas_em_ordem():
    paginas = [_pagina([("s", "Sec", ["x"])], id_pagina="learn:b"), _pagina([("s", "Sec", ["y"])], id_pagina="learn:a")]
    trechos = montar_trechos(paginas, "secao", cabecalho=False)
    assert [t.id_pagina for t in trechos] == ["learn:b", "learn:a"]
    assert montar_trechos(paginas, "janela", cabecalho=False)[0].texto == "x"


def test_corpus_guidance_inclui_guidance_e_ancoras_de_regra():
    fontes = [
        {"id": "a", "indexar": True, "origem": ["toc:power-bi/guidance"]},
        {"id": "b", "indexar": True, "origem": ["regra:MOD-005"]},
        {"id": "c", "indexar": True, "origem": ["toc:dax"]},
        {"id": "d", "indexar": False, "origem": ["toc:power-bi/guidance"]},
    ]
    assert ids_do_corpus_guidance(fontes) == frozenset({"a", "b"})


def test_para_regua_leva_texto_puro():
    (trecho,) = trechos_por_secao(_pagina([("s", "Sec", ["corpo"])]), cabecalho=True)
    assert trecho.para_regua() == Trecho(texto="corpo", id_pagina="learn:x/p", ancora="s")


def _dez_tokens_por_palavra(texto):
    return 10 * len(texto.split())


def test_trecho_acima_do_limite_de_tokens_e_partido_ao_meio():
    pagina = _pagina([("s", "Sec", ["1 2 3 4 5 6 7 8"])])
    trechos = trechos_por_secao(pagina, cabecalho=False, contar_tokens=_dez_tokens_por_palavra, limite_tokens=40)
    assert [t.texto for t in trechos] == ["1 2 3 4", "5 6 7 8"]
    assert [t.id for t in trechos] == ["learn:x/p#s/1", "learn:x/p#s/2"]


def test_limite_de_tokens_conta_o_cabecalho():
    pagina = _pagina([("s", "Sec", ["1 2"])])
    trechos = trechos_por_secao(pagina, cabecalho=True, contar_tokens=_dez_tokens_por_palavra, limite_tokens=40)
    assert [t.texto_indexado for t in trechos] == ["Título › Sec\n1", "Título › Sec\n2"]


def test_janela_acima_do_limite_de_tokens_tambem_e_partida():
    pagina = _pagina([("s", "Sec", [" ".join(f"w{i}" for i in range(8))])])
    trechos = trechos_por_janela(
        pagina, cabecalho=False, janela=8, passo=6, contar_tokens=_dez_tokens_por_palavra, limite_tokens=40
    )
    assert [t.texto for t in trechos] == ["w0 w1 w2 w3", "w4 w5 w6 w7"]


def test_palavra_unica_acima_do_limite_fica_como_esta():
    pagina = _pagina([("s", "Sec", ["gigante"])])
    trechos = trechos_por_secao(pagina, cabecalho=False, contar_tokens=lambda t: 1000, limite_tokens=40)
    assert [t.texto for t in trechos] == ["gigante"]


def test_montar_trechos_repassa_o_contador():
    pagina = _pagina([("s", "Sec", ["1 2 3 4 5 6 7 8"])])
    trechos = montar_trechos([pagina], "secao", cabecalho=False, contar_tokens=_dez_tokens_por_palavra, limite_tokens=40)
    assert len(trechos) == 2
