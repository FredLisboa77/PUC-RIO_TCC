"""O catálogo versionado, conferido contra os retratos versionados.

Ao contrário dos testes do PBIP real, estes sempre rodam: `rag/tocs/` está no
Git. O primeiro teste pega edição à mão do `sources.yaml` e catálogo
desatualizado em relação aos retratos.
"""

import pytest

from rag.catalogo import (
    ARQUIVO_FONTES,
    ARQUIVO_LEITURAS,
    ARQUIVO_OBSERVACOES,
    PASTA_TOCS,
    ancoras_do_registro,
    como_yaml,
    ler_leituras_sqlbi,
    ler_observacoes,
    ler_retratos,
    montar_catalogo,
)


@pytest.fixture(scope="module")
def resultado():
    return montar_catalogo(
        ler_retratos(PASTA_TOCS),
        ancoras_do_registro(),
        ler_observacoes(ARQUIVO_OBSERVACOES),
        ler_leituras_sqlbi(ARQUIVO_LEITURAS),
    )


def test_sources_yaml_versionado_e_o_que_o_gerador_produz(resultado):
    # Texto, não bytes: com core.autocrlf o checkout no Windows traz CRLF.
    assert ARQUIVO_FONTES.read_text(encoding="utf-8") == como_yaml(resultado.fontes), (
        "rag/sources.yaml desatualizado ou editado à mão — rode `python -m rag.catalogo gerar`"
    )


def test_a_ancora_de_cada_regra_esta_no_catalogo_indexado(resultado):
    ancoras = ancoras_do_registro()
    assert len(ancoras) == 9
    cobertas = {r for f in resultado.fontes if f.indexar for r in f.regras}
    assert cobertas == set(ancoras)


def test_tamanho_do_corpus_indexado(resultado):
    indexadas = [f for f in resultado.fontes if f.indexar]
    assert 1300 <= len(indexadas) <= 1600


def test_todo_o_indexado_e_learn_em_ingles(resultado):
    for fonte in resultado.fontes:
        if fonte.indexar:
            assert fonte.organizacao == "Microsoft", fonte.id
            assert fonte.url.startswith("https://learn.microsoft.com/en-us/"), fonte.id


def test_o_sqlbi_e_so_referencia(resultado):
    sqlbi = [f for f in resultado.fontes if f.organizacao == "SQLBI"]
    assert sqlbi
    assert all(not f.indexar and f.id.startswith("sqlbi:") and f.regras for f in sqlbi)
