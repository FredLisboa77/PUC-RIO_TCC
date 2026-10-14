"""Wilson e kappa contra valores de referência."""

import pytest

from avaliacao_geracao.estatistica import kappa, wilson


@pytest.mark.parametrize("sucessos,total,esperado", [
    (52, 56, (0.8302, 0.9719)),
    (46, 52, (0.7703, 0.9460)),
    (0, 10, (0.0, 0.2775)),
    (10, 10, (0.7225, 1.0)),
])
def test_wilson_contra_referencia(sucessos, total, esperado):
    baixo, alto = wilson(sucessos, total)
    assert (round(baixo, 4), round(alto, 4)) == esperado


def test_wilson_sem_denominador_e_none():
    assert wilson(0, 0) is None


def test_kappa_exemplo_classico():
    """20 ambos sim, 5 e 10 em desacordo, 15 ambos não: concordância 0,7, acaso 0,5."""
    assert kappa(20, 5, 10, 15) == pytest.approx(0.4)


def test_kappa_concordancia_perfeita_e_degenerada():
    assert kappa(10, 0, 0, 5) == pytest.approx(1.0)
    assert kappa(10, 0, 0, 0) is None  # Review Focus 5: acaso = 1
    assert kappa(0, 0, 0, 0) is None
