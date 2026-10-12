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
