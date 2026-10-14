"""Contrato do achado enriquecido: coerência entre situação e campos."""

import pytest
from pydantic import ValidationError

from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from fabricas_analise import achado, contexto, meta


def _gerado(**extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(),
        contexto=contexto(2),
        geracao=Geracao(explicacao="e", recomendacao="Use DIVIDE.", citacoes=[1]),
        situacao="gerado",
        cita_ancora=True,
        fidelidade=Fidelidade(),
        modelo="m",
        segundos=1.0,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _descartado(**extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(), contexto=contexto(1), situacao="sem_fundamentacao",
        motivo_descarte="json_invalido", modelo="m",
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def test_gerado_coerente_e_aceito():
    assert _gerado().situacao == "gerado"


def test_gerado_sem_geracao_e_recusado():
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(geracao=None)


def test_gerado_com_motivo_de_descarte_e_recusado():
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(motivo_descarte="erro_llm")


def test_sem_fundamentacao_precisa_de_motivo():
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(motivo_descarte=None)


def test_sem_fundamentacao_nao_pode_ter_fidelidade_nem_cita_ancora():
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(fidelidade=Fidelidade())
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(cita_ancora=False)


def test_recomendacao_final_usa_a_do_llm_quando_gerado():
    assert _gerado().recomendacao_final(meta()) == "Use DIVIDE."


def test_recomendacao_final_cai_na_padrao_quando_descartado():
    assert _descartado().recomendacao_final(meta()) == meta().recomendacao_padrao


def test_recomendacao_final_recusa_meta_de_outra_regra():
    with pytest.raises(ValueError, match="MOD-002"):
        _gerado().recomendacao_final(meta("MOD-002"))


def test_so_regras_coerente_e_aceito():
    item = AchadoEnriquecido.so_regras(achado())
    assert (item.situacao, item.contexto, item.modelo) == ("so_regras", [], None)


def test_so_regras_nao_pode_ter_contexto_nem_geracao():
    base = dict(achado=achado(), situacao="so_regras", modelo=None)
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(**base, contexto=contexto(1))
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(
            **base, contexto=[], geracao=Geracao(explicacao="e", recomendacao="r", citacoes=[1])
        )
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(**base, contexto=[], segundos=1.0)


def test_so_regras_nao_pode_ter_modelo_e_os_outros_precisam():
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(achado=achado(), contexto=[], situacao="so_regras", modelo="m")
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(modelo=None)
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(modelo=None)


def test_recomendacao_final_em_so_regras_e_a_padrao():
    item = AchadoEnriquecido.so_regras(achado())
    assert item.recomendacao_final(meta()) == meta().recomendacao_padrao


@pytest.mark.parametrize("citacoes", [[99], [], [1, 1]])
def test_gerado_com_citacao_fora_do_contexto_vazia_ou_repetida_e_recusado(citacoes):
    """ADR-003: um JSON de fora não pode trazer explicação sem fonte válida."""
    with pytest.raises(ValidationError, match="citações"):
        _gerado(geracao=Geracao(explicacao="e", recomendacao="Use DIVIDE.", citacoes=citacoes))


def test_do_cache_padrao_e_falso_e_so_regras_nao_pode_ter():
    assert _gerado().do_cache is False
    assert _gerado(do_cache=True).do_cache is True
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(achado=achado(), contexto=[], situacao="so_regras", modelo=None, do_cache=True)
