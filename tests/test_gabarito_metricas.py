"""Métricas do gabarito: contas feitas à mão."""

import pytest

from core.rules.base import Achado, Evidencia
from gabarito.candidatos import ErroDeGabarito
from gabarito.metricas import Matriz, medir, taxas
from gabarito.planilha import LinhaGabarito


def _linha(id_regra, projeto, objeto, veredito):
    return LinhaGabarito(id=f"{id_regra}|{projeto}|{objeto}", projeto=projeto, id_regra=id_regra, objeto=objeto,
                         veredito=veredito, justificativa="j" if veredito != "não viola" else None)


def _achado(id_regra, objeto):
    return Achado(id_regra=id_regra, evidencia=Evidencia(tipo_objeto="tabela", objeto=objeto), mensagem="m")


def test_taxas_principal_piso_e_teto():
    m = Matriz(vp=6, fp=2, fn=1, vn=10, ind_marcados=2, ind_nao_marcados=1)
    t = taxas(m)
    assert t["precisao"] == {"principal": 6 / 8, "piso": 6 / 10, "teto": 8 / 10}
    assert t["recall"] == {"principal": 6 / 7, "piso": 6 / 8, "teto": 8 / 9}


def test_sem_divisor_e_none_nunca_zero_nem_um():
    t = taxas(Matriz())
    assert t["precisao"] == {"principal": None, "piso": None, "teto": None}
    assert t["recall"] == {"principal": None, "piso": None, "teto": None}


def _cenario():
    gabarito = [
        _linha("MOD-003", "P1", "A", "viola"),          # marcado → VP
        _linha("MOD-003", "P1", "B", "não viola"),      # marcado → FP
        _linha("MOD-003", "P2", "C", "viola"),          # não marcado → FN
        _linha("MOD-003", "P2", "D", "não viola"),      # não marcado → VN
        _linha("PERF-003", "P1", "T[x]", "indeterminado"),  # marcado → ind
        _linha("PERF-003", "P1", "T[y]", "viola"),      # marcado → VP
        _linha("MOD-001", "P1", "Z", "não viola"),      # não marcado → VN
    ]
    achados = {
        "P1": [_achado("MOD-003", "A"), _achado("MOD-003", "B"), _achado("PERF-003", "T[x]"), _achado("PERF-003", "T[y]")],
        "P2": [],
    }
    return gabarito, achados


def test_matriz_por_regra():
    r = medir(*_cenario())
    assert r.por_regra["MOD-003"].matriz == Matriz(vp=1, fp=1, fn=1, vn=1)
    assert r.por_regra["PERF-003"].matriz == Matriz(vp=1, ind_marcados=1)


def test_regra_sem_achado_nem_violacao_fica_none():
    r = medir(*_cenario())
    mod001 = r.por_regra["MOD-001"]
    assert mod001.taxas["precisao"]["principal"] is None
    assert mod001.taxas["recall"]["principal"] is None


def test_micro_soma_e_macro_ignora_none():
    r = medir(*_cenario())
    assert r.total_micro.matriz == Matriz(vp=2, fp=1, fn=1, vn=2, ind_marcados=1)
    assert r.macro["precisao"] == pytest.approx((0.5 + 1.0) / 2)


def test_por_categoria():
    r = medir(*_cenario())
    assert r.por_categoria["modelagem"].matriz == Matriz(vp=1, fp=1, fn=1, vn=2)
    assert r.por_categoria["performance"].matriz == Matriz(vp=1, ind_marcados=1)


def test_gatilhos_r03_e_r12():
    r = medir(*_cenario())
    assert r.r03 == ["MOD-003"]
    assert r.r12 == {"vp": 2, "vp_sem_perf003": 1, "gatilho": 40}


def test_divergencias_listam_fp_e_fn_com_justificativa():
    r = medir(*_cenario())
    assert [(d.tipo, d.id) for d in r.divergencias] == [("FP", "MOD-003|P1|B"), ("FN", "MOD-003|P2|C")]


def test_achado_sem_linha_no_gabarito_aborta():
    gabarito, achados = _cenario()
    achados["P2"].append(_achado("MOD-003", "Sumida"))
    with pytest.raises(ErroDeGabarito, match="MOD-003\\|P2\\|Sumida"):
        medir(gabarito, achados)


def test_gabarito_com_veredito_vazio_aborta():
    gabarito, achados = _cenario()
    gabarito[0] = _linha("MOD-003", "P1", "A", None)
    with pytest.raises(ErroDeGabarito, match="sem veredito"):
        medir(gabarito, achados)


def test_macro_por_categoria_media_das_regras_da_categoria():
    r = medir(*_cenario())
    assert r.macro_por_categoria["modelagem"] == {"precisao": 0.5, "recall": 0.5}
    assert r.macro_por_categoria["performance"] == {"precisao": 1.0, "recall": 1.0}
