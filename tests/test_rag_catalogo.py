"""Montagem do catálogo de fontes.

Os retratos dos testes são feitos à mão e pequenos; os reais, com 1.420
páginas, são exercitados em `test_rag_dados_reais.py`.
"""

import json
import re
from datetime import date

import pytest
import yaml

from rag import catalogo
from rag.catalogo import (
    CABECALHO_YAML,
    LICENCA_LEARN,
    LICENCA_SQLBI,
    ErroDeCatalogo,
    Fonte,
    LeituraSqlbi,
    atualizar,
    como_yaml,
    escrever_yaml,
    gerar,
    ler_leituras_sqlbi,
    ler_observacoes,
    ler_retratos,
    main,
    montar_catalogo,
    resumo,
)
from rag.tocs import SECOES, ItemToc, Retrato, caminho_do_retrato, serializar_retrato
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


LEITURA = LeituraSqlbi(
    url="https://www.sqlbi.com/articles/mark-as-date-table/",
    titulo="Mark as Date table",
    regras=["MOD-005"],
    verificado_em=HOJE,
)
ANCORAS = {"MOD-005": L + "power-bi/transform-model/desktop-date-tables"}
EN_ANCORA = {"power-bi/transform-model": [("desktop-date-tables", "Date tables")]}


def test_leitura_do_sqlbi_vira_referencia_nao_indexada():
    resultado = montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA])
    assert por_id(resultado)["sqlbi:mark-as-date-table"] == Fonte(
        id="sqlbi:mark-as-date-table",
        url="https://www.sqlbi.com/articles/mark-as-date-table/",
        url_pt_br=None,
        titulo="Mark as Date table",
        organizacao="SQLBI",
        data_acesso="2026-10-09",
        licenca=LICENCA_SQLBI,
        origem=["curadoria:sqlbi"],
        indexar=False,
        regras=["MOD-005"],
        observacao=None,
    )


def test_learn_e_sqlbi_ficam_ordenados_juntos_por_id():
    resultado = montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA])
    assert [f.id for f in resultado.fontes] == [
        "learn:power-bi/transform-model/desktop-date-tables",
        "sqlbi:mark-as-date-table",
    ]


@pytest.mark.parametrize(
    "mudanca, trecho",
    [
        ({"url": "https://sqlbi.com/articles/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "https://www.sqlbi.com/blog/marco/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "http://www.sqlbi.com/articles/x/"}, "https://www.sqlbi.com/articles/"),
        ({"url": "https://www.sqlbi.com/articles/"}, "https://www.sqlbi.com/articles/"),
        ({"regras": []}, "sem regra"),
        ({"regras": ["XYZ-001"]}, "XYZ-001"),
    ],
)
def test_leitura_invalida_falha_nomeando_a_entrada(mudanca, trecho):
    leitura = LEITURA.model_copy(update=mudanca)
    with pytest.raises(ErroDeCatalogo, match=re.escape(trecho)):
        montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[leitura])


def test_leitura_repetida_falha():
    sem_barra = LEITURA.model_copy(
        update={"url": "https://www.sqlbi.com/articles/mark-as-date-table"}
    )
    with pytest.raises(ErroDeCatalogo, match="repetida"):
        montar(en=EN_ANCORA, ancoras=ANCORAS, leituras=[LEITURA, sem_barra])


def test_nota_pode_ser_dada_a_uma_leitura_do_sqlbi():
    resultado = montar(
        en=EN_ANCORA,
        ancoras=ANCORAS,
        leituras=[LEITURA],
        observacoes={"sqlbi:mark-as-date-table": "Complementa a âncora."},
    )
    assert por_id(resultado)["sqlbi:mark-as-date-table"].observacao == "Complementa a âncora."


def gravar_retratos(pasta, en=None, pt=None):
    for (idioma, secao), retrato in retratos(en, pt).items():
        caminho = caminho_do_retrato(pasta, idioma, secao)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(serializar_retrato(retrato), encoding="utf-8")


def test_ler_retratos_volta_o_que_foi_gravado(tmp_path):
    gravar_retratos(tmp_path, en={"dax": [("a", "A")]})
    assert ler_retratos(tmp_path) == retratos(en={"dax": [("a", "A")]})


def test_ler_retratos_sem_um_arquivo_falha_nomeando_e_indicando_atualizar(tmp_path):
    gravar_retratos(tmp_path)
    faltando = caminho_do_retrato(tmp_path, "pt-br", "powerquery-m")
    faltando.unlink()
    with pytest.raises(ErroDeCatalogo, match="atualizar") as erro:
        ler_retratos(tmp_path)
    assert "powerquery-m" in str(erro.value)


def test_ler_retratos_com_estrutura_inesperada_falha(tmp_path):
    gravar_retratos(tmp_path)
    caminho_do_retrato(tmp_path, "en-us", "dax").write_text('{"x": 1}', encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="estrutura inesperada"):
        ler_retratos(tmp_path)


@pytest.mark.parametrize("conteudo", [None, "", "# só comentário\n", "# cabeçalho\n{}\n"])
def test_observacoes_ausentes_ou_vazias_sao_vazias(tmp_path, conteudo):
    caminho = tmp_path / "observacoes.yaml"
    if conteudo is not None:
        caminho.write_text(conteudo, encoding="utf-8")
    assert ler_observacoes(caminho) == {}


def test_observacoes_lidas(tmp_path):
    caminho = tmp_path / "observacoes.yaml"
    caminho.write_text("learn:dax/a: Nota sobre a página.\n", encoding="utf-8")
    assert ler_observacoes(caminho) == {"learn:dax/a": "Nota sobre a página."}


def test_observacoes_em_formato_errado_falham(tmp_path):
    caminho = tmp_path / "observacoes.yaml"
    caminho.write_text("- uma lista\n", encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="id -> texto"):
        ler_observacoes(caminho)


@pytest.mark.parametrize("conteudo", [None, "", "# só comentário\n", "[]\n"])
def test_leituras_ausentes_ou_vazias_sao_vazias(tmp_path, conteudo):
    caminho = tmp_path / "leituras.yaml"
    if conteudo is not None:
        caminho.write_text(conteudo, encoding="utf-8")
    assert ler_leituras_sqlbi(caminho) == []


def test_leituras_lidas(tmp_path):
    caminho = tmp_path / "leituras.yaml"
    caminho.write_text(
        "- url: https://www.sqlbi.com/articles/mark-as-date-table/\n"
        "  titulo: Mark as Date table\n"
        "  regras: [MOD-005]\n"
        "  verificado_em: '2026-10-09'\n",
        encoding="utf-8",
    )
    assert ler_leituras_sqlbi(caminho) == [LEITURA]


def test_leitura_sem_campo_obrigatorio_falha(tmp_path):
    caminho = tmp_path / "leituras.yaml"
    caminho.write_text("- url: https://www.sqlbi.com/articles/x/\n", encoding="utf-8")
    with pytest.raises(ErroDeCatalogo, match="entrada inválida"):
        ler_leituras_sqlbi(caminho)


def test_yaml_e_deterministico_com_lf_e_unicode(tmp_path):
    resultado = montar(en={"dax": [("a", "Ação")]})
    um, outro = tmp_path / "um.yaml", tmp_path / "outro.yaml"
    escrever_yaml(resultado.fontes, um)
    escrever_yaml(resultado.fontes, outro)
    assert um.read_bytes() == outro.read_bytes()
    assert b"\r\n" not in um.read_bytes()
    assert "Ação" in um.read_text(encoding="utf-8")


def test_yaml_comeca_avisando_que_e_gerado_e_volta_igual():
    resultado = montar(en={"dax": [("a", "A")]}, leituras=[])
    texto = como_yaml(resultado.fontes)
    assert texto.startswith(CABECALHO_YAML)
    dados = yaml.safe_load(texto)
    assert [Fonte.model_validate(d) for d in dados] == resultado.fontes
    assert list(dados[0]) == list(Fonte.model_fields)


def test_gerar_escreve_o_catalogo(tmp_path):
    gravar_retratos(tmp_path / "tocs", en={"dax": [("a", "A")]})
    destino = tmp_path / "sources.yaml"
    resultado = gerar(
        pasta_tocs=tmp_path / "tocs",
        destino=destino,
        observacoes=tmp_path / "nao-existe.yaml",
        leituras=tmp_path / "nao-existe.yaml",
        ancoras={},
    )
    assert destino.read_text(encoding="utf-8") == como_yaml(resultado.fontes)
    assert [f.id for f in resultado.fontes] == ["learn:dax/a"]


def test_atualizar_baixa_confere_o_sqlbi_e_gera(tmp_path):
    chamadas = []

    def buscar(url):
        chamadas.append(url)
        return json.dumps({"items": [{"href": "pagina", "toc_title": "Página"}]}).encode()

    leituras = tmp_path / "leituras.yaml"
    leituras.write_text(
        "- url: https://www.sqlbi.com/articles/x/\n  titulo: X\n  regras: [R-1]\n"
        "  verificado_em: '2026-10-09'\n",
        encoding="utf-8",
    )
    resultado = atualizar(
        buscar=buscar,
        hoje=HOJE,
        pasta_tocs=tmp_path / "tocs",
        pasta_bruta=tmp_path / "bruto",
        destino=tmp_path / "sources.yaml",
        observacoes=tmp_path / "nao-existe.yaml",
        leituras=leituras,
        ancoras={"R-1": L + "dax/pagina"},
    )
    assert "https://www.sqlbi.com/articles/x/" in chamadas
    assert {f.id for f in resultado.fontes} >= {"learn:dax/pagina", "sqlbi:x"}
    assert (tmp_path / "sources.yaml").is_file()


def test_resumo_traz_contagens_exclusoes_e_ancoras():
    ancoras = {
        "DAX-001": L + "dax/a",
        "MOD-005": L + "power-bi/transform-model/desktop-date-tables",
    }
    resultado = montar(
        en={
            "dax": [("a", "A"), ("https://aka.ms/x", "Fora")],
            "power-bi/transform-model": [("desktop-date-tables", "Date tables")],
        },
        ancoras=ancoras,
        leituras=[LEITURA],
    )
    texto = resumo(resultado, ancoras)
    # 2 do Learn (dax/a e a âncora de MOD-005), 1 do SQLBI, 1 link fora do Learn;
    # `pt` replica `en`, então as duas do Learn têm url_pt_br.
    assert "2 indexadas" in texto
    assert "1 só referência" in texto
    assert "toc:dax: 1" in texto
    assert "regra: 2" in texto
    assert "curadoria:sqlbi: 1" in texto
    assert f"{FORA_DO_LEARN}: 1" in texto
    assert "com url_pt_br: 2 de 2" in texto
    assert "DAX-001 -> learn:dax/a" in texto
    assert "MOD-005 -> learn:power-bi/transform-model/desktop-date-tables" in texto


def test_main_sem_retratos_sai_com_erro_indicando_atualizar(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catalogo, "PASTA_TOCS", tmp_path / "vazia")
    monkeypatch.setattr(catalogo, "ARQUIVO_FONTES", tmp_path / "sources.yaml")
    assert main(["gerar"]) == 1
    assert "atualizar" in capsys.readouterr().err
    assert not (tmp_path / "sources.yaml").exists()


def test_atualizar_valida_o_sqlbi_antes_de_qualquer_rede_ou_gravacao(tmp_path):
    chamadas = []

    def buscar(url):
        chamadas.append(url)
        return b'{"items": []}'

    leituras = tmp_path / "leituras.yaml"
    leituras.write_text(
        "- url: https://outro-host.example/articles/x/\n  titulo: X\n  regras: [R-1]\n"
        "  verificado_em: '2026-10-09'\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeCatalogo, match="www.sqlbi.com/articles"):
        atualizar(
            buscar=buscar,
            hoje=HOJE,
            pasta_tocs=tmp_path / "tocs",
            pasta_bruta=tmp_path / "bruto",
            destino=tmp_path / "sources.yaml",
            observacoes=tmp_path / "nao-existe.yaml",
            leituras=leituras,
            ancoras={"R-1": L + "dax/pagina"},
        )
    assert chamadas == []
    assert not (tmp_path / "tocs").exists()
