"""Enriquecimento de um achado: contexto → LLM → validação → fidelidade."""

from core.analise.enriquecimento import enriquecer
from core.analise.llm import ContextoExcedido, ErroDeLLM
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta, resposta


def _enriquecer(llm):
    return enriquecer(achado(), meta(), base=base_padrao(), gabarito=gabarito(), llm=llm)


def test_resposta_valida_vira_achado_gerado():
    r = _enriquecer(LLMFalso(resposta(citacoes=(1, 2))))
    assert r.situacao == "gerado"
    assert r.cita_ancora is True
    assert r.fidelidade.divergencias == []
    assert (r.modelo, r.segundos) == ("llm-falso", 0.5)
    assert r.contexto[0].origem == "ancora"


def test_citar_so_complementar_nao_cita_a_ancora():
    r = _enriquecer(LLMFalso(resposta(citacoes=(2,))))
    assert (r.situacao, r.cita_ancora) == ("gerado", False)


def test_resposta_invalida_cai_na_recomendacao_padrao():
    r = _enriquecer(LLMFalso(resposta(citacoes=(9,))))
    assert (r.situacao, r.motivo_descarte) == ("sem_fundamentacao", "citacao_inexistente")
    assert r.recomendacao_final(meta()) == meta().recomendacao_padrao
    assert r.segundos == 0.5


def test_erro_do_llm_vira_erro_llm_e_preserva_o_contexto():
    r = _enriquecer(LLMFalso(ErroDeLLM("timeout")))
    assert (r.situacao, r.motivo_descarte, r.segundos) == ("sem_fundamentacao", "erro_llm", None)
    assert r.contexto[0].origem == "ancora"


def test_divergencia_de_fidelidade_nao_descarta():
    r = _enriquecer(LLMFalso(resposta(explicacao="O modelo tem duas tabelas automáticas.")))
    assert r.situacao == "gerado"
    assert r.fidelidade.divergencias == ["número 2 ausente do achado e dos trechos"]


def test_prompt_enviado_traz_a_ancora_como_trecho_1():
    llm = LLMFalso()
    _enriquecer(llm)
    assert "[1] T › Seção\nYou should disable the auto date time option" in llm.chamadas[0][1]["content"]


def test_tokens_do_prompt_vao_para_o_achado_gerado_ou_descartado():
    assert _enriquecer(LLMFalso(tokens_prompt=1500)).tokens_prompt == 1500
    assert _enriquecer(LLMFalso(resposta(citacoes=(9,)), tokens_prompt=1500)).tokens_prompt == 1500


def test_contexto_excedido_tira_o_ultimo_complementar_e_tenta_de_novo():
    llm = LLMFalso(ContextoExcedido("7231 tokens"))
    r = _enriquecer(llm)
    assert r.situacao == "gerado"
    assert [t.origem for t in r.contexto] == ["ancora"]
    assert r.reducoes_de_contexto == 1
    assert len(llm.chamadas) == 2
    assert "[2]" not in llm.chamadas[1][1]["content"]


def test_contexto_excedido_ate_so_com_a_ancora_descarta_o_achado():
    llm = LLMFalso(ContextoExcedido("a"), ContextoExcedido("b"))
    r = _enriquecer(llm)
    assert (r.situacao, r.motivo_descarte) == ("sem_fundamentacao", "contexto_excedido")
    assert len(llm.chamadas) == 2
