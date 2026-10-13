"""Tradução de um trecho citado: só de exibição, nunca gravada."""

import json

import pytest

from core.analise.llm import ContextoExcedido
from core.analise.traducao import ESQUEMA_TRADUCAO, ErroDeTraducao, traduzir_trecho
from fabricas_analise import LLMFalso


def test_traduz_e_manda_o_texto_e_o_esquema():
    llm = LLMFalso(json.dumps({"traducao": "  Desative a opção Auto date/time.  "}, ensure_ascii=False))
    assert traduzir_trecho("Disable the Auto date/time option.", llm) == "Desative a opção Auto date/time."
    mensagens = llm.chamadas[0]
    assert mensagens[0]["role"] == "system" and "DAX" in mensagens[0]["content"]
    assert mensagens[1] == {"role": "user", "content": "Disable the Auto date/time option."}


def test_esquema_pede_um_campo_so():
    assert ESQUEMA_TRADUCAO["required"] == ["traducao"]


@pytest.mark.parametrize("texto", ["não é json", "[1, 2]", json.dumps({"traducao": "   "}), json.dumps({"outro": "x"})])
def test_resposta_ruim_vira_erro_de_traducao(texto):
    with pytest.raises(ErroDeTraducao):
        traduzir_trecho("x", LLMFalso(texto))


def test_erro_do_llm_passa_adiante():
    with pytest.raises(ContextoExcedido):
        traduzir_trecho("x", LLMFalso(ContextoExcedido("longo demais")))
