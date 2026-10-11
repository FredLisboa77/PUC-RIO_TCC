"""A consulta que o pipeline manda ao índice: termos da regra, em inglês, mais
o contexto do achado. A mesma função alimenta o conjunto de avaliação."""

import pytest

from core.rules.base import Achado, Evidencia
from core.rules.todas import REGISTRO
from rag.consulta import TIPOS_EM_INGLES, montar_consulta

METAS = {m.id: m for m in REGISTRO.metas()}


def _achado(id_regra, tipo, objeto):
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(tipo_objeto=tipo, objeto=objeto),
        mensagem="mensagem em português que não entra na consulta",
    )


def test_consulta_por_regra_une_os_termos():
    assert montar_consulta(METAS["MOD-003"]) == (
        "star schema model relationships; dimension table fact table; "
        "table not related; filter propagation"
    )


def test_consulta_por_achado_acrescenta_tipo_e_objeto():
    achado = _achado("MOD-003", "tabela", "Date Role")
    assert montar_consulta(METAS["MOD-003"], achado) == (
        "star schema model relationships; dimension table fact table; "
        "table not related; filter propagation | table Date Role"
    )


@pytest.mark.parametrize(
    "objeto",
    ["Sales[Avg $/Unit LY]", "Backorder Percentage[Backorder %]", "Sales Order[K] → Sales[K]"],
)
def test_nome_do_objeto_e_preservado_como_esta(objeto):
    consulta = montar_consulta(METAS["DAX-001"], _achado("DAX-001", "medida", objeto))
    assert consulta.endswith(f" | measure {objeto}")


def test_mensagem_e_trecho_ficam_de_fora():
    achado = Achado(
        id_regra="DAX-001",
        evidencia=Evidencia(tipo_objeto="medida", objeto="T[M]", trecho="DIVIDE([A], [B])"),
        mensagem="divide com o operador",
    )
    consulta = montar_consulta(METAS["DAX-001"], achado)
    assert "operador" not in consulta and "[A]" not in consulta


def test_todo_tipo_de_objeto_tem_traducao():
    assert TIPOS_EM_INGLES == {
        "tabela": "table",
        "coluna": "column",
        "medida": "measure",
        "relacionamento": "relationship",
        "particao": "partition",
        "modelo": "model",
    }


def test_mesma_entrada_mesma_saida():
    achado = _achado("PERF-003", "coluna", "Sales[Unit Price]")
    assert montar_consulta(METAS["PERF-003"], achado) == montar_consulta(METAS["PERF-003"], achado)
