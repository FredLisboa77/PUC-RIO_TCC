"""Validação da resposta do LLM: a primeira falha decide o motivo do descarte."""

import json

import pytest

from core.analise.validacao import validar


def _json(**campos) -> str:
    resposta = {"explicacao": "Tabelas automáticas aumentam o modelo.", "recomendacao": "Desative a opção.", "citacoes": [1]}
    resposta.update(campos)
    return json.dumps(resposta, ensure_ascii=False)


def test_resposta_valida_e_aceita():
    geracao, motivo = validar(_json(citacoes=[1, 3]), 3)
    assert motivo is None
    assert geracao.citacoes == [1, 3]


def test_campos_sao_aparados():
    geracao, _ = validar(_json(explicacao="  x  ", recomendacao=" y "), 1)
    assert (geracao.explicacao, geracao.recomendacao) == ("x", "y")


@pytest.mark.parametrize(
    "texto",
    [
        "não é json",
        "[1, 2]",
        json.dumps({"explicacao": "x", "recomendacao": "y"}),
        _json(citacoes="1"),
        _json(explicacao=3),
    ],
)
def test_json_invalido(texto):
    assert validar(texto, 3) == (None, "json_invalido")


@pytest.mark.parametrize("citacoes", [[True], ["1"], [1.0]])
def test_citacao_que_nao_e_inteiro_e_json_invalido(citacoes):
    # `True` é `int` em Python; sem checar o tipo exato, passaria por citação 1.
    assert validar(_json(citacoes=citacoes), 3) == (None, "json_invalido")


@pytest.mark.parametrize("campo", ["explicacao", "recomendacao"])
def test_campo_vazio(campo):
    assert validar(_json(**{campo: "   "}), 3) == (None, "campo_vazio")


@pytest.mark.parametrize("citacoes", [[], [1, 2, 3, 4], [2, 2]])
def test_citacoes_fora_do_limite(citacoes):
    assert validar(_json(citacoes=citacoes), 5) == (None, "citacoes_fora_do_limite")


@pytest.mark.parametrize("citacoes", [[0], [4], [1, -1]])
def test_citacao_inexistente(citacoes):
    assert validar(_json(citacoes=citacoes), 3) == (None, "citacao_inexistente")
