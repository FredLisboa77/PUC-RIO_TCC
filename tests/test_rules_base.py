"""O contrato entre as regras e o resto do pipeline.

A validação aqui não é cerimônia: a ADR-003 exige que todo achado seja
fundamentado num trecho de documentação recuperado, e uma regra sem URL
canónica, sem termos de consulta ou sem recomendação padrão não tem como
cumprir isso. Por isso o `RegraMeta` se recusa a existir sem eles.
"""

import pytest
from pydantic import ValidationError

from core.rules.base import ORDEM_SEVERIDADE, Achado, Evidencia, RegraMeta

COMPLETA = {
    "id": "MOD-999",
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "severidade": "alta",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema", "dimension table"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil ao leitor.",
}


def test_regra_meta_aceita_metadados_completos():
    meta = RegraMeta(**COMPLETA)

    assert meta.id == "MOD-999"
    assert meta.termos_consulta == ("star schema", "dimension table")
    assert meta.nota_de_verificacao is None


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("url_canonica", ""),
        ("url_canonica", "ver documentacao da Microsoft"),
        ("termos_consulta", []),
        ("recomendacao_padrao", ""),
        ("recomendacao_padrao", "   "),
        ("recomendacao_padrao", "Evite isso."),
        ("severidade", "critica"),
        ("categoria", "modelo"),
    ],
)
def test_regra_meta_recusa_metadado_que_nao_sustenta_o_achado(campo, valor):
    campos = COMPLETA | {campo: valor}

    with pytest.raises(ValidationError):
        RegraMeta(**campos)


def test_achado_carrega_so_a_ocorrencia():
    """Nada de título, severidade ou URL copiados: o catálogo é fonte única."""
    achado = Achado(
        id_regra="MOD-999",
        evidencia=Evidencia(tipo_objeto="tabela", objeto="DimProduct"),
        mensagem="A tabela 'DimProduct' tem o problema X.",
    )

    assert set(achado.model_dump()) == {"id_regra", "evidencia", "mensagem"}
    assert achado.evidencia.detalhe == {}
    assert achado.evidencia.tabela is None


def test_a_ordem_de_severidade_vai_da_alta_para_a_baixa():
    assert ORDEM_SEVERIDADE["alta"] < ORDEM_SEVERIDADE["media"] < ORDEM_SEVERIDADE["baixa"]
