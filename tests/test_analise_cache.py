"""Cache das respostas do LLM: acerto, chave, falhas e rótulo."""

import json

import pytest

from core.analise.cache import ClienteComCache, chave_de
from core.analise.llm import ContextoExcedido, ErroDeLLM
from fabricas_analise import LLMFalso

MENSAGENS = [{"role": "user", "content": "explique"}]
ESQUEMA = {"type": "object"}


def test_segunda_chamada_vem_do_cache_sem_chamar_o_llm(tmp_path):
    llm = LLMFalso('{"a": 1}')
    cliente = ClienteComCache(llm, tmp_path)
    primeira = cliente.gerar(MENSAGENS, ESQUEMA)
    segunda = cliente.gerar(MENSAGENS, ESQUEMA)
    assert (primeira.texto, primeira.do_cache) == ('{"a": 1}', False)
    assert (segunda.texto, segunda.do_cache) == ('{"a": 1}', True)
    assert len(llm.chamadas) == 1
    assert cliente.nome == "llm-falso"


def test_chave_muda_com_mensagens_esquema_e_modelo():
    """Review Focus 3: índice reconstruído muda o contexto, e a chave muda junto."""
    base = chave_de("m", MENSAGENS, ESQUEMA)
    assert base == chave_de("m", [dict(MENSAGENS[0])], dict(ESQUEMA))
    assert base != chave_de("m", [{"role": "user", "content": "explique."}], ESQUEMA)
    assert base != chave_de("m", MENSAGENS, {"type": "array"})
    assert base != chave_de("outro", MENSAGENS, ESQUEMA)


@pytest.mark.parametrize("falha", [ErroDeLLM("caiu"), ContextoExcedido("longo")])
def test_falha_do_llm_passa_adiante_e_nao_e_guardada(tmp_path, falha):
    cliente = ClienteComCache(LLMFalso(falha), tmp_path)
    with pytest.raises(ErroDeLLM):
        cliente.gerar(MENSAGENS, ESQUEMA)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("conteudo", ["{ quebrado", json.dumps({"outro": 1}), json.dumps({"texto": 5})])
def test_arquivo_ilegivel_ou_de_outro_formato_e_tratado_como_ausente(tmp_path, conteudo):
    """Review Focus 2."""
    (tmp_path / f"{chave_de('llm-falso', MENSAGENS, ESQUEMA)}.json").write_text(conteudo, encoding="utf-8")
    llm = LLMFalso('{"a": 2}')
    resposta = ClienteComCache(llm, tmp_path).gerar(MENSAGENS, ESQUEMA)
    assert (resposta.texto, resposta.do_cache, len(llm.chamadas)) == ('{"a": 2}', False, 1)
    assert ClienteComCache(LLMFalso(), tmp_path).gerar(MENSAGENS, ESQUEMA).texto == '{"a": 2}'


def test_pasta_sem_escrita_usa_a_resposta_e_nao_grava(tmp_path):
    arquivo_no_lugar_da_pasta = tmp_path / "cache"
    arquivo_no_lugar_da_pasta.write_text("x", encoding="utf-8")
    resposta = ClienteComCache(LLMFalso('{"a": 3}'), arquivo_no_lugar_da_pasta).gerar(MENSAGENS, ESQUEMA)
    assert resposta.texto == '{"a": 3}'


def test_aquecer_vai_sempre_ao_llm_real(tmp_path):
    llm = LLMFalso(falha_no_aquecimento=True)
    with pytest.raises(ErroDeLLM):
        ClienteComCache(llm, tmp_path).aquecer()
    assert llm.aquecimentos == 1
