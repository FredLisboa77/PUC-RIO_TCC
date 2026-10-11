"""Conjunto de avaliação da recuperação: gabarito, consultas e métricas.

Dados sintéticos; os testes sobre a base e os PBIP reais estão em
`test_rag_avaliacao_real.py`.
"""

import pytest

from core.rules.todas import REGISTRO
from core.rules.base import Achado, Evidencia
from core.rules.runner import FalhaDeRegra, ResultadoRegras
from rag import avaliacao as modulo_avaliacao
from rag.avaliacao import (
    ARQUIVO_GABARITO,
    K_MAX,
    ConjuntoAvaliacao,
    Consulta,
    ErroDeAvaliacao,
    FraseMarca,
    Gabarito,
    Trecho,
    achados_dos_projetos,
    avaliar,
    como_yaml,
    deduzir_secao,
    formatar_relatorio,
    gerar,
    id_da_pagina,
    ler_conjunto,
    ler_frases_marca,
    ler_pagina_extraida,
    main,
    resumo_conjunto,
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


RELEVANTE = Trecho(texto="Text with “Alpha” Beta here.", id_pagina="p", ancora="a")
OUTRO = Trecho(texto="other", id_pagina="q", ancora="b")

CONJUNTO = ConjuntoAvaliacao(
    gabaritos=[
        Gabarito(id_regra="R1", frase_marca='"alpha" beta', id_pagina="p", ancora="a"),
        Gabarito(id_regra="R2", frase_marca="gamma", id_pagina="p", ancora="c"),
    ],
    consultas=[
        Consulta(id="REGRA/R1", tipo="regra", id_regra="R1", texto="q1"),
        Consulta(id="P1/R1/1", tipo="achado", projeto="P1", id_regra="R1", objeto="T", texto="q2"),
        Consulta(id="REGRA/R2", tipo="regra", id_regra="R2", texto="q3"),
    ],
)

RESPOSTAS = {"q1": [RELEVANTE, OUTRO, OUTRO], "q2": [OUTRO, OUTRO, RELEVANTE], "q3": []}


def _buscar(texto, k):
    return RESPOSTAS[texto][:k]


def test_metricas_micro_contadas_a_mao():
    micro = avaliar(_buscar, CONJUNTO).micro
    assert micro.consultas == 3
    assert micro.acerto[1] == pytest.approx(1 / 3)
    assert micro.acerto[3] == pytest.approx(2 / 3)
    assert micro.mrr == pytest.approx(4 / 9)
    assert micro.precisao[3] == pytest.approx(2 / 9)


def test_macro_e_a_media_das_regras_e_difere_da_micro():
    relatorio = avaliar(_buscar, CONJUNTO)
    assert relatorio.por_regra["R1"].acerto[1] == pytest.approx(1 / 2)
    assert relatorio.por_regra["R1"].mrr == pytest.approx(2 / 3)
    assert relatorio.por_regra["R2"].acerto[10] == 0
    assert relatorio.macro.acerto[1] == pytest.approx(1 / 4)
    assert relatorio.macro.acerto[3] == pytest.approx(1 / 2)
    assert relatorio.macro.mrr == pytest.approx(1 / 3)
    assert relatorio.macro.mrr != pytest.approx(relatorio.micro.mrr)


def test_corte_por_tipo():
    por_tipo = avaliar(_buscar, CONJUNTO).por_tipo
    assert por_tipo["regra"].consultas == 2 and por_tipo["regra"].acerto[1] == pytest.approx(1 / 2)
    assert por_tipo["achado"].acerto[1] == 0 and por_tipo["achado"].acerto[3] == 1


def test_erros_listam_posicao_e_primeiro_devolvido():
    erros = avaliar(_buscar, CONJUNTO).erros
    assert [(e.id, e.posicao, e.primeiro_devolvido) for e in erros] == [
        ("P1/R1/1", 3, "q#b"),
        ("REGRA/R2", None, None),
    ]


def test_aspas_tipograficas_casam_com_aspas_retas():
    assert avaliar(_buscar, CONJUNTO).resultados[0].posicao == 1


def test_consulta_de_regra_sem_gabarito_falha_antes_de_medir():
    chamadas = []

    def buscar(texto, k):
        chamadas.append(texto)
        return []

    conjunto = CONJUNTO.model_copy(
        update={"consultas": [*CONJUNTO.consultas, Consulta(id="REGRA/R9", tipo="regra", id_regra="R9", texto="q9")]}
    )
    with pytest.raises(ErroDeAvaliacao, match="R9"):
        avaliar(buscar, conjunto)
    assert chamadas == []


def test_recuperador_que_devolve_mais_que_k_falha():
    with pytest.raises(ErroDeAvaliacao, match="REGRA/R1.*11"):
        avaliar(lambda texto, k: [OUTRO] * (K_MAX + 1), CONJUNTO)


def test_conjunto_sem_consultas_falha():
    with pytest.raises(ErroDeAvaliacao, match="nenhuma consulta"):
        avaliar(_buscar, CONJUNTO.model_copy(update={"consultas": []}))


def test_relatorio_formatado():
    texto = formatar_relatorio(avaliar(_buscar, CONJUNTO))
    assert "Macro por regra (decide)" in texto
    assert "MRR@10 0.333" in texto
    assert "Micro (3 consultas)" in texto
    assert "P1/R1/1: primeiro acerto na posição 3" in texto
    assert "REGRA/R2: não apareceu" in texto
    assert "Precision@K" in texto


def _projetos(tmp_path, codigos):
    for codigo in codigos:
        (tmp_path / f"{codigo}_Projeto {codigo}").mkdir()
    return tmp_path


def test_achados_dos_projetos_roda_os_sete_em_ordem(tmp_path):
    vistos = []

    def auditar(caminho):
        vistos.append(caminho.name)
        return ResultadoRegras(achados=[_achado("MOD-003", caminho.name)], regras_executadas=9)

    achados = achados_dos_projetos(_projetos(tmp_path, [f"P{i}" for i in range(1, 9)]), auditar)
    assert list(achados) == ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    assert vistos == [f"P{i}_Projeto P{i}" for i in range(1, 8)]


def test_projeto_ausente_falha_nomeando_o_projeto(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="P4"):
        achados_dos_projetos(_projetos(tmp_path, ["P1", "P2", "P3"]), lambda c: ResultadoRegras())


def test_regra_com_falha_num_projeto_para_o_gerador(tmp_path):
    def auditar(caminho):
        return ResultadoRegras(regras_com_falha=[FalhaDeRegra(id_regra="DAX-001", erro="boom")])

    with pytest.raises(ErroDeAvaliacao, match="P1.*DAX-001"):
        achados_dos_projetos(_projetos(tmp_path, [f"P{i}" for i in range(1, 8)]), auditar)


def test_pagina_extraida_ausente_indica_coleta_e_extracao(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="rag.coleta.*rag.extracao"):
        ler_pagina_extraida(STAR, tmp_path)


def test_resumo_conta_consultas_por_tipo_e_por_regra():
    texto = resumo_conjunto(_gerar({"P1": [_achado("MOD-006", "Product")]}))
    assert "Consultas: 3 (2 por regra, 1 por achado)" in texto
    assert "MOD-006 -> learn:power-bi/guidance/star-schema#snowflake-dimensions" in texto
    assert "MOD-006: 2 consulta(s)" in texto


def test_main_sem_dados_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_avaliacao, "PASTA_PBIP", tmp_path / "nao-existe")
    assert main(["gerar"]) == 1
    assert "P1" in capsys.readouterr().err


def test_resumo_imprime_no_console_padrao_do_windows():
    resumo_conjunto(_gerar({"P1": [_achado("MOD-006", "Product")]})).encode("cp1252")
